"""Search above the sidebar: find a setting on any page by its text, then go there and show it.

The text searched is what the pages show (labels, buttons, check boxes, page names), in the user's language, read
when the search runs, so pages that change their text stay findable. A few English technical words (sddm, kvantum,
gtk, …) also find the app's own words for them, in every language.
"""

import unicodedata

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Pango  # noqa: E402

from ott_i18n import _  # noqa: E402

MAX_RESULTS = 12
MIN_CHARS = 2
_HIGHLIGHT = "search-hit"
_HIGHLIGHT_MS = 2500
_FILE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _synonyms():
    # English terms people know from other tools -> the words this app uses (already translated catalog entries)
    return {
        "gtk": [_("Look")], "theme": [_("Themes"), _("Look"), _("Bar theme")], "icon": [_("Icons")], "cursor": [_("Cursor")],
        "font": [_("Font")], "dark": [_("Look")], "sddm": [_("Look"), _("Themes")], "login": [_("Look"), _("Themes")],
        "preset": [_("Themes")], "rice": [_("Themes")],
        "bar": [_("Bar & windows")], "gaps": [_("Bar & windows")], "border": [_("Bar & windows")],
        "systray": [_("Bar & windows")], "tray": [_("Bar & windows")],
        "variety": [_("Wallpaper")], "background": [_("Wallpaper"), _("Themes")], "feh": [_("Wallpaper")],
        "monitor": [_("Displays")], "screen": [_("Displays")], "resolution": [_("Displays")],
        "xrandr": [_("Displays")], "arandr": [_("Displays")],
        "touchpad": [_("Mouse & touchpad")], "mouse": [_("Mouse & touchpad")], "libinput": [_("Mouse & touchpad")],
        "layout": [_("Keyboard")], "xkb": [_("Keyboard")], "setxkbmap": [_("Keyboard")],
        "azerty": [_("Keyboard")], "qwerty": [_("Keyboard")], "workspace": [_("Keyboard")], "tag": [_("Keyboard")],
        "autostart": [_("Startup apps")], "run.sh": [_("Startup apps")],
        "browser": [_("Default apps")], "terminal": [_("Default apps")], "file manager": [_("Default apps")],
        "keybind": [_("Keys")], "shortcut": [_("Keys")], "sxhkd": [_("Keys")],
        "update": [_("Update & News")], "news": [_("Update & News")], "kernel": [_("Update & News")],
        "pacman": [_("Update & News")],
    }


def normalize(text):
    """Return text folded for matching: lower case, no accents, single spaces."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.casefold().replace("-", " ").split())


def _is_file_name(text):
    # the Wallpaper page names its pictures: a file name is not a setting
    return " " not in text and text.lower().endswith(_FILE_EXTS)


def _texts(widget):
    # the visible texts of one widget (labels, buttons; a check button's label is its child Label)
    if isinstance(widget, Gtk.Label):
        text = widget.get_text()
        return [] if _is_file_name(text) else [text]
    if isinstance(widget, (Gtk.Button, Gtk.CheckButton)) and not isinstance(widget, Gtk.MenuButton):
        label = widget.get_label() if hasattr(widget, "get_label") else None
        return [label] if label else []
    return []


def _walk(widget):
    child = widget.get_first_child()
    while child is not None:
        if child.get_visible():
            yield child
            yield from _walk(child)
        child = child.get_next_sibling()


def find(pages, query):
    """Return up to MAX_RESULTS matches [(page name, page title, widget or None, text)] for query.

    pages: [(name, title, root widget)]. Best first: page names, then a section heading or row that is exactly the
    word looked for ("sddm" -> the Wallpaper page's Login screen part), then rows starting with it, then the rest.
    """
    q = normalize(query)
    if len(q) < MIN_CHARS:
        return []
    # a synonym counts once the query is a word of it (from 3 letters) or names it: "sdd" and "sddm cursor" find sddm
    syn = [w for key, words in _synonyms().items()
           if (len(q) >= 3 and key.startswith(q)) or key in q.split() for w in words]
    wanted = [q] + [normalize(w) for w in syn]
    scored, seen = [], set()
    for name, title, _root in pages:
        if any(w in normalize(title) for w in wanted):
            scored.append((0, len(scored), (name, title, None, title)))
            seen.add((name, normalize(title)))
    for name, title, root in pages:
        for widget in _walk(root):
            for text in _texts(widget):
                key = (name, normalize(text))
                if not text or key in seen or not any(w in key[1] for w in wanted):
                    continue
                seen.add(key)
                if key[1] in wanted:
                    rank = 1
                elif any(key[1].startswith(w) for w in wanted):
                    rank = 2
                else:
                    rank = 3
                scored.append((rank, len(scored), (name, title, widget, text)))
    return [hit for _rank, _order, hit in sorted(scored)[:MAX_RESULTS]]


def _row_y(scroller, widget):
    # the row's place on the page itself (the Viewport's child), not in the visible part: right even when scrolled
    content = scroller.get_child()
    if isinstance(content, Gtk.Viewport):
        content = content.get_child()
    ok, rect = widget.compute_bounds(content)
    return rect.get_y() if ok else None


def _follow(scroller, widget):
    # A page opened for the first time has no layout yet, and the Look page grows in bursts while its pictures load
    # (still for half a second, then taller). So keep the row near the top for 5 s, unless the user scrolls.
    adj = scroller.get_vadjustment()
    state = {"set": None, "ticks": 0}

    def tick():
        state["ticks"] += 1
        if state["set"] is not None and abs(adj.get_value() - state["set"]) > 1:
            return False  # the user scrolled
        y = _row_y(scroller, widget)
        if y is not None:
            value = min(max(0, y - 40), max(0, adj.get_upper() - adj.get_page_size()))
            adj.set_value(value)
            state["set"] = adj.get_value()
        return state["ticks"] < 25

    GLib.timeout_add(200, tick)


def _scroller_of(child, widget):
    # the stack child is the page's scroller, except for a page with its own (Look): then the scroller around widget
    if isinstance(child, Gtk.ScrolledWindow):
        return child
    parent = widget.get_parent()
    while parent is not None and parent is not child:
        if isinstance(parent, Gtk.ScrolledWindow):
            return parent
        parent = parent.get_parent()
    return None


def _show(child, widget):
    # scroll the page to the row and light it up for a moment
    scroller = _scroller_of(child, widget)
    if scroller is not None:
        _follow(scroller, widget)
    target = widget
    while target is not None and isinstance(target, Gtk.Label) and isinstance(target.get_parent(), Gtk.CheckButton):
        target = target.get_parent()
    target.add_css_class(_HIGHLIGHT)
    GLib.timeout_add(_HIGHLIGHT_MS, lambda: target.remove_css_class(_HIGHLIGHT) and False)


class SearchBox:
    """A search entry with a drop-down list of matches; choosing one opens its page and shows the row."""

    def __init__(self, stack, pages):
        self._stack = stack
        self._pages = pages
        self._results = []
        self.entry = Gtk.SearchEntry(placeholder_text=_("Search settings"))
        self.entry.set_margin_start(8)
        self.entry.set_margin_end(8)
        self.entry.set_margin_top(8)
        self.entry.set_margin_bottom(4)
        self.entry.connect("search-changed", self._on_changed)
        self.entry.connect("activate", lambda _widget: self._go(0))
        self.entry.connect("stop-search", lambda _widget: self._popover.popdown())
        self._list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self._list.connect("row-activated", lambda _box, row: self._go(row.get_index()))
        scroll = Gtk.ScrolledWindow(propagate_natural_height=True, max_content_height=420)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self._list)
        self._popover = Gtk.Popover(autohide=False, has_arrow=False)
        self._popover.set_position(Gtk.PositionType.BOTTOM)
        self._popover.set_size_request(340, -1)
        self._popover.set_child(scroll)
        self._popover.set_parent(self.entry)
        self.widget = self.entry

    def _on_changed(self, entry):
        while (row := self._list.get_first_child()) is not None:
            self._list.remove(row)
        self._results = find(self._pages, entry.get_text())
        if len(normalize(entry.get_text())) < MIN_CHARS:
            self._popover.popdown()
            return
        for _name, title, _widget, text in self._results:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(4)
            box.set_margin_bottom(4)
            box.set_margin_start(6)
            box.set_margin_end(6)
            head = Gtk.Label(label=title, xalign=0)
            head.add_css_class("section-title")
            box.append(head)
            if text != title:
                line = Gtk.Label(label=text, xalign=0)
                line.set_ellipsize(Pango.EllipsizeMode.END)
                line.set_max_width_chars(44)
                line.add_css_class("muted")
                box.append(line)
            self._list.append(box)
        if not self._results:
            none = Gtk.Label(label=_("Nothing found."), xalign=0)
            none.add_css_class("muted")
            none.set_margin_top(6)
            none.set_margin_bottom(6)
            none.set_margin_start(6)
            row = Gtk.ListBoxRow(activatable=False)
            row.set_child(none)
            self._list.append(row)
        self._popover.popup()

    def _go(self, index):
        if not 0 <= index < len(self._results):
            return
        name, _title, widget, _text = self._results[index]
        self._popover.popdown()
        self._stack.set_visible_child_name(name)
        if widget is not None:
            # after the page switch has laid the page out
            _show(self._stack.get_child_by_name(name), widget)
