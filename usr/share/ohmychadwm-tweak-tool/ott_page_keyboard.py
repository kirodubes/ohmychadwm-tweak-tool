"""Keyboard page: one or two typing layouts for the whole computer, and Ohmychadwm's AZERTY/QWERTY workspace keys."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

import log  # noqa: E402
import ott_chadwm  # noqa: E402
import ott_keyboard  # noqa: E402
import ott_root  # noqa: E402
from ott_i18n import _  # noqa: E402
from ott_widgets import (  # noqa: E402
    muted,
    page_box,
    row_label,
    run_async,
    section,
    set_status,
    settings_grid,
    status_label,
    warning,
)

_NONE = _("None")


def _dropdown(labels):
    model = Gtk.StringList.new(labels)
    dd = Gtk.DropDown(model=model)
    dd.set_expression(Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
    dd.set_enable_search(True)
    # GTK matches from the start by default: "us" would never find "English (US) (us)"
    dd.set_search_match_mode(Gtk.StringFilterMatchMode.SUBSTRING)
    dd.set_hexpand(True)
    return dd


class KeyboardPage:
    """Pick the keyboard layouts and the keys Ohmychadwm switches workspaces with."""

    def __init__(self):
        self._layouts = ott_keyboard.available_layouts()
        self._labels = [f"{desc} ({code})" for code, desc in self._layouts]
        self._codes = [code for code, _desc in self._layouts]
        self._busy = False

        box = page_box()
        box.append(section(_("Keyboard layouts")))
        box.append(muted(_("Pick the layout you type with. Add a second one to switch between them with {keys}.")
                         .format(keys="Alt+Shift")))
        grid = settings_grid()
        self._first = _dropdown(self._labels)
        self._second = _dropdown([_NONE, *self._labels])
        grid.attach(row_label(_("First layout")), 0, 0, 1, 1)
        grid.attach(self._first, 1, 0, 1, 1)
        grid.attach(row_label(_("Second layout")), 0, 1, 1, 1)
        grid.attach(self._second, 1, 1, 1, 1)
        box.append(grid)
        box.append(muted(_("Saved for the whole computer: XFCE and the login screen use it too.")))

        box.append(section(_("Workspace keys")))
        box.append(muted(_("The keys Ohmychadwm listens for to switch workspaces. AZERTY keyboards have no plain "
                           "number keys, so they need their own set. Changing it rebuilds Ohmychadwm.")))
        keys_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        self._qwerty = Gtk.CheckButton(label=_("QWERTY (US / world)"))
        self._azerty = Gtk.CheckButton(label=_("AZERTY (Belgian / French)"))
        self._azerty.set_group(self._qwerty)
        keys_row.append(self._qwerty)
        keys_row.append(self._azerty)
        box.append(keys_row)
        self._mismatch = warning()
        box.append(self._mismatch)
        for widget in (self._first, self._second):
            widget.connect("notify::selected", lambda *_args: self._update_hint())
        self._azerty.connect("toggled", lambda *_args: self._update_hint())

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._status = status_label()
        buttons.append(self._status)
        self._btn_restart = Gtk.Button(label=_("Restart Ohmychadwm now"))
        self._btn_restart.set_visible(False)
        self._btn_restart.connect("clicked", self._on_restart)
        self._btn_apply = Gtk.Button(label=_("Apply"))
        self._btn_apply.add_css_class("suggested-action")
        self._btn_apply.connect("clicked", self._on_apply)
        buttons.append(self._btn_restart)
        buttons.append(self._btn_apply)
        box.append(buttons)

        self.widget = box
        self.refresh()

    def refresh(self):
        """Show what the session types with now and the workspace keys config.def.h holds."""
        if self._busy:
            return
        layouts, self._options = ott_keyboard.current()
        layouts = layouts or ott_keyboard.saved_layouts() or ["us"]
        self._select(self._first, layouts[0], 0)
        if len(layouts) > 1:
            self._select(self._second, layouts[1], 1)
        else:
            self._second.set_selected(0)
        self._layouts_now = layouts
        self._azerty_now = ott_keyboard.azerty(ott_chadwm.read_config())
        (self._azerty if self._azerty_now else self._qwerty).set_active(True)
        for widget in (self._qwerty, self._azerty):
            widget.set_sensitive(self._azerty_now is not None)
        self._update_hint()

    def _select(self, dropdown, code, offset):
        if code in self._codes:
            dropdown.set_selected(self._codes.index(code) + offset)

    def _chosen(self):
        layouts = [self._codes[self._first.get_selected()]]
        second = self._second.get_selected()
        if second > 0:
            layouts.append(self._codes[second - 1])
        return layouts

    def _update_hint(self):
        if not self._codes:
            return
        mismatch = not ott_keyboard.keys_match(self._chosen(), self._azerty.get_active())
        self._mismatch.set_text(_("Your first layout and the workspace keys don't match: the workspace keys may not "
                                  "work.") if mismatch else "")
        self._mismatch.set_visible(mismatch)

    def _on_apply(self, _widget):
        if self._busy or not self._codes:
            return
        layouts = self._chosen()
        if len(layouts) == 2 and layouts[0] == layouts[1]:
            set_status(self._status, _("Pick two different layouts, or {none} as the second.").format(none=_NONE),
                       error=True)
            return
        options = ott_keyboard.options_for(layouts, self._options)
        layouts_changed = layouts != self._layouts_now
        is_azerty = self._azerty.get_active()
        keys_changed = self._azerty_now is not None and is_azerty != self._azerty_now
        if not layouts_changed and not keys_changed:
            set_status(self._status, _("Nothing changed."))
            return
        self._busy = True
        self._btn_apply.set_sensitive(False)
        self._btn_restart.set_visible(False)
        set_status(self._status, _("Recompiling Ohmychadwm…") if keys_changed else _("Applying…"))
        run_async(lambda: _apply(layouts if layouts_changed else None, options,
                                 is_azerty if keys_changed else None), self._applied)

    def _applied(self, result):
        ok, msg, rebuilt = result
        self._busy = False
        self._btn_apply.set_sensitive(True)
        (log.log_success if ok else log.log_error)(f"Keyboard: {msg}")
        if not ok:
            set_status(self._status, msg, error=True)
        elif rebuilt and ott_chadwm.can_restart():
            set_status(self._status, _("Applied. Restart Ohmychadwm to see it."))
            self._btn_restart.set_visible(True)
        elif rebuilt and ott_chadwm.in_session():
            set_status(self._status, _("Applied. Press Super+Shift+R to see it."))
        elif rebuilt:
            set_status(self._status, _("Applied. It shows at your next Ohmychadwm login."))
        else:
            set_status(self._status, _("Applied: {layouts}.").format(layouts=" + ".join(self._chosen())))
        self.refresh()

    def _on_restart(self, _widget):
        self._btn_restart.set_visible(False)
        ott_chadwm.restart()


def _apply(layouts, options, is_azerty):
    """Rebuild for new workspace keys, save both with one pkexec, then switch the layout; return (ok, msg, rebuilt)."""
    root_args, old_config = [], None
    if layouts:
        root_args += ["--keyboard", ",".join(layouts), "--keyboard-options", options]
    if is_azerty is not None:
        try:
            old_config = ott_chadwm.read_config()
            ott_chadwm.write_config(ott_keyboard.set_azerty(old_config, is_azerty))
        except (OSError, ValueError) as e:
            return False, f"config.def.h: {e}", False
        compiled, msg = ott_chadwm.compile_wm()
        if not compiled:
            ott_chadwm.write_config(old_config)
            return False, msg, False
        root_args += ["--install", ott_chadwm.BUILT_BINARY]
    try:
        ok, err = ott_root.run_root(root_args)
    finally:
        if is_azerty is not None:
            ott_chadwm.clean()
    if not ok:
        if old_config is not None:
            # the installed Ohmychadwm still has the old keys: keep config.def.h telling the truth
            ott_chadwm.write_config(old_config)
        return False, (_("Saving was cancelled or failed: {error}").format(error=err) if err
                       else _("Saving was cancelled or failed.")), False
    if is_azerty is not None:
        ott_keyboard.swap_cheatsheet(is_azerty)
    if layouts:
        # after the save, so a cancelled password prompt leaves the session as it was
        ok, err = ott_keyboard.apply_now(layouts, options)
        if not ok:
            return False, _("Saved, but switching this session failed: {error}").format(error=err), False
    return True, "keyboard saved", is_azerty is not None
