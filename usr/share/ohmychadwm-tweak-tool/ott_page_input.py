"""Mouse & touchpad page: live via xinput while you change it, Save writes xorg.conf.d (one password prompt)."""

import json

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

import log  # noqa: E402
import ott_input  # noqa: E402
import ott_root  # noqa: E402
from ott_widgets import (  # noqa: E402
    clear,
    muted,
    page_box,
    row_label,
    run_async,
    section,
    set_status,
    settings_grid,
    status_label,
)

# kind -> [(key, label, tooltip)]
_ROWS = {
    "pointer": [
        ("accel", "Pointer speed", "Slower to the left, faster to the right"),
        ("natural", "Natural scrolling", "Content follows your fingers, as on a phone"),
        ("left_handed", "Left-handed", "Swap the left and right buttons"),
    ],
    "touchpad": [
        ("accel", "Pointer speed", "Slower to the left, faster to the right"),
        ("tapping", "Tap to click", "A light tap counts as a click"),
        ("natural", "Natural scrolling", "Content follows your fingers, as on a phone"),
        ("dwt", "Off while typing", "Ignore the touchpad while you type"),
    ],
}
_TITLES = {"pointer": "Mouse", "touchpad": "Touchpad"}


class InputPage:
    """Mouse and touchpad settings, applied live and saved for every login."""

    def __init__(self):
        self.widget = page_box()
        self._busy = False
        self._live_timer = 0
        self.refresh()

    def refresh(self):
        """Re-read the devices and the saved file, and rebuild the page."""
        if self._busy:
            return
        clear(self.widget)
        self._widgets = {}
        self._devices = ott_input.devices()
        values = ott_input.current(self._devices)
        kinds = {kind for _id, _name, kind, _props in self._devices}
        self.widget.append(muted(
            "Changes are used right away. Save keeps them for every login "
            f"({ott_input.CONF_PATH}, asks your password once)."
        ))
        if not self._devices:
            self.widget.append(muted("No mouse or touchpad was found through xinput (is xorg-xinput installed?)."))
        for kind in ("pointer", "touchpad"):
            if kind not in kinds and kind == "touchpad":
                continue
            self.widget.append(section(_TITLES[kind]))
            names = [name for _id, name, k, _props in self._devices if k == kind]
            if names:
                self.widget.append(muted(", ".join(names)))
            grid = settings_grid()
            for row, (key, label, tip) in enumerate(_ROWS[kind]):
                value = values[kind][key]
                if key == "accel":
                    w = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -1.0, 1.0, 0.05)
                    w.set_value(value)
                    w.set_hexpand(True)
                    w.add_mark(0.0, Gtk.PositionType.BOTTOM, None)
                    w.connect("value-changed", lambda *_: self._live())
                else:
                    w = Gtk.Switch()
                    w.set_active(value)
                    w.set_halign(Gtk.Align.START)
                    w.connect("notify::active", lambda *_: self._live())
                w.set_tooltip_text(tip)
                self._widgets[(kind, key)] = w
                grid.attach(row_label(label), 0, row, 1, 1)
                grid.attach(w, 1, row, 1, 1)
            self.widget.append(grid)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        reset = Gtk.Button(label="Defaults")
        reset.set_tooltip_text("libinput's own defaults — press Save to keep them")
        reset.connect("clicked", self._on_defaults)
        self._btn_save = Gtk.Button(label="Save")
        self._btn_save.add_css_class("suggested-action")
        self._btn_save.connect("clicked", self._on_save)
        buttons.append(reset)
        buttons.append(self._btn_save)
        self.widget.append(buttons)
        self._status = status_label()
        self.widget.append(self._status)

    def _settings(self):
        out = {}
        for (kind, key), w in self._widgets.items():
            out.setdefault(kind, {})[key] = round(w.get_value(), 2) if isinstance(w, Gtk.Scale) else w.get_active()
        return ott_input.validate(out)

    def _live(self):
        # dragging the speed slider fires on every step: wait until it rests
        if self._live_timer:
            GLib.source_remove(self._live_timer)
        self._live_timer = GLib.timeout_add(200, self._live_now)

    def _live_now(self):
        self._live_timer = 0
        settings, devices = self._settings(), self._devices
        run_async(lambda: ott_input.apply_live(settings, devices), self._live_done)
        return False

    def _live_done(self, errors):
        for e in errors:
            log.log_warn(f"Mouse & touchpad: {e}")
        if errors:
            set_status(self._status, "Some settings could not be used:\n" + "\n".join(errors), error=True)

    def _on_defaults(self, _widget):
        for (kind, key), w in self._widgets.items():
            value = ott_input.DEFAULTS[kind][key]
            if isinstance(w, Gtk.Scale):
                w.set_value(value)
            else:
                w.set_active(value)
        set_status(self._status, "Defaults loaded and used now — press Save to keep them.")

    def _on_save(self, _widget):
        if self._busy:
            return
        self._busy = True
        self._btn_save.set_sensitive(False)
        set_status(self._status, "Waiting for your password…")
        arg = json.dumps(self._settings())
        run_async(lambda: ott_root.run_root(["--input", arg]), self._saved)

    def _saved(self, result):
        ok, err = result
        self._busy = False
        self._btn_save.set_sensitive(True)
        if ok:
            log.log_success(f"Mouse & touchpad saved to {ott_input.CONF_PATH}")
            set_status(self._status, "Saved. Every login uses these settings now.")
        else:
            log.log_error(f"Mouse & touchpad: {err}")
            set_status(self._status, "Saving was cancelled or failed" + (f": {err}" if err else ""), error=True)
