"""Displays page: resolution, refresh rate, on/off and primary per output; 15 s keep/revert, then saved for login."""

import os
import subprocess

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

import log  # noqa: E402
import ott_chadwm  # noqa: E402
import ott_display  # noqa: E402
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
            grid.attach(row_label(out.name), 0, row, 1, 1)
            grid.attach(dd_mode, 1, row, 1, 1)
            grid.attach(dd_rate, 2, row, 1, 1)
            grid.attach(on, 3, row, 1, 1)
            grid.attach(primary, 4, row, 1, 1)
            self._rows[out.name] = (dd_mode, dd_rate, on, primary)
        self.widget.append(grid)

        self._btn_apply = Gtk.Button(label=_("Apply"))
        self._btn_apply.add_css_class("suggested-action")
        self._btn_apply.set_halign(Gtk.Align.END)
        self._btn_apply.connect("clicked", self._on_apply)
        self.widget.append(self._btn_apply)
        self._status = status_label()
        self.widget.append(self._status)

    def _mode_changed(self, dd_mode, out, dd_rate):
        rates = _rates(out, selected(dd_mode))
        dd_rate.set_model(Gtk.StringList.new(rates))
        dd_rate.set_selected(0)

    def _on_apply(self, _widget):
        if self._busy:
            return
        wanted, primary = {}, None
        for name, (dd_mode, dd_rate, on, prim) in self._rows.items():
            mode = selected(dd_mode) if on.get_active() else None
            wanted[name] = (mode, selected(dd_rate).removesuffix(" Hz") or None)
            if prim.get_active() and mode:
                primary = name
        if not any(m for m, _r in wanted.values()):
            set_status(self._status, _("At least one display has to stay on."), error=True)
            return
        self._busy = True
        self._btn_apply.set_sensitive(False)
        set_status(self._status, _("Switching…"))
        run_async(lambda: ott_display.switch(wanted, primary), self._switched)

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
