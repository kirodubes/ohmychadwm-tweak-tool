"""App placement: the rules[] table of config.def.h (screen, workspace, floating), open windows, screens in dwm order.

Text transforms are pure functions over the file contents so they can be tested without touching disk.
"""

import os
import re
import subprocess

from gi.repository import Gio

# Classes go into C source as a string literal: no quotes, no backslashes.
CLASS_OK = re.compile(r"^[A-Za-z0-9._ +-]{1,80}$")
# A start command goes into run.sh as a shell word: one program name, nothing the shell would read.
COMMAND_OK = re.compile(r"^[A-Za-z0-9._+-]{1,60}$")
WORKSPACES = range(1, 11)  # tags[] has ten names in every ohmychadwm config
MODES = ("tiled", "float", "center")
_FLAGS = {"tiled": (0, 0), "float": (0, 1), "center": (1, 1)}  # mode -> (iscentered, isfloating)

_ARRAY_START = re.compile(r"^\s*static\s+const\s+Rule\s+rules\[\]\s*=\s*\{")
_ARRAY_END = re.compile(r"^\s*\};")
_STR = r'(NULL|"[^"\\]*")'
_ENTRY = re.compile(rf"^\s*\{{\s*{_STR}\s*,\s*{_STR}\s*,\s*{_STR}\s*,\s*([^,{{}}]+?)\s*,"
                    r"\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\}\s*,?\s*(?://.*|/\*.*\*/)?\s*$")
_SHIFT = re.compile(r"^\(?\s*1\s*<<\s*(\d)\s*\)?$")
_LIVE_ENTRY = re.compile(r"^\s*\{")  # any rule line, also hand-written ones _ENTRY can't read
# C forbids an empty rules[]: when the last rule goes, this one stays. No window has this class; the page hides it.
PLACEHOLDER = "ohmychadwm-no-rules"
_PLACEHOLDER_LINE = (f'    {{ "{PLACEHOLDER}", NULL, NULL, 0, 0, 0, -1 }},'
                     " /* keeps rules[] non-empty: C forbids an empty array */\n")


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
        if cls == PLACEHOLDER:
            continue
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
    # plain rules for cls (no instance, no title) and the placeholder; rules that also match an instance or a
    # title are kept
    keep = []
    for line in lines[start + 1:end]:
        m = _ENTRY.match(line)
        if m and _unquote(m[1]) in (cls, PLACEHOLDER) and _unquote(m[2]) is None and _unquote(m[3]) is None:
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
    body = _without(lines, start, end, cls)
    if not any(_LIVE_ENTRY.match(line) for line in body):
        body.append(_PLACEHOLDER_LINE)
    return "".join(lines[:start + 1] + body + lines[end:])


_MONITOR = re.compile(r"^\s*(\d+):\s+\+?(\*?)(\S+)\s+(\d+)/\d+x(\d+)/\d+\+(-?\d+)\+(-?\d+)\s")
_SIDES = {"x": ("left", "middle", "right"), "y": ("top", "middle", "bottom")}


def _places(screens):
    """Return {connector: (side, primary)}: side is left/middle/right (or top/middle/bottom when stacked), or the
    1-based place from the left when there are more than three; None for a single screen."""
    if len(screens) < 2:
        return {s["name"]: (None, s["primary"]) for s in screens}
    cx = [s["x"] + s["w"] / 2 for s in screens]
    cy = [s["y"] + s["h"] / 2 for s in screens]
    axis = "x" if max(cx) - min(cx) >= max(cy) - min(cy) else "y"
    order = sorted(screens, key=lambda s: s[axis] + s["w" if axis == "x" else "h"] / 2)
    out = {}
    for i, s in enumerate(order):
        if len(order) == 2:
            side = _SIDES[axis][0 if i == 0 else 2]
        elif len(order) == 3:
            side = _SIDES[axis][i]
        else:
            side = i + 1
        out[s["name"]] = (side, s["primary"])
    return out


def parse_monitors(listmonitors):
    """Return [(number, name, 'WxH', (side, primary))] from `xrandr --listmonitors`, in dwm's numbering order."""
    screens = []
    for line in listmonitors.splitlines():
        m = _MONITOR.match(line)
        if m:
            screens.append({"num": int(m[1]), "primary": bool(m[2]), "name": m[3], "w": int(m[4]), "h": int(m[5]),
                            "x": int(m[6]), "y": int(m[7])})
    places = _places(screens)
    return [(s["num"], s["name"], f"{s['w']}x{s['h']}", places[s["name"]]) for s in screens]


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


def _command_of(pid):
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            argv0 = f.read().split(b"\0")[0].decode(errors="replace")
    except (OSError, ValueError):
        return None
    name = os.path.basename(argv0)
    return name if COMMAND_OK.match(name) else None


def open_windows():
    """Return {class: (title, command)} of the windows open now (dwm keeps _NET_CLIENT_LIST), not this app's."""
    ids = re.findall(r"0x[0-9a-f]+", _xprop("-root", "_NET_CLIENT_LIST").partition("#")[2])
    out = {}
    for wid in ids:
        info = _xprop("-id", wid, "WM_CLASS", "_NET_WM_NAME", "_NET_WM_PID")
        pid = re.search(r"_NET_WM_PID\(CARDINAL\) = (\d+)$", info, re.M)
        if pid and int(pid[1]) == os.getpid():
            continue
        classes = re.findall(r'"([^"]*)"', info.partition("WM_CLASS")[2].splitlines()[0]) if "WM_CLASS" in info else []
        # python3 is every PyGObject app at once (this one too): a rule on it would move them all
        if len(classes) < 2 or not CLASS_OK.match(classes[1]) or classes[1].lower().startswith("python"):
            continue
        title = re.search(r'_NET_WM_NAME\(\w+\) = "(.*)"', info)
        out.setdefault(classes[1], (title[1] if title else classes[1], _command_of(pid[1]) if pid else None))
    return out


def _desktop_command(info):
    exe = os.path.basename(info.get_executable() or "")
    return exe if COMMAND_OK.match(exe) else None


def choices():
    """Return [(class, title, open_now, command)]: open windows first, then installed apps that name their class.

    command is what a run.sh line starts (one word, or None when there is no safe one).
    """
    apps = [i for i in Gio.AppInfo.get_all() if isinstance(i, Gio.DesktopAppInfo) and i.should_show()]
    by_class = {i.get_startup_wm_class(): i for i in apps if i.get_startup_wm_class()}
    rows, seen = [], set()
    for cls, (title, command) in sorted(open_windows().items(), key=lambda item: item[0].lower()):
        info = by_class.get(cls)
        rows.append((cls, title, True, (_desktop_command(info) if info else None) or command))
        seen.add(cls)
    for info in sorted(apps, key=lambda i: i.get_display_name().lower()):
        cls = info.get_startup_wm_class()
        if cls and CLASS_OK.match(cls) and cls not in seen:
            rows.append((cls, info.get_display_name(), False, _desktop_command(info)))
            seen.add(cls)
    return rows
