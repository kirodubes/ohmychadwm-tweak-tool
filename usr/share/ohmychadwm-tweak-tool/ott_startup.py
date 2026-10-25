"""Startup apps: the `run …` lines of the user's ohmychadwm run.sh, switched on/off by (un)commenting them.

Only lines that start with `run` (or `#run`) are ever changed, so the session loop and the scripted blocks of
run.sh are never touched. The xrandr line is left to the Displays page. Pure text transforms plus read/write.
"""

import os
import re
import shutil
from dataclasses import dataclass

RUN_SH = os.path.expanduser("~/.config/ohmychadwm/scripts/run.sh")
ADDED_TAG = "# added by ohmychadwm-tweak-tool"

_RUN_RE = re.compile(r"^(?P<indent>\s*)(?P<off>#\s*)?run\s+(?P<cmd>.+?)(?:\s+#\s*(?P<note>.*))?\s*$")
# Without these the bar or the password prompts stop working, so the page warns before switching them off.
ESSENTIAL = ("slstatus", "polkit-gnome-authentication-agent-1", "xfce4-notifyd")


@dataclass
class Entry:
    """One run line of run.sh."""

    command: str
    enabled: bool
    note: str
    added: bool  # added by this app, so it may be removed again


def _match(line):
    m = _RUN_RE.match(line.rstrip("\n"))
    if not m or m["cmd"].startswith("xrandr"):
        return None
    return m


def entries(text):
    """Return [Entry] for every run line in text, in file order (one entry per command)."""
    out, seen = [], set()
    for line in text.splitlines():
        m = _match(line)
        if not m or m["cmd"] in seen:
            continue
        seen.add(m["cmd"])
        note = m["note"] or ""
        added = ADDED_TAG.lstrip("# ") == note
        out.append(Entry(m["cmd"], not m["off"], "" if added else note, added))
    return out


def set_enabled(text, command, enabled):
    """Return text with the run line for command commented (off) or uncommented (on)."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        m = _match(line)
        if not m or m["cmd"] != command:
            continue
        rest = line[m.start("off") if m["off"] else len(m["indent"]):]
        rest = rest[len(m["off"]):] if m["off"] else rest
        lines[i] = m["indent"] + ("" if enabled else "#") + rest
        break
    return "".join(lines)


def add(text, command):
    """Return text with `run command` added after the last run line (or before the session loop)."""
    command = " ".join(command.split())
    if not command or any(e.command == command for e in entries(text)):
        return text
    lines = text.splitlines(keepends=True)
    last = max((i for i, line in enumerate(lines) if _match(line)), default=-1)
    if last < 0:
        loop = next((i for i, line in enumerate(lines) if line.startswith("while ")), len(lines))
        last = loop - 1
    lines.insert(last + 1, f"run {command}  {ADDED_TAG}\n")
    return "".join(lines)


def remove(text, command):
    """Return text without the run line for command, but only when this app added it."""
    out = []
    for line in text.splitlines(keepends=True):
        m = _match(line)
        if m and m["cmd"] == command and (m["note"] or "") == ADDED_TAG.lstrip("# "):
            continue
        out.append(line)
    return "".join(out)


def read():
    """Return run.sh's contents, or '' when ohmychadwm isn't set up."""
    try:
        with open(RUN_SH, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def write(text):
    """Write run.sh, keeping a one-time .oma-bak copy and its executable bit."""
    backup = RUN_SH + ".oma-bak"
    if os.path.exists(RUN_SH) and not os.path.exists(backup):
        shutil.copy2(RUN_SH, backup)
    mode = os.stat(RUN_SH).st_mode if os.path.exists(RUN_SH) else 0o755
    with open(RUN_SH, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(RUN_SH, mode)
