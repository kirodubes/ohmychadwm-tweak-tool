# CHANGELOG

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
- Keys parses sxhkdrc and the `keys[]` array (TAGKEYS expanded, `KEY_*` macros resolved for `KIRO_AZERTY`,
  spawn variables resolved to their command).

### Files Modified
- `usr/bin/ohmychadwm-tweak-tool`, `usr/bin/ott`, `usr/bin/oma` (new)
- `usr/share/applications/ohmychadwm-tweak-tool.desktop` (new)
- `usr/share/ohmychadwm-tweak-tool/*` (new)
- `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `LICENSE`, `ruff.toml`, `.gitignore`, `setup.sh`, `up.sh`, `kiro.jpg`
