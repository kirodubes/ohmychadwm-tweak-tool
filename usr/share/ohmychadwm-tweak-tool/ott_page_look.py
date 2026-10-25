"""Look page: GTK theme, icons, cursor + size, font, light/dark and the bar theme + font, kept in sync everywhere."""

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import GLib, Gtk, Pango  # noqa: E402

import log  # noqa: E402
import ott_chadwm  # noqa: E402
import ott_env  # noqa: E402
import ott_root  # noqa: E402
import ott_scan  # noqa: E402
import ott_system  # noqa: E402
import ott_targets  # noqa: E402
from ott_widgets import (  # noqa: E402
    dropdown,
    settings_grid,
    muted,
    row_label,
    section,
    select,
    selected,
    set_status,
    status_label,
    warning,
)

_CURSOR_SIZES = [16, 24, 32, 48, 64]

# Standard freedesktop icon names — every complete icon theme ships these.
_PREVIEW_ICONS = [
    "folder",
    "user-home",
    "folder-download",
    "user-trash",
    "utilities-terminal",
    "internet-web-browser",
    "text-x-generic",
    "image-x-generic",
    "audio-x-generic",
    "preferences-system",
]


def _system_cursor_lines(sel):
    """Return drift lines for the system default and SDDM cursor against sel."""
    sysc = ott_system.read()
    lines = []
    if sysc["default"] != sel.cursor:
        lines.append(f"System default cursor: cursor = {sysc['default'] or 'not set'}")
    if sysc["sddm"] != sel.cursor:
        lines.append(f"Login screen (SDDM): cursor = {sysc['sddm'] or 'not set'}")
    elif sysc["sddm_size"] not in (None, str(sel.cursor_size)):
        lines.append(f"Login screen (SDDM): cursor size = {sysc['sddm_size']}")
    return lines


# ── The page ─────────────────────────────────────────────────────────────────


class LookPage:
    """Drift banner, GTK pickers, ohmychadwm bar theme + font, Apply."""

    own_scroll = True

    def __init__(self):
        self._gtk_themes = ott_scan.gtk_themes()
        self._preview_theme = Gtk.IconTheme()
        self._preview_theme.set_search_path(ott_scan.icon_theme_search_path())
        self._busy = False

        state = ott_targets.read_all()
        sel = ott_targets.current(state)
        self._forced = state.get(ott_targets.SYSTEM) is not None
        sysc = ott_system.read()
        self._sys_cursor_follows = sysc["default"] == sel.cursor and sysc["sddm"] in (None, sel.cursor)
        config = ott_chadwm.read_config()
        self._has_chadwm = bool(config)

        self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.widget.append(self._build_banner())

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for side in ("start", "end", "top", "bottom"):
            getattr(body, f"set_margin_{side}")(18)
        body.append(self._build_gtk_section(sel))
        body.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        body.append(self._build_bar_section(sel, config))
        scroller.set_child(body)
        self.widget.append(scroller)

        self.widget.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self.widget.append(self._build_footer())

        self._update_theme_note()
        self._update_force_note()
        self._update_icon_preview()
        self._update_font_warning()
        self._refresh_drift(state)

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_banner(self):
        self._banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self._banner.add_css_class("drift-banner")
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_hexpand(True)
        title = Gtk.Label(label="Your settings are out of sync", xalign=0)
        title.add_css_class("drift-title")
        self._banner_detail = muted()
        text.append(title)
        text.append(self._banner_detail)
        fix = Gtk.Button(label="Fix all")
        fix.set_valign(Gtk.Align.CENTER)
        fix.set_tooltip_text("Write the choices below to every settings file")
        fix.connect("clicked", self._on_apply)
        self._banner.append(text)
        self._banner.append(fix)
        return self._banner

    def _build_gtk_section(self, sel):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.append(section("Applications"))
        box.append(muted("Used by Thunar and every GTK 2, 3 and 4 application."))
        grid = settings_grid()

        self._dd_theme = dropdown(self._gtk_themes.keys(), sel.theme)
        self._dd_theme.connect("notify::selected", lambda *_: self._update_theme_note())
        self._theme_note = muted()
        grid.attach(row_label("Theme"), 0, 0, 1, 1)
        grid.attach(self._dd_theme, 1, 0, 2, 1)
        grid.attach(self._theme_note, 1, 1, 2, 1)
        self._chk_force = Gtk.CheckButton(label="Force this theme on every app (system-wide)")
        self._chk_force.set_tooltip_text(
            "Sets GTK_THEME in /etc/environment, as Kiro ships it. Needs your password; shows after re-login."
        )
        self._chk_force.set_active(self._forced)
        self._chk_force.connect("toggled", lambda *_: self._update_force_note())
        self._force_note = warning()
        force_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        force_box.append(self._chk_force)
        force_box.append(self._force_note)
        grid.attach(force_box, 1, 7, 2, 1)

        self._chk_sys_cursor = Gtk.CheckButton(
            label="Also use this cursor on the login screen and as the system default"
        )
        self._chk_sys_cursor.set_tooltip_text(
            "Sets /usr/share/icons/default and the SDDM CursorTheme / CursorSize. Needs your password."
        )
        self._chk_sys_cursor.set_active(self._sys_cursor_follows)
        self._chk_sys_cursor.connect("toggled", lambda *_: self._refresh_drift())
        grid.attach(self._chk_sys_cursor, 1, 8, 2, 1)

        self._dd_icons = dropdown(ott_scan.icon_themes(), sel.icons)
        self._dd_icons.connect("notify::selected", lambda *_: self._update_icon_preview())
        self._icon_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._icon_strip.add_css_class("icon-strip")
        grid.attach(row_label("Icons"), 0, 2, 1, 1)
        grid.attach(self._dd_icons, 1, 2, 2, 1)
        grid.attach(self._icon_strip, 1, 3, 2, 1)

        self._dd_cursor = dropdown(ott_scan.cursor_themes(), sel.cursor)
        sizes = [str(s) for s in sorted(set(_CURSOR_SIZES) | {sel.cursor_size})]
        self._dd_size = Gtk.DropDown.new_from_strings(sizes)
        self._dd_size.set_selected(sizes.index(str(sel.cursor_size)))
        self._dd_size.set_tooltip_text("Cursor size in pixels")
        grid.attach(row_label("Cursor"), 0, 4, 1, 1)
        grid.attach(self._dd_cursor, 1, 4, 1, 1)
        grid.attach(self._dd_size, 2, 4, 1, 1)

        self._font_btn = Gtk.FontDialogButton(dialog=Gtk.FontDialog(title="Choose a font"))
        self._font_btn.set_font_desc(Pango.FontDescription.from_string(sel.font))
        self._font_btn.set_hexpand(True)
        self._font_btn.connect("notify::font-desc", lambda *_: self._update_font_warning())
        grid.attach(row_label("Font"), 0, 5, 1, 1)
        grid.attach(self._font_btn, 1, 5, 2, 1)

        self._chk_light = Gtk.CheckButton(label="Light")
        self._chk_dark = Gtk.CheckButton(label="Dark")
        self._chk_dark.set_group(self._chk_light)
        (self._chk_dark if sel.dark else self._chk_light).set_active(True)
        style = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        style.append(self._chk_light)
        style.append(self._chk_dark)
        style.set_tooltip_text("Preferred style for apps that follow it (GTK 4 / libadwaita)")
        grid.attach(row_label("Style"), 0, 6, 1, 1)
        grid.attach(style, 1, 6, 2, 1)

        box.append(grid)
        return box

    def _build_bar_section(self, sel, config):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.append(section("Ohmychadwm bar"))
        if not self._has_chadwm:
            box.append(muted("~/.config/ohmychadwm is not set up for this user — log into Ohmychadwm once first."))
            self._dd_bar = None
            self._chk_bar_font = None
            self._font_warning = muted()
            return box
        box.append(muted(
            "Colours and font of the top bar. Changing these recompiles Ohmychadwm (asks your password once)."
        ))
        grid = settings_grid()

        self._bar_theme_now = ott_chadwm.active_theme(config) or ""
        self._dd_bar = dropdown(ott_chadwm.themes(), self._bar_theme_now)
        grid.attach(row_label("Bar theme"), 0, 0, 1, 1)
        grid.attach(self._dd_bar, 1, 0, 1, 1)

        self._bar_font_now = ott_chadwm.bar_font(config)
        self._chk_bar_font = Gtk.CheckButton(label="Also use the font above for the bar")
        self._chk_bar_font.set_active(self._bar_font_now is not None)
        self._chk_bar_font.connect("toggled", lambda *_: self._update_font_warning())
        grid.attach(self._chk_bar_font, 1, 1, 1, 1)
        self._font_warning = warning()
        grid.attach(self._font_warning, 1, 2, 1, 1)

        box.append(grid)
        return box

    def _build_footer(self):
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for side in ("start", "end", "top", "bottom"):
            getattr(footer, f"set_margin_{side}")(12)
        self._status = status_label()
        self._btn_restart = Gtk.Button(label="Restart Ohmychadwm now")
        self._btn_restart.set_visible(False)
        self._btn_restart.connect("clicked", self._on_restart)
        reset = Gtk.Button(label="Reset to Kiro default")
        reset.connect("clicked", self._on_reset)
        self._btn_apply = Gtk.Button(label="Apply")
        self._btn_apply.add_css_class("suggested-action")
        self._btn_apply.connect("clicked", self._on_apply)
        footer.append(self._status)
        footer.append(self._btn_restart)
        footer.append(reset)
        footer.append(self._btn_apply)
        return footer

    # ── Live feedback ────────────────────────────────────────────────────────

    def _update_theme_note(self):
        name = selected(self._dd_theme)
        if self._gtk_themes.get(name, True):
            self._theme_note.set_label("")
            self._theme_note.set_visible(False)
        else:
            self._theme_note.set_label("This theme has no GTK 4 version — GTK 4 apps will look like Adwaita.")
            self._theme_note.set_visible(True)

    def _update_force_note(self):
        if self._chk_force.get_active():
            self._force_note.set_visible(False)
        else:
            self._force_note.set_label(
                "Without it, apps follow your personal settings — some GTK 4 / libadwaita apps may keep their own look."
            )
            self._force_note.set_visible(True)

    def _update_icon_preview(self):
        while (child := self._icon_strip.get_first_child()) is not None:
            self._icon_strip.remove(child)
        self._preview_theme.set_theme_name(selected(self._dd_icons))
        for name in _PREVIEW_ICONS:
            paintable = self._preview_theme.lookup_icon(name, None, 32, 1, Gtk.TextDirection.NONE, 0)
            image = Gtk.Image.new_from_paintable(paintable)
            image.set_pixel_size(32)
            image.set_tooltip_text(name)
            self._icon_strip.append(image)

    def _font_desc(self):
        desc = self._font_btn.get_font_desc()
        return desc if desc is not None else Pango.FontDescription.from_string("Sans 11")

    def _update_font_warning(self):
        if self._chk_bar_font is None:
            return
        family = self._font_desc().get_family() or ""
        if self._chk_bar_font.get_active() and not ott_scan.is_nerd_font(family):
            self._font_warning.set_label(
                f"“{family}” is not a Nerd Font — the bar's tag icons may show as empty boxes."
            )
            self._font_warning.set_visible(True)
        else:
            self._font_warning.set_visible(False)

    def _system_cursor_drift(self, sel):
        return _system_cursor_lines(sel) if self._chk_sys_cursor.get_active() else []

    def _refresh_drift(self, state=None):
        sel = self._selection()
        lines = ott_targets.drift(sel, state) + self._system_cursor_drift(sel)
        self._banner_detail.set_label("\n".join(lines))
        self._banner.set_visible(bool(lines))

    def _set_status(self, text, error=False):
        set_status(self._status, text, error)
        return False

    # ── Reading the widgets ──────────────────────────────────────────────────

    def _selection(self):
        desc = self._font_desc()
        return ott_targets.Selection(
            theme=selected(self._dd_theme),
            icons=selected(self._dd_icons),
            cursor=selected(self._dd_cursor),
            cursor_size=int(selected(self._dd_size)),
            font=ott_targets.norm_font(desc.to_string()),
            dark=self._chk_dark.get_active(),
        )

    def _bar_plan(self):
        """Return (theme, font-or-None) wanted for the bar, or None when ohmychadwm isn't set up."""
        if self._dd_bar is None:
            return None
        font = None
        if self._chk_bar_font.get_active():
            desc = self._font_desc()
            font = (desc.get_family() or "Sans", max(1, round(desc.get_size() / Pango.SCALE)))
        return selected(self._dd_bar), font

    # ── Actions ──────────────────────────────────────────────────────────────

    def _on_reset(self, _widget):
        sel = ott_targets.kiro_default()
        select(self._dd_theme, sel.theme)
        select(self._dd_icons, sel.icons)
        select(self._dd_cursor, sel.cursor)
        select(self._dd_size, str(sel.cursor_size))
        self._font_btn.set_font_desc(Pango.FontDescription.from_string(sel.font))
        (self._chk_dark if sel.dark else self._chk_light).set_active(True)
        self._chk_force.set_active(True)  # the Kiro ISO ships GTK_THEME forced
        self._chk_sys_cursor.set_active(True)  # ...and the same cursor for SDDM and /usr/share/icons/default
        if self._dd_bar is not None:
            select(self._dd_bar, ott_chadwm.default_theme())
            self._chk_bar_font.set_active(False)
        self._set_status("Kiro defaults loaded for everything — press Apply to use them.")

    def _on_apply(self, _widget):
        if self._busy:
            return
        self._busy = True
        self._btn_apply.set_sensitive(False)
        self._btn_restart.set_visible(False)
        self._set_status("Applying…")
        sel = self._selection()
        bar = self._bar_plan()
        force = self._chk_force.get_active()
        sys_cursor = self._chk_sys_cursor.get_active()
        threading.Thread(target=self._apply_worker, args=(sel, bar, force, sys_cursor), daemon=True).start()

    def _apply_worker(self, sel, bar, force, sys_cursor):
        log.log_section("Apply")
        results = ott_targets.apply(sel)
        for label, ok, msg in results:
            (log.log_success if ok else log.log_error)(f"{label}: {msg}")

        root_args, notes, bar_result = [], [], None
        env_theme, env_active = ott_env.read()
        if force and (not env_active or env_theme != sel.theme):
            root_args += ["--gtk-theme", sel.theme]
            notes.append("theme")
        elif not force and env_active:
            root_args.append("--release-gtk-theme")
            notes.append("theme")
        if sys_cursor and _system_cursor_lines(sel):
            root_args += ["--system-cursor", sel.cursor, "--cursor-size", str(sel.cursor_size)]

        compiled = False
        if bar is not None:
            theme, font = bar
            try:
                text = ott_chadwm.read_config()
                new = ott_chadwm.set_theme(text, theme)
                new = ott_chadwm.set_bar_font(new, *font) if font else ott_chadwm.clear_bar_font(new)
                if new != text:
                    GLib.idle_add(self._set_status, "Recompiling Ohmychadwm…")
                    ott_chadwm.write_config(new)
                    compiled, msg = ott_chadwm.compile_wm()
                    if compiled:
                        root_args += ["--install", ott_chadwm.BUILT_BINARY]
                    else:
                        bar_result = (False, msg)
            except (OSError, ValueError) as e:
                # must still reach _apply_finished, or Apply stays greyed out until restart
                bar_result = (False, f"Ohmychadwm bar: {e}")

        if root_args:
            # one pkexec for everything that needs root, so at most one password prompt
            GLib.idle_add(self._set_status, "Waiting for your password…")
            ok, err = ott_root.run_root(root_args)
            if not ok:
                results.append(("System changes", False, "cancelled or failed" + (f": {err}" if err else "")))
                notes.clear()
            elif compiled:
                bar_result = (True, "Ohmychadwm rebuilt and installed")
        if compiled:
            ott_chadwm.clean()
        if bar_result is not None:
            (log.log_success if bar_result[0] else log.log_error)(bar_result[1])
        GLib.idle_add(self._apply_finished, results, bar_result, notes)

    def _apply_finished(self, results, bar_result, notes):
        self._busy = False
        self._btn_apply.set_sensitive(True)
        failed = [f"{label}: {msg}" for label, ok, msg in results if not ok]
        if bar_result is not None and not bar_result[0]:
            failed.append(bar_result[1])
        if failed:
            self._set_status("Some settings could not be written:\n" + "\n".join(failed), error=True)
        elif bar_result is not None:
            relogin = " Log out and back in for the system-wide theme." if notes else ""
            if ott_chadwm.can_restart():
                self._set_status("Applied. Restart Ohmychadwm to see the new bar." + relogin)
                self._btn_restart.set_visible(True)
            else:
                self._set_status("Applied. Press Super+Shift+R to see the new bar." + relogin)
        elif notes:
            self._set_status("Applied. Log out and back in to see the new theme everywhere.")
        else:
            self._set_status("Applied. Apps you open from now on use the new look.")
        self._refresh_drift()
        return False

    def _on_restart(self, _widget):
        self._btn_restart.set_visible(False)
        ott_chadwm.restart()
