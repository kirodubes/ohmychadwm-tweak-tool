"""App placement page: the screen, workspace and floating of an app's windows (chadwm rules[], rebuilds ohmychadwm)."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Pango  # noqa: E402

import log  # noqa: E402
import ott_chadwm  # noqa: E402
import ott_placement  # noqa: E402
import ott_root  # noqa: E402
import ott_startup  # noqa: E402
from ott_widgets import (  # noqa: E402
    clear,
    muted,
    page_box,
    row_label,
    run_async,
    section,
    session_note,
    set_status,
    settings_grid,
    status_label,
)
from ott_i18n import _  # noqa: E402


def _mode_labels():
    return {"tiled": _("Tiled, as usual"), "float": _("Floating"), "center": _("Floating, in the middle")}


def summary(rule, monitors):
    """Return one line of what a rule does, e.g. "When firefox opens: screen 2 (HDMI-0) · workspace 10"."""
    if rule["monitor"] >= 0:
        name = next((n for num, n, _size in monitors if num == rule["monitor"]), None)
        screen = (_("screen {n} ({name})").format(n=rule["monitor"] + 1, name=name) if name
                  else _("screen {n}, not connected now").format(n=rule["monitor"] + 1))
    else:
        screen = _("the screen you are working on")
    parts = []
    if rule["workspace"]:
        parts.append(_("workspace {n}").format(n=rule["workspace"]))
    elif rule["workspace"] == 0:
        parts.append(_("the workspace you are on"))
    else:
        parts.append(_("workspaces {mask}").format(mask=rule["tags"]))
    if rule["mode"] is not None:
        parts.append(_mode_labels()[rule["mode"]].lower())
    else:
        parts.append(_("own floating settings"))
    if rule["instance"] or rule["title"]:
        parts.append(_("only windows named “{name}”").format(name=rule["title"] or rule["instance"]))
    if rule["monitor"] < 0 and rule["workspace"] == 0 and rule["mode"] == "tiled":
        return _("When {app} opens: {placement} (this rule changes nothing)").format(
            app=rule["class"] or "*", placement=" · ".join([screen] + parts))
    return _("When {app} opens: {placement}").format(app=rule["class"] or "*",
                                                     placement=" · ".join([screen] + parts))


class PlacementPage:
    """The rules[] table of config.def.h: where an app's windows open. Save rule and Remove rebuild at once."""

    def __init__(self):
        self.widget = page_box()
        self._busy = False
        self._text = ""
        self._choices, self._monitors = [], []
        self.refresh()

    def refresh(self):
        """Rebuild the page from config.def.h."""
        if self._busy:
            return
        clear(self.widget)
        self.widget.append(section(_("App placement")))
        if (note := session_note()) is not None:
            self.widget.append(note)
        config = ott_chadwm.read_config()
        if not config:
            self.widget.append(muted(_("~/.config/ohmychadwm is not set up for this user — log into Ohmychadwm once "
                                     "first.")))
            return
        self._text = config
        self.widget.append(muted(_("Choose on which screen and workspace an app opens, and whether it floats. "
                                   "Open windows are listed first. Saving a rule recompiles Ohmychadwm (asks your "
                                   "password); it takes effect the next time the app opens a window. Tick “Also "
                                   "start it at login” to have it open there by itself when you log in.")))
        self._rules_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.widget.append(self._rules_box)

        grid = settings_grid()
        self._dd_app = Gtk.DropDown.new_from_strings([_("Reading the open windows…")])
        self._dd_app.set_enable_search(True)
        self._dd_app.set_search_match_mode(Gtk.StringFilterMatchMode.SUBSTRING)
        self._dd_app.set_expression(Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
        self._dd_screen = Gtk.DropDown.new_from_strings([_("The screen you are working on")])
        self._dd_workspace = Gtk.DropDown.new_from_strings(
            [_("The workspace you are on")] + [str(n) for n in ott_placement.WORKSPACES])
        self._dd_mode = Gtk.DropDown.new_from_strings(list(_mode_labels().values()))
        for row, (label, dd) in enumerate(((_("App"), self._dd_app), (_("Screen"), self._dd_screen),
                                           (_("Workspace"), self._dd_workspace), (_("Open as"), self._dd_mode))):
            dd.set_hexpand(True)
            grid.attach(row_label(label), 0, row, 1, 1)
            grid.attach(dd, 1, row, 1, 1)
        self._chk_login = Gtk.CheckButton(label=_("Also start it at login"))
        self._chk_login.set_sensitive(False)
        grid.attach(self._chk_login, 1, 4, 1, 1)
        self._dd_app.connect("notify::selected", lambda _dd, _pspec: self._sync_login())
        self.widget.append(grid)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons.set_halign(Gtk.Align.END)
        reread = Gtk.Button(label=_("Refresh"))
        reread.set_tooltip_text(_("Read the open windows and the screens again"))
        reread.connect("clicked", lambda _widget: self._load())
        self._btn_restart = Gtk.Button(label=_("Restart Ohmychadwm now"))
        self._btn_restart.set_visible(False)
        self._btn_restart.connect("clicked", self._on_restart)
        self._btn_save = Gtk.Button(label=_("Save rule"))
        self._btn_save.add_css_class("suggested-action")
        self._btn_save.connect("clicked", self._on_save)
        # next to the button, not only in the status line below, which can be out of view
        self._spinner = Gtk.Spinner(valign=Gtk.Align.CENTER, visible=False)
        for b in (self._spinner, reread, self._btn_restart, self._btn_save):
            buttons.append(b)
        self.widget.append(buttons)
        self.widget.append(muted(_("Screens are numbered the way Ohmychadwm counts them: the primary screen is "
                                   "screen 1. Rearranging your screens on the Displays page can change the numbers.")))
        self._status = status_label()
        self.widget.append(self._status)
        self._show_rules()
        self._load()

    def _load(self):
        run_async(lambda: (ott_placement.choices(), ott_placement.monitors()), self._fill)

    def _fill(self, result):
        self._choices, self._monitors = result
        labels = [_("{title}  ({window_class}, open now)").format(title=title, window_class=cls) if now
                  else _("{title}  ({window_class})").format(title=title, window_class=cls)
                  for cls, title, now, _command in self._choices]
        self._dd_app.set_model(Gtk.StringList.new(labels or [_("No apps found: open the app, then press Refresh")]))
        current = self._current_screen()
        self._dd_screen.set_model(Gtk.StringList.new(
            [_("The screen you are working on (now screen {n}: {name})").format(n=current[0] + 1, name=current[1])
             if current else _("The screen you are working on")]
            + [_("Screen {n}: {name} ({size})").format(n=num + 1, name=name, size=size)
               for num, name, size in self._monitors]))
        self._sync_login()
        self._show_rules()

    def _current_screen(self):
        # the screen this window is on is the one the user works on now
        root = self.widget.get_root()
        surface = root.get_surface() if root else None
        monitor = surface.get_display().get_monitor_at_surface(surface) if surface else None
        connector = monitor.get_connector() if monitor else None
        return next(((num, name) for num, name, _size in self._monitors if name == connector), None)

    def _command_for(self, cls):
        return next((command for c, _title, _now, command in self._choices if c == cls), None)

    def _login_entries(self):
        return {e.command: e for e in ott_startup.entries(ott_startup.read())}

    def _sync_login(self):
        if not self._choices:
            return
        command = self._choices[self._dd_app.get_selected()][3]
        entry = self._login_entries().get(command) if command else None
        self._chk_login.set_sensitive(command is not None)
        self._chk_login.set_active(bool(entry and entry.enabled))
        self._chk_login.set_tooltip_text(
            _("Starts “{command}” when you log in; it shows on the Startup apps page too.").format(command=command)
            if command else _("No start command found for this app: add it on the Startup apps page."))

    def _show_rules(self):
        clear(self._rules_box)
        try:
            rules = ott_placement.rules(self._text)
        except ValueError as e:
            self._rules_box.append(muted(str(e)))
            return
        if not rules:
            self._rules_box.append(muted(_("No rules yet: apps open on the screen and workspace you are working on.")))
        else:
            self._rules_box.append(muted(_("Rules now. They move an app's window when it opens; only the ones marked "
                                           "“starts at login” open by themselves.")))
        login = {c for c, e in self._login_entries().items() if e.enabled}
        for rule in rules:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            text = summary(rule, self._monitors)
            if self._command_for(rule["class"]) in login:
                text = _("{rule} · starts at login").format(rule=text)
            label = Gtk.Label(label=text, xalign=0)
            label.set_hexpand(True)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            row.append(label)
            if rule["editable"]:
                btn = Gtk.Button(label=_("Remove"))
                btn.set_sensitive(not self._busy)
                btn.connect("clicked", self._on_remove, rule["class"])
                row.append(btn)
            else:
                label.set_tooltip_text(_("Written by hand in config.def.h: change it there."))
            self._rules_box.append(row)

    def _on_save(self, _widget):
        if not self._choices:
            set_status(self._status, _("No apps found: open the app, then press Refresh."), error=True)
            return
        cls, _title, _now, command = self._choices[self._dd_app.get_selected()]
        screen = self._dd_screen.get_selected()
        monitor = self._monitors[screen - 1][0] if 0 < screen <= len(self._monitors) else -1
        workspace, mode = self._dd_workspace.get_selected(), list(_mode_labels())[self._dd_mode.get_selected()]
        if workspace == 0 and monitor == -1 and mode == "tiled":
            set_status(self._status, _("Choose a screen, a workspace or floating for {name}: as it is, the rule would "
                                       "change nothing.").format(name=cls), error=True)
            return
        login = self._set_login(command, self._chk_login.get_active()) if command else ""
        self._change(lambda text: ott_placement.set_rule(text, cls, workspace, monitor, mode),
                     _("Saved the rule for {name}.").format(name=cls) + login,
                     _("This rule is already there.") + login)

    def _on_remove(self, _widget, cls):
        command = self._command_for(cls)
        login = self._set_login(command, False, only_own=True) if command else ""
        self._change(lambda text: ott_placement.remove_rule(text, cls),
                     _("Removed the rule for {name}.").format(name=cls) + login,
                     _("The rule for {name} was already gone.").format(name=cls) + login)

    def _set_login(self, command, on, only_own=False):
        """Put command's run line in run.sh on or off; return a sentence for the status, or ''."""
        text = ott_startup.read()
        entry = next((e for e in ott_startup.entries(text) if e.command == command), None)
        if on and entry is None:
            new = ott_startup.add(text, command)
        elif on and not entry.enabled:
            new = ott_startup.set_enabled(text, command, True)
        elif not on and entry is not None and entry.enabled and (entry.added or not only_own):
            # a line this app added goes; one Kiro ships is only switched off, so Startup apps can turn it on again
            new = ott_startup.remove(text, command) if entry.added else ott_startup.set_enabled(text, command, False)
        else:
            return ""
        try:
            ott_startup.write(new)
        except OSError as e:
            return " " + _("Could not change the startup apps: {error}").format(error=e)
        return " " + (_("It starts at your next login.") if on else _("It no longer starts at login."))

    def _change(self, transform, done_text, same_text):
        # always from the file on disk: another page may have rebuilt since this one was drawn
        if self._busy:
            return
        old = ott_chadwm.read_config()
        try:
            new = transform(old)
        except ValueError as e:
            set_status(self._status, str(e), error=True)
            return
        if new == old:
            self._text = old
            self._show_rules()
            self._sync_login()
            set_status(self._status, same_text)
            return
        self._busy = True
        self._btn_save.set_sensitive(False)
        self._btn_restart.set_visible(False)
        self._busy_spinner(True)
        self._show_rules()
        set_status(self._status, _("Recompiling Ohmychadwm… then a window asks for your password."))
        run_async(lambda: _rebuild(old, new), lambda result: self._applied(result, done_text))

    def _applied(self, result, done_text):
        ok, msg = result
        self._busy = False
        self._busy_spinner(False)
        self._btn_save.set_sensitive(True)
        (log.log_success if ok else log.log_error)(f"App placement: {msg}")
        self._text = ott_chadwm.read_config()
        self._show_rules()
        self._sync_login()
        if not ok:
            set_status(self._status, msg, error=True)
        elif ott_chadwm.can_restart():
            set_status(self._status, done_text + " " + _("Restart Ohmychadwm to use it."))
            self._btn_restart.set_visible(True)
        elif ott_chadwm.in_session():
            set_status(self._status, done_text + " " + _("Press Super+Shift+R to use it."))
        else:
            set_status(self._status, done_text + " " + _("It shows at your next Ohmychadwm login."))

    def _busy_spinner(self, on):
        self._spinner.set_visible(on)
        (self._spinner.start if on else self._spinner.stop)()

    def _on_restart(self, _widget):
        self._btn_restart.set_visible(False)
        ott_chadwm.restart()


def _rebuild(old, new):
    """Write the rules, compile, install with one pkexec; on failure put the old file back. Return (ok, message)."""
    try:
        ott_chadwm.write_config(new)
    except OSError as e:
        return False, f"config.def.h: {e}"
    compiled, msg = ott_chadwm.compile_wm()
    if compiled:
        try:
            installed, err = ott_root.run_root(["--install", ott_chadwm.BUILT_BINARY])
        finally:
            ott_chadwm.clean()
        if installed:
            return True, "Ohmychadwm rebuilt and installed"
        msg = (_("Installing the new Ohmychadwm was cancelled or failed: {error}").format(error=err) if err
               else _("Installing the new Ohmychadwm was cancelled or failed."))
    # the page must never show rules the installed binary doesn't have
    try:
        ott_chadwm.write_config(old)
    except OSError:
        pass
    return False, msg
