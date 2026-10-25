"""Every place the desktop look is stored: read it, detect drift, write it.

One appearance choice lives in many files (GTK2/3/4, gsettings, xfconf, the X
cursor). Each target gets a reader and a writer here. Toolkit-free so it can be
tested with HOME pointed at a scratch directory. Writers never raise into the
UI: apply() returns a list of (label, ok, message).
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass

import ott_env

SCHEMA = "org.gnome.desktop.interface"

# Display labels, in the order the drift banner lists them.
SYSTEM = "System GTK_THEME"
GTK3 = "GTK 3 (Thunar)"
GTK4 = "GTK 4"
GTK2 = "GTK 2"
GSETTINGS = "gsettings"
XFCONF = "XFCE xsettings"
CURSOR_INDEX = "Personal default cursor"
XRESOURCES = "Xresources"

FALLBACK_CURSOR_SIZE = 24

_INI_KEYS = {
    "theme": "gtk-theme-name",
    "icons": "gtk-icon-theme-name",
    "cursor": "gtk-cursor-theme-name",
    "cursor_size": "gtk-cursor-theme-size",
    "font": "gtk-font-name",
    "dark": "gtk-application-prefer-dark-theme",
}
_GSETTINGS_KEYS = {
    "theme": "gtk-theme",
    "icons": "icon-theme",
    "cursor": "cursor-theme",
    "cursor_size": "cursor-size",
    "font": "font-name",
    "dark": "color-scheme",
}
_XFCONF_PROPS = {
    "theme": ("/Net/ThemeName", "string"),
    "icons": ("/Net/IconThemeName", "string"),
    "cursor": ("/Gtk/CursorThemeName", "string"),
    "cursor_size": ("/Gtk/CursorThemeSize", "int"),
    "font": ("/Gtk/FontName", "string"),
}


@dataclass
class Selection:
    """One complete appearance choice."""

    theme: str
    icons: str
    cursor: str
    cursor_size: int
    font: str
    dark: bool


def _p(path):
    return os.path.expanduser(path)


def gtk3_ini():
    """Return the GTK 3 settings.ini path (read by Thunar in the ohmychadwm session)."""
    return _p("~/.config/gtk-3.0/settings.ini")


def gtk4_ini():
    """Return the GTK 4 settings.ini path."""
    return _p("~/.config/gtk-4.0/settings.ini")


def gtkrc2():
    """Return the GTK 2 rc path."""
    return _p("~/.gtkrc-2.0")


def cursor_index():
    """Return the ~/.icons/default/index.theme path (X fallback cursor)."""
    return _p("~/.icons/default/index.theme")


def xresources():
    """Return the ~/.Xresources path."""
    return _p("~/.Xresources")


# ── Small parsing helpers ────────────────────────────────────────────────────


def _parse(path, sep):
    """Return {key: value} for 'key<sep>value' lines, quotes stripped; {} when the file is missing."""
    out = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                s = line.strip()
                if not s or s[0] in "#!;[" or sep not in s:
                    continue
                key, value = s.split(sep, 1)
                out[key.strip()] = value.strip().strip('"')
    except OSError:
        pass
    return out


def _backup(path):
    """Keep a one-time copy of the user's original file next to it."""
    backup = path + ".oma-bak"
    if os.path.isfile(path) and not os.path.exists(backup):
        shutil.copy2(path, backup)


def _upsert(path, lines_by_key, sep, section=None):
    """Replace each key's line in place, appending missing ones (under section when given)."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = [section] if section else []
    pending = dict(lines_by_key)
    for i, line in enumerate(lines):
        for key in list(pending):
            if re.match(rf"\s*{re.escape(key)}\s*{re.escape(sep)}", line):
                lines[i] = pending.pop(key)
    if pending:
        at = len(lines)
        if section:
            if section in lines:
                at = lines.index(section) + 1
                # keep new keys inside the section: insert before the next section header
                while at < len(lines) and not lines[at].startswith("["):
                    at += 1
                while at > 0 and not lines[at - 1].strip():
                    at -= 1
            else:
                lines += ["", section] if lines else [section]
                at = len(lines)
        lines[at:at] = list(pending.values())
    _backup(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def norm_font(font):
    """Normalise a font string so 'Noto Sans,  10' and 'Noto Sans 10' compare equal."""
    return " ".join((font or "").replace(",", " ").split())


def _bool(value):
    if value is None:
        return None
    return str(value).strip().lower() in ("1", "true", "yes", "prefer-dark")


def _int(value):
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return n or None  # 0 means "toolkit default" — treat as unset


def _run(cmd):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


# ── Readers ──────────────────────────────────────────────────────────────────


def _read_ini(path):
    if not os.path.isfile(path):
        return None
    kv = _parse(path, "=")
    return {field: kv.get(key) for field, key in _INI_KEYS.items()}


def _read_gtkrc2():
    if not os.path.isfile(gtkrc2()):
        return None
    kv = _parse(gtkrc2(), "=")
    return {f: kv.get(k) for f, k in _INI_KEYS.items() if f != "dark"}


def _read_gsettings():
    if not shutil.which("gsettings"):
        return None
    rc, out = _run(["gsettings", "list-recursively", SCHEMA])
    if rc != 0:
        return None
    kv = {}
    for line in out.splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3 and parts[0] == SCHEMA:
            kv[parts[1]] = parts[2].strip().strip("'")
    vals = {f: kv.get(k) for f, k in _GSETTINGS_KEYS.items()}
    vals["cursor_size"] = vals["cursor_size"].removeprefix("int32 ") if vals["cursor_size"] else None
    return vals


def _read_xfconf():
    if not shutil.which("xfconf-query"):
        return None
    vals = {}
    for field, (prop, _type) in _XFCONF_PROPS.items():
        rc, out = _run(["xfconf-query", "-c", "xsettings", "-p", prop])
        vals[field] = out if rc == 0 and out else None
    return vals


def _read_cursor_index():
    if not os.path.isfile(cursor_index()):
        return None
    return {"cursor": _parse(cursor_index(), "=").get("Inherits")}


def _read_xresources():
    if not os.path.isfile(xresources()):
        return None
    kv = _parse(xresources(), ":")
    return {"cursor": kv.get("Xcursor.theme"), "cursor_size": kv.get("Xcursor.size")}


def _read_system():
    theme, active = ott_env.read()
    return {"theme": theme} if active else None


def read_all():
    """Return {target label: {field: raw value or None}}, or None for a target that isn't configured."""
    return {
        SYSTEM: _read_system(),
        GTK3: _read_ini(gtk3_ini()),
        GTK4: _read_ini(gtk4_ini()),
        GTK2: _read_gtkrc2(),
        GSETTINGS: _read_gsettings(),
        XFCONF: _read_xfconf(),
        CURSOR_INDEX: _read_cursor_index(),
        XRESOURCES: _read_xresources(),
    }


def _from_values(vals, fallback):
    vals = vals or {}
    return Selection(
        theme=vals.get("theme") or fallback.theme,
        icons=vals.get("icons") or fallback.icons,
        cursor=vals.get("cursor") or fallback.cursor,
        cursor_size=_int(vals.get("cursor_size")) or fallback.cursor_size,
        font=norm_font(vals.get("font")) or fallback.font,
        dark=_bool(vals.get("dark")) if vals.get("dark") is not None else fallback.dark,
    )


def kiro_default():
    """Return the look Kiro ships, read from /etc/skel when present."""
    hard = Selection("Arc-Dawn-Dark", "Surfn", "Bibata-Modern-Ice", FALLBACK_CURSOR_SIZE, "Noto Sans 11", True)
    skel3 = _read_ini("/etc/skel/.config/gtk-3.0/settings.ini")
    skel4 = _read_ini("/etc/skel/.config/gtk-4.0/settings.ini") or {}
    sel = _from_values(skel3, hard)
    if skel4.get("dark") is not None:
        sel.dark = _bool(skel4["dark"])
    return sel


def current(state=None):
    """Return the selection the session uses now: a forced GTK_THEME, then GTK 3 (what Thunar shows), then gsettings."""
    state = state or read_all()
    sel = _from_values(state.get(GTK3), _from_values(state.get(GSETTINGS), kiro_default()))
    if state.get(SYSTEM):
        sel.theme = state[SYSTEM]["theme"] or sel.theme
    gs = state.get(GSETTINGS) or {}
    if gs.get("dark") is not None:
        sel.dark = _bool(gs["dark"])
    # gtk-cursor-theme-size=0 means "use the X default", which is Xcursor.size — the size actually on screen
    if _int((state.get(GTK3) or {}).get("cursor_size")) is None:
        sel.cursor_size = _int((state.get(XRESOURCES) or {}).get("cursor_size")) or sel.cursor_size
    return sel


def drift(sel, state=None):
    """Return human-readable lines for every target that disagrees with sel."""
    state = state or read_all()
    expected = {
        "theme": sel.theme,
        "icons": sel.icons,
        "cursor": sel.cursor,
        "cursor_size": sel.cursor_size,
        "font": norm_font(sel.font),
        "dark": sel.dark,
    }
    lines = []
    for label, vals in state.items():
        if vals is None:
            if label in (GTK4, GTK2, CURSOR_INDEX):
                lines.append(f"{label}: not configured")
            continue
        for field, raw in vals.items():
            want = expected[field]
            if field == "cursor_size":
                got = _int(raw)
                if got is None:
                    continue
            elif field == "dark":
                got = _bool(raw)
                if got is None or label == GTK3:  # GTK 3 themes carry their own dark variant
                    continue
            elif field == "font":
                got = norm_font(raw) or None
            else:
                got = raw or None
            if got != want:
                shown = {True: "dark", False: "light"}.get(got, got) if field == "dark" else got
                lines.append(f"{label}: {field.replace('_', ' ')} = {shown or 'not set'}")
    return lines


# ── Writers ──────────────────────────────────────────────────────────────────


def _ini_lines(sel, with_dark):
    vals = {
        "theme": sel.theme,
        "icons": sel.icons,
        "cursor": sel.cursor,
        "cursor_size": sel.cursor_size,
        "font": sel.font,
    }
    if with_dark:
        vals["dark"] = "true" if sel.dark else "false"
    return {_INI_KEYS[f]: f"{_INI_KEYS[f]}={v}" for f, v in vals.items()}


def _write_gtk3(sel):
    _upsert(gtk3_ini(), _ini_lines(sel, with_dark=False), "=", "[Settings]")


def _write_gtk4(sel):
    _upsert(gtk4_ini(), _ini_lines(sel, with_dark=True), "=", "[Settings]")


def _write_gtkrc2(sel):
    lines = {
        "gtk-theme-name": f'gtk-theme-name="{sel.theme}"',
        "gtk-icon-theme-name": f'gtk-icon-theme-name="{sel.icons}"',
        "gtk-font-name": f'gtk-font-name="{sel.font}"',
        "gtk-cursor-theme-name": f'gtk-cursor-theme-name="{sel.cursor}"',
        "gtk-cursor-theme-size": f"gtk-cursor-theme-size={sel.cursor_size}",
    }
    _upsert(gtkrc2(), lines, "=")


def _write_gsettings(sel):
    if not shutil.which("gsettings"):
        return "gsettings not installed, skipped"
    pairs = [
        ("gtk-theme", sel.theme),
        ("icon-theme", sel.icons),
        ("cursor-theme", sel.cursor),
        ("cursor-size", str(sel.cursor_size)),
        ("font-name", sel.font),
        ("color-scheme", "prefer-dark" if sel.dark else "default"),
    ]
    for key, value in pairs:
        rc, out = _run(["gsettings", "set", SCHEMA, key, value])
        if rc != 0:
            raise RuntimeError(out or f"gsettings set {key} failed")
    return None


def _write_xfconf(sel):
    if not shutil.which("xfconf-query"):
        return "xfconf-query not installed, skipped"
    values = {"theme": sel.theme, "icons": sel.icons, "cursor": sel.cursor,
              "cursor_size": str(sel.cursor_size), "font": sel.font}
    for field, (prop, ptype) in _XFCONF_PROPS.items():
        rc, out = _run(["xfconf-query", "-c", "xsettings", "-p", prop, "-n", "-t", ptype, "-s", values[field]])
        if rc != 0:
            # a property stored as type "empty" refuses a typed set — reset it, then create it
            _run(["xfconf-query", "-c", "xsettings", "-p", prop, "-r"])
            rc, out = _run(["xfconf-query", "-c", "xsettings", "-p", prop, "-n", "-t", ptype, "-s", values[field]])
            if rc != 0:
                raise RuntimeError(out or f"xfconf-query {prop} failed")
    return None


def _write_cursor_index(sel):
    _upsert(cursor_index(), {"Inherits": f"Inherits={sel.cursor}"}, "=", "[Icon Theme]")


def _write_xresources(sel):
    lines = {
        "Xcursor.theme": f"Xcursor.theme: {sel.cursor}",
        "Xcursor.size": f"Xcursor.size: {sel.cursor_size}",
    }
    _upsert(xresources(), lines, ":")
    if not os.environ.get("DISPLAY"):
        return None
    if shutil.which("xrdb"):
        _run(["xrdb", "-merge", xresources()])
    if shutil.which("xsetroot"):
        _run(["xsetroot", "-cursor_name", "left_ptr"])
    return None


_WRITERS = [
    (GTK3, _write_gtk3),
    (GTK4, _write_gtk4),
    (GTK2, _write_gtkrc2),
    (GSETTINGS, _write_gsettings),
    (XFCONF, _write_xfconf),
    (CURSOR_INDEX, _write_cursor_index),
    (XRESOURCES, _write_xresources),
]


def apply(sel):
    """Write sel to every target; return [(label, ok, message)]."""
    results = []
    for label, writer in _WRITERS:
        try:
            note = writer(sel)
            results.append((label, True, note or "written"))
        except (OSError, RuntimeError) as e:
            results.append((label, False, str(e)))
    return results
