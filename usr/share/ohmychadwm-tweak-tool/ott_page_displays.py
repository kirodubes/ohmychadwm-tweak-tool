"""Displays page: resolution, refresh rate, on/off and primary per output; 15 s keep/revert, then saved for login."""

import os
import subprocess
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

import log  # noqa: E402
import ott_chadwm  # noqa: E402
import ott_display  # noqa: E402
import ott_session  # noqa: E402
from ott_widgets import (  # noqa: E402
    warning,
    KEEP_SECONDS,
    ask_keep,
    clear,
    dropdown,
    muted,
    page_box,
    row_label,
    run_async,
    section,
    selected,
    set_status,
    settings_grid,
    status_label,
)
from ott_i18n import _  # noqa: E402


def _rates(out, mode):
    return [f"{r} Hz" for r in out.modes.get(mode, [])]


class DisplaysPage:
    """One row per connected output; Apply switches now, Keep saves ~/.screenlayout/<user>.sh."""

    def __init__(self, window):
        self._window = window
        self.widget = page_box()
        self._busy = False
        self.refresh()

    def refresh(self):
        """Re-read the outputs from xrandr and rebuild the page."""
        if self._busy:
            return
        clear(self.widget)
        self._rows = {}
        self.widget.append(section(_("Displays")))
        if not ott_chadwm.in_session():
            self.widget.append(warning(_("You are not in an Ohmychadwm session: a change shows right away, but the "
                                       "saved layout is only used at your Ohmychadwm logins. This desktop keeps "
                                       "its own display settings.")))
        short = ott_display.layout_path().replace(os.path.expanduser("~"), "~", 1)
        self.widget.append(muted(
            _("Changes are used right away. Keep them within {seconds} seconds and they are saved to {path} "
              "(arandr format, so arandr can edit it too) for every login, otherwise the old layout comes back.").format(
                seconds=KEEP_SECONDS, path=short)
        ))
        try:
            outputs = ott_display.query()
        except (OSError, subprocess.CalledProcessError) as e:
            self.widget.append(muted(_("xrandr could not read the displays: {error}").format(error=e)))
            return
        connected = [o for o in outputs if o.connected]
        if not connected:
            self.widget.append(muted(_("xrandr reports no connected display.")))
            return
        vbox = ott_display.is_virtualbox()
        grid = settings_grid()
        group = None
        # screens that are on first, left to right, then the ones that are off
        current = ott_display.left_to_right(connected)
        current += [o.name for o in connected if o.name not in current]
        self._order, self._models = current, ott_display.models()
        places = [_("Position {number} from the left").format(number=n) for n in range(1, len(connected) + 1)]
        for row, out in enumerate(connected):
            names = list(out.modes)
            mode = out.mode or out.preferred or (names[0] if names else None)
            # VirtualBox guests start small (1024x768): offer 1920x1080 as Ohmychadwm Appearance did
            if vbox and ott_display.VIRTUALBOX_MODE in names:
                mode = ott_display.VIRTUALBOX_MODE
            dd_mode = dropdown(names, mode)
            dd_rate = dropdown(_rates(out, mode), f"{out.rate} Hz" if out.rate else None)
            dd_rate.set_hexpand(False)
            dd_mode.connect("notify::selected", lambda dd, _p, o=out, r=dd_rate: self._mode_changed(dd, o, r))
            on = Gtk.CheckButton(label=_("On"))
            on.set_active(out.mode is not None)
            primary = Gtk.CheckButton(label=_("Primary"))
            if group is None:
                group = primary
            else:
                primary.set_group(group)
            primary.set_active(out.primary or (len(connected) == 1))
            model = self._models.get(out.name)
            grid.attach(row_label(f"{model} ({out.name})" if model else out.name), 0, row, 1, 1)
            grid.attach(dd_mode, 1, row, 1, 1)
            grid.attach(dd_rate, 2, row, 1, 1)
            grid.attach(on, 3, row, 1, 1)
            grid.attach(primary, 4, row, 1, 1)
            dd_place = Gtk.DropDown.new_from_strings(places)
            dd_place.set_selected(current.index(out.name))
            dd_place.set_hexpand(False)
            if len(connected) > 1:
                grid.attach(dd_place, 5, row, 1, 1)
            self._rows[out.name] = (dd_mode, dd_rate, on, primary, dd_place)
        self.widget.append(grid)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        buttons.set_halign(Gtk.Align.END)
        btn_identify = Gtk.Button(label=_("Identify"))
        btn_identify.set_tooltip_text(_("Show each display's position, model and name on that display for a few "
                                        "seconds"))
        btn_identify.connect("clicked", self._on_identify)
        self._btn_apply = Gtk.Button(label=_("Apply"))
        self._btn_apply.add_css_class("suggested-action")
        self._btn_apply.connect("clicked", self._on_apply)
        if len(connected) > 1:
            buttons.append(btn_identify)
        buttons.append(self._btn_apply)
        self.widget.append(buttons)
        self._status = status_label()
        self.widget.append(self._status)

    def _on_identify(self, _widget):
        """Show a full-screen card on every display that is on: its position from the left, model and name."""
        if self._busy:
            return
        listed = self._window.get_display().get_monitors()
        monitors = {m.get_connector(): m for m in (listed.get_item(i) for i in range(listed.get_n_items()))}
        targets = [name for name in self._order if name in monitors]
        windows = []

        def show(name, shown):
            lines = [str(self._order.index(name) + 1), self._models.get(name) or "", name]
            label = Gtk.Label()
            label.set_markup("\n".join(GLib.markup_escape_text(line) for line in lines if line))
            label.set_justify(Gtk.Justification.CENTER)
            win = Gtk.Window(decorated=False)
            win.add_css_class("identify")
            win.set_child(label)
            click = Gtk.GestureClick()
            click.connect("pressed", close_all)
            win.add_controller(click)
            win.fullscreen_on_monitor(monitors[name])
            win.present()
            windows.append(win)
            shown.set()
            return False

        def close_all(*_args):
            for win in windows:
                win.destroy()
            windows.clear()
            self._busy = False
            return False

        def work():
            # chadwm opens a window on the screen that has the pointer and ignores the screen GTK asks for
            where = ott_session.pointer()
            for name in targets:
                in_session = ott_session.select_screen(name)
                shown = threading.Event()
                GLib.idle_add(show, name, shown)
                shown.wait(2)
                if in_session:
                    time.sleep(0.3)
            if where:
                ott_session.move_pointer(where)

        self._busy = True
        log.log_info(f"Displays: identify on {len(targets)} display(s)")
        run_async(work, lambda _result: GLib.timeout_add_seconds(4, close_all))

    def _mode_changed(self, dd_mode, out, dd_rate):
        rates = _rates(out, selected(dd_mode))
        dd_rate.set_model(Gtk.StringList.new(rates))
        dd_rate.set_selected(0)

    def _on_apply(self, _widget):
        if self._busy:
            return
        wanted, primary, place = {}, None, {}
        for name, (dd_mode, dd_rate, on, prim, dd_place) in self._rows.items():
            mode = selected(dd_mode) if on.get_active() else None
            wanted[name] = (mode, selected(dd_rate).removesuffix(" Hz") or None)
            if prim.get_active() and mode:
                primary = name
            if mode:
                place[name] = dd_place.get_selected()
        if not any(m for m, _r in wanted.values()):
            set_status(self._status, _("At least one display has to stay on."), error=True)
            return
        if len(set(place.values())) != len(place):
            set_status(self._status, _("Two displays have the same position: give each display its own place."),
                       error=True)
            return
        order = sorted(place, key=place.get)
        self._busy = True
        self._btn_apply.set_sensitive(False)
        set_status(self._status, _("Switching…"))
        run_async(lambda: ott_display.switch(wanted, primary, order), self._switched)

    def _switched(self, result):
        ok, msg, new, old = result
        (log.log_success if ok else log.log_error)(f"Displays: {msg}")
        if not ok:
            self._done(False, msg)
            return

        def answer(keep):
            if keep:
                self._done(*ott_display.save(new))
            else:
                run_async(lambda: ott_display.revert(old), lambda r: self._done(*r))

        ask_keep(self._window, _("Keep this display layout?"), answer)

    def _done(self, ok, msg):
        (log.log_success if ok else log.log_error)(f"Displays: {msg}")
        self._busy = False
        self.refresh()
        set_status(self._status, msg, error=not ok)
