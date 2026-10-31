"""The ohmychadwm half: bar theme include, the managed font + bar & window block, rebuild and restart.

Every theme header defines its own THEME_FONT, so the #ifndef fallback in
config.def.h never fires. The bar font and the bar & window options are therefore
overridden by one managed #undef/#define block placed *after* the theme includes. Text transforms are pure
functions over the file contents so they can be tested without touching disk.
"""

import os
import re
import shutil
import subprocess
from ott_i18n import _

CHADWM_DIR = os.path.expanduser("~/.config/ohmychadwm/chadwm")
CONFIG = os.path.join(CHADWM_DIR, "config.def.h")

_INCLUDE_RE = re.compile(r'^(\s*)(//\s*)?#include\s+"themes/([^"/]+)\.h"')
BLOCK_BEGIN = "/* >>> ohmychadwm-tweak-tool managed - regenerated, do not hand-edit >>> */"
BLOCK_END = "/* <<< ohmychadwm-tweak-tool managed <<< */"
# Written by Ohmychadwm Appearance, the app this one replaces: read and replaced, never written.
_OLD_MARKERS = (
    "/* >>> ohmychadwm-appearance managed - regenerated, do not hand-edit >>> */",
    "/* <<< ohmychadwm-appearance managed <<< */",
)
_BEGINS = (BLOCK_BEGIN, _OLD_MARKERS[0])
_ENDS = (BLOCK_END, _OLD_MARKERS[1])

# Bar & window options every themes/*.h defines, in the order the block lists them.
OPTIONS = ("THEME_BORDER", "THEME_GAPS", "THEME_SMARTGAPS", "THEME_TOPBAR", "THEME_SHOWSYSTRAY", "THEME_AUTOHIDE")
_DEFINE_RE = re.compile(r"^\s*#define\s+(THEME_\w+)\s+(.+?)\s*(?:/[*/].*)?$")


def themes():
    """Return the sorted bar theme names found in the user's chadwm/themes directory."""
    try:
        names = os.listdir(os.path.join(CHADWM_DIR, "themes"))
    except OSError:
        return []
    return sorted((n[:-2] for n in names if n.endswith(".h")), key=str.lower)


def read_config():
    """Return the user's config.def.h contents, or '' when ohmychadwm isn't set up."""
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def write_config(text):
    """Write config.def.h, keeping a one-time .oma-bak copy of the original."""
    # .oma-bak is the name Ohmychadwm Appearance used: a new name would back up an already edited file.
    backup = CONFIG + ".oma-bak"
    if not os.path.exists(backup) and os.path.exists(CONFIG):
        shutil.copy2(CONFIG, backup)
    with open(CONFIG, "w", encoding="utf-8") as f:
        f.write(text)


def active_theme(text):
    """Return the name of the uncommented theme include, or None."""
    for line in text.splitlines():
        m = _INCLUDE_RE.match(line)
        if m and not m.group(2):
            return m.group(3)
    return None


def set_theme(text, name):
    """Return text with exactly one theme include active: the one called name."""
    lines = text.splitlines(keepends=True)
    seen = False
    last = -1
    for i, line in enumerate(lines):
        m = _INCLUDE_RE.match(line)
        if not m:
            continue
        last = i
        indent, _comment, stem = m.groups()
        eol = "\n" if line.endswith("\n") else ""
        if stem == name:
            seen = True
            lines[i] = f'{indent}#include "themes/{stem}.h"{eol}'
        else:
            lines[i] = f'{indent}//#include "themes/{stem}.h"{eol}'
    if not seen:
        if last < 0:
            raise ValueError("no theme #include lines found in config.def.h")
        lines.insert(last + 1, f'#include "themes/{name}.h"\n')
    return "".join(lines)


def theme_values(name):
    """Return {option: int} as themes/<name>.h defines the bar & window options."""
    try:
        with open(os.path.join(CHADWM_DIR, "themes", f"{name}.h"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return {}
    values = {}
    for line in text.splitlines():
        m = _DEFINE_RE.match(line)
        if m and m.group(1) in OPTIONS:
            try:
                values[m.group(1)] = int(m.group(2))
            except ValueError:
                pass
    return values


def _split_block(text):
    """Return (lines outside every managed block, the block's #define lines)."""
    out, inside, block = [], False, []
    for line in text.splitlines(keepends=True):
        if line.strip() in _BEGINS:
            inside = True
        elif line.strip() in _ENDS:
            inside = False
        elif inside:
            block.append(line)
        else:
            out.append(line)
    return out, block


def _block_defines(text):
    defines = {}
    for line in _split_block(text)[1]:
        m = _DEFINE_RE.match(line)
        if m:
            defines[m.group(1)] = m.group(2)
    return defines


def bar_font(text):
    """Return (family, size) from the managed block, or None when the theme's own font is used."""
    d = _block_defines(text)
    if "THEME_FONT" not in d or "THEME_FONTSIZE" not in d:
        return None
    try:
        return d["THEME_FONT"].strip('"'), int(d["THEME_FONTSIZE"])
    except ValueError:
        return None


def bar_options(text):
    """Return {option: int} for the bar & window options the managed block overrides."""
    out = {}
    for key, value in _block_defines(text).items():
        if key in OPTIONS:
            try:
                out[key] = int(value)
            except ValueError:
                pass
    return out


def _write_block(text, font, options):
    """Return text with one managed block (font and/or options) after the last theme include, or none if empty."""
    lines = _split_block(text)[0]
    if not font and not options:
        return "".join(lines)
    last = max((i for i, line in enumerate(lines) if _INCLUDE_RE.match(line)), default=-1)
    if last < 0:
        raise ValueError("no theme #include lines found in config.def.h")
    block = [BLOCK_BEGIN + "\n"]
    if font:
        family = font[0].replace('"', "").replace("\\", "")
        block += [
            "#undef  THEME_FONT\n",
            f'#define THEME_FONT     "{family}"\n',
            "#undef  THEME_FONTSIZE\n",
            f"#define THEME_FONTSIZE {int(round(font[1]))}\n",
        ]
    for key in OPTIONS:
        if key in options:
            block += [f"#undef  {key}\n", f"#define {key} {int(options[key])}\n"]
    block.append(BLOCK_END + "\n")
    lines[last + 1:last + 1] = block
    return "".join(lines)


def set_bar_font(text, family, size):
    """Return text whose managed block overrides THEME_FONT/THEME_FONTSIZE (options are kept)."""
    return _write_block(text, (family, size), bar_options(text))


def clear_bar_font(text):
    """Return text without the bar font override (the theme's own font applies again; options are kept)."""
    return _write_block(text, None, bar_options(text))


def set_bar_options(text, options):
    """Return text whose managed block overrides exactly these bar & window options (the font is kept)."""
    return _write_block(text, bar_font(text), {k: v for k, v in options.items() if k in OPTIONS})


SKEL_CONFIG = "/etc/skel/.config/ohmychadwm/chadwm/config.def.h"
FALLBACK_THEME = "dracul"
BUILT_BINARY = os.path.join(CHADWM_DIR, "ohmychadwm")


def default_theme():
    """Return the bar theme Kiro ships (active include in the skel config.def.h)."""
    try:
        with open(SKEL_CONFIG, encoding="utf-8") as f:
            return active_theme(f.read()) or FALLBACK_THEME
    except OSError:
        return FALLBACK_THEME


def _run(cmd):
    proc = subprocess.run(cmd, cwd=CHADWM_DIR, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def compile_wm():
    """Compile ohmychadwm as the user into BUILT_BINARY; return (ok, message)."""
    # config.h is only regenerated from config.def.h when missing, so clean first.
    _run(["make", "clean"])
    rc, out = _run(["make"])
    if rc != 0:
        clean()
        return False, _("Compile failed:") + "\n" + out[-1500:]
    return True, "compiled"


def clean():
    """Remove build products from the user's chadwm directory."""
    _run(["make", "clean"])


def in_session():
    """Return True when the app runs inside an ohmychadwm session (not XFCE or another desktop)."""
    names = " ".join(os.environ.get(k, "") for k in ("DESKTOP_SESSION", "XDG_SESSION_DESKTOP", "XDG_CURRENT_DESKTOP"))
    if names.strip():
        return "ohmychadwm" in names.lower()
    # startx and friends set none of these: then a running ohmychadwm is the session
    return subprocess.run(["pgrep", "-u", str(os.getuid()), "-x", "ohmychadwm"], capture_output=True).returncode == 0


def can_restart():
    """Return True when the app can restart ohmychadwm itself (needs xdotool and a running ohmychadwm session)."""
    return shutil.which("xdotool") is not None and in_session()


def restart():
    """Send Super+Shift+R; dwm's restart exits 0 and the run.sh session loop relaunches it."""
    subprocess.Popen(["xdotool", "key", "--clearmodifiers", "super+shift+r"])
