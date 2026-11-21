"""App placement page: the screen, workspace and floating of an app's windows (chadwm rules[], rebuilds ohmychadwm)."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Pango  # noqa: E402

import log  # noqa: E402
import ott_chadwm  # noqa: E402
import ott_placement  # noqa: E402
import ott_root  # noqa: E402
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
    """Return one line of what a rule does, e.g. "When firefox opens: screen 2 (HDMI-1) · workspace 10"."""
    parts = []
    if rule["monitor"] >= 0:
        name = next((n for num, n, _size in monitors if num == rule["monitor"]), None)
        parts.append(_("screen {n} ({name})").format(n=rule["monitor"] + 1, name=name) if name
                     else _("screen {n}, not connected now").format(n=rule["monitor"] + 1))
    if rule["workspace"]:
        parts.append(_("workspace {n}").format(n=rule["workspace"]))
    elif rule["workspace"] is None:
        parts.append(_("workspaces {mask}").format(mask=rule["tags"]))
    if rule["mode"] in ("float", "center"):
        parts.append(_mode_labels()[rule["mode"]].lower())
    elif rule["mode"] is None:
        parts.append(_("own floating settings"))
    if rule["instance"] or rule["title"]:
        parts.append(_("only windows named “{name}”").format(name=rule["title"] or rule["instance"]))
    if not parts:
        return _("When {app} opens: no effect, it opens like any other app").format(app=rule["class"] or "*")
    return _("When {app} opens: {placement}").format(app=rule["class"] or "*", placement=" · ".join(parts))


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
                                   "password); it takes effect the next time the app opens a window.")))
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
        for b in (reread, self._btn_restart, self._btn_save):
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
                  for cls, title, now in self._choices]
        self._dd_app.set_model(Gtk.StringList.new(labels or [_("No apps found: open the app, then press Refresh")]))
        self._dd_screen.set_model(Gtk.StringList.new(
            [_("The screen you are working on")]
            + [_("Screen {n}: {name} ({size})").format(n=num + 1, name=name, size=size)
               for num, name, size in self._monitors]))
        self._show_rules()

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
            self._rules_box.append(muted(_("Rules now. They only move a window when you open the app; they never "
                                           "start it (that is the Startup apps page).")))
        for rule in rules:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            label = Gtk.Label(label=summary(rule, self._monitors), xalign=0)
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
        cls = self._choices[self._dd_app.get_selected()][0]
        screen = self._dd_screen.get_selected()
        monitor = self._monitors[screen - 1][0] if 0 < screen <= len(self._monitors) else -1
        workspace, mode = self._dd_workspace.get_selected(), list(_mode_labels())[self._dd_mode.get_selected()]
        if workspace == 0 and monitor == -1 and mode == "tiled":
            set_status(self._status, _("Choose a screen, a workspace or floating for {name}: as it is, the rule would "
                                       "change nothing.").format(name=cls), error=True)
            return
        self._change(lambda text: ott_placement.set_rule(text, cls, workspace, monitor, mode),
                     _("Saved the rule for {name}.").format(name=cls))

    def _on_remove(self, _widget, cls):
        self._change(lambda text: ott_placement.remove_rule(text, cls),
                     _("Removed the rule for {name}.").format(name=cls))

    def _change(self, transform, done_text):
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
            set_status(self._status, _("This rule is already there."))
            return
        self._busy = True
        self._btn_save.set_sensitive(False)
        self._btn_restart.set_visible(False)
        self._show_rules()
        set_status(self._status, _("Recompiling Ohmychadwm…"))
        run_async(lambda: _rebuild(old, new), lambda result: self._applied(result, done_text))

    def _applied(self, result, done_text):
        ok, msg = result
        self._busy = False
        self._btn_save.set_sensitive(True)
        (log.log_success if ok else log.log_error)(f"App placement: {msg}")
        self._text = ott_chadwm.read_config()
        self._show_rules()
        if not ok:
            set_status(self._status, msg, error=True)
        elif ott_chadwm.can_restart():
            set_status(self._status, done_text + " " + _("Restart Ohmychadwm to use it."))
            self._btn_restart.set_visible(True)
        elif ott_chadwm.in_session():
            set_status(self._status, done_text + " " + _("Press Super+Shift+R to use it."))
        else:
            set_status(self._status, done_text + " " + _("It shows at your next Ohmychadwm login."))

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
