#!/usr/bin/env python3
"""Ohmychadwm Tweak Tool — look, bar, wallpaper, displays, input, startup, apps and keys for ohmychadwm."""

# ── Force Python UTF-8 mode on a non-UTF-8 locale ─────────────────────────
# Never crash on a non-UTF-8 system locale (e.g. latin-1 fr_BE). Re-exec only
# when the locale's encoding is not UTF-8; the re-exec'd process is UTF-8, so
# the guard is loop-safe.
import codecs
import os
import subprocess
import sys
import time

if codecs.lookup(sys.getfilesystemencoding()).name != "utf-8":
    os.environ["PYTHONUTF8"] = "1"
    os.execv(sys.executable, [sys.executable, "-X", "utf8", *sys.argv])

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import ott_config  # noqa: E402
import ott_display  # noqa: E402
import ott_env  # noqa: E402
import ott_gui  # noqa: E402
import log  # noqa: E402

_FIRST_LOGIN_MARK = "first_login_shown"
_DPMS_MARK = "dpms_sleep_15"
# First login only: open as a centred floating window instead of a tile (next to the installer on a small screen)
_FLOAT = False
_INTERFACE_SCHEMA = "org.gnome.desktop.interface"
_THEME_DIRS = ("~/.themes", "~/.local/share/themes", "/usr/share/themes")
_RESTART_POLL_MS = 500


def _gresource_theme(name):
    """Return True when the GTK theme keeps its GTK 4 stylesheet in a gresource (Arc, Arc-Dark, Arc-Lighter)."""
    return bool(name) and any(os.path.isfile(os.path.join(os.path.expanduser(d), name, "gtk-4.0", "gtk.gresource"))
                              for d in _THEME_DIRS)


def _forced_theme():
    theme, active = ott_env.read()
    return theme if active and theme else None


def _follow_forced_theme():
    # the session's GTK_THEME is what /etc/environment said at login; a restart after a look must use today's line
    theme = _forced_theme()
    if theme:
        os.environ["GTK_THEME"] = theme
    else:
        os.environ.pop("GTK_THEME", None)


def _pkexec_running():
    me = str(os.getpid())
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
                fields = f.read().rsplit(")", 1)[1].split()
            with open(f"/proc/{pid}/comm", encoding="utf-8") as f:
                comm = f.read().strip()
        except OSError:
            continue
        if fields[1] == me and comm == "pkexec":
            return True
    return False


class TweakApp(Gtk.Application):
    """GTK4 application entry point for ohmychadwm-tweak-tool."""

    def __init__(self):
        super().__init__(application_id="com.kiro.ohmychadwm-tweak-tool")
        self._interface = None
        self._window = None
        self._theme_at_start = None
        self._restart_pending = False
        self.connect("startup", self._on_startup)
        self.connect("activate", self.on_activate)

    def _on_startup(self, _app):
        # Plain GTK4 (no libadwaita) ignores the desktop's color-scheme, so follow it here,
        # live. Dark unless the desktop asks for light: Kiro's ohmychadwm is dark.
        source = Gio.SettingsSchemaSource.get_default()
        if source and source.lookup(_INTERFACE_SCHEMA, True):
            self._interface = Gio.Settings.new(_INTERFACE_SCHEMA)
            self._interface.connect("changed::color-scheme", lambda *_args: self._apply_color_scheme())
            self._interface.connect("changed::gtk-theme", lambda *_args: self._on_theme_changed())
            self._theme_at_start = self._interface.get_string("gtk-theme")
        # GTK_THEME beats gtk-theme and prefer-dark: an Apply that only rewrites that line (Style Dark when
        # gsettings already says adw-gtk3-dark) would leave this window on the old, light theme
        self._env_monitor = Gio.File.new_for_path(ott_env.ENV_FILE).monitor_file(Gio.FileMonitorFlags.NONE, None)
        self._env_monitor.connect("changed", lambda *_args: self._on_forced_theme_changed())
        self._apply_color_scheme(starting=True)

    def _on_forced_theme_changed(self):
        if _forced_theme() != os.environ.get("GTK_THEME"):
            self._restart_soon()

    def _apply_color_scheme(self, starting=False):
        scheme = self._interface.get_string("color-scheme") if self._interface else "prefer-dark"
        settings = Gtk.Settings.get_default()
        want = Gtk.InterfaceColorScheme.LIGHT if scheme == "prefer-light" else Gtk.InterfaceColorScheme.DARK
        log.debug_print(f"color-scheme {scheme}")
        # set the scheme itself: prefer-dark=true read from settings.ini leaves it DEFAULT (light), and
        # adw-gtk3(-dark) only turns dark on @media (prefers-color-scheme: dark)
        if want == settings.props.gtk_interface_color_scheme:
            return
        if not starting and _gresource_theme(settings.props.gtk_theme_name):
            # GTK 4.24 drops an Arc theme's stylesheet when light/dark changes in an open window: see-through
            self._restart_soon()
            return
        settings.props.gtk_interface_color_scheme = want

    def _on_theme_changed(self):
        # an open GTK 4 window can't take a new theme reliably (Arc goes see-through); a fresh start always can
        if self._interface.get_string("gtk-theme") != self._theme_at_start:
            self._restart_soon()

    def _restart_soon(self):
        if self._restart_pending or self._window is None:
            return
        self._restart_pending = True
        GLib.timeout_add(_RESTART_POLL_MS, self._restart_when_idle)

    def _restart_when_idle(self):
        pages = getattr(self._window, "ott_pages", {})
        if any(getattr(page, "_busy", False) for page in pages.values()) or _pkexec_running():
            return True  # a look is still being applied or a password is asked: try again
        page = self._window.ott_stack.get_visible_child_name()
        self._window.save_size()
        args = [
            a for i, a in enumerate(sys.argv[1:], 1)
            if a not in ("--page", "--first-login") and sys.argv[i - 1] != "--page"
        ]
        log.log_info(f"GTK theme changed: restarting on the {page} page")
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__), *args, "--page", page])
        return False

    def on_activate(self, _app):
        """Show the main window, creating it on the first activation only."""
        # Ctrl+Alt+H while the app is open activates this instance again: raise the window, don't add a second one
        window = self.get_active_window() or Main(self)
        self._window = window
        window.present()


class Main(Gtk.ApplicationWindow):
    """Main application window."""

    def __init__(self, app):
        super().__init__(application=app, title="Ohmychadwm Tweak Tool")
        prefs = ott_config.load_prefs()
        self.set_default_size(prefs.get("window_width", 900), prefs.get("window_height", 680))
        self.connect("close-request", self._on_close)
        if _FLOAT:
            self.connect("realize", self._mark_dialog)
        self._load_css()
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)
        ott_gui.build(self)
        log.log_timing("GUI built")

    def _load_css(self):
        css_path = os.path.join(BASE_DIR, "ott.css")
        if not os.path.isfile(css_path):
            return
        provider = Gtk.CssProvider()
        provider.load_from_path(css_path)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _mark_dialog(self, _window):
        # chadwm floats and centres a dialog-type window, but reads the type only when the window maps; GTK 4 has no
        # type hint, so xprop sets it here, between realize and map. Synchronous on purpose: it must land before map.
        xid = getattr(self.get_surface(), "get_xid", None)
        if xid is None:
            return
        try:
            subprocess.run(
                ["xprop", "-id", str(xid()), "-f", "_NET_WM_WINDOW_TYPE", "32a",
                 "-set", "_NET_WM_WINDOW_TYPE", "_NET_WM_WINDOW_TYPE_DIALOG"],
                timeout=2, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            log.log_warn(f"first login: could not float the window: {e}")

    def save_size(self):
        """Remember the window size for the next start."""
        w, h = self.get_default_size()
        ott_config.update_prefs({"window_width": w, "window_height": h})

    def _on_close(self, _window):
        self.save_size()
        return False


def main():
    """Parse flags and run the application."""
    if "--debug" in sys.argv:
        log.DEBUG = True
    # once per user, also at the --first-login start of every login (which quits right after the first one)
    if not ott_config.load_prefs().get(_DPMS_MARK):
        changed = ott_display.dpms_sleep_to_15()
        if changed is not None:
            ott_config.update_prefs({_DPMS_MARK: time.strftime("%Y-%m-%d")})
            if changed:
                log.log_info(f"Screens now sleep after 15 minutes: {', '.join(changed)}")
    if "--first-login" in sys.argv:
        # every login, after run.sh ran the saved layout: a screen on a second GPU can come up under another name
        renamed = ott_display.heal_layout()
        if renamed:
            log.log_info("Screen layout follows renamed outputs: "
                         + ", ".join(f"{old} -> {new}" for old, new in renamed.items()))
        # run.sh starts this at every login; only the first one opens the window. Checked after the UTF-8 re-exec,
        # so the mark written here can't make the re-exec'd process quit.
        if ott_config.load_prefs().get(_FIRST_LOGIN_MARK):
            return
        ott_config.update_prefs({_FIRST_LOGIN_MARK: time.strftime("%Y-%m-%d")})
        ott_gui.START_PAGE = "displays"
        global _FLOAT
        _FLOAT = True
    if "--page" in sys.argv[:-1]:
        ott_gui.START_PAGE = sys.argv[sys.argv.index("--page") + 1]
    log.log_section("Ohmychadwm Tweak Tool")
    _follow_forced_theme()
    TweakApp().run(None)


if __name__ == "__main__":
    main()
