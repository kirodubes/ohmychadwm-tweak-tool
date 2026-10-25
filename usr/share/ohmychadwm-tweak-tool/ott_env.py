"""The system-wide GTK_THEME line in /etc/environment.

Kiro ships GTK_THEME there, and it beats every settings file for the GTK theme
in GTK 3 and GTK 4 apps. pam_env reads it at login, so changes show after a
re-login. Pure text transforms live here so they can be tested without root;
ott_root.py applies them to the real file.
"""

import re

ENV_FILE = "/etc/environment"

_LINE_RE = re.compile(r"^(\s*#\s*)?GTK_THEME\s*=\s*(.*?)\s*$")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9 ._+-]+$")


def parse(text):
    """Return (theme, active) for the GTK_THEME line; (None, False) when there is none."""
    found = (None, False)
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        theme = m.group(2).strip().strip("\"'") or None
        if not m.group(1):
            return theme, True  # an active line wins over any commented one
        found = (theme, False)
    return found


def read():
    """Return (theme, active) from /etc/environment."""
    try:
        with open(ENV_FILE, encoding="utf-8") as f:
            return parse(f.read())
    except OSError:
        return None, False


def valid_name(name):
    """Return True for a theme name that is safe to write into /etc/environment."""
    return bool(name) and bool(_SAFE_NAME.match(name))


def force(text, theme):
    """Return text with one active GTK_THEME line set to theme (other GTK_THEME lines removed)."""
    if not valid_name(theme):
        raise ValueError(f"unsafe theme name: {theme!r}")
    lines = text.splitlines()
    out, placed, quoted = [], False, True
    for line in lines:
        m = _LINE_RE.match(line)
        if not m:
            out.append(line)
            continue
        if not placed:
            quoted = '"' in m.group(2) or not m.group(2)
            out.append(f'GTK_THEME="{theme}"' if quoted else f"GTK_THEME={theme}")
            placed = True
    if not placed:
        out.append(f'GTK_THEME="{theme}"')
    return "\n".join(out) + "\n"


def release(text):
    """Return text with every active GTK_THEME line commented out (kept, so it can be re-enabled)."""
    out = []
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        out.append("#" + line.lstrip() if m and not m.group(1) else line)
    return "\n".join(out) + "\n"
