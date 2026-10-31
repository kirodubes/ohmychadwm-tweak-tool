"""Wallpaper page: pick from the Ohmychadwm wallpapers or Variety's folders, set it with feh (kept via ~/.fehbg)."""

import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango  # noqa: E402

import log  # noqa: E402
import ott_wallpaper  # noqa: E402
from ott_widgets import dropdown, muted, page_box, section, selected, session_note, set_status  # noqa: E402
from ott_i18n import _  # noqa: E402

_CHOOSE = _("Choose folder…")
_THUMB_W, _THUMB_H = 160, 100


class WallpaperPage:
    """Thumbnail picker with preview; Apply sets the wallpaper now and feh remembers it."""

    def __init__(self, window):
        self._window = window
        self._sources = ott_wallpaper.sources()
        self._custom = None
        self._load_gen = 0
        current, mode = ott_wallpaper.current()
        self._selected = current if os.path.isfile(current) else None

        box = page_box()
        box.append(section(_("Wallpaper")))
        if (note := session_note()) is not None:
            box.append(note)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.append(Gtk.Label(label=_("Show"), xalign=0))
        self._source = Gtk.DropDown.new_from_strings([label for label, _dirs in self._sources] + [_CHOOSE])
        self._source.connect("notify::selected", self._on_source_changed)
        row.append(self._source)
        box.append(row)

        self._empty = muted()
        self._empty.set_visible(False)
        box.append(self._empty)
        self._btn_fetch = Gtk.Button(label=_("Start Variety to download wallpapers"))
        self._btn_fetch.set_halign(Gtk.Align.START)
        self._btn_fetch.set_visible(False)
        self._btn_fetch.connect("clicked", self._on_start_variety)
        box.append(self._btn_fetch)

        self._flow = Gtk.FlowBox()
        self._flow.set_valign(Gtk.Align.START)
        self._flow.set_max_children_per_line(20)
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flow.set_homogeneous(True)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(-1, 300)
        scroll.set_vexpand(True)
        scroll.set_child(self._flow)
        box.append(scroll)

        self._preview = Gtk.Picture()
        self._preview.set_can_shrink(True)
        self._preview.set_content_fit(Gtk.ContentFit.CONTAIN)
        self._preview.set_size_request(-1, 180)
        self._preview.set_visible(False)
        box.append(self._preview)

        self._path = Gtk.Label(label=_("No wallpaper selected"), xalign=0)
        self._path.set_ellipsize(Pango.EllipsizeMode.START)
        box.append(self._path)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_prev = Gtk.Button(label=_("Previous (Variety)"))
        btn_prev.connect("clicked", lambda _w: self._variety("--previous"))
        btn_next = Gtk.Button(label=_("Next (Variety)"))
        btn_next.connect("clicked", lambda _w: self._variety("--next"))
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self._dd_mode = dropdown(ott_wallpaper.MODES, mode)
        self._dd_mode.set_hexpand(False)
        self._dd_mode.set_tooltip_text(_("fill: cover the screen · scale: stretch · center · max: fit · tile"))
        self._btn_apply = Gtk.Button(label=_("Apply wallpaper"))
        self._btn_apply.add_css_class("suggested-action")
        self._btn_apply.set_sensitive(self._selected is not None)
        self._btn_apply.connect("clicked", self._on_apply)
        buttons.append(btn_prev)
        buttons.append(btn_next)
        buttons.append(spacer)
        buttons.append(self._dd_mode)
        buttons.append(self._btn_apply)
        box.append(buttons)

        self._status = muted()
        box.append(self._status)

        self.widget = box
        if self._selected:
            self._show_selected(self._selected)
        # open on the first source that has images: Variety's folders stay empty until Variety has run
        first = next((i for i, (_label, dirs) in enumerate(self._sources) if ott_wallpaper.list_images(dirs)), 0)
        if first:
            self._source.set_selected(first)  # notify::selected loads it
        else:
            self._load(self._sources[0][1])

    # ── Loading thumbnails ───────────────────────────────────────────────────

    def _on_source_changed(self, dd, _pspec):
        index = dd.get_selected()
        if index < len(self._sources):
            self._load(self._sources[index][1])
            return
        dialog = Gtk.FileDialog(title=_("Choose a wallpaper folder"))
        dialog.set_initial_folder(Gio.File.new_for_path(self._custom or os.path.expanduser("~/Pictures")))
        dialog.select_folder(self._window, None, self._on_folder_chosen)

    def _on_folder_chosen(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        self._custom = folder.get_path()
        self._load([self._custom])

    def _load(self, folders):
        self._load_gen += 1
        gen = self._load_gen
        child = self._flow.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._flow.remove(child)
            child = nxt
        images = ott_wallpaper.list_images(folders)
        in_variety = any(f.startswith(ott_wallpaper.VARIETY_DIR) for f in folders)
        self._empty.set_visible(not images)
        self._empty.set_text(_("No images here yet. Variety fills this folder while it runs.") if in_variety
                             else _("No images here yet."))
        self._btn_fetch.set_visible(not images and in_variety)
        log.debug_print(f"{len(images)} wallpapers in {folders}")
        queue = list(images)

        def load_next():
            # one thumbnail per idle tick keeps the window responsive on big folders
            if gen != self._load_gen or not queue:
                return False
            path = queue.pop(0)
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, _THUMB_W, _THUMB_H, True)
            except GLib.Error:
                return True
            pic = Gtk.Picture.new_for_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
            pic.set_can_shrink(False)
            pic.set_size_request(_THUMB_W, _THUMB_H)
            name = Gtk.Label(label=os.path.basename(path))
            name.set_max_width_chars(18)
            name.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            inner.append(pic)
            inner.append(name)
            btn = Gtk.Button()
            btn.set_child(inner)
            btn.connect("clicked", lambda _w, p=path: self._on_thumb(p))
            self._flow.append(btn)
            return True

        GLib.idle_add(load_next)

    # ── Actions ──────────────────────────────────────────────────────────────

    def _show_selected(self, path):
        self._path.set_text(path)
        self._preview.set_filename(path)
        self._preview.set_visible(True)

    def _on_thumb(self, path):
        self._selected = path
        self._show_selected(path)
        self._btn_apply.set_sensitive(True)

    def _on_apply(self, _widget):
        path = self._selected
        if not path or not os.path.isfile(path):
            set_status(self._status, _("Select a wallpaper first."), error=True)
            return
        self._btn_apply.set_sensitive(False)
        set_status(self._status, _("Setting wallpaper…"))
        mode = selected(self._dd_mode)
        threading.Thread(target=self._apply_worker, args=(path, mode), daemon=True).start()

    def _apply_worker(self, path, mode):
        ok, msg = ott_wallpaper.apply(path, mode)
        GLib.idle_add(self._apply_done, ok, msg)

    def _apply_done(self, ok, msg):
        self._btn_apply.set_sensitive(True)
        if not ok:
            set_status(self._status, msg, error=True)
        else:
            set_status(self._status, msg + " " + _("It stays after you log out."))
        return False

    def _variety(self, arg):
        if ott_wallpaper.variety(arg):
            set_status(self._status, _("Asked Variety for another wallpaper."))
        else:
            set_status(self._status, _("Variety is not installed."), error=True)

    def _on_start_variety(self, _widget):
        if ott_wallpaper.variety():
            set_status(self._status, _("Variety started. Pick this source again in a minute to see its downloads."))
        else:
            set_status(self._status, _("Variety is not installed."), error=True)
