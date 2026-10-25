"""Default apps: xdg-mime defaults, plus the terminal and file manager on ohmychadwm's keys.

sxhkdrc hard-codes alacritty and thunar on Super+Enter and friends, so xdg-mime alone would not change what
those keys open: the terminal and file manager are written into the user's sxhkdrc, then sxhkd reloads it.
Only a key whose command is a single word is rewritten, so a hand-made command stays. Toolkit-free.
"""

import configparser
import os
import shutil
import subprocess

import ott_keys

# (label, mime types; the first one is read as the current default)
CATEGORIES = [
    ("Web browser", ["x-scheme-handler/https", "x-scheme-handler/http", "text/html"]),
    ("File manager", ["inode/directory"]),
    ("Text editor", ["text/plain"]),
    ("Image viewer", ["image/png", "image/jpeg", "image/gif", "image/webp"]),
    ("Video player", ["video/mp4", "video/x-matroska", "video/webm"]),
    ("Music player", ["audio/mpeg", "audio/flac", "audio/ogg"]),
    ("PDF viewer", ["application/pdf"]),
    ("Mail", ["x-scheme-handler/mailto"]),
]

TERMINAL_KEYS = ["super + Return", "super + KP_Enter", "super + t"]
FILES_KEYS = ["super + shift + Return", "super + shift + KP_Enter", "super + F8"]
TERMINALS = ["alacritty", "kitty", "ghostty", "wezterm", "xfce4-terminal", "terminator", "tilix", "konsole",
             "gnome-terminal", "lxterminal", "st", "urxvt", "xterm"]
FILE_MANAGERS = ["thunar", "pcmanfm", "pcmanfm-qt", "nemo", "nautilus", "caja", "dolphin", "spacefm"]

_APP_DIRS = [os.path.expanduser("~/.local/share/applications"), "/usr/share/applications"]


def _desktop_files():
    """Return {desktop id: (name, mime types)} for every visible app, the user's own copies first."""
    found = {}
    for folder in _APP_DIRS:
        try:
            names = os.listdir(folder)
        except OSError:
            continue
        for fname in names:
            if not fname.endswith(".desktop") or fname in found:
                continue
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                cp.read(os.path.join(folder, fname), encoding="utf-8")
                entry = cp["Desktop Entry"]
            except (configparser.Error, KeyError, UnicodeDecodeError):
                continue
            if entry.get("NoDisplay", "false").lower() == "true" or entry.get("Hidden", "false").lower() == "true":
                continue
            mimes = [m for m in entry.get("MimeType", "").split(";") if m]
            found[fname] = (entry.get("Name", fname[:-8]), mimes)
    return found


def candidates(apps=None):
    """Return {label: [(desktop id, name)]} of the installed apps that open each category."""
    apps = _desktop_files() if apps is None else apps
    out = {}
    for label, mimes in CATEGORIES:
        rows = [(did, name) for did, (name, types) in apps.items() if any(m in types for m in mimes)]
        out[label] = sorted(rows, key=lambda r: r[1].lower())
    return out


def current(label):
    """Return the desktop id xdg-mime has as default for a category, or ''."""
    mime = dict(CATEGORIES)[label][0]
    try:
        out = subprocess.run(["xdg-mime", "query", "default", mime], capture_output=True, text=True)
    except OSError:
        return ""
    return out.stdout.strip()


def set_default(label, desktop_id):
    """Make desktop_id the default for every mime type of a category; return (ok, message)."""
    try:
        if label == "Web browser":
            subprocess.run(["xdg-settings", "set", "default-web-browser", desktop_id], capture_output=True)
        proc = subprocess.run(["xdg-mime", "default", desktop_id, *dict(CATEGORIES)[label]],
                              capture_output=True, text=True)
    except OSError as e:
        return False, f"{label}: {e}"
    if proc.returncode != 0:
        return False, f"{label}: {proc.stderr.strip()}"
    return True, f"{label}: {desktop_id}"


def installed(names):
    """Return the names from the list that are on PATH."""
    return [n for n in names if shutil.which(n)]


def key_command(text, keys):
    """Return the single-word command on the first of keys that has one in sxhkdrc text, or None."""
    for k in keys:
        cmd = ott_keys.sxhkd_command(text, k)
        if cmd and len(cmd.split()) == 1:
            return cmd
    return None


def set_key_command(text, keys, command):
    """Return sxhkdrc text with every single-word command on keys replaced by command."""
    for k in keys:
        cmd = ott_keys.sxhkd_command(text, k)
        if cmd and len(cmd.split()) == 1:
            text = ott_keys.set_sxhkd_command(text, k, command)
    return text


def reload_sxhkd():
    """Ask a running sxhkd to re-read its config (SIGUSR1)."""
    subprocess.run(["pkill", "-USR1", "-x", "sxhkd"], capture_output=True)
