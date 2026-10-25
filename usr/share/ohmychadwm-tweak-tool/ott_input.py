"""Mouse and touchpad: live via xinput (libinput properties), saved as an xorg.conf.d InputClass file.

xinput changes are gone at logout, so Save also writes CONF_PATH through the root helper; X reads it at every
start. validate() runs as root before anything is written, so the helper only ever writes values it built itself.
Toolkit-free.
"""

import re
import subprocess

CONF_PATH = "/etc/X11/xorg.conf.d/30-ohmychadwm-input.conf"

# (key, xinput property, xorg.conf Option, kind)
_FIELDS = {
    "pointer": [
        ("accel", "libinput Accel Speed", "AccelSpeed", float),
        ("natural", "libinput Natural Scrolling Enabled", "NaturalScrolling", bool),
        ("left_handed", "libinput Left Handed Enabled", "LeftHanded", bool),
    ],
    "touchpad": [
        ("accel", "libinput Accel Speed", "AccelSpeed", float),
        ("tapping", "libinput Tapping Enabled", "Tapping", bool),
        ("natural", "libinput Natural Scrolling Enabled", "NaturalScrolling", bool),
        ("dwt", "libinput Disable While Typing Enabled", "DisableWhileTyping", bool),
    ],
}
# libinput's own defaults, used when neither the file nor a live device says otherwise.
DEFAULTS = {
    "pointer": {"accel": 0.0, "natural": False, "left_handed": False},
    "touchpad": {"accel": 0.0, "tapping": False, "natural": False, "dwt": True},
}
_MATCH = {"pointer": "MatchIsPointer", "touchpad": "MatchIsTouchpad"}
_IDENT = {"pointer": "ohmychadwm pointer", "touchpad": "ohmychadwm touchpad"}

_SLAVE_RE = re.compile(r"^\W*(?P<name>.+?)\s+id=(?P<id>\d+)\s+\[slave\s+pointer")
_PROP_RE = re.compile(r"^\s+(?P<name>[^(]+?)\s+\(\d+\):\s+(?P<value>.*)$")
_OPTION_RE = re.compile(r'^\s*Option\s+"(\w+)"\s+"([^"]*)"')
_IDENT_RE = re.compile(r'^\s*Identifier\s+"([^"]*)"')


def validate(settings):
    """Return a clean {kind: {key: value}} from settings, raising ValueError on anything unexpected."""
    if not isinstance(settings, dict):
        raise ValueError("expected an object")
    clean = {}
    for kind, values in settings.items():
        if kind not in _FIELDS or not isinstance(values, dict):
            raise ValueError(f"unknown device kind {kind!r}")
        fields = {f[0]: f[3] for f in _FIELDS[kind]}
        clean[kind] = {}
        for key, value in values.items():
            if key not in fields:
                raise ValueError(f"unknown {kind} setting {key!r}")
            if fields[key] is bool:
                if not isinstance(value, bool):
                    raise ValueError(f"{kind}.{key} must be true or false")
            else:
                value = float(value)
                if not -1.0 <= value <= 1.0:
                    raise ValueError(f"{kind}.{key} must be between -1 and 1")
                value = round(value, 2)
            clean[kind][key] = value
    return clean


def build_conf(settings):
    """Return the xorg.conf.d text for validated settings (touchpad last, so it wins over the pointer section)."""
    out = ["# Written by ohmychadwm-tweak-tool (Mouse & touchpad). Saving there again overwrites this file.\n"]
    for kind in ("pointer", "touchpad"):
        values = settings.get(kind)
        if not values:
            continue
        out += [
            "\nSection \"InputClass\"\n",
            f'    Identifier "{_IDENT[kind]}"\n',
            f'    {_MATCH[kind]} "on"\n',
            '    MatchDriver "libinput"\n',
        ]
        for key, _prop, option, typ in _FIELDS[kind]:
            if key in values:
                value = values[key]
                text = ("on" if value else "off") if typ is bool else f"{value:g}"
                out.append(f'    Option "{option}" "{text}"\n')
        out.append("EndSection\n")
    return "".join(out)


def read_conf(path=CONF_PATH):
    """Return {kind: {key: value}} from the saved file, or {} when there is none."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return {}
    by_ident = {v: k for k, v in _IDENT.items()}
    out, kind = {}, None
    for line in lines:
        if m := _IDENT_RE.match(line):
            kind = by_ident.get(m.group(1))
            if kind:
                out.setdefault(kind, {})
        elif kind and (m := _OPTION_RE.match(line)):
            for key, _prop, option, typ in _FIELDS[kind]:
                if option == m.group(1):
                    try:
                        out[kind][key] = m.group(2) == "on" if typ is bool else float(m.group(2))
                    except ValueError:
                        pass
        elif line.strip() == "EndSection":
            kind = None
    return out


def _xinput(*args):
    return subprocess.run(["xinput", *args], capture_output=True, text=True, check=True).stdout


def _props(dev_id):
    props = {}
    for line in _xinput("list-props", dev_id).splitlines():
        if m := _PROP_RE.match(line):
            props[m.group("name")] = m.group("value").split(",")[0].strip()
    return props


def devices():
    """Return [(id, name, kind, props)] for every libinput mouse ("pointer") and touchpad; [] without xinput."""
    try:
        listing = _xinput("list", "--short")
    except (OSError, subprocess.CalledProcessError):
        return []
    found = []
    for line in listing.splitlines():
        m = _SLAVE_RE.match(line)
        # keyboards with media or RGB keys (ckb-next, …) also register a pointer: not a mouse
        if not m or "XTEST" in m.group("name") or "keyboard" in m.group("name").lower():
            continue
        try:
            props = _props(m.group("id"))
        except subprocess.CalledProcessError:
            continue
        if "libinput Accel Speed" not in props:
            continue
        kind = "touchpad" if "libinput Tapping Enabled" in props else "pointer"
        found.append((m.group("id"), m.group("name"), kind, props))
    return found


def current(devs=None):
    """Return {kind: {key: value}}: the saved file first, then the first live device, then libinput's defaults."""
    saved = read_conf()
    devs = devices() if devs is None else devs
    out = {}
    for kind, fields in _FIELDS.items():
        live = next((props for _id, _name, k, props in devs if k == kind), {})
        values = dict(DEFAULTS[kind])
        for key, prop, _option, typ in fields:
            if prop in live:
                try:
                    values[key] = live[prop] == "1" if typ is bool else float(live[prop])
                except ValueError:
                    pass
            if key in saved.get(kind, {}):
                values[key] = saved[kind][key]
        out[kind] = values
    return out


def apply_live(settings, devs=None):
    """Set validated settings on every matching device now; return a list of error strings."""
    errors = []
    for dev_id, name, kind, props in devices() if devs is None else devs:
        for key, prop, _option, typ in _FIELDS[kind]:
            if key not in settings.get(kind, {}) or prop not in props:
                continue
            value = settings[kind][key]
            text = ("1" if value else "0") if typ is bool else f"{value:g}"
            try:
                _xinput("set-prop", dev_id, prop, text)
            except (OSError, subprocess.CalledProcessError) as e:
                errors.append(f"{name}: {prop}: {e}")
    return errors
