"""App placement: the rules[] table of config.def.h (screen, workspace, floating), open windows, screens in dwm order.

Text transforms are pure functions over the file contents so they can be tested without touching disk.
"""

import os
import re
import subprocess

from gi.repository import Gio

# Classes go into C source as a string literal: no quotes, no backslashes.
CLASS_OK = re.compile(r"^[A-Za-z0-9._ +-]{1,80}$")
WORKSPACES = range(1, 11)  # tags[] has ten names in every ohmychadwm config
MODES = ("tiled", "float", "center")
_FLAGS = {"tiled": (0, 0), "float": (0, 1), "center": (1, 1)}  # mode -> (iscentered, isfloating)

_ARRAY_START = re.compile(r"^\s*static\s+const\s+Rule\s+rules\[\]\s*=\s*\{")
_ARRAY_END = re.compile(r"^\s*\};")
_STR = r'(NULL|"[^"\\]*")'
_ENTRY = re.compile(rf"^\s*\{{\s*{_STR}\s*,\s*{_STR}\s*,\s*{_STR}\s*,\s*([^,{{}}]+?)\s*,"
                    r"\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\}\s*,?\s*(?://.*|/\*.*\*/)?\s*$")
_SHIFT = re.compile(r"^\(?\s*1\s*<<\s*(\d)\s*\)?$")


def _unquote(s):
    return None if s == "NULL" else s[1:-1]


def _array(lines):
    """Return (start, end) line indexes of the rules[] array: the opening line and its closing '};'."""
    for i, line in enumerate(lines):
        if _ARRAY_START.match(line):
            for j in range(i + 1, len(lines)):
                if _ARRAY_END.match(lines[j]):
                    return i, j
    raise ValueError("no rules[] table found in config.def.h")


def _workspace(tags):
    """Return 0 for no workspace, 1-10 for one workspace, None for a mask this page doesn't write."""
    if tags == "0":
        return 0
    m = _SHIFT.match(tags)
    return int(m[1]) + 1 if m else None


def _mode(centered, floating):
    for mode, flags in _FLAGS.items():
        if flags == (centered, floating):
            return mode
    return None


def rules(text):
    """Return every rule in rules[] as dicts; 'editable' is False for ones written by hand in another form."""
    lines = text.splitlines(keepends=True)
    start, end = _array(lines)
    out = []
    for line in lines[start + 1:end]:
        m = _ENTRY.match(line)
        if not m:
            continue
        cls, instance, title = (_unquote(m[i]) for i in (1, 2, 3))
        workspace, mode = _workspace(m[4].strip()), _mode(int(m[5]), int(m[6]))
        out.append({
            "class": cls, "instance": instance, "title": title, "tags": m[4].strip(),
            "workspace": workspace, "mode": mode, "monitor": int(m[7]),
            "editable": bool(cls) and instance is None and title is None and workspace is not None and mode is not None,
        })
    return out


def format_rule(cls, workspace, monitor, mode):
    """Return one rules[] line in the column layout of the shipped table."""
    centered, floating = _FLAGS[mode]
    tags = f"1 << {workspace - 1}" if workspace else "0"
    name = f'"{cls}", '
    return (f"    {{ {name:<12}NULL,       NULL,       {tags + ',':<14}{str(centered) + ',':<13}"
            f"{str(floating) + ',':<13}{monitor} }},\n")


def _without(lines, start, end, cls):
    # plain rules for cls (no instance, no title); rules that also match an instance or a title are kept
    keep = []
    for line in lines[start + 1:end]:
        m = _ENTRY.match(line)
        if m and _unquote(m[1]) == cls and _unquote(m[2]) is None and _unquote(m[3]) is None:
            continue
        keep.append(line)
    return keep


def set_rule(text, cls, workspace, monitor, mode):
    """Return text with the rule for cls replaced by one for (workspace 0-10, monitor -1.., mode)."""
    if not CLASS_OK.match(cls):
        raise ValueError(f"not a window class: {cls!r}")
    if workspace not in (0, *WORKSPACES) or monitor < -1 or mode not in MODES:
        raise ValueError("workspace, screen or mode out of range")
    lines = text.splitlines(keepends=True)
    start, end = _array(lines)
    body = _without(lines, start, end, cls) + [format_rule(cls, workspace, monitor, mode)]
    return "".join(lines[:start + 1] + body + lines[end:])


def remove_rule(text, cls):
    """Return text without the plain rules (no instance, no title) for cls."""
    lines = text.splitlines(keepends=True)
    start, end = _array(lines)
    return "".join(lines[:start + 1] + _without(lines, start, end, cls) + lines[end:])


_MONITOR = re.compile(r"^\s*(\d+):\s+\+?\*?(\S+)\s+(\d+)/\d+x(\d+)/\d+\+(-?\d+)\+(-?\d+)\s")


def parse_monitors(listmonitors):
    """Return [(number, name, 'WxH')] from `xrandr --listmonitors`; dwm numbers its monitors in this order."""
    out = []
    for line in listmonitors.splitlines():
        m = _MONITOR.match(line)
        if m:
            out.append((int(m[1]), m[2], f"{m[3]}x{m[4]}"))
    return out


def monitors():
    """Return the screens in the order dwm numbers them (Xinerama order: the primary first)."""
    try:
        out = subprocess.run(["xrandr", "--listmonitors"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_monitors(out)


def _xprop(*args):
    try:
        return subprocess.run(["xprop", *args], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def open_windows():
    """Return {class: title} of the windows open now (dwm keeps _NET_CLIENT_LIST), not this app's."""
    ids = re.findall(r"0x[0-9a-f]+", _xprop("-root", "_NET_CLIENT_LIST").partition("#")[2])
    out = {}
    for wid in ids:
        info = _xprop("-id", wid, "WM_CLASS", "_NET_WM_NAME", "_NET_WM_PID")
        if re.search(rf"_NET_WM_PID\(CARDINAL\) = {os.getpid()}$", info, re.M):
            continue
        classes = re.findall(r'"([^"]*)"', info.partition("WM_CLASS")[2].splitlines()[0]) if "WM_CLASS" in info else []
        # python3 is every PyGObject app at once (this one too): a rule on it would move them all
        if len(classes) < 2 or not CLASS_OK.match(classes[1]) or classes[1].lower().startswith("python"):
            continue
        title = re.search(r'_NET_WM_NAME\(\w+\) = "(.*)"', info)
        out.setdefault(classes[1], title[1] if title else classes[1])
    return out


def choices():
    """Return [(class, title, open_now)]: the open windows first, then installed apps that name their window class."""
    rows, seen = [], set()
    for cls, title in sorted(open_windows().items(), key=lambda item: item[0].lower()):
        rows.append((cls, title, True))
        seen.add(cls)
    apps = [i for i in Gio.AppInfo.get_all() if isinstance(i, Gio.DesktopAppInfo) and i.should_show()]
    for info in sorted(apps, key=lambda i: i.get_display_name().lower()):
        cls = info.get_startup_wm_class()
        if cls and CLASS_OK.match(cls) and cls not in seen:
            rows.append((cls, info.get_display_name(), False))
            seen.add(cls)
    return rows
