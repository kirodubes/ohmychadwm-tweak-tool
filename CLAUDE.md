# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Ohmychadwm Tweak Tool is a GTK4 Python settings app for the **ohmychadwm** X11 desktop: a header row (title,
♥ Support, Quit) and a `Gtk.StackSidebar` with one page per area, the same layout as the KIROTUX premium apps. It is
**free** and ships in `nemesis_repo` (Kiro and Kiro-next get it through `ohmychadwm`'s depends).

It **replaces `ohmychadwm-appearance` (OMA)**. OMA's single page is the Look page here. The PKGBUILD carries
`provides/conflicts/replaces=('ohmychadwm-appearance')`, so `pacman -Syu` offers the swap and `ohmychadwm`'s old
dependency stays satisfied. Keep all three.

- **Language**: Python 3, GTK4 + PyGObject.
- **Entry point**: `usr/share/ohmychadwm-tweak-tool/ohmychadwm-tweak-tool.py` (`--debug`, `--page NAME`)
- **Launchers**: `usr/bin/ohmychadwm-tweak-tool` + relative symlinks `ott` and `oma`. **`oma` must stay**: existing
  users keep their own sxhkdrc (skel is copied once), and theirs runs `oma` on Ctrl+Alt+X.
- **Runs as the normal user.** All root work goes through ONE helper, `ott_root.py` (`run_root()` calls it via
  `pkexec`): `GTK_THEME` in `/etc/environment`, the system/SDDM cursor, the SDDM wallpaper, the xorg.conf.d input file and installing
  the rebuilt binary. One prompt per Apply/Save. Never add other root escalation.
- **Design study** (offline, in Kiro-HQ): `STUDIES/OHMYCHADWM-APPEARANCE-STUDY.md` (the Look page's reasons).

## Architecture

```
usr/share/ohmychadwm-tweak-tool/
├── ohmychadwm-tweak-tool.py  # Gtk.Application + window, CSS, follows color-scheme, prefs window size
├── ott_gui.py                # header row, support dialog, StackSidebar, Status page, _BrokenPage/_safe
├── ott_widgets.py            # section / muted / warning / dropdown / settings_grid / status / run_async / ask_keep
├── ott_page_themes.py        # Themes: 10 picture tiles (FlowBox), one click = ott_apply.apply_look + feh
├── ott_page_look.py          # Look (OMA's page): drift banner, pickers, force GTK_THEME, system cursor, bar theme+font
├── ott_page_bar.py           # Bar & windows: THEME_BORDER/GAPS/SMARTGAPS/TOPBAR/SHOWSYSTRAY/AUTOHIDE → rebuild
├── ott_page_wallpaper.py     # Wallpaper (KHP layout): sources, thumbnails, preview, Variety prev/next, feh
├── ott_page_displays.py      # Displays: per output mode/rate/on/primary, 15 s keep/revert, save
├── ott_page_input.py         # Mouse & touchpad: live xinput (debounced), Save → pkexec --input
├── ott_page_keyboard.py      # Keyboard: 1–2 layouts (pkexec --keyboard → localectl, then setxkbmap) + KIRO_AZERTY rebuild
├── ott_page_update.py        # Update & News: checkupdates, Update now in a terminal, restart after a new kernel, Kiro News
├── ott_page_startup.py       # Startup apps: run lines of run.sh on/off, add/remove own
├── ott_page_apps.py          # Default apps: terminal/file manager in sxhkdrc, xdg-mime per category
├── ott_page_keys.py          # Keys: searchable read-only list
├── ott_themes.py             # the 10 looks (ISO packages only) + resolve_all(): installed names, missing parts
├── ott_apply.py              # apply_look(): user files, bar rebuild, ONE pkexec (used by Look and Themes)
├── ott_targets.py            # Look targets: read_all / current / drift / apply  (toolkit-free, from OMA)
├── ott_chadwm.py             # config.def.h: theme include, managed block (font + options), rebuild, restart
├── ott_scan.py ott_env.py ott_system.py   # from OMA: theme scan, GTK_THEME line, system/SDDM cursor
├── ott_display.py            # xrandr parse / plan / arandr script / switch / revert / save
├── ott_input.py              # libinput props via xinput, validate(), build_conf() for xorg.conf.d
├── ott_wallpaper.py          # sources, list_images, ~/.fehbg, feh, variety
├── ott_startup.py            # run.sh run-line transforms
├── ott_apps.py               # .desktop scan, xdg-mime, sxhkdrc key commands
├── ott_search.py             # search above the sidebar (Ctrl+F): page texts + English synonyms (from khp_search)
├── ott_keyboard.py           # layouts (evdev.lst, setxkbmap -query, 00-keyboard.conf), options, KIRO_AZERTY define
├── ott_update.py             # checkupdates, kernel-restart check, /usr/share/kiro-news/feed.json, open a terminal
├── ott_keys.py               # sxhkdrc parser + chadwm keys[] parser (KIRO_AZERTY macros resolved)
├── ott_root.py               # the pkexec helper: --gtk-theme / --release-gtk-theme / --system-cursor / --sddm-background / --input / --keyboard / --install
├── ott_config.py             # prefs (~/.config/ohmychadwm-tweak-tool/prefs.json; falls back to OMA's)
├── log.py
└── ott.css
```

Module prefix `ott_` = **o**hmychadwm **t**weak **t**ool. Pages expose `.widget` and usually `refresh()`; the
sidebar calls `refresh()` on every visit (not Wallpaper or Update & News), because the Look page changes what Bar & windows shows.
A page with `own_scroll = True` (Look, which keeps its Apply footer visible) is not wrapped in a ScrolledWindow.

## Write targets

| Target | Page | Fields |
|---|---|---|
| `/etc/environment` `GTK_THEME` (root) | Look | theme. **Beats every file below** for GTK 3 and 4; shows after re-login |
| `/usr/share/icons/default/index.theme` + SDDM conf (root, optional) | Look | `Inherits=` cursor; SDDM `[Theme] CursorTheme`/`CursorSize` in the conf that already sets it. SDDM ignores icons/default once CursorTheme is set, so write BOTH |
| `/usr/share/sddm/themes/edu-simplicity/theme.conf.user` (root, optional) | Themes | `[General] background=` an image under `/usr/share/backgrounds` only (the `sddm` user must read it). Only themes in `ott_system.BACKGROUND_THEMES` read it (kiro-sddm-simplicity 2026.11.20+ reads `config.background`); no package owns the file |
| `~/.config/gtk-3.0/settings.ini`, `gtk-4.0/settings.ini`, `~/.gtkrc-2.0` | Look | theme, icons, cursor, size, font (+ prefer-dark in gtk-4.0). **Thunar reads gtk-3.0**: xfsettingsd is NOT running |
| gsettings `org.gnome.desktop.interface`, xfconf `xsettings` | Look | theme, icons, cursor, size, font, color-scheme |
| `~/.icons/default/index.theme`, `~/.Xresources` | Look | cursor (`xrdb -merge` + `xsetroot -cursor_name left_ptr`) |
| `~/.config/ohmychadwm/chadwm/config.def.h` | Look, Bar | theme include; one managed block with font and bar & window options |
| `~/.fehbg` | Wallpaper | written by feh itself |
| `~/.screenlayout/<user>.sh` | Displays | arandr format, written only after **Keep** |
| `/etc/X11/xorg.conf.d/40-ohmychadwm-input.conf` (root) | Mouse & touchpad | InputClass `MatchIsPointer` then `MatchIsTouchpad` |
| `/etc/X11/xorg.conf.d/00-keyboard.conf` via `localectl set-x11-keymap` (root) | Keyboard | 1–2 layouts + options; `grp:alt_shift_toggle` only with two layouts, other options kept |
| `config.def.h` `#define KIRO_AZERTY` | Keyboard | workspace keys; rebuild + `--install`, then `keybindings-<set>.txt` → `keybindings.txt` |
| `~/.config/ohmychadwm/scripts/run.sh` | Startup apps | only `run …` / `#run …` lines |
| `~/.config/ohmychadwm/sxhkd/sxhkdrc` + xdg-mime | Default apps | single-word commands on the terminal/file-manager keys |

`current()` (Look) takes an active `GTK_THEME` first for the theme, then GTK 3 (what Thunar shows), then gsettings,
then the Kiro default from `/etc/skel`. The cursor size is the exception: GTK 3 `0` means "X default", so
`Xcursor.size` wins.

## Gotchas — do not revert

- **Display name is capitalised: "Ohmychadwm".** Every user-visible string says "Ohmychadwm". Paths, the binary,
  the package name, the app id and `--` CLI help stay lowercase `ohmychadwm`.
- **Migration from OMA** (existing users never get skel changes):
  - `ott_chadwm` reads and strips the old `ohmychadwm-appearance managed` markers as well as its own, and writes only
    the new ones. Never drop `_OLD_MARKERS`, or the first Apply leaves a second block behind.
  - The backup suffix stays **`.oma-bak`** in every module: a new suffix would back up an already-edited file as if
    it were the original.
  - `ott_config` reads `~/.config/ohmychadwm-appearance/prefs.json` until it has written its own.
  - `usr/bin/oma` stays (see Launchers).
- **`GTK_THEME` is Kiro's real theme switch.** The ISO ships `GTK_THEME=Arc-Dawn-Dark` in `/etc/environment`, and
  ATT's themes page toggles that exact line. The "force" checkbox keeps it (rewrites it); unticking comments it out
  (`#GTK_THEME=…`, kept so it can be re-enabled, and ATT still recognises it). `ott_env.force` keeps the line's
  quoting style and rejects unsafe names. Never drop the line, and never set the theme only in `settings.ini` while
  the line is active, because nothing would change.
- `/usr/share/icons/default/index.theme` belongs to `default-cursors` but is a pacman **backup** file: edits survive
  upgrades (as `.pacnew`). Don't "protect" it some other way.
- **Reset covers its whole page.** Look's **Reset to Kiro default**: GTK pickers from `/etc/skel`, force back on,
  system cursor checkbox on, the bar theme from the skel `config.def.h`, the bar font removed. Bar & windows' **Use
  the theme's values** removes every option override. Keep both complete when adding a setting.
- **xfconf: always use `xfconf-query`, never edit `xsettings.xml`.** xfconfd caches the channel and overwrites hand
  edits.
- **One managed block after the last theme include** holds the bar font and the bar & window options. Every
  `themes/*.h` defines its own `THEME_*` values (all 45 define the six options), so the `#ifndef` fallbacks in
  config.def.h never fire. The block `#undef`s first (no redefinition warnings) and is regenerated whole; the Look
  page keeps the options and the Bar page keeps the font. Bar & windows writes only values that differ from the
  active theme, so the theme still decides the rest.
- **Rebuild must `make clean` first.** The Makefile only copies config.def.h → config.h when config.h is missing.
- **Restart = `xdotool key super+shift+r`.** dwm's `restart()` exits 0 and the `run.sh` loop relaunches it. Don't
  kill the process: a non-zero exit after 5 s counts as a logout.
- Edit the **user** copies under `~/.config/ohmychadwm`, never `/etc/skel`.
- All file writes are line-based (keys, comments and lines the app doesn't own survive) with a one-time
  `<file>.oma-bak` backup. Don't switch to configparser for writing, which drops comments.
- **Displays**: changes run now, and only **Keep** (15 s countdown, else revert) writes `~/.screenlayout/<user>.sh`,
  the file `run.sh` runs at login, in arandr's format. `--rate` is only written when it isn't the mode's default,
  because arandr itself never writes one. When a width changes, enabled outputs are re-placed side by side.
- **Mouse & touchpad**: `ott_root --input` takes JSON and runs `ott_input.validate()` **as root** before writing,
  so the helper only writes text it built itself. Keyboards with RGB/media drivers register a pointer; they are
  skipped by name.
- **Startup apps** only touch `run`/`#run` lines; the xrandr run line belongs to Displays. Lines it adds carry
  `# added by ohmychadwm-tweak-tool` and only those can be removed.
- **Default apps**: sxhkdrc hard-codes alacritty/thunar, so xdg-mime alone changes nothing on Super+Enter. Only
  single-word commands on those keys are rewritten (`alacritty -e claude` stays); then `pkill -USR1 -x sxhkd`.
- **Keyboard**: the save (pkexec) runs **before** `setxkbmap`, so a cancelled password prompt changes nothing. On a
  failed compile or install `config.def.h` gets its old `KIRO_AZERTY` back, so the page never shows keys the installed
  binary doesn't have. `ott_keyboard` is imported by the root helper: keep it free of `ott_i18n`.
- **Search** (`ott_search`) walks the visible labels/buttons of each page. The Look page has its own scroller
  (`own_scroll`), so `_scroller_of()` scrolls the ScrolledWindow around the hit there. Synonym targets must be texts a
  page really shows, or the synonym finds nothing.
- **Update & News** never runs root itself: Update now opens `sudo pacman -Syu` in a terminal. It loads in a thread
  and only reloads on Look again (`on_switch` skips it, like Wallpaper). Recovery (keys, boot problems) is ATT's.
- **Themes** (2026-11-20): written fresh for this free app; **never copy code from the paid KiroTux premium apps'
  Themes** (`knp_themes`/`khp_themes`), only the idea. Every name in `ott_themes.BUILTIN` must come from a package in
  `kiro-iso/archiso/packages.x86_64`. On the ISO the only icon sets are Surfn-Kiro and neo-candy-icons: the `or-`/`al-`
  candy and beautyline dirs are `Hidden=true` layers neo-candy inherits, not choices. Each look uses a different
  painting. A look keeps the user's font, cursor size and bar font; `border` None drops the THEME_BORDER override.
  GTK_THEME is rewritten only when `/etc/environment` already forces it.
  The tile frame colour is `SchemeSelbr` (the focused window border); `col_borderbar` is only the frame around the bar.
- **Keys** parses sxhkdrc and `keys[]` directly, never `keybindings.txt` (can be stale).
- ohmychadwm's own terminal scripts `scripts/apply-font-globally.sh` / `generate-chadwm-theme.sh` touch rofi/terminal
  fonts and theme generation. They are a different scope, so don't merge them in here.

## Translations (since 2026-10-31)

- `ott_i18n.py` (a copy of the KIROTUX premium apps' `khp_i18n.py`): gettext domain `ohmychadwm-tweak-tool`, catalogs in
  `usr/share/locale`. The saved choice (Status → Language, prefs.json) beats the system language; `OTT_LANGUAGE`
  beats both, and the live tests pin `OTT_LANGUAGE=en` because they read English status texts.
- Every user-visible string goes through `_()`, as a whole sentence with named placeholders
  (`_("Saved to {path}").format(path=…)`), never glued from pieces; counts use `ngettext`. A string that is also a
  dict key or a comparison value (target labels in `ott_targets`, `ott_apps.CATEGORIES`) is marked `N_()` and
  translated where it is shown (`_(label)`).
- Never translated: `ott_root.py` (runs as root via pkexec), log lines, paths, commands, config keys, key and modifier
  names, sentinel values such as `"unchanged"`, and the names Ohmychadwm, chadwm, sxhkd, xrandr, feh.
- After changing any visible text: `po/make-mo.sh` (refreshes the template, merges every `.po`, compiles the `.mo`
  files, writes `usr/share/applications/*.desktop` from `po/*.desktop.in`). New strings stay English until
  translated; the shared rules, registers and tools are in Kiro-HQ `TRANSLATIONS/` (README + ROADMAP §8).
- Edit the menu entry in `po/ohmychadwm-tweak-tool.desktop.in`, never in `usr/share/applications/` (overwritten).
- A system variant without its own catalog borrows its sibling's (`_SIBLING`: pt → pt_BR, zh → zh_CN), and the catalog
  is loaded for the language `_shown()` picked. Keep the same rule in the premium apps' `*_i18n.py`.

## Code style

- ruff (`ruff.toml`, line length 120) must pass. One-line docstrings on public functions; none needed on `_private`
  ones.
- GTK callbacks name unused widget params `_widget`. Never `subprocess.call` from a callback; slow work runs in a
  daemon thread (`run_async`) and reports back via `GLib.idle_add`.
- Test the toolkit-free modules with `HOME=$TMPDIR/fakehome python3 -c …` against copied config files, never against
  the real home. A fake HOME does **not** isolate gsettings, xfconf or `xrdb`: test single `_write_*` functions,
  never `ott_targets.apply()`, which writes the live session.
