"""Update & News: what is waiting, Kiro News, updating in a terminal and restart after a new kernel. Repairing the
package keys and the problems of a boot are ATT's (its Maintenance page), not here.

Everything that needs root runs in a terminal window, so the user sees each step and types their own password;
the app itself never updates the system behind their back.
"""

import html
import json
import os
import re
import shlex
import shutil
import subprocess

from ott_i18n import _

NEWS_FEED = "/usr/share/kiro-news/feed.json"
_TERMINALS = [("alacritty", ["-e"]), ("kitty", []), ("foot", []), ("ghostty", ["-e"]), ("wezterm", ["start", "--"]),
              ("konsole", ["-e"]), ("xfce4-terminal", ["-x"]), ("gnome-terminal", ["--"])]
_TAG_RE = re.compile(r"<[^>]+>")
UPDATE = "sudo pacman -Syu"


def pending():
    """Return the updates waiting as ["name old -> new"], or None when checkupdates could not ask the mirrors."""
    if shutil.which("checkupdates") is None:
        return None
    try:
        result = subprocess.run(["checkupdates"], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 2:  # nothing to update
        return []
    if result.returncode != 0:
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def restart_needed():
    """Return True when the running kernel was replaced by an update (its modules are gone)."""
    return not os.path.isdir(os.path.join("/usr/lib/modules", os.uname().release))


def news(lang, limit=5):
    """Return the newest Kiro News items [{"title", "date", "text", "url"}] in lang when translated."""
    try:
        with open(NEWS_FEED, encoding="utf-8") as f:
            items = json.load(f).get("items") or []
    except (OSError, ValueError, AttributeError):
        return []
    out = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        local = (item.get("i18n") or {}).get(lang) or (item.get("i18n") or {}).get(lang.split("_")[0]) or {}
        text = html.unescape(_TAG_RE.sub(" ", local.get("summary") or item.get("summary") or ""))
        out.append({"title": local.get("title") or item.get("title", ""), "date": item.get("date", ""),
                    "text": " ".join(text.split()), "url": item.get("url", "")})
    return out


def terminal(command):
    """Open command in a terminal window that stays open at the end; return (ok, message)."""
    prompt = shlex.quote(_("Press Enter to close this window.") + " ")
    script = f"{command}; echo; read -r -p {prompt} _"
    for name, flag in _TERMINALS:
        if shutil.which(name):
            try:
                subprocess.Popen([name, *flag, "bash", "-c", script], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
                return True, ""
            except OSError as e:
                return False, str(e)
    return False, _("No terminal found.")


def reboot():
    """Restart the computer."""
    subprocess.Popen(["systemctl", "reboot"], start_new_session=True)
