"""Keys: every binding from the user's sxhkdrc and the keys[] array of chadwm's config.def.h, as readable rows.

keybindings.txt can be out of date, so both sources are parsed directly. The KEY_* macros of config.def.h are
resolved for the KIRO_AZERTY value the file sets. Also holds the sxhkdrc command rewrite the Default apps page
uses. Toolkit-free.
"""

import os
import re
import shutil
from dataclasses import dataclass

from ott_i18n import _

SXHKDRC = os.path.expanduser("~/.config/ohmychadwm/sxhkd/sxhkdrc")


@dataclass
class Binding:
    """One key binding: where it comes from, the keys, and what it does."""

    source: str  # "sxhkd" or "ohmychadwm"
    keys: str
    action: str


# ── sxhkdrc ───────────────────────────────────────────────────────────────────


def _is_key_line(line):
    return bool(line.strip()) and not line[0].isspace() and not line.startswith("#")


def sxhkd_bindings(text):
    """Return [(keys, command, comment)] from sxhkdrc text; comment is the `#` line just above, if any."""
    out = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not _is_key_line(line):
            continue
        command = []
        for nxt in lines[i + 1:]:
            if not nxt.strip() or not nxt[0].isspace():
                break
            command.append(nxt.strip())
        comment = ""
        if i and lines[i - 1].startswith("#") and not lines[i - 1].startswith("##"):
            comment = lines[i - 1].lstrip("#").strip()
        out.append((line.strip(), " ".join(command).rstrip("\\").strip(), comment))
    return out


def sxhkd_command(text, keys):
    """Return the command bound to keys in sxhkdrc text, or None."""
    return next((cmd for k, cmd, _c in sxhkd_bindings(text) if k == keys), None)


def set_sxhkd_command(text, keys, command):
    """Return text with the single command line under keys replaced by command (unchanged when keys is absent)."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if _is_key_line(line) and line.strip() == keys and i + 1 < len(lines) and lines[i + 1][:1].isspace() \
                and lines[i + 1].strip():
            indent = lines[i + 1][:len(lines[i + 1]) - len(lines[i + 1].lstrip())]
            lines[i + 1] = f"{indent}{command}\n"
            break
    return "".join(lines)


def read_sxhkdrc():
    """Return the user's sxhkdrc, or '' when ohmychadwm isn't set up."""
    try:
        with open(SXHKDRC, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def write_sxhkdrc(text):
    """Write sxhkdrc (one-time .oma-bak backup)."""
    backup = SXHKDRC + ".oma-bak"
    if os.path.exists(SXHKDRC) and not os.path.exists(backup):
        shutil.copy2(SXHKDRC, backup)
    with open(SXHKDRC, "w", encoding="utf-8") as f:
        f.write(text)


# ── config.def.h keys[] ───────────────────────────────────────────────────────

_MODS = [("MODKEY", "Super"), ("Mod4Mask", "Super"), ("ControlMask", "Ctrl"), ("ShiftMask", "Shift"),
         ("Mod1Mask", "Alt")]
_KEY_NAMES = {
    "Return": "Enter", "space": "Space", "comma": ",", "period": ".", "minus": "-", "Tab": "Tab",
    "ampersand": "&", "eacute": "é", "quotedbl": '"', "apostrophe": "'", "parenleft": "(", "section": "§",
    "egrave": "è", "exclam": "!", "ccedilla": "ç", "agrave": "à", "semicolon": ";",
    "AudioLowerVolume": _("Volume down"), "AudioRaiseVolume": _("Volume up"), "AudioMute": _("Mute"),
    "MonBrightnessUp": _("Brightness up"), "MonBrightnessDown": _("Brightness down"),
}
_ACTIONS = {
    "togglebar": _("Show / hide the bar"), "togglegaps": _("Gaps on / off"), "togglefullscr": _("Fullscreen"),
    "tabmode": _("Tab bar mode"), "focusstack": _("Focus next / previous window"), "incnmaster": _("More / fewer masters"),
    "shiftview": _("Previous / next tag"), "setmfact": _("Master area smaller / bigger"),
    "setcfact": _("Window size in the stack"), "movestack": _("Move window in the stack"),
    "rotatestack": _("Rotate the stack"), "zoom": _("Swap with master"), "changeopacity": _("Window opacity"),
    "view": _("View tag"), "incrgaps": _("Gaps bigger / smaller"), "incrigaps": _("Inner gaps"), "incrogaps": _("Outer gaps"),
    "incrihgaps": _("Inner horizontal gaps"), "incrivgaps": _("Inner vertical gaps"),
    "incrohgaps": _("Outer horizontal gaps"), "incrovgaps": _("Outer vertical gaps"), "defaultgaps": _("Default gaps"),
    "setlayout": _("Set layout"), "cyclelayout": _("Next / previous layout"), "focusmon": _("Focus other monitor"),
    "tagmon": _("Move window to other monitor"), "setborderpx": _("Border width"), "killall": _("Close all windows"),
    "quit": _("Log out"), "killclient": _("Close window"), "restart": _("Restart Ohmychadwm"),
    "togglefloating": _("Floating on / off"), "toggleview": _("Also show tag"), "tag": _("Move window to tag"),
    "toggletag": _("Also put window on tag"), "hidewin": _("Hide window"), "restorewin": _("Restore window"),
}
_ENTRY_RE = re.compile(r"^\s*\{\s*([\w|]+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(.*)\}\s*,?\s*(?://.*)?$")
_TAGKEYS_RE = re.compile(r"^\s*TAGKEYS\(\s*(\w+)\s*,\s*(\d+)\s*\)")
_DEFINE_RE = re.compile(r"^\s*#define\s+(KEY_\w+)\s+(\w+)")
_SHCMD_RE = re.compile(r'SHCMD\("(.*)"\)')
_CMD_ARRAY_RE = re.compile(r"static\s+const\s+char\s*\*\s*(\w+)\[\]\s*=\s*\{(.*?)\};")


def _key_macros(text):
    """Return {KEY_*: XK_*} for the branch of `#if KIRO_AZERTY` the file selects."""
    m = re.search(r"^\s*#define\s+KIRO_AZERTY\s+(\w+)", text, re.M)
    azerty = bool(m) and m.group(1) in ("true", "1")
    macros, branch = {}, None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#if") and "KIRO_AZERTY" in s:
            branch = True
        elif branch is not None and s.startswith("#else"):
            branch = False
        elif branch is not None and s.startswith("#endif"):
            branch = None
        elif (d := _DEFINE_RE.match(line)) and (branch is None or branch == azerty):
            macros[d.group(1)] = d.group(2)
    return macros


def _keys_label(mods, key, macros):
    names = [label for token, label in _MODS if token in mods.split("|")]
    key = macros.get(key, key)
    key = re.sub(r"^XF86XK_|^XK_", "", key)
    key = _KEY_NAMES.get(key, key.upper() if len(key) == 1 else key)
    return " + ".join(dict.fromkeys(names + [key]))


def _keys_array(text):
    """Return the keys[] lines, with entries split over two lines joined into one."""
    m = re.search(r"Key keys\[\]\s*=\s*\{(.*?)^\};", text, re.S | re.M)
    if not m:
        return []
    out, pending = [], ""
    for line in m.group(1).splitlines():
        if line.strip().startswith(("//", "/*")) or not line.strip():
            continue
        pending = f"{pending} {line.strip()}" if pending else line
        if pending.rstrip().endswith(("},", "}", ")")):
            out.append(pending)
            pending = ""
    return out


def chadwm_bindings(text):
    """Return [Binding] for the keys[] array of config.def.h text."""
    macros = _key_macros(text)
    commands = {name: " ".join(re.findall(r'"([^"]*)"', body)) for name, body in _CMD_ARRAY_RE.findall(text)}
    out = []
    for line in _keys_array(text):
        if t := _TAGKEYS_RE.match(line):
            n = int(t.group(2)) + 1
            for mods, func in (("MODKEY", "view"), ("MODKEY|ControlMask", "toggleview"),
                               ("MODKEY|ShiftMask", "tag"), ("MODKEY|ControlMask|ShiftMask", "toggletag")):
                out.append(Binding("ohmychadwm", _keys_label(mods, t.group(1), macros), f"{_ACTIONS[func]} {n}"))
            continue
        e = _ENTRY_RE.match(line)
        if not e:
            continue
        mods, key, func, arg = e.groups()
        if func == "spawn":
            cmd = _SHCMD_RE.search(arg)
            var = arg.strip(" {}").removeprefix(".v").strip(" =")
            action = _("Run: {command}").format(command=cmd.group(1) if cmd else commands.get(var, var))
        else:
            action = _ACTIONS.get(func, func)
        out.append(Binding("ohmychadwm", _keys_label(mods, key, macros), action))
    return out


_SXHKD_MODS = {"super": "Super", "ctrl": "Ctrl", "control": "Ctrl", "shift": "Shift", "alt": "Alt"}


def _sxhkd_label(keys):
    """Write sxhkd's `super + shift + x` the way the ohmychadwm rows read: `Super + Shift + X`."""
    out = []
    for token in (t.strip() for t in keys.split("+")):
        token = _SXHKD_MODS.get(token, token)
        out.append(_KEY_NAMES.get(token, token.upper() if len(token) == 1 else token))
    return " + ".join(out)


def all_bindings(sxhkdrc, config):
    """Return every Binding: sxhkd first, then ohmychadwm's own keys."""
    rows = [Binding("sxhkd", _sxhkd_label(keys), comment or command)
            for keys, command, comment in sxhkd_bindings(sxhkdrc)]
    return rows + chadwm_bindings(config)
