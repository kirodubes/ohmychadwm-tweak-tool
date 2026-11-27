"""ott-session: go to an app's screen and workspace when it opens, also for the apps that start at login.

chadwm has no way for another program to switch workspaces, so this does what a person does: put the pointer on the
screen (chadwm makes that screen the active one) and press that workspace's key with xdotool. Settings come from
prefs.json ("placement": {"goto": [rule names]}), the rules from config.def.h.
Started by a run.sh line (`ott-session --login`) or by the App placement page; one instance per session.
"""

import os
import re
import subprocess
import sys
import time

import ott_chadwm
import ott_config
import ott_keyboard
import ott_keys
import ott_placement

NAME = "ott-session"
WM_WAIT = 30  # seconds to wait for chadwm at login
SETTLE_QUIET = 3  # login apps have settled when no new window appeared for this long
SETTLE_MAX = 15
_MODS = {"Mod4Mask": "super", "Mod1Mask": "alt", "ControlMask": "ctrl", "ShiftMask": "shift"}


def _say(msg):
    print(f"{time.strftime('%H:%M:%S')} {NAME}: {msg}", file=sys.stderr, flush=True)


def settings():
    """Return the names of the rules with "go to it when it opens", from prefs.json."""
    return set((ott_config.load_prefs().get("placement") or {}).get("goto") or [])


def workspace_keys(config_text):
    """Return {workspace 1-10: xdotool key} from the TAGKEYS lines of config.def.h, KIRO_AZERTY resolved."""
    macros = ott_keys._key_macros(config_text)
    m = re.search(r"^\s*#define\s+MODKEY\s+(\w+)", config_text, re.M)
    mod = _MODS.get(m[1] if m else "Mod4Mask", "super")
    keys = {}
    for line in config_text.splitlines():
        t = ott_keys._TAGKEYS_RE.match(line)
        if t:
            keysym = macros.get(t[1], t[1])
            keys[int(t[2]) + 1] = f"{mod}+{re.sub(r'^XK_', '', keysym)}"
    return keys


def keys_usable(config_text, layouts):
    """Return False when the workspace keys don't match the keyboard (xdotool would add Shift = move the window)."""
    return ott_keyboard.keys_match(layouts, ott_keyboard.azerty(config_text))


_SHIFTVIEW_RE = re.compile(r"\{\s*MODKEY\s*,\s*(XK_\w+)\s*,\s*shiftview\s*,\s*\{\s*\.i\s*=\s*([+-]?1)\s*\}")


def shiftview_keys(config_text):
    """Return (previous, next) xdotool keys of the shiftview bindings (Super+Left/Right in Kiro), or None."""
    found = {int(m[2]): m[1] for m in _SHIFTVIEW_RE.finditer(config_text)}
    m = re.search(r"^\s*#define\s+MODKEY\s+(\w+)", config_text, re.M)
    mod = _MODS.get(m[1] if m else "Mod4Mask", "super")
    if -1 not in found or 1 not in found:
        return None
    return tuple(f"{mod}+{re.sub(r'^XK_', '', found[i])}" for i in (-1, 1))


def steps(current, target, count=10):
    """Return (direction -1/+1, presses) for the shortest way around from workspace current to target."""
    ahead = (target - current) % count
    return (1, ahead) if ahead <= count - ahead else (-1, count - ahead)


def _current_workspace():
    m = re.search(r"= (\d+)", ott_placement._xprop("-root", "_NET_CURRENT_DESKTOP"))
    return int(m[1]) + 1 if m else None


def _switcher():
    """Return go(workspace) for the selected screen, or None when there is no safe way to switch."""
    config = ott_chadwm.read_config()
    arrows = shiftview_keys(config)
    if arrows:
        # arrow keys type the same on every layout; chadwm updates _NET_CURRENT_DESKTOP on a view change only (not
        # on a screen change), so one press first makes it describe the selected screen
        def go(target):
            _press(arrows[1])
            current = _current_workspace()
            if current is None:
                return
            direction, presses = steps(current, target)
            for _i in range(presses):
                _press(arrows[0] if direction < 0 else arrows[1])
        return go
    keys = workspace_keys(config)
    if not keys_usable(config, ott_keyboard.current()[0]):
        _say("the workspace keys don't match the keyboard layout (Keyboard page): not switching workspaces")
        return None
    return lambda target: _press(keys[target]) if target in keys else _say(f"no key for workspace {target}")


def screen_boxes():
    """Return {connector: (number, x, y, w, h)} from `xrandr --listmonitors` (dwm's numbering)."""
    try:
        out = subprocess.run(["xrandr", "--listmonitors"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {}
    boxes = {}
    for line in out.splitlines():
        m = ott_placement._MONITOR.match(line)
        if m:
            boxes[m[3]] = (int(m[1]), int(m[6]), int(m[7]), int(m[4]), int(m[5]))
    return boxes


def _client_ids():
    out = ott_placement._xprop("-root", "_NET_CLIENT_LIST")
    return set(re.findall(r"0x[0-9a-f]+", out.partition("#")[2]))


def _wm_names(wid):
    names = re.findall(r'"([^"]*)"', ott_placement._xprop("-id", wid, "WM_CLASS"))
    return (names[0], names[1]) if len(names) > 1 else (None, None)


def _rule_for(rules, wm_instance, wm_class):
    """Return the plain rule chadwm applies to this window, or None (the last match wins, as in applyrules())."""
    hits = [r for r in rules if r["editable"] and ott_placement.matches(r, wm_instance, wm_class)]
    return hits[-1] if hits else None


def _xdotool(*args):
    subprocess.run(["xdotool", *args], capture_output=True, timeout=5)


def _centre(box):
    _number, x, y, w, h = box
    return str(x + w // 2), str(y + h // 2)


def _select_screen(box, boxes):
    # chadwm selects a screen on pointer motion only when the screen differs from the one of the previous motion,
    # and the first motion of a session only records it (motionnotify(): `m != mon && mon`). So: target, another
    # screen, target again; that also selects it right after login.
    other = next((b for b in boxes.values() if b != box), None)
    for target in ((box, other, box) if other else (box,)):
        _xdotool("mousemove", *_centre(target))
        time.sleep(0.1)
    time.sleep(0.1)


def pointer():
    """Return the pointer position as (x, y) strings, or None when xdotool can't tell."""
    try:
        where = subprocess.run(["xdotool", "getmouselocation", "--shell"], capture_output=True, text=True,
                               timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    pos = dict(line.split("=", 1) for line in where.splitlines() if "=" in line)
    return (pos["X"], pos["Y"]) if "X" in pos and "Y" in pos else None


def move_pointer(pos):
    """Put the pointer back at pos from pointer()."""
    _xdotool("mousemove", *pos)


def select_screen(connector):
    """Make connector chadwm's active screen (new windows open there); return False when it isn't on."""
    boxes = screen_boxes()
    if connector not in boxes:
        return False
    _select_screen(boxes[connector], boxes)
    return True


def _press(key):
    _xdotool("key", "--clearmodifiers", key)
    time.sleep(0.15)


def _wait_for_wm():
    end = time.time() + WM_WAIT
    while time.time() < end:
        if "window id #" in ott_placement._xprop("-root", "_NET_SUPPORTING_WM_CHECK"):
            return True
        time.sleep(0.5)
    return False


def _settle(seen):
    # login apps map their windows during the first seconds; wait until they are all there
    last_change, end = time.time(), time.time() + SETTLE_MAX
    while time.time() < end and time.time() - last_change < SETTLE_QUIET:
        time.sleep(0.5)
        ids = _client_ids()
        if ids - seen:
            seen |= ids
            last_change = time.time()
    return seen


def login_plan(goto, names, rules, boxes):
    """Return [(connector, workspace, rule name)]: what each screen shows after login. Every "go to it" rule among
    names (apps that opened at login) brings its workspace to the front; two on one screen: the last rule wins."""
    by_number = {b[0]: c for c, b in boxes.items()}
    plan = {}
    for rule in rules:
        if rule["class"] in goto and rule["class"] in names and rule["workspace"]:
            connector = by_number.get(max(rule["monitor"], 0))  # "current screen" is the primary one at login
            if connector:
                plan[connector] = (rule["workspace"], rule["class"])
    return [(c, w, n) for c, (w, n) in sorted(plan.items(), key=lambda item: boxes[item[0]][0])]


def show_login_workspaces(goto):
    """Show the login workspaces on every screen, then put the pointer back where it was."""
    go, boxes = _switcher(), screen_boxes()
    if go is None:
        return
    rules = ott_placement.rules(ott_chadwm.read_config())
    open_names = {r["class"] for r in (_rule_for(rules, *_wm_names(wid)) for wid in _client_ids()) if r}
    plan = login_plan(goto, open_names, rules, boxes)
    where = subprocess.run(["xdotool", "getmouselocation", "--shell"], capture_output=True, text=True).stdout
    for connector, workspace, _name in plan:
        _select_screen(boxes[connector], boxes)
        go(workspace)
        _say(f"{connector} shows workspace {workspace}")
    pos = dict(line.split("=", 1) for line in where.splitlines() if "=" in line)
    if "X" in pos and "Y" in pos:
        _xdotool("mousemove", pos["X"], pos["Y"])


def go_to(rule):
    """Select the screen and workspace of rule, so the window that just opened is in front."""
    go = _switcher()
    if go is None:
        return
    if rule["monitor"] >= 0:
        boxes = screen_boxes()
        box = next((b for b in boxes.values() if b[0] == rule["monitor"]), None)
        if box:
            _select_screen(box, boxes)
    if rule["workspace"]:
        go(rule["workspace"])
    _say(f"went to {rule['class']}: screen {rule['monitor'] + 1 if rule['monitor'] >= 0 else 'current'}, "
         f"workspace {rule['workspace'] or 'current'}")


def watch(seen):
    """Follow _NET_CLIENT_LIST; a window id not seen before whose rule has "go to it" brings you there."""
    spy = subprocess.Popen(["xprop", "-root", "-spy", "_NET_CLIENT_LIST"], stdout=subprocess.PIPE, text=True)
    for line in spy.stdout:
        ids = set(re.findall(r"0x[0-9a-f]+", line.partition("#")[2]))
        new, seen = ids - seen, seen | ids  # ids survive Super+Shift+R, so a restart triggers nothing
        goto = settings()
        if not new or not goto:
            continue
        rules = ott_placement.rules(ott_chadwm.read_config())
        for wid in sorted(new):
            rule = _rule_for(rules, *_wm_names(wid))
            if rule and rule["class"] in goto:
                time.sleep(0.2)  # let chadwm finish placing it
                go_to(rule)


def _already_running():
    out = subprocess.run(["pgrep", "-x", NAME], capture_output=True, text=True).stdout.split()
    return any(int(pid) != os.getpid() for pid in out)


def main():
    """Run once per session: at login (--login) show the "go to it" login apps, then watch for new windows."""
    try:
        with open("/proc/self/comm", "w") as f:
            f.write(NAME)  # so run.sh's `pgrep -x` and the page find it under its own name, not python3
    except OSError:
        pass
    if _already_running():
        return
    if not _wait_for_wm():
        _say("Ohmychadwm is not running")
        return
    seen = _client_ids()
    if "--login" in sys.argv:
        seen = _settle(seen)
        goto = settings()
        if goto:
            show_login_workspaces(goto)
    watch(seen)  # cheap; the page stops this helper when no rule has "go to it"


if __name__ == "__main__":
    main()
