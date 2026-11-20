# CHANGELOG

## 2026.11.20

### What Changed
- **New Themes page** (first in the sidebar): ten looks shown as pictures. One click sets the wallpaper, the bar
  colours and window border, the GTK theme and light/dark, the icons and the cursor; with the check box on, the
  login screen (SDDM) gets the same wallpaper and cursor. Ohmychadwm is recompiled and the password is asked once.
  Every part comes from a package on the Kiro ISO; a look whose picture or bar theme is missing is greyed out. The
  frame around each picture shows that look's window border colour and width. The looks are Kiro, Nord Frost,
  Dracula Night, Tokyo Night, Paper Day, Everforest, Desert Gruv, Rosé Pine, Catppuccin Space and Celestial Ocean,
  each on a different Kiro Atelier painting.
- The Keyboard page no longer logs an error when it opens.
- **Search settings** above the sidebar (Ctrl+F): type a word and pick a match; the page opens and the row lights up.
  It searches what the pages show, in your language, and knows a few English words from other tools (sddm, xkb,
  azerty, sxhkd, …).
- **New Keyboard page.** One or two keyboard layouts (Alt+Shift switches between them), saved for the whole computer,
  so XFCE and the login screen type the same. Below it the **workspace keys**: AZERTY or QWERTY, the keys Ohmychadwm
  listens for to switch workspaces. Changing them rebuilds Ohmychadwm, like the menu's keyboard script, but without a
  terminal. A warning shows when the first layout and the workspace keys don't match. It shows on a fresh v26.11.20
  install with a Belgian layout: /etc/skel ships `KIRO_AZERTY false`, so the installer's layout and the workspace keys
  disagree (open question for the ISO, not for this app).
- **New Update & News page.** The updates waiting, **Update now** (opens `sudo pacman -Syu` in a terminal), **Restart
  now** after a new kernel, and the latest Kiro News in your language.
- **No "out of sync" banner on a fresh install.** The Look page warned "GTK 2: not configured" and "Personal default
  cursor: not configured" on a freshly installed Kiro (seen on the v26.11.20 ISO in VirtualBox), although the look was
  exactly the Kiro default. Neither was a real problem: Kiro doesn't install gtk2, and without a personal cursor file
  the system default cursor (Bibata-Modern-Ice) is used.

### Technical Details
- Ported from the KiroTux premium apps (copied and adapted, no shared code): `ott_search.py` from `khp_search.py`
  (own synonyms; `_scroller_of()` because the Look page keeps its own scroller), `ott_update.py` /
  `ott_page_update.py` from `khp_update.py` / `khp_page_update.py` (feed `/usr/share/kiro-news/feed.json`), and the
  layout list of `khp_keyboard.py`.
- `ott_keyboard.py` (new, X11): reads `setxkbmap -query` and `/etc/X11/xorg.conf.d/00-keyboard.conf`, keeps xkb
  options other than `grp:*` and adds `grp:alt_shift_toggle` only for two layouts, edits `#define KIRO_AZERTY`.
- `ott_root.py --keyboard LAYOUTS --keyboard-options OPTS`: validates every code against `evdev.lst` and the options
  against a plain pattern, then runs `localectl set-x11-keymap`. One Apply = one pkexec (layout + rebuilt binary).
  The save runs before `setxkbmap`; a failed compile or install puts the old `KIRO_AZERTY` back in `config.def.h`.
  `ott_keyboard` stays free of `ott_i18n` because the root helper imports it.
- Translations: the premium apps' `.po` files were used as a compendium (`msgmerge --no-fuzzy-matching --compendium`)
  before `po/make-mo.sh`, so 18 of the 27 new strings are translated in all 13 languages; 9 stay English for now.
- Tested on the v26.11.20 VM from a copy of the source: both pages and the search drop-down render; `ott_root
  --keyboard us,be` wrote `00-keyboard.conf` and refused `us;rm`; the VM's keyboard file and session options were
  put back exactly afterwards. The workspace-key rebuild was not run on the VM.
- `ott_targets.drift()`: a missing `~/.icons/default/index.theme` is no longer drift; it falls back to
  `/usr/share/icons/default/index.theme`, which the Look page already checks on its own. A missing `~/.gtkrc-2.0`
  only counts when gtk2 is installed (`/usr/lib/libgtk-x11-2.0.so.0`). A missing GTK 4 settings.ini still counts.
  Apply still writes all three files.
- Checked on the VM, read-only: the shipped module reports both lines, the patched one reports no drift.
- Themes, written fresh (the idea of the KiroTux premium Themes, none of its paid code): `ott_themes.py` holds the
  ten looks and `resolve_all()`. That picks the first installed GTK/icon/cursor name of each fallback list, matches
  Kiro Atelier paintings by subject (any style or version) and reads `col_borderbar` from the bar theme for the tile
  frame. Every name was checked with `pacman -Qo` against the ISO's `packages.x86_64`. On the ISO the only icon sets
  are Surfn-Kiro and neo-candy-icons; the `or-`/`al-` candy and beautyline dirs are hidden layers, not choices.
- `ott_apply.apply_look()`: the Look page's apply worker moved here unchanged, so Look and Themes share one path and
  one pkexec. New: `bar=(theme, font, border)` with `KEEP`, `force=None` (leave `/etc/environment` alone) and
  `sddm_background`. Themes keeps the user's font, cursor size and bar font, rewrites GTK_THEME only when it is
  already forced, and drops the THEME_BORDER override for the Kiro look (the theme's own width).
- `ott_root.py --sddm-background PATH`: only an image under `/usr/share/backgrounds` (realpath, no newline), written
  as `[General] background=` to `theme.conf.user` beside the SDDM theme in use. Only `edu-simplicity` reads it,
  from kiro-sddm-simplicity 2026.11.20, whose `Main.qml` now takes `config.background`. Other themes are skipped
  with a note, and the check box then only offers the cursor.
- Keyboard page: `_azerty_now` is set before the first `refresh()`. Selecting the current layout fired
  `_update_hint()` before it existed (AttributeError traceback in the log; the hint itself was right).
- Translations: the 34 new strings are translated in all 13 languages (look names kept as names), merged with
  `msgmerge --compendium`. The old fuzzy "{tool} not configured, skipped" had a wrong placeholder; it is now empty
  (English).
- Rendered on GTK Broadway with a fake HOME: 10 tiles, two per row in the default window, thumbnails loaded off-thread.

### Files Modified
- `usr/share/ohmychadwm-tweak-tool/ott_search.py`, `ott_keyboard.py`, `ott_page_keyboard.py`, `ott_update.py`,
  `ott_page_update.py` (new)
- `usr/share/ohmychadwm-tweak-tool/ott_gui.py`, `ott_root.py`, `ott.css`
- `po/*.po`, `po/ohmychadwm-tweak-tool.pot`, `usr/share/locale/*/LC_MESSAGES/ohmychadwm-tweak-tool.mo`
- `README.md`, `CLAUDE.md`
- `usr/share/ohmychadwm-tweak-tool/ott_targets.py`
- `usr/share/ohmychadwm-tweak-tool/ott_themes.py`, `ott_page_themes.py`, `ott_apply.py` (new)
- `usr/share/ohmychadwm-tweak-tool/ott_page_look.py`, `ott_system.py`, `ott_search.py`

## 2026.11.06

### What Changed
- **The icon theme now reaches Qt apps too.** Apply on the Look page also writes the icon theme to qt5ct and qt6ct,
  which Qt apps read in the Ohmychadwm session. Before, picking a new icon theme left Qt apps on the old one.
- The drift banner reports qt5ct/qt6ct when their icon theme differs from the pick.
- **Reset to Kiro default** falls back to the Surfn Kiro icons when /etc/skel has no GTK settings (was Surfn).

### Technical Details
- `ott_targets`: new targets `qt5ct`/`qt6ct` (`~/.config/qt5ct/qt5ct.conf`, `~/.config/qt6ct/qt6ct.conf`), read and
  written as `icon_theme=` under `[Appearance]` with the usual line-based `_upsert` and `.oma-bak` backup. Only the
  icon theme: style, palette and fonts stay the user's qt5ct/qt6ct choice. A missing file is skipped, never created
  (`/etc/environment` sets `QT_QPA_PLATFORMTHEME=qt5ct`, but not every user configures qt6ct).
- DMS (niri) keeps its own icon setting on purpose: it is a different session.
- `kiro_default()`: the hard-coded fallback icon theme is `Surfn-Kiro` (Kiro's new default).
- New string "{tool} not configured, skipped" (English until translated); catalogs refreshed with `po/make-mo.sh`.
- CLAUDE.md: a fake `HOME` does not isolate gsettings, xfconf or `xrdb`; test single writers, never `apply()`.

### Files Modified
- `usr/share/ohmychadwm-tweak-tool/ott_targets.py`
- `po/*.po`, `po/ohmychadwm-tweak-tool.pot`
- `CLAUDE.md`, `CHANGELOG.md`

## 2026.10.31

### What Changed
- **The language dropdown moved to the header, top right**, next to Support and Quit, the place every Kiro
  app uses. It left the Status page.
- **Portugal and Taiwan/Hong Kong no longer get English**: a system in Portuguese from Portugal now shows
  Brazilian Portuguese, one in traditional Chinese shows simplified Chinese, the closest catalogs there are.
- **The app speaks 13 languages**: Dutch, German, Spanish, French, Portuguese (Brazil), Russian, Hungarian, Italian,
  Turkish, Polish, Japanese, Chinese (simplified) and Romanian, besides English. It follows the system language;
  **Status → Language** picks another one, **Restart now** reopens the app in it. The menu entry is translated too.
- The terms match the KIROTUX premium apps this app was spun off from (92 strings are word for word the same).

### Technical Details
- `ott_gui.py`: module-level `_language_controls()` (same as alacritty/fish-tweak-tool) in `_header_row()`; the Status
  page's `_language_box` / `_on_language` / `_on_restart` removed; Restart now reopens the app with the same arguments.
- `ott_i18n.py`: `_SIBLING = {"pt": "pt_BR", "zh": "zh_CN"}` in `_shown()`, and the catalog is loaded for the language
  `_shown()` picked (`languages=[ACTIVE or SYSTEM]`) instead of gettext's own lookup, which stops at English for pt_PT.
  Checked with LANG pt_PT, pt_BR, zh_TW, zh_HK, zh_CN, nl_BE, de_AT, fr_CA, ja_JP, en_US and C.
- New `ott_i18n.py`, a copy of the premium apps' i18n module: gettext domain `ohmychadwm-tweak-tool`, catalogs from
  `usr/share/locale` (the repo's own copy when run from git), the saved choice in prefs.json, `OTT_LANGUAGE` beats
  both (the live tests pin English with it). `N_()` marks lookup keys (target labels, file-type categories) that are
  translated where they are shown.
- 279 strings in `_()`, whole sentences with named placeholders; the "dark/light" theme notes and the startup on/off
  messages became whole sentences per case; the countdown uses `ngettext`. Not translated: `ott_root.py` (runs as
  root), log lines, paths, commands, key and modifier names, and the names Ohmychadwm, chadwm, sxhkd, xrandr, feh.
- `po/`: template, 13 `.po` files, `make-mo.sh` (xgettext with `_`, `N_`, `ngettext`; compiles the `.mo` files and
  writes the menu entry from `po/ohmychadwm-tweak-tool.desktop.in`), `.codespellrc` skips the generated `.desktop`.
- Translations: the premium apps' translations reused for identical strings, the rest drafted by GitHub Copilot
  (GPT-6 Luna) with each language's register and the premium terms as a glossary, reviewed by a second AI (GPT-6
  Luna; GPT-6.1 Terra for Russian, Hungarian, Turkish, Polish, Japanese, Chinese and Romanian): 131 findings, 129
  taken. `msgfmt -c` and pofilter clean, plural forms checked at runtime, every page of every language checked
  off-screen.

### Files Modified
- `usr/share/ohmychadwm-tweak-tool/ott_i18n.py` (new), every `ott_page_*.py`, `ott_gui.py` (Language section),
  `ott_widgets.py`, `ott_targets.py`, `ott_apps.py`, `ott_chadwm.py`, `ott_display.py`, `ott_wallpaper.py`,
  `ott_keys.py`
- `po/` (new), `usr/share/locale/*/LC_MESSAGES/ohmychadwm-tweak-tool.mo` (new),
  `usr/share/applications/ohmychadwm-tweak-tool.desktop` (now generated), `.codespellrc` (new)
- `tests/run-live-ohmychadwm.sh`, `tests/live_ohmychadwm.py`, `tests/live_xfce.py` (pin English)
- `README.md`, `CLAUDE.md`, `CHANGELOG.md`

## 2026.10.25

### What Changed
- **Initial package: Ohmychadwm Tweak Tool**, the successor of Ohmychadwm Appearance. One window with a sidebar
  (the layout of the KIROTUX premium apps) for the ohmychadwm desktop. It is free and part of Kiro and Kiro-next.
- **Replaces `ohmychadwm-appearance`**: on upgrade pacman asks "Replace ohmychadwm-appearance with
  ohmychadwm-tweak-tool? [Y/n]". The `oma` command stays, so Ctrl+Alt+X keeps working for existing users.
- **Look**: everything Ohmychadwm Appearance did (GTK theme, icons, cursor, font, light/dark, bar theme and font,
  the out-of-sync banner, forcing `GTK_THEME`, the login-screen cursor, Reset to Kiro default).
- **Bar & windows** (new): window border, gaps, smart gaps, bar at the top or bottom, system tray, bar autohide.
- **Wallpaper** (new): Ohmychadwm wallpapers, Variety downloads and favourites, or any folder, with a preview, a fill
  mode and Previous/Next through Variety. Set with feh, so it stays after logging in again.
- **Displays** (new for real machines; before only VirtualBox): resolution, refresh rate, on/off and primary per
  screen, with the 15-second keep-or-revert, saved for every login.
- **Mouse & touchpad** (new): pointer speed, natural scrolling, left-handed, tap to click, off while typing. Used right
  away, Save keeps them for every login.
- **Startup apps** (new): switch what ohmychadwm starts at login on or off, add your own.
- **Default apps** (new): the terminal and file manager on Super+Enter / Super+Shift+Enter, and the app per file type.
- **Keys** (new): a searchable list of every key binding. **Status**: what the app found.
- **Style Light/Dark now really changes the look.** It only set a preference, so on a dark-only theme like
  Arc-Dawn-Dark, Light changed nothing (found on a test box). Picking Light or Dark now also switches to the theme's
  light or dark sibling (Arc-Dawn-Dark ↔ Arc-Dawn). When the two disagree, a **Use Arc-Dawn** button sits under the
  theme. A theme without a sibling gets a note.
- The Look page says its settings are shared with all your desktops (Xfce4, Ohmychadwm and the rest): they live in the GTK
  files, gsettings and XFCE's own xsettings, which every session reads.
- **Started from XFCE (Ctrl+Alt+H) or another desktop**, the pages that only change Ohmychadwm say so: the bar part of
  Look, Bar & windows, Wallpaper, Startup apps, the terminal/file manager keys, Displays (a change shows now, the
  saved layout only at Ohmychadwm logins) and Keys. The Restart Ohmychadwm button stays hidden there, and Apply says
  the bar shows at the next Ohmychadwm login.
- **Ctrl+Alt+H while the app is open brings its window forward** instead of opening a second window (found in XFCE).
- **Live test** (`tests/run-live-ohmychadwm.sh`, not in the package): run on a box logged in to ohmychadwm, it presses
  every page's buttons and reads each change back (settings files, gsettings, xfconf, xrdb, xrandr, xinput, feh,
  sxhkd, the rebuilt bar), then restores everything. Its "Use <light sibling>" check no longer fails when the box
  already has the dark sibling selected: picking the selected theme again changes nothing, so the test now refreshes
  the theme note itself (found on a test box: 49 passed, this one failed).

### Technical Details
- OMA's toolkit-free modules carried over under the `ott_` prefix (`targets`, `scan`, `env`, `system`, `chadwm`,
  `root`, `config`). OMA's single page became `ott_page_look.py`; its VirtualBox screen section became the Displays
  page (`ott_display.py`, now for every output).
- `ott_chadwm`: the managed config.def.h block holds the bar font **and** six `THEME_*` options. It reads and strips
  OMA's old `ohmychadwm-appearance managed` markers, so a migrated file never ends up with two blocks. Tested on a
  copy with an old block: one new block, font kept, `make` without warnings.
- Backups keep OMA's `.oma-bak` suffix (a new suffix would back up already-edited files). Prefs fall back to OMA's
  `prefs.json`.
- `ott_root.py` gains `--input JSON`: validated as root by `ott_input.validate()`, written as InputClass sections to
  `/etc/X11/xorg.conf.d/40-ohmychadwm-input.conf`. `run_root()` is the single pkexec entry point for every page.
- Displays: `--rate` is written only when it differs from the mode's default, since arandr never writes it; outputs
  are re-placed side by side when a width changes.
- Default apps rewrite only single-word commands on the terminal/file-manager keys in sxhkdrc, then
  `pkill -USR1 -x sxhkd`.
- Mouse & touchpad saves as `40-…`: kiro-system-files ships `30-touchpad.conf` (Tapping on), and Xorg applies
  InputClass files in name order, so a `30-o…` file lost to it.
- Style: `ott_scan.style_variant()` finds the sibling by the `-Dark`/`-Darker`/`-Light` suffix; Light writes
  `color-scheme prefer-light` (not `default`), which apps that follow the desktop, this one included, read as light.
- Live test on a test box in an ohmychadwm session: 50 checks passed, 0 failed, including every pkexec step (force
  GTK_THEME on/off, system + SDDM cursor, two bar rebuilds, the input file) and the Style fix measured on fresh GTK 3
  and GTK 4 windows (brightness 0.96 Light, 0.24 Dark). The runner restores every file it backed up and removes the
  `.oma-bak` files the run created.
- `ott_chadwm.in_session()`: the desktop names in `DESKTOP_SESSION` / `XDG_SESSION_DESKTOP` / `XDG_CURRENT_DESKTOP`,
  or, when none is set (startx), a running `ohmychadwm` for this user. `can_restart()` requires it, so the restart
  key is never sent into another desktop.
- `tests/live_xfce.py`: the same harness inside an XFCE session, without root. It checks the notes on every page,
  that Restart stays hidden, Light/Dark measured on fresh GTK 3/4 windows through xsettings, the icon theme in
  xsettings and the live mouse speed, then restores the user's files. On a test box in XFCE: 17 checks passed.
- `on_activate` reuses `get_active_window()`: GTK activates the running instance again on every launch.
- Keys parses sxhkdrc and the `keys[]` array (TAGKEYS expanded, `KEY_*` macros resolved for `KIRO_AZERTY`,
  spawn variables resolved to their command).

### Files Modified
- `usr/bin/ohmychadwm-tweak-tool`, `usr/bin/ott`, `usr/bin/oma` (new)
- `usr/share/applications/ohmychadwm-tweak-tool.desktop` (new)
- `usr/share/ohmychadwm-tweak-tool/*` (new)
- `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `LICENSE`, `ruff.toml`, `.gitignore`, `setup.sh`, `up.sh`, `kiro.jpg`
