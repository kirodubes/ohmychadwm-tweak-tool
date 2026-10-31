# CHANGELOG

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
