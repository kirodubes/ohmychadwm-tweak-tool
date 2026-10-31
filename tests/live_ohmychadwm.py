#!/usr/bin/env python3
"""Live test: drive the installed ohmychadwm-tweak-tool GUI inside a running ohmychadwm session and read every change back.

Run through run-live-ohmychadwm.sh (it backs up and restores the user's and the system's files, and lets pkexec
through without a password for the run). Not shipped in the package.
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time

APP_DIR = os.environ.get("OTT_APP_DIR", "/usr/share/ohmychadwm-tweak-tool")
OUT = os.environ.get("OTT_OUT", "/tmp/ott-live")
sys.path.insert(0, APP_DIR)
# the checks read the app's English texts
os.environ.setdefault("OTT_LANGUAGE", "en")

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gio, GLib, Gtk, Pango  # noqa: E402

import ott_apps  # noqa: E402
import ott_chadwm  # noqa: E402
import ott_display  # noqa: E402
import ott_env  # noqa: E402
import ott_gui  # noqa: E402
import ott_input  # noqa: E402
import ott_keys  # noqa: E402
import ott_root  # noqa: E402
import ott_scan  # noqa: E402
import ott_startup  # noqa: E402
import ott_system  # noqa: E402
import ott_targets  # noqa: E402
import ott_wallpaper  # noqa: E402

_spec = importlib.util.spec_from_file_location("ott_main", os.path.join(APP_DIR, "ohmychadwm-tweak-tool.py"))
ott_main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ott_main)

# ── Recorders ────────────────────────────────────────────────────────────────

CRASHES, STATUS, RESULTS, SHOTS = [], [], [], []
PAGES = {}

_orig_hook = threading.excepthook


def _thread_crash(args):
    # The app's worker threads have no crash reporting of their own: an exception there leaves a dead button
    CRASHES.append(f"{args.exc_type.__name__}: {args.exc_value}")
    _orig_hook(args)


threading.excepthook = _thread_crash

for _name, _mod in list(sys.modules.items()):
    if _name.startswith("ott_page_") and hasattr(_mod, "set_status"):
        def _rec(label, text, error=False, _orig=_mod.set_status, _page=_name):
            STATUS.append((_page, text, error))
            _orig(label, text, error)
        _mod.set_status = _rec

_orig_safe = ott_gui._safe


def _safe(title, make):
    page = _orig_safe(title, make)
    PAGES[title] = page
    return page


ott_gui._safe = _safe


def record(step, verdict, detail=""):
    RESULTS.append((step, verdict, detail))
    print(f"[{verdict}] {step}: {detail}", flush=True)


def check(step, ok, detail=""):
    record(step, "PASS" if ok else "FAIL", detail)
    return ok


# ── Read-backs ───────────────────────────────────────────────────────────────

def sh(*cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return p.returncode, (p.stdout + p.stderr).strip()


def gs(key):
    return sh("gsettings", "get", "org.gnome.desktop.interface", key)[1].strip("'")


def xfq(prop):
    return sh("xfconf-query", "-c", "xsettings", "-p", prop)[1]


def ini(path, key):
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            for line in f:
                k, _sep, v = line.partition("=")
                if k.strip() == key:
                    return v.strip().strip('"')
    except OSError:
        pass
    return None


def read(path):
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def wm_pid():
    return sh("pgrep", "-u", str(os.getuid()), "-x", "ohmychadwm")[1].split("\n")[0]


def root_pixmap():
    return sh("xprop", "-root", "_XROOTPMAP_ID")[1]


def live_mode(name):
    for out in ott_display.query():
        if out.name == name:
            return out.mode
    return None


def xinput_accel():
    """Return {device: Accel Speed} for every libinput mouse."""
    return {name: round(float(props["libinput Accel Speed"]), 2)
            for _id, name, kind, props in ott_input.devices() if kind == "pointer"}


def shot(name):
    path = os.path.join(OUT, "shots", f"{len(SHOTS) + 1:02d}-{name}.png")
    sh("import", "-window", "root", path)
    SHOTS.append(path)
    return os.path.basename(path)


_PROBE = {
    3: ('import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk; '
        'w = Gtk.Window(title="ott-probe-gtk3"); w.set_default_size(400, 300); w.add(Gtk.Label(label="probe")); '
        'w.connect("destroy", Gtk.main_quit); w.show_all(); Gtk.main()'),
    4: ('import gi; gi.require_version("Gtk", "4.0"); from gi.repository import GLib, Gtk; '
        'w = Gtk.Window(title="ott-probe-gtk4"); w.set_default_size(400, 300); w.set_child(Gtk.Label(label="probe")); '
        'w.present(); GLib.MainLoop().run()'),
}


def brightness(gtk):
    """Start a fresh GTK 3 or 4 window (it reads the settings files now), return its mean brightness 0..1."""
    proc = subprocess.Popen([sys.executable, "-c", _PROBE[gtk]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wid = ""
        for _i in range(40):
            time.sleep(0.25)
            wid = sh("xdotool", "search", "--name", f"^ott-probe-gtk{gtk}$")[1].split("\n")[0]
            if wid:
                break
        if not wid:
            return None
        time.sleep(1.0)
        path = os.path.join(OUT, "shots", f"probe-gtk{gtk}-{len(SHOTS)}.png")
        sh("import", "-window", wid, path)
        rc, out = sh("magick", path, "-colorspace", "gray", "-format", "%[fx:mean]", "info:")
        return round(float(out), 2) if rc == 0 else None
    finally:
        proc.kill()


def last_status(page_mod):
    for page, text, error in reversed(STATUS):
        if page == page_mod:
            return text, error
    return "", False


# ── Steps ────────────────────────────────────────────────────────────────────

class Step:
    """One action on the GUI, the condition that says it finished, and the read-back."""

    def __init__(self, name, act, check, page=None, until=None, timeout=30, settle=1500):
        self.name, self.act, self.check, self.page = name, act, check, page
        self.until, self.timeout, self.settle = until, timeout, settle


def find_toplevel(title):
    for w in Gtk.Window.list_toplevels():
        if w.get_title() == title and w.get_visible():
            return w
    return None


def find_button(widget, label):
    if isinstance(widget, Gtk.Button) and widget.get_label() == label:
        return widget
    child = widget.get_first_child()
    while child is not None:
        found = find_button(child, label)
        if found:
            return found
        child = child.get_next_sibling()
    return None


def dd_names(dd):
    model = dd.get_model()
    return [model.get_item(i).get_string() for i in range(model.get_n_items())]


def pick(dd, value):
    dd.set_selected(dd_names(dd).index(value))


def build_steps():
    st = {}
    steps = []
    add = steps.append
    always = lambda: True  # noqa: E731

    def chk_baseline():
        st["wm0"] = wm_pid()
        st["sel0"] = PAGES["Look"]._selection()
        record("Baseline", "INFO", f"wm pid {st['wm0']}; look {st['sel0']}; screenshot {shot('baseline')}")
    add(Step("baseline", lambda: None, chk_baseline, until=always))

    # ── Look: Style ──────────────────────────────────────────────────────────
    lp = PAGES["Look"]
    themes = ott_scan.gtk_themes()

    def act_style(dark):
        def act():
            lp._chk_sys_cursor.set_active(False)
            # toggle through the other style first, so the switch fires whatever the start state is
            (lp._chk_light if dark else lp._chk_dark).set_active(True)
            (lp._chk_dark if dark else lp._chk_light).set_active(True)
            st["style_theme"] = ott_scan.style_variant(st["sel0"].theme, dark, themes) or st["sel0"].theme
            st["style_dd"] = ott_page_selected(lp._dd_theme)
            lp._on_apply(None)
        return act

    def chk_style(dark):
        def chk():
            word = "dark" if dark else "light"
            want = st["style_theme"]
            check(f"Look {word}: Style picks the theme's {word} sibling", st["style_dd"] == want,
                  f"theme dropdown {st['style_dd']}, expected {want}")
            got = {"gtk3": ini("~/.config/gtk-3.0/settings.ini", "gtk-theme-name"),
                   "gtk4": ini("~/.config/gtk-4.0/settings.ini", "gtk-theme-name"),
                   "gtk2": ini("~/.gtkrc-2.0", "gtk-theme-name"), "gsettings": gs("gtk-theme"),
                   "xfconf": xfq("/Net/ThemeName")}
            check(f"Look {word}: theme {want} in every file", all(v == want for v in got.values()), f"{got}")
            pref = ini("~/.config/gtk-4.0/settings.ini", "gtk-application-prefer-dark-theme")
            scheme = gs("color-scheme")
            check(f"Look {word}: preference written", pref == ("true" if dark else "false")
                  and scheme == ("prefer-dark" if dark else "prefer-light"), f"gtk4 prefer-dark {pref}, color-scheme {scheme}")
            b3, b4 = brightness(3), brightness(4)
            if dark:
                ok = b3 is not None and b4 is not None and b3 < 0.45 and b4 < 0.45
            else:
                ok = b3 is not None and b4 is not None and b3 > 0.55 and b4 > 0.55
            check(f"Look {word}: a new GTK 3 and GTK 4 window really is {word}", ok,
                  f"mean brightness gtk3 {b3}, gtk4 {b4}; screenshot {shot('style-' + word)}")
        return chk

    def chk_twin():
        # Light chosen while a dark-only theme is selected (the state a user can open the app in)
        dark_theme = ott_scan.style_variant(st["sel0"].theme, True, themes)
        light_theme = ott_scan.style_variant(st["sel0"].theme, False, themes)
        if not dark_theme or not light_theme or dark_theme == light_theme:
            record("Look: Use <sibling> button", "INFO", f"{st['sel0'].theme} has no light/dark pair")
            return
        lp._resetting = True
        lp._chk_light.set_active(True)
        lp._resetting = False
        pick(lp._dd_theme, dark_theme)
        # picking the theme that is already selected emits no notify::selected, so refresh the note by hand
        lp._update_theme_note()
        shown = lp._btn_twin.get_visible(), lp._btn_twin.get_label()
        lp._btn_twin.emit("clicked")
        check("Look: Light + dark theme offers 'Use <light sibling>' and it picks it",
              shown == (True, f"Use {light_theme}") and ott_page_selected(lp._dd_theme) == light_theme,
              f"button {shown}, theme now {ott_page_selected(lp._dd_theme)}")
    add(Step("twin button", lambda: None, chk_twin, until=always))
    add(Step("style light", act_style(False), chk_style(False), page="ott_page_look", timeout=60))
    add(Step("style dark", act_style(True), chk_style(True), page="ott_page_look", timeout=60))

    # ── Look: icons, cursor size, font ───────────────────────────────────────
    def act_icons():
        names = dd_names(lp._dd_icons)
        st["icons"] = next((n for n in ("Papirus-Dark", "Papirus", "Adwaita", "breeze")
                            if n in names and n != st["sel0"].icons), next(n for n in names if n != st["sel0"].icons))
        pick(lp._dd_icons, st["icons"])
        st["size"] = "32" if str(st["sel0"].cursor_size) != "32" else "48"
        pick(lp._dd_size, st["size"])
        lp._font_btn.set_font_desc(Pango.FontDescription.from_string("DejaVu Sans 12"))
        lp._chk_sys_cursor.set_active(False)
        lp._on_apply(None)

    def chk_icons():
        got = {"gsettings": gs("icon-theme"), "gtk3": ini("~/.config/gtk-3.0/settings.ini", "gtk-icon-theme-name"),
               "xfconf": xfq("/Net/IconThemeName")}
        check("Look: icon theme everywhere", all(v == st["icons"] for v in got.values()), f"want {st['icons']}: {got}")
        xrdb = re.search(r"Xcursor\.size:\s*(\d+)", sh("xrdb", "-query")[1])
        sizes = {"gsettings": gs("cursor-size"), "xfconf": xfq("/Gtk/CursorThemeSize"),
                 "xrdb": xrdb.group(1) if xrdb else None}
        check("Look: cursor size everywhere, X resources live", all(v == st["size"] for v in sizes.values()),
              f"want {st['size']}: {sizes}")
        check("Look: font in gsettings", gs("font-name") == "DejaVu Sans 12", gs("font-name"))
        inherits = ini("~/.icons/default/index.theme", "Inherits")
        check("Look: personal default cursor", inherits == st["sel0"].cursor, f"Inherits={inherits}")
    add(Step("icons cursor font", act_icons, chk_icons, page="ott_page_look", timeout=60))

    # ── Look: drift banner + Fix all ─────────────────────────────────────────
    def act_drift():
        path = os.path.expanduser("~/.config/gtk-4.0/settings.ini")
        text = read(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(re.sub(r"^gtk-icon-theme-name=.*$", "gtk-icon-theme-name=hicolor", text, flags=re.M))
        lp._refresh_drift()
        st["banner"] = (lp._banner.get_visible(), lp._banner_detail.get_label())
        lp._on_apply(None)

    def chk_drift():
        check("Look: drift banner shows a hand-edited GTK 4 file", st["banner"][0] and "GTK 4" in st["banner"][1],
              repr(st["banner"]))
        check("Look: Fix all brings it back in sync", not lp._banner.get_visible()
              and ini("~/.config/gtk-4.0/settings.ini", "gtk-icon-theme-name") == st["icons"],
              f"banner {lp._banner.get_visible()}")
    add(Step("drift fix all", act_drift, chk_drift, page="ott_page_look", timeout=60))

    # ── Look: force GTK_THEME (pkexec) ───────────────────────────────────────
    def act_force(on):
        def act():
            lp._chk_sys_cursor.set_active(False)
            lp._chk_force.set_active(on)
            lp._on_apply(None)
        return act

    def chk_force(on):
        def chk():
            theme, active = ott_env.read()
            want = ott_page_selected(lp._dd_theme)
            if on:
                check("Look: force writes GTK_THEME (pkexec)", active and theme == want, f"{theme} active={active}")
            else:
                check("Look: untick comments GTK_THEME out", not active and "#GTK_THEME" in read(ott_env.ENV_FILE),
                      f"{theme} active={active}")
        return chk
    add(Step("force on", act_force(True), chk_force(True), page="ott_page_look", timeout=60))
    add(Step("force off", act_force(False), chk_force(False), page="ott_page_look", timeout=60))

    # ── Look: system + login-screen cursor (pkexec) ──────────────────────────
    def act_syscursor():
        names = dd_names(lp._dd_cursor)
        st["cursor"] = next((n for n in names if n != st["sel0"].cursor), st["sel0"].cursor)
        pick(lp._dd_cursor, st["cursor"])
        lp._chk_sys_cursor.set_active(True)
        lp._on_apply(None)

    def chk_syscursor():
        sysc = ott_system.read()
        check("Look: system and SDDM cursor (pkexec)", sysc["default"] == st["cursor"] and sysc["sddm"] in (None, st["cursor"]),
              f"want {st['cursor']}: {sysc}")
    add(Step("system cursor", act_syscursor, chk_syscursor, page="ott_page_look", timeout=60))

    # ── Look: bar theme + bar font → rebuild, install (pkexec), restart ──────
    def act_bar_theme():
        st["bin0"] = mtime(ott_root.INSTALL_PATH)
        names = dd_names(lp._dd_bar)
        st["bar_theme"] = next(n for n in names if n != ott_page_selected(lp._dd_bar))
        pick(lp._dd_bar, st["bar_theme"])
        lp._chk_bar_font.set_active(True)
        lp._chk_sys_cursor.set_active(False)
        lp._on_apply(None)

    def chk_bar_theme():
        text = ott_chadwm.read_config()
        check("Look: bar theme include switched", ott_chadwm.active_theme(text) == st["bar_theme"],
              ott_chadwm.active_theme(text))
        check("Look: bar font block written", ott_chadwm.bar_font(text) == ("DejaVu Sans", 12), f"{ott_chadwm.bar_font(text)}")
        check("Look: rebuilt bar installed (pkexec)", mtime(ott_root.INSTALL_PATH) > st["bin0"],
              f"status '{last_status('ott_page_look')[0]}'")
    add(Step("bar theme", act_bar_theme, chk_bar_theme, page="ott_page_look", timeout=240))

    def act_restart():
        st["wm_before"] = wm_pid()
        lp._on_restart(None)

    def chk_restart():
        now = wm_pid()
        check("Look: Restart Ohmychadwm runs the new build", now and now != st["wm_before"],
              f"pid {st['wm_before']} -> {now}; screenshot {shot('bar-theme-' + st['bar_theme'])}")
    add(Step("restart after bar theme", act_restart, chk_restart,
             until=lambda: wm_pid() not in ("", st.get("wm_before")), timeout=20, settle=2500))

    # ── Look: Reset to Kiro default (widgets only) ───────────────────────────
    def chk_reset():
        k = ott_targets.kiro_default()
        got = (ott_page_selected(lp._dd_theme), ott_page_selected(lp._dd_icons), lp._chk_force.get_active(),
               lp._chk_sys_cursor.get_active(), ott_page_selected(lp._dd_bar), lp._chk_bar_font.get_active(),
               lp._chk_dark.get_active())
        want = (k.theme, k.icons, True, True, ott_chadwm.default_theme(), False, k.dark)
        check("Look: Reset to Kiro default loads everything", got == want, f"got {got} want {want}")
    add(Step("reset look", lambda: lp._on_reset(None), chk_reset, until=always))

    # ── Bar & windows ────────────────────────────────────────────────────────
    bp = PAGES["Bar & windows"]
    loud = {"THEME_BORDER": 6, "THEME_GAPS": 30, "THEME_TOPBAR": 0}

    def act_bar():
        bp.refresh()
        st["bin1"] = mtime(ott_root.INSTALL_PATH)
        for key, value in loud.items():
            w = bp._widgets[key]
            w.set_value(value) if isinstance(w, Gtk.SpinButton) else w.set_active(bool(value))
        bp._on_apply(None)

    def chk_bar():
        opts = ott_chadwm.bar_options(ott_chadwm.read_config())
        check("Bar: options written to the managed block", all(opts.get(k) == v for k, v in loud.items()), f"{opts}")
        check("Bar: rebuilt and installed (pkexec)", mtime(ott_root.INSTALL_PATH) > st["bin1"],
              f"status '{last_status('ott_page_bar')[0]}'")
        check("Bar: one managed block", ott_chadwm.read_config().count(ott_chadwm.BLOCK_BEGIN) == 1, "")
    add(Step("bar apply", act_bar, chk_bar, page="ott_page_bar", timeout=240))

    def act_bar_restart():
        st["wm_before"] = wm_pid()
        bp._on_restart(None)

    add(Step("bar restart", act_bar_restart,
             lambda: check("Bar: Ohmychadwm restarted with border 6, gaps 30, bar at the bottom",
                           wm_pid() != st["wm_before"], f"screenshot {shot('bar-gaps30-bottom')}"),
             until=lambda: wm_pid() not in ("", st.get("wm_before")), timeout=20, settle=3000))

    def act_bar_reset():
        bp._on_reset(None)
        bp._on_apply(None)
    add(Step("bar reset", act_bar_reset,
             lambda: check("Bar: theme's values → no option overrides left",
                           not ott_chadwm.bar_options(ott_chadwm.read_config()), ""),
             page="ott_page_bar", timeout=240))

    # ── Wallpaper ────────────────────────────────────────────────────────────
    wpp = PAGES["Wallpaper"]

    def act_wall():
        st["pix0"] = root_pixmap()
        current, _mode = ott_wallpaper.current()
        images = ott_wallpaper.list_images(dict(ott_wallpaper.sources())["Ohmychadwm wallpapers"])
        st["wall"] = next(p for p in images if p != current)
        wpp._on_thumb(st["wall"])
        wpp._on_apply(None)

    def chk_wall():
        path, mode = ott_wallpaper.current()
        check("Wallpaper: feh shows it and ~/.fehbg keeps it", path == st["wall"], f"{path} ({mode})")
        check("Wallpaper: the root window has a new picture", root_pixmap() != st["pix0"],
              f"screenshot {shot('wallpaper')}")
    add(Step("wallpaper", act_wall, chk_wall, page="ott_page_wallpaper"))

    # ── Displays ─────────────────────────────────────────────────────────────
    dp = PAGES["Displays"]
    layout = ott_display.layout_path()

    def act_display(keep_mode=None):
        def act():
            dp.refresh()
            name, (dd_mode, _rate, _on, _prim) = next(iter(dp._rows.items()))
            st["out"] = name
            st.setdefault("mode0", live_mode(name))
            st["layout_mtime"] = mtime(layout)
            target = keep_mode or next(m for m in dd_names(dd_mode) if m != st["mode0"])
            st["mode_pick"] = target
            pick(dd_mode, target)
            dp._on_apply(None)
        return act

    def chk_trial():
        st["mode_trial"] = live_mode(st["out"])
        dialog = find_toplevel("Keep this change?")
        check("Displays: new mode is live during the countdown", st["mode_trial"] == st["mode_pick"],
              f"{st['out']} {st['mode0']} -> {st['mode_trial']}; screenshot {shot('display-trial')}")
        btn = find_button(dialog, st["answer"]) if dialog else None
        if btn:
            btn.emit("clicked")
        else:
            record("Displays: keep dialog", "FAIL", "dialog or button not found")

    def dialog_up():
        return find_toplevel("Keep this change?") is not None or bool(last_status("ott_page_displays")[1])

    def set_answer(a, act):
        def run():
            st["answer"] = a
            act()
        return run

    add(Step("display trial revert", set_answer("Revert", act_display()), chk_trial, until=dialog_up, settle=2500))
    add(Step("display reverted", lambda: None,
             lambda: check("Displays: Revert brings the old mode back, nothing saved",
                           live_mode(st["out"]) == st["mode0"] and mtime(layout) == st["layout_mtime"],
                           f"now {live_mode(st['out'])}; status '{last_status('ott_page_displays')[0]}'"),
             until=lambda: "reverted" in last_status("ott_page_displays")[0], settle=1500))
    add(Step("display trial keep", set_answer("Keep", act_display()), chk_trial, until=dialog_up, settle=2500))
    add(Step("display kept", lambda: None,
             lambda: check("Displays: Keep saves the layout for login",
                           live_mode(st["out"]) == st["mode_pick"] and f"--mode {st['mode_pick']}" in read(layout),
                           f"now {live_mode(st['out'])}; {read(layout).strip()}"),
             until=lambda: "saved" in last_status("ott_page_displays")[0], settle=1500))
    add(Step("display back", set_answer("Keep", lambda: act_display(st["mode0"])()), chk_trial,
             until=dialog_up, settle=2500))
    add(Step("display back kept", lambda: None,
             lambda: check("Displays: original mode back", live_mode(st["out"]) == st["mode0"], ""),
             until=lambda: "saved" in last_status("ott_page_displays")[0], settle=1500))

    # ── Mouse & touchpad ─────────────────────────────────────────────────────
    ip = PAGES["Mouse & touchpad"]

    def act_mouse():
        ip.refresh()
        st["accel0"] = xinput_accel()
        ip._widgets[("pointer", "accel")].set_value(0.5)

    add(Step("mouse live", act_mouse,
             lambda: check("Mouse: speed 0.5 is live on every mouse",
                           bool(xinput_accel()) and all(v == 0.5 for v in xinput_accel().values()),
                           f"before {st['accel0']} now {xinput_accel()}"),
             until=always, settle=2000))
    add(Step("mouse save", lambda: ip._on_save(None),
             lambda: check("Mouse: Save writes the xorg.conf.d file (pkexec)",
                           ott_input.read_conf().get("pointer", {}).get("accel") == 0.5, read(ott_input.CONF_PATH)),
             page="ott_page_input", timeout=60))

    def act_mouse_defaults():
        ip._on_defaults(None)
        ip._on_save(None)
    add(Step("mouse defaults", act_mouse_defaults,
             lambda: check("Mouse: Defaults back live and saved",
                           all(v == 0.0 for v in xinput_accel().values())
                           and ott_input.read_conf().get("pointer", {}).get("accel") == 0.0, f"{xinput_accel()}"),
             page="ott_page_input", timeout=60))

    # ── Startup apps ─────────────────────────────────────────────────────────
    sp = PAGES["Startup apps"]

    def entry(cmd):
        return next(e for e in ott_startup.entries(ott_startup.read()) if e.command == cmd)

    def act_start_off():
        st["run0"] = ott_startup.read()
        st["start_cmd"] = next(e.command for e in ott_startup.entries(st["run0"]) if e.enabled
                               and not any(x in e.command for x in ott_startup.ESSENTIAL))
        sp._on_toggle(entry(st["start_cmd"]), False)
    add(Step("startup off", act_start_off,
             lambda: check("Startup: switch off comments the run line", not entry(st["start_cmd"]).enabled,
                           st["start_cmd"]), page="ott_page_startup"))
    add(Step("startup on", lambda: sp._on_toggle(entry(st["start_cmd"]), True),
             lambda: check("Startup: switch on again", entry(st["start_cmd"]).enabled, ""), page="ott_page_startup"))

    def act_start_add():
        sp._entry.set_text("xeyes -geometry 50x50")
        sp._on_add(None)
    add(Step("startup add", act_start_add,
             lambda: check("Startup: own program added", entry("xeyes -geometry 50x50").added, ""),
             page="ott_page_startup"))
    add(Step("startup remove", lambda: sp._change(ott_startup.remove, "xeyes -geometry 50x50"),
             lambda: check("Startup: removed, run.sh exactly as before", ott_startup.read() == st["run0"], ""),
             page="ott_page_startup"))

    # ── Default apps ─────────────────────────────────────────────────────────
    ap = PAGES["Default apps"]

    def terminals():
        return sh("pgrep", "-u", str(os.getuid()), "-x", st["term"])[1].split()

    def act_term():
        ap.refresh()
        keys, dd, now = ap._keys_rows["Terminal"]
        st["term0"] = now
        st["term"] = next((t for t in dd_names(dd) if t != now), None)
        if st["term"]:
            pick(dd, st["term"])
            ap._on_apply(None)

    def chk_term():
        if not st["term"]:
            record("Default apps: terminal", "INFO", "only one terminal installed")
            return
        text = ott_keys.read_sxhkdrc()
        check("Default apps: terminal written on every terminal key",
              all(ott_keys.sxhkd_command(text, k) == st["term"] for k in ott_apps.TERMINAL_KEYS
                  if ott_keys.sxhkd_command(text, k) and len(ott_keys.sxhkd_command(text, k).split()) == 1), "")
        before = terminals()
        sh("xdotool", "key", "--clearmodifiers", "super+Return")
        time.sleep(2.5)
        new = [p for p in terminals() if p not in before]
        check(f"Default apps: Super+Enter opens {st['term']} (sxhkd reloaded)", bool(new),
              f"new pids {new}; screenshot {shot('super-enter-' + st['term'])}")
        for p in new:
            sh("kill", p)
    add(Step("terminal", act_term, chk_term, page="ott_page_apps", until=lambda: not st.get("term") or bool(
        last_status("ott_page_apps")[0])))

    def act_term_back():
        if st["term"]:
            pick(ap._keys_rows["Terminal"][1], st["term0"])
            ap._on_apply(None)
    add(Step("terminal back", act_term_back,
             lambda: check("Default apps: terminal back", ott_apps.key_command(ott_keys.read_sxhkdrc(),
                                                                               ott_apps.TERMINAL_KEYS) == st["term0"], ""),
             page="ott_page_apps"))

    def act_mime():
        ap.refresh()
        dd, ids, now = ap._mime_rows["Text editor"]
        st["mime0"] = now
        st["mime_name"] = next((n for n, i in ids.items() if i != now), None)
        if st["mime_name"]:
            st["mime"] = ids[st["mime_name"]]
            pick(dd, st["mime_name"])
            ap._on_apply(None)
    add(Step("mime", act_mime,
             lambda: check("Default apps: text editor set in xdg-mime", not st["mime_name"]
                           or ott_apps.current("Text editor") == st["mime"], ott_apps.current("Text editor")),
             page="ott_page_apps"))

    def act_mime_back():
        if st["mime_name"] and st["mime0"]:
            ok, msg = ott_apps.set_default("Text editor", st["mime0"])
            record("Default apps: text editor back", "PASS" if ok and ott_apps.current("Text editor") == st["mime0"]
                   else "FAIL", msg)
    add(Step("mime back", act_mime_back, lambda: None, until=always))

    # ── Keys + Status ────────────────────────────────────────────────────────
    kp = PAGES["Keys"]

    def chk_keys():
        rows = len(kp._rows)
        search = Gtk.SearchEntry()
        search.set_text("restart")
        kp._on_search(search)
        shown = [t for t, ws in kp._rows if ws[0].get_visible()]
        check("Keys: every binding listed, search filters", rows > 100 and shown
              and all("restart" in t for t in shown) and any("restart ohmychadwm" in t for t in shown),
              f"{rows} rows, {len(shown)} match 'restart'")
        search.set_text("")
        kp._on_search(search)
    add(Step("keys", lambda: None, chk_keys, until=always))

    def chk_status():
        stp = PAGES["Status"]
        stp.refresh()
        record("Status page builds", "PASS", f"session ohmychadwm={ott_chadwm.in_session()}")
    add(Step("status", lambda: None, chk_status, until=always))

    add(Step("end", lambda: None, lambda: record("End", "INFO", f"screenshot {shot('end')}"), until=always))
    return steps


def ott_page_selected(dd):
    item = dd.get_selected_item()
    return item.get_string() if item else ""


# ── Runner ───────────────────────────────────────────────────────────────────

class Runner:
    """Run the steps one by one on the GTK main loop."""

    def __init__(self, app, steps):
        self.app, self.steps, self.i = app, steps, 0

    def start(self):
        GLib.timeout_add(3000, self._next)

    def _next(self):
        if self.i >= len(self.steps):
            self._finish()
            return False
        self.cur = self.steps[self.i]
        self.i += 1
        self.mark, self.crash_mark, self.t0 = len(STATUS), len(CRASHES), time.monotonic()
        print(f"-- {self.cur.name}", flush=True)
        try:
            self.cur.act()
        except Exception as e:  # report and carry on with the next step
            record(self.cur.name, "FAIL", f"action raised {type(e).__name__}: {e}")
            GLib.timeout_add(300, self._next)
            return False
        GLib.timeout_add(250, self._wait)
        return False

    def _done(self):
        if self.cur.until:
            return self.cur.until()
        for page, text, _error in STATUS[self.mark:]:
            if page == self.cur.page and text and not text.endswith("…"):
                return True
        return False

    def _wait(self):
        if len(CRASHES) > self.crash_mark:
            record(self.cur.name, "FAIL", f"worker crashed: {CRASHES[-1]}")
            GLib.timeout_add(300, self._next)
            return False
        if self._done() or time.monotonic() - self.t0 > self.cur.timeout:
            if not self._done():
                record(self.cur.name, "FAIL", f"no result within {self.cur.timeout}s")
            elif self.cur.page and last_status(self.cur.page)[1]:
                record(self.cur.name, "FAIL", f"page reported an error: {last_status(self.cur.page)[0]}")
            GLib.timeout_add(self.cur.settle, self._check)
            return False
        return True

    def _check(self):
        try:
            self.cur.check()
        except Exception as e:  # report and carry on
            record(self.cur.name, "FAIL", f"check raised {type(e).__name__}: {e}")
        GLib.timeout_add(300, self._next)
        return False

    def _finish(self):
        counts = {v: sum(1 for r in RESULTS if r[1] == v) for v in ("PASS", "FAIL", "INFO")}
        with open(os.path.join(OUT, "report.json"), "w") as f:
            json.dump({"results": RESULTS, "crashes": CRASHES, "status": STATUS, "counts": counts}, f, indent=1)
        print(f"== {counts}", flush=True)
        self.app.quit()


def main():
    """Start the real app window with a separate app id and run the steps."""
    os.makedirs(os.path.join(OUT, "shots"), exist_ok=True)
    app = Gtk.Application(application_id="com.kiro.ott-livetest", flags=Gio.ApplicationFlags.NON_UNIQUE)

    def activate(_app):
        window = ott_main.Main(app)
        window.present()
        Runner(app, build_steps()).start()

    app.connect("activate", activate)
    app.run(None)


if __name__ == "__main__":
    main()
