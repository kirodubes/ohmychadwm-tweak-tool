"""GTK4 GUI for ohmychadwm-tweak-tool: header row, then a sidebar with one page per setting area."""

import os
import shutil
import sys
import traceback

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

import log  # noqa: E402
import ott_chadwm  # noqa: E402
import ott_display  # noqa: E402
import ott_i18n  # noqa: E402
import ott_root  # noqa: E402
from ott_page_apps import AppsPage  # noqa: E402
from ott_page_bar import BarPage  # noqa: E402
from ott_page_displays import DisplaysPage  # noqa: E402
from ott_page_input import InputPage  # noqa: E402
from ott_page_keys import KeysPage  # noqa: E402
from ott_page_look import LookPage  # noqa: E402
from ott_page_startup import StartupPage  # noqa: E402
from ott_page_wallpaper import WallpaperPage  # noqa: E402
from ott_widgets import clear, muted, page_box, section  # noqa: E402
from ott_i18n import _  # noqa: E402

_FUNDING = [
    ("GitHub Sponsors", "https://github.com/sponsors/erikdubois", _("best value — almost all goes to the project")),
    ("Ko-fi", "https://ko-fi.com/erikdubois", _("buy a coffee — one-off tip")),
    ("Patreon", "https://www.patreon.com/kiroproject", _("membership tiers + perks")),
    (_("YouTube membership"), "https://www.youtube.com/@ErikDubois/join", _("join on YouTube")),
    ("PayPal", "https://www.paypal.me/erikdubois", _("direct one-off")),
]

# Tools a page needs: (command, what for)
_TOOLS = [
    ("xdotool", _("restart Ohmychadwm from the app")),
    ("xinput", _("Mouse & touchpad")),
    ("xrandr", _("Displays")),
    ("arandr", _("edit the saved display layout by hand")),
    ("feh", _("Wallpaper")),
    ("xdg-mime", _("Default apps")),
    ("make", _("rebuild Ohmychadwm")),
]


def _open_url(parent, url):
    Gtk.UriLauncher.new(url).launch(parent, None, None)


def _show_support_dialog(window):
    dlg = Gtk.Window(title=_("Support Kiro"), transient_for=window, modal=True)
    dlg.set_default_size(440, -1)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    for side in ("start", "end", "top", "bottom"):
        getattr(box, f"set_margin_{side}")(18)

    heading = Gtk.Label(xalign=0)
    heading.set_markup("<b>{}</b>".format(GLib.markup_escape_text(_("Support Kiro"))))
    box.append(heading)

    intro = muted(
        _("Kiro and its tools are built by one person, for the community — and kept free. "
        "If the Ohmychadwm Tweak Tool saves you time, a little support keeps the work going. "
        "Thank you for being here.")
    )
    intro.set_max_width_chars(52)
    box.append(intro)

    for name, url, note in _FUNDING:
        btn = Gtk.Button()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        label = Gtk.Label(xalign=0)
        label.set_markup(f"<b>{GLib.markup_escape_text(name)}</b>")
        content.append(label)
        content.append(muted(note))
        btn.set_child(content)
        btn.connect("clicked", lambda _w, u=url: _open_url(dlg, u))
        box.append(btn)

    close = Gtk.Button(label=_("Close"))
    close.set_halign(Gtk.Align.END)
    close.connect("clicked", lambda _w: dlg.close())
    box.append(close)

    dlg.set_child(box)
    dlg.present()


def _language_controls():
    """Build the header-row language dropdown, its Restart now button and the saved note."""
    codes = [None, *ott_i18n.available()]
    labels = [_("System ({language})").format(language=ott_i18n.name(ott_i18n.SYSTEM))]
    labels.extend(ott_i18n.name(code) for code in codes[1:])
    dropdown = Gtk.DropDown.new_from_strings(labels)
    dropdown.set_tooltip_text(_("Language"))
    dropdown.set_valign(Gtk.Align.CENTER)
    dropdown.set_selected(codes.index(ott_i18n.chosen()))
    note = Gtk.Label(xalign=1, wrap=True, visible=False)
    note.add_css_class("muted")
    restart = Gtk.Button(label=_("Restart now"), visible=False)
    restart.set_valign(Gtk.Align.CENTER)

    def on_language_changed(_dropdown, _pspec):
        code = codes[dropdown.get_selected()]
        ott_i18n.save_choice(code)
        changed = (code or ott_i18n.SYSTEM) != (ott_i18n.ACTIVE or ott_i18n.SYSTEM)
        note.set_text(_("Saved. The app shows the new language when it starts again.") if changed else "")
        note.set_visible(changed)
        restart.set_visible(changed)

    def on_restart(_widget):
        argv = [sys.executable, os.path.abspath(sys.argv[0]), *sys.argv[1:]]
        ott_i18n.restore_environment()
        os.execv(sys.executable, argv)

    dropdown.connect("notify::selected", on_language_changed)
    restart.connect("clicked", on_restart)
    return dropdown, note, restart


def _header_row(window):
    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    header.set_margin_start(12)
    header.set_margin_end(12)
    header.set_margin_top(10)
    header.set_margin_bottom(8)
    title = Gtk.Label(label=_("Ohmychadwm Tweak Tool"), xalign=0)
    title.set_name("title")
    title.set_hexpand(True)
    btn_support = Gtk.Button(label=_("♥ Support"))
    btn_support.set_tooltip_text(_("Support Kiro's development"))
    btn_support.add_css_class("support-button")
    btn_support.connect("clicked", lambda _w: _show_support_dialog(window))
    btn_quit = Gtk.Button(label=_("Quit"))
    btn_quit.connect("clicked", lambda _w: window.close())
    language_dropdown, language_note, btn_restart = _language_controls()
    header.append(title)
    header.append(language_note)
    header.append(language_dropdown)
    header.append(btn_restart)
    header.append(btn_support)
    header.append(btn_quit)
    return header


def _status_grid(rows):
    grid = Gtk.Grid(column_spacing=18, row_spacing=8)
    for i, (key, value, ok) in enumerate(rows):
        k = Gtk.Label(label=key, xalign=0)
        k.add_css_class("muted")
        v = Gtk.Label(label=value, xalign=0, selectable=True)
        # Not focusable: GTK would focus the first selectable label and open with its text highlighted.
        v.set_focusable(False)
        v.set_wrap(True)
        if ok is False:
            v.add_css_class("warn")
        grid.attach(k, 0, i, 1, 1)
        grid.attach(v, 1, i, 1, 1)
    return grid


class StatusPage:
    """What the app found: the ohmychadwm setup, the built bar, and the tools each page needs."""

    def __init__(self):
        self.widget = page_box()
        self.refresh()

    def refresh(self):
        """Re-check everything."""
        clear(self.widget)
        config = ott_chadwm.read_config()
        installed = os.path.isfile(ott_root.INSTALL_PATH)
        self.widget.append(section(_("Your desktop")))
        self.widget.append(_status_grid([
            (_("Session"), "Ohmychadwm" if ott_chadwm.in_session()
             else _("not an Ohmychadwm session — changes show there"), ott_chadwm.in_session()),
            (_("Config"), ott_chadwm.CONFIG if config else _("missing — log into Ohmychadwm once first"), bool(config)),
            (_("Bar theme"), ott_chadwm.active_theme(config) or _("none"), True),
            (_("Your own bar build"), ott_root.INSTALL_PATH if installed
             else _("none yet — the packaged Ohmychadwm runs"), True),
            (_("Display layout"), ott_display.layout_path(), True),
            (_("Virtual machine"), "VirtualBox" if ott_display.is_virtualbox() else _("no"), True),
        ]))
        self.widget.append(section(_("Tools")))
        self.widget.append(_status_grid([
            (cmd, (_("found — {why}") if shutil.which(cmd) else _("missing — {why}")).format(why=why),
             shutil.which(cmd) is not None)
            for cmd, why in _TOOLS
        ]))

class _BrokenPage:
    """Stand-in for a section that failed to build, so the rest of the app still opens."""

    def __init__(self, title, error):
        self.widget = page_box()
        self.widget.append(section(title))
        self.widget.append(muted(_("This section could not load: {error}").format(error=error)))

    def refresh(self):
        """Nothing to refresh."""


def _safe(title, make):
    try:
        return make()
    except Exception as e:  # one broken section must never stop the whole window
        log.log_error(f"{title}: {e}\n{traceback.format_exc()}")
        return _BrokenPage(title, e)


# Page to open first (--page NAME on the command line), e.g. "wallpaper".
START_PAGE = None


def build(window):
    """Fill the main window."""
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    root.append(_header_row(window))
    root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

    sections = [
        ("look", _("Look"), _safe("Look", LookPage)),
        ("bar", _("Bar & windows"), _safe("Bar & windows", BarPage)),
        ("wallpaper", _("Wallpaper"), _safe("Wallpaper", lambda: WallpaperPage(window))),
        ("displays", _("Displays"), _safe("Displays", lambda: DisplaysPage(window))),
        ("mouse", _("Mouse & touchpad"), _safe("Mouse & touchpad", InputPage)),
        ("startup", _("Startup apps"), _safe("Startup apps", StartupPage)),
        ("apps", _("Default apps"), _safe("Default apps", AppsPage)),
        ("keys", _("Keys"), _safe("Keys", KeysPage)),
        ("status", _("Status"), _safe("Status", StatusPage)),
    ]
    pages = {}
    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    stack.set_hexpand(True)
    for name, title, page in sections:
        pages[name] = page
        if getattr(page, "own_scroll", False):
            child = page.widget  # the Look page keeps its Apply footer outside its own scroller
        else:
            child = Gtk.ScrolledWindow()
            child.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            child.set_child(page.widget)
        stack.add_titled(child, name, title)
    if START_PAGE and stack.get_child_by_name(START_PAGE.lower()):
        stack.set_visible_child_name(START_PAGE.lower())

    def on_switch(st, _pspec):
        # the other pages read files the Look page changes (bar theme), so re-read on every visit
        page = pages.get(st.get_visible_child_name())
        if page is not None and hasattr(page, "refresh") and st.get_visible_child_name() != "wallpaper":
            page.refresh()

    stack.connect("notify::visible-child-name", on_switch)
    sidebar = Gtk.StackSidebar(stack=stack)
    sidebar.set_size_request(190, -1)
    body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    body.set_vexpand(True)
    body.append(sidebar)
    body.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
    body.append(stack)
    root.append(body)
    window.set_child(root)
