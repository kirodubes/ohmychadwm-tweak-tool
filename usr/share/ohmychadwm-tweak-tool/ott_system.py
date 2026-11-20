"""System-wide cursor (/usr/share/icons/default/index.theme, SDDM) and the SDDM login wallpaper.

The X fallback cursor comes from /usr/share/icons/default (owned by
default-cursors, but listed as a pacman backup file, so edits survive upgrades
as .pacnew). SDDM ignores that file once its own [Theme] CursorTheme is set,
which Kiro does in /etc/sddm.conf.d/kde_settings.conf. Pure text transforms
here; ott_root.py applies them as root.
"""

import glob
import os
import re

DEFAULT_INDEX = "/usr/share/icons/default/index.theme"
SDDM_FALLBACK = "/etc/sddm.conf.d/kde_settings.conf"
SDDM_THEMES = "/usr/share/sddm/themes"
BACKGROUNDS_DIR = "/usr/share/backgrounds"
# SDDM themes whose Main.qml reads config.background (kiro-sddm-simplicity 2026.11.20+); a theme.conf.user beside
# their theme.conf overrides it, and no package owns that file
BACKGROUND_THEMES = ("edu-simplicity",)
_IMAGE_EXTS = (".jpg", ".jpeg", ".png")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _get(text, section, key):
    current = None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            current = s[1:-1]
        elif current == section and re.match(rf"{re.escape(key)}\s*=", s):
            return s.split("=", 1)[1].strip() or None
    return None


def set_key(text, section, key, value):
    """Return text with key=value inside [section], replacing an existing key or adding it (and the section)."""
    lines = text.splitlines()
    current, start, end, done = None, None, None, False
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            if current == section and end is None:
                end = i
            current = s[1:-1]
            if current == section and start is None:
                start = i
        elif current == section and re.match(rf"{re.escape(key)}\s*=", s):
            lines[i] = f"{key}={value}"
            done = True
    if not done:
        if start is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines += [f"[{section}]", f"{key}={value}"]
        else:
            at = end if end is not None else len(lines)
            while at > start + 1 and not lines[at - 1].strip():
                at -= 1
            lines.insert(at, f"{key}={value}")
    return "\n".join(lines) + "\n"


def sddm_conf():
    """Return the SDDM config file that sets CursorTheme (last one wins), else the Kiro default path."""
    candidates = sorted(glob.glob("/etc/sddm.conf.d/*.conf")) + ["/etc/sddm.conf"]
    hits = [p for p in candidates if os.path.isfile(p) and _get(_read(p), "Theme", "CursorTheme")]
    return hits[-1] if hits else SDDM_FALLBACK


def read():
    """Return {'default': cursor or None, 'sddm': cursor or None, 'sddm_size': str or None}."""
    sddm = _read(sddm_conf())
    return {
        "default": _get(_read(DEFAULT_INDEX), "Icon Theme", "Inherits"),
        "sddm": _get(sddm, "Theme", "CursorTheme"),
        "sddm_size": _get(sddm, "Theme", "CursorSize"),
    }


def set_default_cursor(text, cursor):
    """Return index.theme text inheriting cursor."""
    return set_key(text, "Icon Theme", "Inherits", cursor)


def set_sddm_cursor(text, cursor, size):
    """Return SDDM config text with [Theme] CursorTheme and CursorSize set."""
    return set_key(set_key(text, "Theme", "CursorTheme", cursor), "Theme", "CursorSize", str(int(size)))


def sddm_theme():
    """Return the SDDM theme in use ([Theme] Current, last config file wins), or None."""
    candidates = sorted(glob.glob("/etc/sddm.conf.d/*.conf")) + ["/etc/sddm.conf"]
    found = [_get(_read(p), "Theme", "Current") for p in candidates if os.path.isfile(p)]
    found = [t for t in found if t]
    return found[-1] if found else None


def background_conf():
    """Return the theme.conf.user that sets the login wallpaper, or None when the SDDM theme can't show one."""
    theme = sddm_theme()
    if theme not in BACKGROUND_THEMES:
        return None
    # an older kiro-sddm-simplicity has a fixed picture and would ignore theme.conf.user
    if "config.background" not in _read(os.path.join(SDDM_THEMES, theme, "Main.qml")):
        return None
    return os.path.join(SDDM_THEMES, theme, "theme.conf.user")


def valid_background(path):
    """Return True for an image file under /usr/share/backgrounds (the sddm user can read it)."""
    if not isinstance(path, str) or "\n" in path or not path.lower().endswith(_IMAGE_EXTS):
        return False
    real = os.path.realpath(path)
    return real.startswith(BACKGROUNDS_DIR + "/") and os.path.isfile(real)


def set_background(text, path):
    """Return theme.conf.user text with [General] background set to path."""
    return set_key(text, "General", "background", path)
