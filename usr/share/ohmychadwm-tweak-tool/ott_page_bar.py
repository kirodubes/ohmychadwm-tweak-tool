"""Bar & windows page: border width, gaps, smart gaps, bar position, systray, autohide (rebuilds ohmychadwm)."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

import log  # noqa: E402
import ott_chadwm  # noqa: E402
import ott_root  # noqa: E402
from ott_widgets import (  # noqa: E402
    session_note,
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
from ott_i18n import _  # noqa: E402

# (option, label, kind, minimum, maximum, tooltip)
_FIELDS = [
    ("THEME_BORDER", _("Window border"), "spin", 0, 20, _("Border width around every window, in pixels")),
    ("THEME_GAPS", _("Gaps"), "spin", 0, 60, _("Space between windows and around the screen edge, in pixels")),
    ("THEME_SMARTGAPS", _("Smart gaps"), "switch", 0, 1, _("No outer gap when only one window is open")),
    ("THEME_TOPBAR", _("Bar at the top"), "switch", 0, 1, _("Off puts the bar at the bottom of the screen")),
    ("THEME_SHOWSYSTRAY", _("System tray"), "switch", 0, 1, _("Show the tray icons (network, volume, …) in the bar")),
    ("THEME_AUTOHIDE", _("Hide the bar after"), "spin", 0, 60, _("Seconds without use before the bar hides; 0 = never")),
]


class BarPage:
    """The bar & window options of the managed config.def.h block, over the active theme's own values."""

    def __init__(self):
        self.widget = page_box()
        self._busy = False
        self.refresh()

    def refresh(self):
        """Rebuild the page from config.def.h (the Look page may have changed the bar theme)."""
        if self._busy:
            return
        clear(self.widget)
        self._widgets = {}
        config = ott_chadwm.read_config()
        self.widget.append(section(_("Bar & windows")))
        if (note := session_note()) is not None:
            self.widget.append(note)
        if not config:
            self.widget.append(muted(_("~/.config/ohmychadwm is not set up for this user — log into Ohmychadwm once "
                                     "first.")))
            return
        theme = ott_chadwm.active_theme(config) or ""
        self._theme_values = ott_chadwm.theme_values(theme)
        overrides = ott_chadwm.bar_options(config)
        self.widget.append(muted(
            _("Starts from what the bar theme “{theme}” sets; anything you change here stays when you pick another "
              "theme. Applying recompiles Ohmychadwm (asks your password once).").format(theme=theme)
        ))
        grid = settings_grid()
        for row, (key, label, kind, lo, hi, tip) in enumerate(_FIELDS):
            value = overrides.get(key, self._theme_values.get(key, lo))
            if kind == "spin":
                w = Gtk.SpinButton.new_with_range(lo, hi, 1)
                w.set_value(value)
            else:
                w = Gtk.Switch()
                w.set_active(bool(value))
                w.set_halign(Gtk.Align.START)
            w.set_tooltip_text(tip)
            self._widgets[key] = w
            grid.attach(row_label(label), 0, row, 1, 1)
            grid.attach(w, 1, row, 1, 1)
        self.widget.append(grid)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        self._btn_restart = Gtk.Button(label=_("Restart Ohmychadwm now"))
        self._btn_restart.set_visible(False)
        self._btn_restart.connect("clicked", self._on_restart)
        reset = Gtk.Button(label=_("Use the theme's values"))
        reset.set_tooltip_text(_("Drop every change on this page, so the bar theme decides again"))
        reset.connect("clicked", self._on_reset)
        self._btn_apply = Gtk.Button(label=_("Apply"))
        self._btn_apply.add_css_class("suggested-action")
        self._btn_apply.connect("clicked", self._on_apply)
        buttons.append(self._btn_restart)
        buttons.append(reset)
        buttons.append(self._btn_apply)
        self.widget.append(buttons)
        self._status = status_label()
        self.widget.append(self._status)

    def _value(self, key):
        w = self._widgets[key]
        return int(w.get_value()) if isinstance(w, Gtk.SpinButton) else int(w.get_active())

    def _on_reset(self, _widget):
        for key, _label, kind, lo, _hi, _tip in _FIELDS:
            value = self._theme_values.get(key, lo)
            if kind == "spin":
                self._widgets[key].set_value(value)
            else:
                self._widgets[key].set_active(bool(value))
        set_status(self._status, _("The theme's values are loaded — press Apply to use them."))

    def _on_apply(self, _widget):
        if self._busy:
            return
        # only what differs from the theme goes in the block, so the theme still decides the rest
        wanted = {key: self._value(key) for key, *_rest in _FIELDS
                  if self._value(key) != self._theme_values.get(key)}
        self._busy = True
        self._btn_apply.set_sensitive(False)
        self._btn_restart.set_visible(False)
        set_status(self._status, _("Recompiling Ohmychadwm…"))
        run_async(lambda: _rebuild(wanted), self._applied)

    def _applied(self, result):
        ok, msg = result
        self._busy = False
        self._btn_apply.set_sensitive(True)
        (log.log_success if ok else log.log_error)(f"Bar & windows: {msg}")
        if not ok:
            set_status(self._status, msg, error=True)
            return
        if msg == "unchanged":
            set_status(self._status, _("Nothing changed."))
        elif ott_chadwm.can_restart():
            set_status(self._status, _("Applied. Restart Ohmychadwm to see it."))
            self._btn_restart.set_visible(True)
        elif ott_chadwm.in_session():
            set_status(self._status, _("Applied. Press Super+Shift+R to see it."))
        else:
            set_status(self._status, _("Applied. It shows at your next Ohmychadwm login."))

    def _on_restart(self, _widget):
        self._btn_restart.set_visible(False)
        ott_chadwm.restart()


def _rebuild(wanted):
    """Write the options into config.def.h, compile, install with one pkexec; return (ok, message)."""
    try:
        text = ott_chadwm.read_config()
        new = ott_chadwm.set_bar_options(text, wanted)
        if new == text:
            return True, "unchanged"
        ott_chadwm.write_config(new)
    except (OSError, ValueError) as e:
        return False, f"config.def.h: {e}"
    compiled, msg = ott_chadwm.compile_wm()
    if not compiled:
        return False, msg
    try:
        ok, err = ott_root.run_root(["--install", ott_chadwm.BUILT_BINARY])
    finally:
        ott_chadwm.clean()
    if not ok:
        return False, (_("Installing the new Ohmychadwm was cancelled or failed: {error}").format(error=err) if err
                       else _("Installing the new Ohmychadwm was cancelled or failed."))
    return True, "Ohmychadwm rebuilt and installed"
