"""Default apps page: xdg-mime defaults, and the terminal / file manager on ohmychadwm's keys (sxhkdrc)."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

import log  # noqa: E402
import ott_apps  # noqa: E402
import ott_keys  # noqa: E402
from ott_widgets import (  # noqa: E402
    session_note,
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


class AppsPage:
    """Pick the app per file type, and what Super+Enter / Super+Shift+Enter open."""

    def __init__(self):
        self.widget = page_box()
        self.refresh()

    def refresh(self):
        """Re-read the installed apps and the current defaults."""
        clear(self.widget)
        self._mime_rows = {}
        self.widget.append(section("Terminal & file manager"))
        if (note := session_note()) is not None:
            self.widget.append(note)
        sxhkdrc = ott_keys.read_sxhkdrc()
        self._keys_rows = {}
        if sxhkdrc:
            self.widget.append(muted("What the keys open. Written into ~/.config/ohmychadwm/sxhkd/sxhkdrc and used "
                                     "right away."))
            grid = settings_grid()
            for row, (label, keys, names, hint) in enumerate([
                ("Terminal", ott_apps.TERMINAL_KEYS, ott_apps.TERMINALS, "Super+Enter, Super+T"),
                ("File manager", ott_apps.FILES_KEYS, ott_apps.FILE_MANAGERS, "Super+Shift+Enter, Super+F8"),
            ]):
                now = ott_apps.key_command(sxhkdrc, keys)
                if now is None:
                    continue
                dd = dropdown(ott_apps.installed(names), now)
                dd.set_tooltip_text(hint)
                grid.attach(row_label(label), 0, row, 1, 1)
                grid.attach(dd, 1, row, 1, 1)
                grid.attach(muted(hint), 2, row, 1, 1)
                self._keys_rows[label] = (keys, dd, now)
            self.widget.append(grid)
        else:
            self.widget.append(muted("~/.config/ohmychadwm is not set up for this user, so the keys can't be set."))

        self.widget.append(section("File types"))
        self.widget.append(muted("Which app opens links, folders and files (xdg-mime)."))
        candidates = ott_apps.candidates()
        grid = settings_grid()
        for row, (label, _mimes) in enumerate(ott_apps.CATEGORIES):
            rows = candidates[label]
            if not rows:
                continue
            names = [f"{name} ({did})" for did, name in rows]
            now = ott_apps.current(label)
            current = next((n for n, (did, _name) in zip(names, rows) if did == now), None)
            dd = dropdown(names, current)
            grid.attach(row_label(label), 0, row, 1, 1)
            grid.attach(dd, 1, row, 1, 1)
            self._mime_rows[label] = (dd, dict(zip(names, (did for did, _n in rows))), now)
        self.widget.append(grid)

        self._btn_apply = Gtk.Button(label="Apply")
        self._btn_apply.add_css_class("suggested-action")
        self._btn_apply.set_halign(Gtk.Align.END)
        self._btn_apply.connect("clicked", self._on_apply)
        self.widget.append(self._btn_apply)
        self._status = status_label()
        self.widget.append(self._status)

    def _on_apply(self, _widget):
        keys_changes = [(keys, selected(dd)) for keys, dd, now in self._keys_rows.values()
                        if selected(dd) and selected(dd) != now]
        mime_changes = [(label, ids[selected(dd)]) for label, (dd, ids, now) in self._mime_rows.items()
                        if selected(dd) in ids and ids[selected(dd)] != now]
        if not keys_changes and not mime_changes:
            set_status(self._status, "Nothing changed.")
            return
        self._btn_apply.set_sensitive(False)
        run_async(lambda: _apply(keys_changes, mime_changes), self._applied)

    def _applied(self, errors):
        self._btn_apply.set_sensitive(True)
        for e in errors:
            log.log_error(f"Default apps: {e}")
        self.refresh()
        if errors:
            set_status(self._status, "Some defaults could not be set:\n" + "\n".join(errors), error=True)
        else:
            set_status(self._status, "Applied.")


def _apply(keys_changes, mime_changes):
    """Write sxhkdrc (then reload sxhkd) and the xdg-mime defaults; return a list of errors."""
    errors = []
    if keys_changes:
        text = ott_keys.read_sxhkdrc()
        for keys, command in keys_changes:
            text = ott_apps.set_key_command(text, keys, command)
        try:
            ott_keys.write_sxhkdrc(text)
            ott_apps.reload_sxhkd()
            log.log_success("Default apps: sxhkdrc updated, sxhkd reloaded")
        except OSError as e:
            errors.append(f"sxhkdrc: {e}")
    for label, desktop_id in mime_changes:
        ok, msg = ott_apps.set_default(label, desktop_id)
        if ok:
            log.log_success(f"Default apps: {msg}")
        else:
            errors.append(msg)
    return errors
