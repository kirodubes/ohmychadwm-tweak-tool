#!/usr/bin/env python3
"""Ohmychadwm Tweak Tool — look, bar, wallpaper, displays, input, startup, apps and keys for ohmychadwm."""

# ── Force Python UTF-8 mode on a non-UTF-8 locale ─────────────────────────
# Never crash on a non-UTF-8 system locale (e.g. latin-1 fr_BE). Re-exec only
# when the locale's encoding is not UTF-8; the re-exec'd process is UTF-8, so
# the guard is loop-safe.
import codecs
import os
import sys

if codecs.lookup(sys.getfilesystemencoding()).name != "utf-8":
    os.environ["PYTHONUTF8"] = "1"
    os.execv(sys.executable, [sys.executable, "-X", "utf8", *sys.argv])

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import ott_config  # noqa: E402
import ott_gui  # noqa: E402
import log  # noqa: E402

_INTERFACE_SCHEMA = "org.gnome.desktop.interface"


class TweakApp(Gtk.Application):
    """GTK4 application entry point for ohmychadwm-tweak-tool."""

    def __init__(self):
        super().__init__(application_id="com.kiro.ohmychadwm-tweak-tool")
        self._interface = None
        self.connect("startup", self._on_startup)
        self.connect("activate", self.on_activate)

    def _on_startup(self, _app):
        # Plain GTK4 (no libadwaita) ignores the desktop's color-scheme, so follow it here,
        # live. Dark unless the desktop asks for light: Kiro's ohmychadwm is dark.
        source = Gio.SettingsSchemaSource.get_default()
        if source and source.lookup(_INTERFACE_SCHEMA, True):
            self._interface = Gio.Settings.new(_INTERFACE_SCHEMA)
            self._interface.connect("changed::color-scheme", lambda *_args: self._apply_color_scheme())
        self._apply_color_scheme()

    def _apply_color_scheme(self):
        scheme = self._interface.get_string("color-scheme") if self._interface else "prefer-dark"
        Gtk.Settings.get_default().props.gtk_application_prefer_dark_theme = scheme != "prefer-light"
        log.debug_print(f"color-scheme {scheme}")

    def on_activate(self, _app):
        """Show the main window, creating it on the first activation only."""
        # Ctrl+Alt+H while the app is open activates this instance again: raise the window, don't add a second one
        window = self.get_active_window() or Main(self)
        window.present()


class Main(Gtk.ApplicationWindow):
    """Main application window."""

    def __init__(self, app):
        super().__init__(application=app, title="Ohmychadwm Tweak Tool")
        prefs = ott_config.load_prefs()
        self.set_default_size(prefs.get("window_width", 900), prefs.get("window_height", 680))
        self.connect("close-request", self._on_close)
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

    def _on_close(self, _window):
        w, h = self.get_default_size()
        ott_config.update_prefs({"window_width": w, "window_height": h})
        return False


def main():
    """Parse flags and run the application."""
    if "--debug" in sys.argv:
        log.DEBUG = True
    if "--page" in sys.argv[:-1]:
        ott_gui.START_PAGE = sys.argv[sys.argv.index("--page") + 1]
    log.log_section("Ohmychadwm Tweak Tool")
    TweakApp().run(None)


if __name__ == "__main__":
    main()
