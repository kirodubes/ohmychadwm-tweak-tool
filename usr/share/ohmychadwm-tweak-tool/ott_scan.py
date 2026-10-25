"""Discover installed GTK themes, icon themes, cursor themes and ohmychadwm bar themes.

Toolkit-free (no GTK import) so it stays unit-testable. Theme *names* are the
directory names, because that is what every settings file stores.
"""

import os

THEME_DIRS = ["~/.themes", "~/.local/share/themes", "/usr/share/themes"]
ICON_DIRS = ["~/.icons", "~/.local/share/icons", "/usr/share/icons"]

# "default" is the ~/.icons/default inherit shim and hicolor is the universal
# fallback every icon theme inherits — neither is a choice a user makes.
_SKIP_ICON_DIRS = {"default", "hicolor"}


def _existing_dirs(paths):
    for p in paths:
        p = os.path.expanduser(p)
        if os.path.isdir(p):
            yield p


def _subdirs(base):
    try:
        names = os.listdir(base)
    except OSError:
        return []
    return [n for n in names if os.path.isdir(os.path.join(base, n))]


def _sorted(d):
    return dict(sorted(d.items(), key=lambda kv: kv[0].lower()))


def gtk_themes():
    """Return {name: has_gtk4} for every theme that ships a gtk-3.0 directory."""
    found = {}
    for base in _existing_dirs(THEME_DIRS):
        for name in _subdirs(base):
            path = os.path.join(base, name)
            if name not in found and os.path.isdir(os.path.join(path, "gtk-3.0")):
                found[name] = os.path.isdir(os.path.join(path, "gtk-4.0"))
    return _sorted(found)


def _read_index(path):
    try:
        with open(os.path.join(path, "index.theme"), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def icon_themes():
    """Return a sorted list of icon theme names (dirs whose index.theme lists icon Directories)."""
    found = set()
    for base in _existing_dirs(ICON_DIRS):
        for name in _subdirs(base):
            if name in _SKIP_ICON_DIRS or name in found:
                continue
            index = _read_index(os.path.join(base, name))
            if "Directories=" in index and "Hidden=true" not in index:
                found.add(name)
    return sorted(found, key=str.lower)


def cursor_themes():
    """Return a sorted list of cursor theme names (dirs that ship a cursors/ subdirectory)."""
    found = set()
    for base in _existing_dirs(ICON_DIRS):
        for name in _subdirs(base):
            if name not in _SKIP_ICON_DIRS and os.path.isdir(os.path.join(base, name, "cursors")):
                found.add(name)
    return sorted(found, key=str.lower)


def icon_theme_search_path():
    """Return the icon directories for a private Gtk.IconTheme preview."""
    return list(_existing_dirs(ICON_DIRS))


def is_nerd_font(family):
    """Return True when the font family is a Nerd Font (has the bar's tag glyphs)."""
    return "nerd font" in (family or "").lower()
