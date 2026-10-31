"""Wallpapers: where to pick them from, the current one from ~/.fehbg, and setting one with feh.

feh writes ~/.fehbg itself, and ohmychadwm's run.sh runs that file at login, so setting it once is enough.
Toolkit-free.
"""

import glob
import os
import re
import shlex
import subprocess

import log
from ott_i18n import _

OHMYCHADWM_DIR = os.path.expanduser("~/.config/ohmychadwm/wallpapers")
VARIETY_DIR = os.path.expanduser("~/.config/variety")
FEHBG = os.path.expanduser("~/.fehbg")
# What run.sh shows when there is no ~/.fehbg yet.
KIRO_DEFAULT = os.path.join(OHMYCHADWM_DIR, "kiro-swirl.png")

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")
MODES = ["fill", "scale", "center", "max", "tile"]
_BG_RE = re.compile(r"--bg-(fill|scale|center|max|tile)\b")


def sources():
    """Return [(label, [folders])] to pick wallpapers from."""
    downloaded = sorted(d for d in glob.glob(os.path.join(VARIETY_DIR, "Downloaded", "*")) if os.path.isdir(d))
    # list_images reads only the top level, and the shipped Kiro wallpaper sits in the kiro/ subfolder
    kiro = [OHMYCHADWM_DIR, "/usr/share/backgrounds", "/usr/share/backgrounds/kiro"]
    return [
        (_("Ohmychadwm wallpapers"), kiro),
        (_("Variety downloads"), downloaded or [os.path.join(VARIETY_DIR, "Downloaded")]),
        (_("Variety favourites"), [os.path.join(VARIETY_DIR, "Favorites")]),
    ]


def list_images(folders):
    """Return the image files in folders (top level of each), sorted by name."""
    images = []
    for folder in folders:
        try:
            names = os.listdir(folder)
        except OSError:
            continue
        images += [os.path.join(folder, n) for n in names if n.lower().endswith(IMAGE_EXTS)]
    return sorted(images, key=lambda p: os.path.basename(p).lower())


def current():
    """Return (path, mode) from ~/.fehbg, or (KIRO_DEFAULT, 'scale') when feh hasn't set one yet."""
    try:
        with open(FEHBG, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return KIRO_DEFAULT, "scale"
    for line in text.splitlines():
        if not line.lstrip().startswith("feh"):
            continue
        m = _BG_RE.search(line)
        try:
            parts = shlex.split(line)
        except ValueError:
            continue
        paths = [p for p in parts[1:] if not p.startswith("-")]
        if paths:
            return paths[0], m.group(1) if m else "fill"
    return KIRO_DEFAULT, "scale"


def apply(path, mode):
    """Show path with feh in mode now (feh also rewrites ~/.fehbg); return (ok, message). Call from a thread."""
    if mode not in MODES:
        return False, f"unknown mode {mode!r}"
    try:
        proc = subprocess.run(["feh", f"--bg-{mode}", path], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, _("feh could not run: {error}").format(error=e)
    ok = proc.returncode == 0
    (log.log_success if ok else log.log_error)(f"Wallpaper via feh: {path} {proc.stderr.strip()}".rstrip())
    return ok, _("Set by feh.") if ok else _("feh failed: {error}").format(error=proc.stderr.strip())


def variety(*args):
    """Run variety with args (starts Variety when it isn't running)."""
    try:
        subprocess.Popen(["variety", *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except OSError as e:
        log.log_error(f"variety: {e}")
        return False
