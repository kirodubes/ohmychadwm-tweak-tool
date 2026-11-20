"""Themes page: sixteen pictures, one click sets the whole look (wallpaper, login screen, bar, GTK, icons, cursor)."""

import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

import log  # noqa: E402
import ott_apply  # noqa: E402
import ott_chadwm  # noqa: E402
import ott_env  # noqa: E402
import ott_root  # noqa: E402
import ott_system  # noqa: E402
import ott_targets  # noqa: E402
import ott_themes  # noqa: E402
import ott_wallpaper  # noqa: E402
from ott_widgets import muted, page_box, run_async, section, session_note, set_status, status_label  # noqa: E402
from ott_i18n import N_, _  # noqa: E402

_THUMB_W, _THUMB_H = 240, 135
_RESTART_CHECK_MS = 3000


def _tile_css(looks):
    # the frame around each picture shows the bar theme's window border: its colour, its width (doubled to be seen)
    rules = []
    for r in looks:
        width = r.look["border"] or ott_chadwm.theme_values(r.bar or "").get("THEME_BORDER", 1)
        color = r.border_color or "#888888"
        rules.append(f".look-{r.look['key']} {{ border: {max(2, 2 * width)}px solid {color}; }}")
    return "\n".join(rules)


def _bar_options(r):
    """Return the THEME_* overrides of look r: None where it matches what the bar theme sets anyway."""
    own = ott_chadwm.theme_values(r.bar)
    wanted = {"THEME_BORDER": r.look["border"], "THEME_TOPBAR": int(r.look["top"])}
    return {k: None if v is None or v == own.get(k) else v for k, v in wanted.items()}


def _load_pixbuf(path):
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, _THUMB_W, _THUMB_H, False)
    except GLib.Error as e:
        log.log_warn(f"Themes: no thumbnail for {path}: {e.message}")
        return None


class ThemesPage:
    """Sixteen looks as pictures; a click applies the whole look with at most one password prompt."""

    def __init__(self):
        self.widget = page_box()
        self._busy = False
        self._tiles = {}
        self._spinners = {}
        self._looks = ott_themes.resolve_all()

        self.widget.append(section(_("Themes")))
        if (note := session_note()) is not None:
            self.widget.append(note)
        self.widget.append(muted(_(
            "Click a picture to use its whole look: wallpaper, bar colours, window border, GTK theme, icons and "
            "cursor. Ohmychadwm is recompiled and restarted, and your password is asked once.")))
        self._chk_login = Gtk.CheckButton(label=_("Also the login screen (SDDM): the same wallpaper and cursor"))
        self._chk_login.set_active(True)
        if ott_system.background_conf() is None:
            self._chk_login.set_label(_("Also the login screen (SDDM) cursor"))
            self._chk_login.set_tooltip_text(_("This login screen theme can't show another wallpaper."))
        self.widget.append(self._chk_login)

        provider = Gtk.CssProvider()
        provider.load_from_data(_tile_css(self._looks).encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True)
        flow.set_max_children_per_line(4)
        flow.set_valign(Gtk.Align.START)
        flow.set_min_children_per_line(1)
        flow.set_column_spacing(12)
        flow.set_row_spacing(12)
        for r in self._looks:
            flow.append(self._tile(r))
        self.widget.append(flow)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._spinner = Gtk.Spinner()
        self._spinner.set_valign(Gtk.Align.START)
        footer.append(self._spinner)
        self._status = status_label()
        footer.append(self._status)
        self.widget.append(footer)
        self.refresh()

    def _tile(self, r):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_size_request(_THUMB_W, -1)
        frame = Gtk.Frame()
        frame.add_css_class(f"look-{r.look['key']}")
        frame.set_size_request(_THUMB_W, _THUMB_H)
        pic = Gtk.Picture()
        pic.set_content_fit(Gtk.ContentFit.COVER)
        pic.set_can_shrink(True)
        pic.set_size_request(_THUMB_W, _THUMB_H)
        # a spinner over the picture while this look is applied
        overlay = Gtk.Overlay(child=pic)
        spinner = Gtk.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        spinner.set_size_request(48, 48)
        spinner.set_visible(False)
        overlay.add_overlay(spinner)
        self._spinners[r.look["key"]] = spinner
        frame.set_child(overlay)
        box.append(frame)
        name = Gtk.Label(label=r.look["name"], xalign=0)
        name.add_css_class("section-title")
        box.append(name)
        where = _("Bar at the top.") if r.look["top"] else _("Bar at the bottom.")
        for text in (f"{r.look['desc']} {where}", " · ".join(n for n in (r.bar, r.icons, r.cursor) if n)):
            lbl = muted(text)
            lbl.set_max_width_chars(28)  # a wrapped label's natural width is its whole text: keep tiles side by side
            box.append(lbl)
        in_use = Gtk.Label(label=_("In use"), xalign=0)
        in_use.add_css_class("status-line")
        in_use.set_visible(False)
        box.append(in_use)

        btn = Gtk.Button(child=box)
        btn.add_css_class("flat")
        btn.set_halign(Gtk.Align.CENTER)
        if r.usable:
            btn.set_tooltip_text(_("Use the look “{name}”").format(name=r.look["name"]))
            btn.connect("clicked", lambda _widget, look=r: self._on_apply(look))
        else:
            btn.set_sensitive(False)
            btn.set_tooltip_text(_("Not installed: {what}").format(what=", ".join(r.missing)))
        self._tiles[r.look["key"]] = (btn, in_use)
        if r.picture:
            run_async(lambda: _load_pixbuf(r.picture),
                      lambda pixbuf: pic.set_paintable(Gdk.Texture.new_for_pixbuf(pixbuf)) if pixbuf else None)
        return btn

    def refresh(self):
        """Mark the look in use (the Look and Bar pages may have changed it)."""
        if self._busy:
            return
        sel = ott_targets.current()
        bar = ott_chadwm.active_theme(ott_chadwm.read_config())
        for r in self._looks:
            used = (r.bar, r.gtk, r.icons, r.cursor) == (bar, sel.theme, sel.icons, sel.cursor)
            self._tiles[r.look["key"]][1].set_visible(used)

    def _on_apply(self, r):
        if self._busy:
            return
        self._busy = True
        for btn, _in_use in self._tiles.values():
            btn.set_sensitive(False)
        self._working(r, True)
        set_status(self._status, _("Applying “{name}”…").format(name=r.look["name"]))
        login = self._chk_login.get_active()
        threading.Thread(target=self._apply_worker, args=(r, login), daemon=True).start()

    def _apply_worker(self, r, login):
        now = ott_targets.current()
        sel = ott_targets.Selection(r.gtk, r.icons, r.cursor, now.cursor_size, now.font, r.look["dark"])
        wall_ok, wall_msg = ott_wallpaper.apply(r.picture, "fill")
        # Kiro forces GTK_THEME in /etc/environment: when that line is active it must name the new theme too
        force = True if ott_env.read()[1] else None
        background = r.picture if login and ott_system.background_conf() else None
        results, bar_result, notes = ott_apply.apply_look(
            sel, (r.bar, ott_apply.KEEP, _bar_options(r)), force, login, background,
            status=lambda text: GLib.idle_add(set_status, self._status, text))
        if not wall_ok:
            results.append((N_("Wallpaper"), False, wall_msg))
        GLib.idle_add(self._finished, r, results, bar_result, notes)

    def _working(self, r, on):
        for spinner in (self._spinners[r.look["key"]], self._spinner):
            spinner.set_visible(on)
            (spinner.start if on else spinner.stop)()

    def _done(self, r, text, error=False):
        self._busy = False
        self._working(r, False)
        for look in self._looks:
            self._tiles[look.look["key"]][0].set_sensitive(look.usable)
        set_status(self._status, text, error=error)
        self.refresh()
        return False

    def _finished(self, r, results, bar_result, notes):
        failed = [f"{_(label)}: {msg}" for label, ok, msg in results if not ok]
        if bar_result is not None and not bar_result[0]:
            failed.append(bar_result[1])
        if failed:
            return self._done(r, _("Some settings could not be written:") + "\n" + "\n".join(failed), error=True)
        relogin = " " + _("Log out and back in for the system-wide theme.") if notes else ""
        if bar_result is None:
            if notes:
                return self._done(r, _("Applied. Log out and back in to see the new theme everywhere."))
            return self._done(r, _("Applied. Apps you open from now on use the new look."))
        if not ott_chadwm.can_restart():
            if ott_chadwm.in_session():
                return self._done(r, _("Applied. Press Super+Shift+R to see the new bar.") + relogin)
            return self._done(r, _("Applied. The new bar shows at your next Ohmychadwm login.") + relogin)
        # restart at once, so the new bar and window borders show; the spinner keeps turning until it is checked
        set_status(self._status, _("Restarting Ohmychadwm…"))
        ott_chadwm.restart()
        GLib.timeout_add(_RESTART_CHECK_MS, self._restarted, r, relogin)
        return False

    def _restarted(self, r, relogin):
        if ott_chadwm.running_binary() == ott_root.INSTALL_PATH:
            return self._done(r, _("Applied. Ohmychadwm restarted with the new bar.") + relogin)
        # a run.sh from before 2026.11.20 keeps starting /usr/bin/ohmychadwm until the next login
        return self._done(r, _("Applied. Log out and back in once to see the new bar and window borders.") + relogin)
