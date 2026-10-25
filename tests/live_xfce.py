#!/usr/bin/env python3
"""Live test inside an XFCE session: what the installed ohmychadwm-tweak-tool does outside ohmychadwm.

Checks the "not in an Ohmychadwm session" notes on every page, that Restart Ohmychadwm stays hidden, that the Look
page really changes XFCE (light/dark on fresh GTK 3/4 windows, icons through xsettings) and that the mouse speed
applies live. Needs no root: it never saves the input file, never forces GTK_THEME and never rebuilds the bar. It
backs up and restores the user's files itself. Run it from a terminal in XFCE: python3 live_xfce.py
"""

import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import live_ohmychadwm as lo  # noqa: E402  (shares the app, recorders and read-backs)
from live_ohmychadwm import Gio, Gtk, Step, check, gs, ini, pick, record, shot, xfq  # noqa: E402

NOTE = "not in an Ohmychadwm session"
# page title -> should it carry the note
EXPECT_NOTE = {"Look": True, "Bar & windows": True, "Wallpaper": True, "Displays": True, "Mouse & touchpad": False,
               "Startup apps": True, "Default apps": True, "Keys": True, "Status": False}
FILES = [".config/gtk-3.0", ".config/gtk-4.0", ".gtkrc-2.0", ".icons/default", ".Xresources"]
XFCONF = ["/Net/ThemeName", "/Net/IconThemeName", "/Gtk/CursorThemeName", "/Gtk/CursorThemeSize", "/Gtk/FontName"]
BACKUP = os.path.join(lo.OUT, "xfce-backup")


def labels(widget):
    """Yield the text of every label under widget."""
    if isinstance(widget, Gtk.Label):
        yield widget.get_label()
    child = widget.get_first_child()
    while child is not None:
        yield from labels(child)
        child = child.get_next_sibling()


def backup():
    shutil.rmtree(BACKUP, ignore_errors=True)
    os.makedirs(BACKUP)
    for rel in FILES:
        src = os.path.join(os.path.expanduser("~"), rel)
        dst = os.path.join(BACKUP, rel.replace("/", "__"))
        if os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=True)
        elif os.path.exists(src):
            shutil.copy2(src, dst)
    with open(os.path.join(BACKUP, "dconf.ini"), "w") as f:
        f.write(subprocess.run(["dconf", "dump", "/org/gnome/desktop/interface/"], capture_output=True,
                               text=True).stdout)
    with open(os.path.join(BACKUP, "xfconf"), "w") as f:
        for prop in XFCONF:
            f.write(f"{prop}\t{xfq(prop)}\n")
    lo.st_accel = lo.xinput_accel()


def restore():
    home = os.path.expanduser("~")
    for rel in FILES:
        src = os.path.join(BACKUP, rel.replace("/", "__"))
        dst = os.path.join(home, rel)
        if os.path.isdir(dst) and not os.path.islink(dst):
            shutil.rmtree(dst)
        elif os.path.lexists(dst):
            os.remove(dst)
        if os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=True)
        elif os.path.exists(src):
            shutil.copy2(src, dst)
    with open(os.path.join(BACKUP, "dconf.ini")) as f:
        subprocess.run(["dconf", "load", "/org/gnome/desktop/interface/"], input=f.read(), text=True)
    with open(os.path.join(BACKUP, "xfconf")) as f:
        for line in f:
            prop, _tab, value = line.rstrip("\n").partition("\t")
            if value:
                subprocess.run(["xfconf-query", "-c", "xsettings", "-p", prop, "-s", value])
    for _id, name, kind, _props in lo.ott_input.devices():
        if kind == "pointer" and name in lo.st_accel:
            subprocess.run(["xinput", "set-prop", _id, "libinput Accel Speed", str(lo.st_accel[name])])
    if os.path.exists(os.path.expanduser("~/.Xresources")):
        subprocess.run(["xrdb", "-merge", os.path.expanduser("~/.Xresources")])
    print("restored", flush=True)


def build_steps(stack):
    st = {}
    steps = []
    add = steps.append
    always = lambda: True  # noqa: E731
    lp = lo.PAGES["Look"]
    themes = lo.ott_scan.gtk_themes()

    def chk_session():
        check("XFCE: the app knows it is not in Ohmychadwm",
              not lo.ott_chadwm.in_session() and not lo.ott_chadwm.can_restart(),
              f"XDG_CURRENT_DESKTOP={os.environ.get('XDG_CURRENT_DESKTOP')}")
    add(Step("session", lambda: None, chk_session, until=always))

    for title, want in EXPECT_NOTE.items():
        name = {"Look": "look", "Bar & windows": "bar", "Wallpaper": "wallpaper", "Displays": "displays",
                "Mouse & touchpad": "mouse", "Startup apps": "startup", "Default apps": "apps", "Keys": "keys",
                "Status": "status"}[title]

        def act(n=name):
            stack.set_visible_child_name(n)

        def chk(t=title, w=want, n=name):
            has = any(NOTE in text for text in labels(lo.PAGES[t].widget))
            check(f"XFCE: {t} {'shows the' if w else 'has no'} Ohmychadwm-session note", has == w,
                  f"note shown: {has}; screenshot {shot('xfce-' + n)}")
        add(Step(f"page {name}", act, chk, until=always, settle=1200))

    def chk_restart():
        bp = lo.PAGES["Bar & windows"]
        bp._applied((True, "Ohmychadwm rebuilt and installed"))
        bar_msg = lo.last_status("ott_page_bar")[0]
        lp._apply_finished([], (True, "Ohmychadwm rebuilt and installed"), [])
        look_msg = lo.last_status("ott_page_look")[0]
        check("XFCE: after a bar Apply no Restart button, the message points to the next Ohmychadwm login",
              not bp._btn_restart.get_visible() and not lp._btn_restart.get_visible()
              and "next Ohmychadwm login" in bar_msg and "next Ohmychadwm login" in look_msg,
              f"bar: '{bar_msg}'; look: '{look_msg}'")
    add(Step("restart hidden", lambda: stack.set_visible_child_name("bar"), chk_restart, until=always))

    def act_style(dark):
        def act():
            stack.set_visible_child_name("look")
            st["sel0"] = st.get("sel0") or lp._selection()
            st["forced"] = lo.ott_env.read()[1]
            if st["forced"]:
                lo.STATUS.append(("ott_page_look", "skipped", False))  # ends the wait at once
                return
            lp._chk_sys_cursor.set_active(False)
            (lp._chk_light if dark else lp._chk_dark).set_active(True)
            (lp._chk_dark if dark else lp._chk_light).set_active(True)
            st["want"] = lo.ott_scan.style_variant(st["sel0"].theme, dark, themes) or st["sel0"].theme
            lp._on_apply(None)
        return act

    def chk_style(dark):
        def chk():
            word = "dark" if dark else "light"
            if st["forced"]:
                record(f"XFCE {word}", "INFO", "GTK_THEME is forced in /etc/environment: skipped (would need root)")
                return
            got = {"xfconf (what xfsettingsd serves)": xfq("/Net/ThemeName"),
                   "gtk3": ini("~/.config/gtk-3.0/settings.ini", "gtk-theme-name"), "gsettings": gs("gtk-theme")}
            check(f"XFCE {word}: theme {st['want']} in xsettings and the files", all(v == st["want"] for v in
                                                                                   got.values()), f"{got}")
            b3, b4 = lo.brightness(3), lo.brightness(4)
            ok = b3 is not None and b4 is not None and ((b3 < 0.45 and b4 < 0.45) if dark else (b3 > 0.55 and b4 > 0.55))
            check(f"XFCE {word}: a new GTK 3 and GTK 4 window really is {word}", ok,
                  f"brightness gtk3 {b3}, gtk4 {b4}; screenshot {shot('xfce-style-' + word)}")
        return chk
    add(Step("xfce light", act_style(False), chk_style(False), page="ott_page_look", timeout=60))
    add(Step("xfce dark", act_style(True), chk_style(True), page="ott_page_look", timeout=60))

    def act_icons():
        names = lo.dd_names(lp._dd_icons)
        st["icons"] = next(n for n in ("Papirus-Dark", "Papirus", "Adwaita", "breeze", *names)
                           if n in names and n != lp._selection().icons)
        pick(lp._dd_icons, st["icons"])
        lp._chk_sys_cursor.set_active(False)
        lp._on_apply(None)
    add(Step("xfce icons", act_icons,
             lambda: check("XFCE: icon theme reaches xsettings (live in XFCE)", xfq("/Net/IconThemeName") == st["icons"],
                           f"want {st['icons']} got {xfq('/Net/IconThemeName')}"),
             page="ott_page_look", timeout=60))

    def act_mouse():
        stack.set_visible_child_name("mouse")
        lo.PAGES["Mouse & touchpad"].refresh()
        lo.PAGES["Mouse & touchpad"]._widgets[("pointer", "accel")].set_value(0.5)
    add(Step("xfce mouse", act_mouse,
             lambda: check("XFCE: mouse speed 0.5 is live", bool(lo.xinput_accel())
                           and all(v == 0.5 for v in lo.xinput_accel().values()), f"{lo.xinput_accel()}"),
             until=always, settle=2000))
    return steps


def main():
    """Run the XFCE checks in the real app window and restore the user's files after."""
    os.makedirs(os.path.join(lo.OUT, "shots"), exist_ok=True)
    backup()
    app = Gtk.Application(application_id="com.kiro.ott-livetest-xfce", flags=Gio.ApplicationFlags.NON_UNIQUE)

    def activate(_app):
        window = lo.ott_main.Main(app)
        window.present()
        stack = next(w for w in _walk(window) if isinstance(w, Gtk.Stack))
        lo.Runner(app, build_steps(stack)).start()

    app.connect("activate", activate)
    try:
        app.run(None)
    finally:
        restore()


def _walk(widget):
    yield widget
    child = widget.get_first_child()
    while child is not None:
        yield from _walk(child)
        child = child.get_next_sibling()


if __name__ == "__main__":
    main()
