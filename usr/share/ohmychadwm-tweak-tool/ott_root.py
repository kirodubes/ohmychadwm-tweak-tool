#!/usr/bin/env python3
"""Root helper, run via pkexec: GTK_THEME, system/SDDM cursor, SDDM wallpaper, mouse/touchpad, keyboard layout, rebuilt ohmychadwm.

Every root action of the app goes through this one script, so one Apply asks
for the password at most once. The install destination is fixed.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ott_env  # noqa: E402
import ott_input  # noqa: E402
import ott_keyboard  # noqa: E402
import ott_system  # noqa: E402

INSTALL_PATH = "/usr/local/bin/ohmychadwm"
HELPER = os.path.abspath(__file__)


def run_root(args):
    """Run this helper once through pkexec with args; return (ok, error text). Called from the GUI's worker thread."""
    proc = subprocess.run(["pkexec", sys.executable, HELPER, *args], capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def _write_file(path, transform, backup=True):
    """Apply transform to a root-owned text file: one-time .oma-bak backup, atomic replace, mode 0644."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        text = ""
    new = transform(text)
    if new == text:
        return
    bak = path + ".oma-bak"
    if backup and os.path.isfile(path) and not os.path.exists(bak):
        shutil.copy2(path, bak)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".ott-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def main():
    """Parse arguments and perform the requested root actions."""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gtk-theme", help="force this GTK_THEME system-wide")
    group.add_argument("--release-gtk-theme", action="store_true", help="comment out GTK_THEME")
    parser.add_argument("--system-cursor", help="cursor for /usr/share/icons/default and the SDDM login screen")
    parser.add_argument("--cursor-size", type=int, default=24, help="SDDM cursor size (with --system-cursor)")
    parser.add_argument("--sddm-background", help="login screen wallpaper, an image under /usr/share/backgrounds")
    parser.add_argument("--input", help="mouse/touchpad settings as JSON, written to " + ott_input.CONF_PATH)
    parser.add_argument("--keyboard", help="X11 keyboard layouts for the whole computer, e.g. us,be (localectl)")
    parser.add_argument("--keyboard-options", default="", help="xkb options with --keyboard")
    parser.add_argument("--install", help="built ohmychadwm binary to install to " + INSTALL_PATH)
    args = parser.parse_args()

    if args.gtk_theme:
        _write_file(ott_env.ENV_FILE, lambda text: ott_env.force(text, args.gtk_theme))
    elif args.release_gtk_theme:
        _write_file(ott_env.ENV_FILE, ott_env.release)

    if args.system_cursor:
        if not ott_env.valid_name(args.system_cursor):
            parser.error(f"unsafe cursor name: {args.system_cursor!r}")
        cursor = args.system_cursor
        _write_file(ott_system.DEFAULT_INDEX, lambda text: ott_system.set_default_cursor(text, cursor))
        _write_file(ott_system.sddm_conf(), lambda text: ott_system.set_sddm_cursor(text, cursor, args.cursor_size))

    if args.sddm_background:
        if not ott_system.valid_background(args.sddm_background):
            parser.error(f"not an image under {ott_system.BACKGROUNDS_DIR}: {args.sddm_background!r}")
        conf = ott_system.background_conf()
        if conf is None:
            print(f"SDDM theme {ott_system.sddm_theme()!r} has no wallpaper setting; login wallpaper unchanged")
        else:
            path = os.path.realpath(args.sddm_background)
            # the app's own file (no package owns it): a backup would only be a stray file under /usr
            _write_file(conf, lambda text: ott_system.set_background(text, path), backup=False)

    if args.input:
        try:
            settings = ott_input.validate(json.loads(args.input))
        except ValueError as e:
            parser.error(f"bad --input: {e}")
        _write_file(ott_input.CONF_PATH, lambda _text: ott_input.build_conf(settings))

    if args.keyboard:
        layouts = args.keyboard.split(",")
        if not ott_keyboard.valid_layouts(layouts) or not ott_keyboard.valid_options(args.keyboard_options):
            parser.error(f"bad --keyboard: {args.keyboard!r} {args.keyboard_options!r}")
        subprocess.run(ott_keyboard.localectl_args(layouts, args.keyboard_options), check=True)

    if args.install:
        os.makedirs(os.path.dirname(INSTALL_PATH), exist_ok=True)
        tmp = INSTALL_PATH + ".ott-tmp"
        shutil.copyfile(args.install, tmp)
        os.chmod(tmp, 0o755)
        os.replace(tmp, INSTALL_PATH)  # atomic, safe while the old binary is running


if __name__ == "__main__":
    main()
