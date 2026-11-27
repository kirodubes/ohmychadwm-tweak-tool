"""Displays: read the outputs from xrandr, switch now, and save the layout as ~/.screenlayout/<user>.sh.

ohmychadwm's run.sh runs that file on session start. The script is written in arandr's format, so arandr can
open and edit it later. Works on any machine; inside VirtualBox 1920x1080 is preselected. Toolkit-free.
"""

import getpass
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from ott_i18n import _

LAYOUT_DIR = os.path.expanduser("~/.screenlayout")

VIRTUALBOX_MODE = "1920x1080"

# "Virtual-1 connected primary 1920x1080+0+0 left (normal left inverted right x axis y axis) 0mm x 0mm"
_HEADER = re.compile(
    r"^(?P<name>\S+) (?P<state>connected|disconnected)(?P<primary> primary)?"
    r"(?: (?P<w>\d+)x(?P<h>\d+)\+(?P<x>\d+)\+(?P<y>\d+))?(?: (?P<rot>normal|left|inverted|right))?"
)
# "   1920x1080     60.00*+  50.00    59.94  "
_MODE = re.compile(r"^\s+(\d+x\d+)i?\s+(.*)$")
_RATE = re.compile(r"(\d+\.\d+)([*+ ]*)")


@dataclass
class Output:
    """One xrandr output as it is now, with the modes and rates it offers."""

    name: str
    connected: bool
    primary: bool = False
    mode: str | None = None  # WxH, None when the output is off
    rate: str | None = None
    x: int = 0
    y: int = 0
    rotate: str = "normal"
    modes: dict = field(default_factory=dict)  # WxH -> [rate, ...] in xrandr's order
    preferred: str | None = None


def is_virtualbox():
    """Return True when running inside a VirtualBox guest."""
    try:
        out = subprocess.run(["systemd-detect-virt", "--vm"], capture_output=True, text=True).stdout.strip()
        if out:
            return out == "oracle"
    except OSError:
        pass
    try:
        with open("/sys/class/dmi/id/product_name", encoding="utf-8") as f:
            return f.read().strip() == "VirtualBox"
    except OSError:
        return False


def layout_path():
    """Return the layout file run.sh runs on login: ~/.screenlayout/<user>.sh."""
    return os.path.join(LAYOUT_DIR, f"{getpass.getuser()}.sh")


def parse(xrandr_query):
    """Return [Output] from `xrandr --query` text, connected and disconnected."""
    outputs, current = [], None
    for line in xrandr_query.splitlines():
        m = _HEADER.match(line)
        if m:
            current = Output(name=m["name"], connected=m["state"] == "connected", primary=bool(m["primary"]))
            if m["w"]:
                current.mode = f"{m['w']}x{m['h']}"
                current.x, current.y = int(m["x"]), int(m["y"])
                current.rotate = m["rot"] or "normal"
            outputs.append(current)
            continue
        mode = _MODE.match(line)
        if current is None or not mode:
            continue
        rates = current.modes.setdefault(mode[1], [])
        for rate, flags in _RATE.findall(mode[2]):
            if rate not in rates:
                rates.append(rate)
            if "*" in flags and current.mode == mode[1]:
                current.rate = rate
            if "+" in flags and current.preferred is None:
                current.preferred = mode[1]
    return outputs


def query():
    """Return [Output] for this X screen; raises OSError / CalledProcessError when xrandr fails."""
    return parse(subprocess.run(["xrandr", "--query"], capture_output=True, text=True, check=True).stdout)


def _edid_name(edid):
    # the four 18-byte descriptors of the EDID base block; tag 0xFC holds the monitor name
    for offset in (54, 72, 90, 108):
        desc = edid[offset:offset + 18]
        if len(desc) == 18 and desc[:3] == b"\0\0\0" and desc[3] == 0xFC:
            return desc[5:].split(b"\n")[0].decode("ascii", "replace").strip() or None
    return None


def parse_models(prop_text):
    """Return {output: monitor model} from `xrandr --prop` text, read from each output's EDID."""
    models, current, hexbuf, in_edid = {}, None, [], False
    for line in prop_text.splitlines() + [""]:
        if in_edid:
            if re.fullmatch(r"[0-9a-fA-F]+", line.strip()):
                hexbuf.append(line.strip())
                continue
            in_edid = False
            try:
                name = _edid_name(bytes.fromhex("".join(hexbuf)))
            except ValueError:
                name = None
            if name:
                models[current] = name
        m = _HEADER.match(line)
        if m:
            current = m["name"]
        elif line.strip() == "EDID:" and current:
            in_edid, hexbuf = True, []
    return models


def models():
    """Return {output: monitor model} for the connected outputs; {} when xrandr fails."""
    try:
        text = subprocess.run(["xrandr", "--prop"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {}
    return parse_models(text)


def dpms_sleep_to_15():
    """Set the power manager's screen sleep to 15 minutes where it still has Kiro's old default (blank 15, sleep 30).

    Blanking doesn't reach a screen on a second GPU, DPMS sleep does (kiro-xfce 2026.11.27). A user's own values are
    left alone. Return the properties set, or None when xfconf can't be read (try again at the next start).
    """
    if not shutil.which("xfconf-query"):
        return []
    channel = "xfce4-power-manager"
    try:
        proc = subprocess.run(["xfconf-query", "-c", channel, "-l", "-v"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        # no channel yet = the power manager never saved anything: nothing to migrate
        return [] if "does not exist" in proc.stderr else None
    values = dict(line.split(None, 1) for line in proc.stdout.splitlines() if len(line.split(None, 1)) == 2)
    changed = []
    for power in ("ac", "battery"):
        blank, sleep = f"/{channel}/blank-on-{power}", f"/{channel}/dpms-on-{power}-sleep"
        if values.get(blank, "").strip() == "15" and values.get(sleep, "").strip() == "30":
            if subprocess.run(["xfconf-query", "-c", channel, "-p", sleep, "-s", "15"],
                              capture_output=True, timeout=10).returncode == 0:
                changed.append(sleep)
    return changed


def _width(out):
    w, h = (int(n) for n in out.mode.split("x"))
    return h if out.rotate in ("left", "right") else w


def left_to_right(outputs):
    """Return the names of the enabled outputs, left to right."""
    return [o.name for o in sorted((o for o in outputs if o.mode), key=lambda o: (o.x, o.y))]


def plan(outputs, wanted, primary, order=None):
    """Return new [Output] with wanted {name: (mode or None, rate)} applied and primary set.

    order is the wanted left-to-right list of output names. When it differs from the current order, or a width
    changes, the enabled outputs are placed side by side again (in order, else in their current order), so they
    never overlap; otherwise every position stays as it is.
    """
    new, reflow = [], False
    for out in outputs:
        out = Output(**{**out.__dict__, "modes": out.modes})
        if out.name in wanted:
            mode, rate = wanted[out.name]
            old_width = _width(out) if out.mode else None
            out.mode, out.rate = mode, (rate if mode else None)
            if (_width(out) if out.mode else None) != old_width:
                reflow = True
        out.primary = out.name == primary and out.mode is not None
        new.append(out)
    enabled = [o for o in new if o.mode]
    if order:
        rank = {name: i for i, name in enumerate(order)}
        wanted_order = [o.name for o in sorted(enabled, key=lambda o: (rank.get(o.name, len(rank)), o.x))]
        if wanted_order != left_to_right(enabled):
            reflow = True
    else:
        rank = None
    if reflow:
        x = 0
        key = (lambda o: (rank.get(o.name, len(rank)), o.x)) if rank else (lambda o: o.x)
        for out in sorted(enabled, key=key):
            out.x, out.y = x, 0
            x += _width(out)
    return new


def build_script(outputs):
    """Return an arandr-style layout script for outputs, or None when no output is on."""
    args, active = [], False
    for out in outputs:
        args += ["--output", out.name]
        if out.connected and out.mode:
            active = True
            if out.primary:
                args.append("--primary")
            args += ["--mode", out.mode, "--pos", f"{out.x}x{out.y}", "--rotate", out.rotate]
            # arandr writes no --rate, so only add one when it isn't the mode's default (first) rate
            if out.rate and out.rate != (out.modes.get(out.mode) or [None])[0]:
                args += ["--rate", out.rate]
        else:
            args.append("--off")
    if not active:
        return None
    return "#!/bin/sh\nxrandr " + " ".join(args) + "\n"


def _run(script):
    proc = subprocess.run(["sh", "-c", script], capture_output=True, text=True)
    return proc.returncode == 0, proc.stderr.strip()


def switch(wanted, primary, order=None):
    """Apply wanted {name: (mode or None, rate)} in order (left to right) now without saving.

    Return (ok, message, new_script, old_script).
    """
    try:
        outputs = query()
    except (OSError, subprocess.CalledProcessError) as e:
        return False, _("xrandr failed: {error}").format(error=e), None, None
    old = build_script(outputs)
    new = build_script(plan(outputs, wanted, primary, order))
    if new is None:
        return False, _("At least one display has to stay on."), None, None
    ok, err = _run(new)
    if not ok:
        _run(old)
        return False, _("xrandr could not use this layout: {error}").format(error=err), None, None
    return True, _("Display layout changed."), new, old


def revert(old_script):
    """Switch back to the layout from before switch(); return (ok, message)."""
    if old_script is None:
        return False, _("There is no previous layout to go back to.")
    ok, err = _run(old_script)
    return (True, _("Display layout reverted, nothing saved.")) if ok else (False, _("Revert failed: {error}").format(
        error=err))


def save(script):
    """Write script to layout_path() (one-time .oma-bak backup); return (ok, message)."""
    path = layout_path()
    try:
        os.makedirs(LAYOUT_DIR, exist_ok=True)
        backup = path + ".oma-bak"
        if os.path.isfile(path) and not os.path.exists(backup):
            shutil.copy2(path, backup)
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        os.chmod(path, 0o755)
    except OSError as e:
        return False, f"{path}: {e}"
    short = path.replace(os.path.expanduser("~"), "~", 1)
    return True, _("Layout kept and saved to {path}, so every login uses it.").format(path=short)
