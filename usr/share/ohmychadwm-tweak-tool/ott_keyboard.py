"""Keyboard: the typing layouts (setxkbmap now, localectl for good) and Ohmychadwm's workspace keys (KIRO_AZERTY).

Two different things: the layout decides which character a key types, everywhere. KIRO_AZERTY decides which keys
Ohmychadwm listens for to switch workspaces, and is compiled into the bar binary.
"""

import os
import re
import shutil
import subprocess

import log

EVDEV_LST = "/usr/share/X11/xkb/rules/evdev.lst"
X11_CONF = "/etc/X11/xorg.conf.d/00-keyboard.conf"
KB_DIR = os.path.expanduser("~/.config/ohmychadwm")
SWITCH_OPTION = "grp:alt_shift_toggle"
AZERTY_LAYOUTS = ("be", "fr")

_LAYOUT_LINE = re.compile(r"^\s+(\S+)\s+(.+?)\s*$")
_AZERTY_RE = re.compile(r"^(\s*#define\s+KIRO_AZERTY\s+)(\w+)", re.M)
_CODE_RE = re.compile(r"^[a-z0-9_()-]+$")
_OPTIONS_RE = re.compile(r"^[a-z0-9_:,()-]*$")


def available_layouts():
    """Return [(code, description)] from xkeyboard-config, sorted by description."""
    layouts = []
    in_section = False
    try:
        with open(EVDEV_LST, encoding="utf-8") as f:
            for line in f:
                if line.startswith("!"):
                    in_section = line.strip() == "! layout"
                    continue
                m = _LAYOUT_LINE.match(line) if in_section else None
                # "custom" is xkeyboard-config's empty placeholder for a user-made layout: not a real choice
                if m and m.group(1) != "custom":
                    layouts.append((m.group(1), m.group(2)))
    except OSError as e:
        log.log_error(f"Cannot read {EVDEV_LST}: {e}")
    return sorted(layouts, key=lambda item: item[1].lower())


def valid_layouts(layouts):
    """Return True when layouts is one or two known layout codes (run as root before localectl)."""
    known = {code for code, _desc in available_layouts()}
    return 1 <= len(layouts) <= 2 and all(_CODE_RE.match(code) and code in known for code in layouts)


def valid_options(options):
    """Return True when options is a plain xkb option list like 'grp:alt_shift_toggle,compose:ralt'."""
    return bool(_OPTIONS_RE.match(options or ""))


def parse_query(text):
    """Return (layouts, options) from `setxkbmap -query` output."""
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    layouts = [code.strip() for code in fields.get("layout", "").split(",") if code.strip()]
    return layouts, fields.get("options", "")


def current():
    """Return (layouts, options) the X session types with now; ([], '') when unknown."""
    try:
        out = subprocess.run(["setxkbmap", "-query"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return [], ""
    return parse_query(out)


def parse_x11_conf(text):
    """Return the layout codes of an xorg.conf.d keyboard file (Option "XkbLayout")."""
    m = re.search(r'Option\s+"XkbLayout"\s+"([^"]*)"', text)
    return [code.strip() for code in m.group(1).split(",") if code.strip()] if m else []


def saved_layouts():
    """Return the layouts saved for the whole computer (installer or an earlier Apply), [] when none."""
    try:
        with open(X11_CONF, encoding="utf-8") as f:
            return parse_x11_conf(f.read())
    except OSError:
        return []


def options_for(layouts, options):
    """Return options with the layout switch added for two layouts and removed for one; other options stay."""
    kept = [opt for opt in options.split(",") if opt and not opt.startswith("grp:")]
    if len(layouts) > 1:
        kept.append(SWITCH_OPTION)
    return ",".join(kept)


def apply_now(layouts, options):
    """Switch the running X session to layouts; return (ok, error text)."""
    cmd = ["setxkbmap", "-layout", ",".join(layouts), "-option", ""]
    if options:
        cmd += ["-option", options]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    return proc.returncode == 0, proc.stderr.strip()


def localectl_args(layouts, options):
    """Return the localectl command that saves layouts for X11 (writes 00-keyboard.conf)."""
    return ["localectl", "set-x11-keymap", ",".join(layouts), "", "", options]


def azerty(config_text):
    """Return True/False for the KIRO_AZERTY define in config.def.h, None when it is missing."""
    m = _AZERTY_RE.search(config_text or "")
    return None if m is None else m.group(2) == "true"


def set_azerty(config_text, on):
    """Return config_text with KIRO_AZERTY set to on."""
    return _AZERTY_RE.sub(lambda m: m.group(1) + ("true" if on else "false"), config_text, count=1)


def keys_match(layouts, is_azerty):
    """Return False when the first layout and the workspace keys clearly disagree (be/fr with QWERTY keys or back)."""
    if not layouts or is_azerty is None:
        return True
    return (layouts[0] in AZERTY_LAYOUTS) == is_azerty


def swap_cheatsheet(is_azerty):
    """Copy keybindings-azerty.txt or -qwerty.txt over keybindings.txt, as ohmychadwm-keyboard-layout does."""
    variant = os.path.join(KB_DIR, "keybindings-{}.txt".format("azerty" if is_azerty else "qwerty"))
    if os.path.isfile(variant):
        shutil.copyfile(variant, os.path.join(KB_DIR, "keybindings.txt"))

