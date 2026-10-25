"""Keys page: a searchable list of every binding from sxhkdrc and ohmychadwm's own keys."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

import ott_chadwm  # noqa: E402
import ott_keys  # noqa: E402
from ott_widgets import clear, muted, page_box, section, warning  # noqa: E402

_SOURCE = {"sxhkd": "sxhkdrc", "ohmychadwm": "Ohmychadwm"}


class KeysPage:
    """Read-only list of the key bindings, filtered as you type."""

    def __init__(self):
        self.widget = page_box()
        self.refresh()

    def refresh(self):
        """Re-read sxhkdrc and config.def.h."""
        clear(self.widget)
        self.widget.append(section("Keys"))
        if not ott_chadwm.in_session():
            self.widget.append(warning("You are not in an Ohmychadwm session: these are Ohmychadwm's keys, not the "
                                       "ones of the desktop you are in now."))
        self.widget.append(muted("From ~/.config/ohmychadwm/sxhkd/sxhkdrc and the keys of "
                                 "~/.config/ohmychadwm/chadwm/config.def.h, as they are now."))
        self._rows = []
        bindings = ott_keys.all_bindings(ott_keys.read_sxhkdrc(), ott_chadwm.read_config())
        search = Gtk.SearchEntry(placeholder_text="Search keys or actions")
        search.connect("search-changed", self._on_search)
        self.widget.append(search)
        self._empty = muted("No key matches.")
        self._empty.set_visible(not bindings)
        grid = Gtk.Grid(column_spacing=18, row_spacing=4)
        for i, b in enumerate(bindings):
            keys = Gtk.Label(label=b.keys, xalign=0)
            keys.add_css_class("monospace")
            action = Gtk.Label(label=b.action, xalign=0, selectable=True)
            action.set_focusable(False)  # else GTK focuses the first one and opens with its text highlighted
            action.set_wrap(True)
            action.set_hexpand(True)
            src = muted(_SOURCE[b.source])
            grid.attach(keys, 0, i, 1, 1)
            grid.attach(action, 1, i, 1, 1)
            grid.attach(src, 2, i, 1, 1)
            self._rows.append((f"{b.keys} {b.action} {_SOURCE[b.source]}".lower(), (keys, action, src)))
        self.widget.append(grid)
        self.widget.append(self._empty)

    def _on_search(self, entry):
        needle = entry.get_text().lower().strip()
        shown = 0
        for text, widgets in self._rows:
            visible = needle in text
            shown += visible
            for w in widgets:
                w.set_visible(visible)
        self._empty.set_visible(shown == 0)
