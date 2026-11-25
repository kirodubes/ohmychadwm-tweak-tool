# CHANGELOG

## 2026.11.25

### What Changed
- **The Themes page shows its pictures on pure Arch too.** A viewer's video showed 18 empty frames: the pictures
  come from kiro-atelier-wallpapers and kiro-system-files, which a plain Arch install with ohmychadwm doesn't have.
  The app now ships a small thumbnail of every look and the tiles show that. Applying a look still needs the
  wallpaper package; its tile still says what is missing.
- **Install the wallpapers from the Themes page.** Only while paintings are missing, a line above the tiles says so,
  with an **Install the wallpapers** button. It opens a terminal with `sudo pacman -S --needed
  kiro-atelier-wallpapers` (the user sees each step and types their own password). As soon as the paintings are
  there, the line goes away and the looks can be used, without restarting the app.
- The Kiro look's "Not installed" tooltip named kiro-atelier-wallpapers; its picture comes from kiro-system-files,
  and the tooltip now says so. The install button doesn't offer kiro-system-files: it rewrites `/etc` files, too much
  for a plain Arch system.

### Technical Details
- 18 thumbnails at the tile size (300x169, JPEG q82, 256 KB in all) in `usr/share/ohmychadwm-tweak-tool/thumbs/`,
  named after the look's `key`, made with `magick … -resize "300x169!"` (the same stretch the tile used).
- `_tile` loads `thumbs/<key>.jpg` first and falls back to the installed picture when a look has no thumb.
- `ott_themes.wallpapers_missing()`: any look whose painting doesn't resolve in `KA_DIR` (the Kiro look's own picture
  is not counted). The button reuses `ott_update.terminal()`, the same root-in-a-terminal path as Update now, so the
  app still has only one pkexec helper. A 2 s `GLib.timeout_add_seconds` watch re-resolves the looks and rebuilds the
  tiles (`_resolve()` + `_fill()`) once the paintings are there; `refresh()` does the same on a page visit.
- Tested in GTK Broadway with `KA_DIR` pointed at an empty folder: the line and the thumbnails show, Apply is greyed;
  switching `KA_DIR` back hides the line and all 18 looks become usable, the tiles still showing their pictures.
- 5 new or changed strings, translated in all 13 languages with each catalog's own word for "wallpaper" and "look";
  449/449 everywhere.

### Files Modified
- `usr/share/ohmychadwm-tweak-tool/ott_page_themes.py`, `ott_themes.py`
- `usr/share/ohmychadwm-tweak-tool/thumbs/*.jpg` (new)
- `po/*.po`, `po/ohmychadwm-tweak-tool.pot`, `usr/share/locale/*/LC_MESSAGES/ohmychadwm-tweak-tool.mo`
- `CLAUDE.md`

## 2026.11.24

### What Changed
- **All 13 languages are complete again.** The App placement page, the Keyboard page's workspace keys and a few
  smaller texts from the 2026-11-21 to 11-23 work showed in English: 62 untranslated and 18 fuzzy strings per
  language. They are now translated in nl, de, es, fr, ru, pt_BR, hu, it, tr, zh_CN, ja, pl and ro.

### Technical Details
- Drafted from one table per language (`fill-po.py --table`), with the terms the catalogs and the KiroTux premium
  apps already use (e.g. "workspace" = werkblad / Arbeitsfläche / espacio de trabajo). The 18 fuzzy entries were
  wrong msgmerge guesses ("Save rule" had taken "Opslaan", "App" had taken "Toepassen") and were translated anew.
- The summary line lowercases the mode labels (`_mode_labels()[…].lower()`), so they avoid nouns that must stay
  capitalised (German "Schwebend, mittig", not "in der Mitte"). Hungarian and Turkish keep `{app}`/`{name}` without
  a suffix ("{app} megnyitásakor", "{app} açıldığında", colon forms elsewhere).
- Second review pass by two separate reviewers (49 fixes taken, e.g. "Restart Ohmychadwm to use it" also follows a removed rule, so it now says "the change", not "the rule"); `msgfmt -c` and `pofilter` (variables, brace format,
  untranslated) clean; 445/445 translated in every catalog.

### Files Modified
- `po/*.po`, `po/ohmychadwm-tweak-tool.pot`
- `usr/share/locale/*/LC_MESSAGES/ohmychadwm-tweak-tool.mo`

## 2026.11.23

### What Changed
- **Opens by itself at the first login, on the Displays page**, like the KiroTux premium apps' Welcome page. A new
  user (or the live ISO in QEMU/VirtualBox) can set the screen resolution straight away. It opens once, on every
  machine; later logins skip it.
- **At that first login it floats in the middle of the screen** (900x680) instead of taking a tile. On the live
  ISO's 1024x768 screen it used to get half the width next to the installer, which cut the Displays page off.
  Opened any other way it tiles as before.

### Technical Details
- New `--first-login` flag: Ohmychadwm's `run.sh` (ohmychadwm 2026.11.23) runs `ohmychadwm-tweak-tool --first-login`
  at every login. Not an `/etc/xdg/autostart` entry: chadwm never reads that folder, and XFCE would.
- If `first_login_shown` is in prefs.json the process returns before any GTK work; otherwise it writes the date
  there and starts on the `displays` page. The check sits in `main()`, after the UTF-8 re-exec, so the mark can't
  make the re-exec'd process quit.
- Both self-restarts (GTK theme change, Status → Language → Restart now) drop `--first-login` from argv, or the
  restarted window would see the mark and close.
- Floating without a window rule: chadwm's `manage()` calls `updatewindowtype()`, which floats and centres a
  `_NET_WM_WINDOW_TYPE_DIALOG` window, but only reads the type when the window maps. GTK 4 has no type hint, so a
  `realize` handler sets the property with `xprop` (from `xorg-apps`), synchronously so it lands before the map. A
  later restart (theme change) drops `--first-login` and the window tiles again. Tested in VirtualBox: dialog type,
  900x680 at 508,198 on 1920x1080.

### Files Modified
- `usr/share/ohmychadwm-tweak-tool/ohmychadwm-tweak-tool.py`
- `usr/share/ohmychadwm-tweak-tool/ott_gui.py`
- `CLAUDE.md`

## 2026.11.21

### What Changed
- **New App placement page** (after Bar & windows): choose on which screen and workspace an app opens, and
  whether it floats (in the middle or not), for example Firefox on screen 2, workspace 10. The open windows are
  listed first, then the installed apps that name their window class. The rules Ohmychadwm already has (Gimp,
  Firefox on workspace 9, mintstick) show too and can be removed or replaced. **Save rule** and **Remove** recompile
  Ohmychadwm straight away (password asked once) and offer a restart. A first version with separate Add and Apply
  buttons said "Nothing changed" when the choices were made and Apply pressed without Add (riker test). A rule takes effect the next time
  the app opens a window. Same idea as the KiroTux premium apps' App placement page, written for chadwm.
  Each rule reads as a sentence ("When Firefox opens: workspace 9"), rules that change nothing say "no effect",
  and a line above them says rules never start an app (first wording on riker read as a list of apps that start).
  The app list leaves out python3 windows: that class is every Python GTK app at once, this one included.
  Remove on a rule that is already gone now says so and redraws the list (it said "This rule is already there").
  A spinner turns next to Save rule while Ohmychadwm recompiles, and the status says the password window comes next.
  **Removing the last rule no longer fails to compile** (riker): C forbids an empty `rules[]`, so the last Remove
  leaves one placeholder rule (class `ohmychadwm-no-rules`, matches no window). The page hides it and the next saved
  rule replaces it. The failed compile had already put the old file back, so nothing broke.
  Every rule now names its screen, also when it has none: "When Alacritty opens: the screen you are working on ·
  workspace 4". A rule that only sets a screen is no longer called "no effect". The workspace and how it opens are
  always named too, in short words: "When Alacritty opens: screen 2 (HDMI-0) · current workspace · tiled". A rule
  that changes nothing lists the same three and ends with "(this rule changes nothing)". The dropdowns start with
  "Current screen (now screen 1: DVI-D-0)" and "Current workspace" ("the screen you are working on" was too long).
- **App placement: "Also start it at login".** A rule alone only moves an app's window when you open the app; with
  this ticked the app also opens by itself at login, on its screen and workspace. It writes the same `run …` line as
  the Startup apps page, so it shows there too. Rules that start at login say "starts at login". Removing a rule
  also stops the login start, when this app added it (a line Kiro ships is never removed).
- **Edit a rule**: every rule has an Edit button that puts its app, screen, workspace, how it opens and the login
  tick back in the form; change what you want and press Save rule (saving replaces the app's old rule).
- **"Go to it when it opens"** on a rule: when the app opens a window, its screen and workspace come to the front
  with the app focused, instead of the app opening out of sight (on riker: Firefox → screen 1, workspace 10). Also
  after login: every "go to it" app that starts at login is in front on its screen (two on one screen: the last rule
  wins), and a line under the rules says what each screen shows after login. No recompile, no password; a restart
  of Ohmychadwm (Super+Shift+R) doesn't make the screens jump.
- A separate "When you log in" section (a workspace per screen) was tried and removed the same day: it contradicted
  the rules (on riker it put the right screen on an empty workspace 10 while Firefox stayed hidden on the left).
- **Rules for apps that aren't open also work when the menu entry's window class is off.** A Vivaldi rule did
  nothing on riker: its menu entry says `vivaldi`, its window is class `Vivaldi-stable`, instance `vivaldi-stable`,
  and chadwm compares case-sensitively. A rule saved for an app that isn't open is now written twice, on the class
  and on the instance; the page shows it as one rule. Picking the app from the open windows still writes one line
  with the real class.
- **The login switch lands on the right screen.** Right after login chadwm ignores the first pointer movement
  (it only records the screen), so both screens were set on the primary one. The helper now goes target screen →
  other screen → target screen.
- **Every screen says where it stands**: "Screen 2 (HDMI-0, left)", "Screen 1 (DVI-D-0, right, primary)", in the
  rules, the Screen list and the login section. On riker the primary screen is the right one, so "screen 2" was the
  left screen and a login setting went to the wrong screen. The place comes from the xrandr layout: left/middle/right,
  top/bottom when stacked, "number n from the left" with more than three screens.
- **The Screen list says which screen you are on now**: "The screen you are working on (now screen 1: DVI-D-0)".
- **"Go to it" apps no longer stay hidden on their workspace after login** (HQ PC: Firefox and Vivaldi on
  workspace 10 started at login, but you stayed on workspace 1). A replaced run.sh had lost the `ott-session --login`
  line, and saving a rule again did not put it back while the "go to it" choice was unchanged. Every Save rule now
  puts it back.
- **Style Dark no longer leaves the tweak tool itself light** (HQ PC): after an Apply that only changed the
  system-wide theme line (`GTK_THEME` in `/etc/environment`), the open window kept the old light theme. It now
  restarts itself on the same page, as it already did when the GTK theme changed.
  After that restart it was still light (HQ PC, adw-gtk3-dark): it now asks GTK for the dark colour scheme itself.

### Technical Details
- `ott_placement.py` (new, toolkit-free): parses the `rules[]` table of `config.def.h`, `set_rule()` /
  `remove_rule()` rewrite only plain rules (instance and title `NULL`, tags `0` or `1 << n`) for the exact class and
  keep every other line. chadwm ORs the tags of all matching rules, so one plain rule per class is kept. Screens come
  from `xrandr --listmonitors`, which lists them in the order dwm numbers them (Xinerama, the primary first); open
  windows from `xprop` (`_NET_CLIENT_LIST`, `WM_CLASS`). Classes are checked against `CLASS_OK` before they go into
  C source.
- `ott_page_placement.py` (new): each Save rule / Remove reads `config.def.h` fresh, writes, compiles, installs
  through the existing `--install` helper, and restores the old file when the compile or the install fails, so the
  page never shows rules the installed binary doesn't have and never writes over another page's rebuild.
- Search: monitor, screen, workspace, tag, rule, window rule and floating also find App placement.
- `ott_session.py` + `usr/bin/ott-session` (new): chadwm has no way for a program to switch workspaces and Erik
  wanted no change to chadwm's code (dwm.c lives in every user's home), so a small helper does what a person does:
  pointer to the screen's centre (chadwm selects a screen on pointer motion), then Super+Right once (chadwm only
  updates `_NET_CURRENT_DESKTOP` on a view change, not on a screen change), read `_NET_CURRENT_DESKTOP`, and the
  shortest way round with Super+Left/Right (`shiftview` wraps, so workspace 10, which has no key, works). Arrow keys
  type the same on every layout; configs without the shiftview keys fall back to the number keys, refused when
  `ott_keyboard.keys_match()` says they don't fit the layout (xdotool would add Shift = move the window). It watches
  `xprop -spy _NET_CLIENT_LIST`; window ids seen before are ignored, so Super+Shift+R triggers nothing. With
  `--login` it first waits until no new window came for 3 s (max 15 s), then shows the "go to it" login apps
  (`login_plan()`). It renames
  itself to `ott-session` via /proc/self/comm, so run.sh's `pgrep -x` and the page find one instance. The page adds
  `run ott-session --login` to run.sh and starts the helper while a rule has "go to it", and removes both when none has.
  Setting in prefs.json: `placement.goto` (rule names). Tested on riker: login switch, go to it, no jump on
  Super+Shift+R.
- Package recipe: `xdotool` and `xorg-xprop` are dependencies now (xdotool was optional).
- `ott_placement.rules()` merges a class line and an instance line with the same name and settings into one rule
  (`both`); `matches()` mirrors chadwm's `applyrules()` (case-sensitive substring on class/instance) and
  `ott_session` uses it to find a window's rule. `set_rule(both=True)` / `remove_rule()` write and drop both lines.
- Login start: `ott_placement.choices()` also returns a one-word start command per app (the .desktop `Exec` program,
  else `/proc/<_NET_WM_PID>/cmdline` of the open window), checked against `COMMAND_OK` before it goes into run.sh.
  `_set_login()` adds or switches on the line with `ott_startup`; unticking removes a line this app added and only
  comments out one Kiro ships. The rules run before chadwm starts at login, which is fine: `scan()` applies the
  rules to windows that already exist. The current screen comes from `Gdk.Display.get_monitor_at_surface()` of
  this window, matched to `xrandr --listmonitors` by connector name.
- `_set_goto()` returned early when the flag was unchanged, so `save_goto()`, the only code that adds the helper's
  run.sh line, never ran; it now always calls `save_goto()` and only skips the status sentence.
- The app `execv`s itself only when gsettings `gtk-theme` changed. When it already said `adw-gtk3-dark` and an
  Apply only rewrote `GTK_THEME="adw-gtk3"` to `adw-gtk3-dark`, no restart came, and the process kept
  `GTK_THEME=adw-gtk3`: GTK ignores prefer-dark when `GTK_THEME` is set, so the window stayed light. A
  `Gio.FileMonitor` on `/etc/environment` now calls `_restart_soon()` when the active line differs from the
  process's `GTK_THEME`; the restart still waits for `_busy` and pkexec, and `_follow_forced_theme()` picks up the new line.
- adw-gtk3-dark's `gtk-4.0/` is byte-identical to adw-gtk3's: one libadwaita stylesheet that turns dark only on
  `@media (prefers-color-scheme: dark)`, which GTK 4.24 takes from `gtk-interface-color-scheme`. `prefer-dark=true`
  read from `settings.ini` leaves that DEFAULT (light), and `_apply_color_scheme()` returned early because prefer-dark
  was already True. It now sets `gtk_interface_color_scheme` to DARK/LIGHT directly (checked under Xvfb).

### Files Modified
- `usr/share/ohmychadwm-tweak-tool/ott_placement.py` (new)
- `usr/share/ohmychadwm-tweak-tool/ott_page_placement.py` (new)
- `usr/share/ohmychadwm-tweak-tool/ott_gui.py`
- `usr/share/ohmychadwm-tweak-tool/ott_search.py`
- `usr/share/ohmychadwm-tweak-tool/ohmychadwm-tweak-tool.py`
- `po/*.po`, `po/ohmychadwm-tweak-tool.pot`, `usr/share/locale/*/LC_MESSAGES/ohmychadwm-tweak-tool.mo`
- `CLAUDE.md`

## 2026.11.20

### What Changed
- **New Themes page** (first in the sidebar): ten looks shown as pictures. One click sets the wallpaper, the bar
  colours and window border, the GTK theme and light/dark, the icons and the cursor; with the check box on, the
  login screen (SDDM) gets the same wallpaper and cursor. Ohmychadwm is recompiled and the password is asked once.
  Every part comes from a package on the Kiro ISO; a look whose picture or bar theme is missing is greyed out. The
  frame around each picture shows that look's window border colour and width. The looks are Kiro, Nord Frost,
  Dracula Night, Tokyo Night, Paper Day, Everforest, Desert Gruv, Rosé Pine, Catppuccin Space and Celestial Ocean,
  each on a different Kiro Atelier painting.
- **Themes: 16 looks, and you see the result at once.** Six new looks (Bright Moon, Monokai House, Summit Dawn,
  Dragon Fire, Neptune Deep, Venom), and every look says whether its bar sits at the top or the bottom (half of them
  each). Desert Dusk and Celestial Ocean got their own bar colours: they were copies of Everforest and of the Kiro look.
  After a click a spinner turns on the picture and next to the status, and Ohmychadwm restarts by itself, so the new
  bar and window borders show straight away.
- **No false "Your settings are out of sync" after a look.** The Look page kept the choices it read when the app
  started, so after a Themes click it compared old choices with the new files, showed the banner, and its Apply or
  Fix all would have put the old look back. It now reloads its choices when the files changed while you were away,
  and keeps your unsaved edits when nothing changed.
- **No see-through app window after a look.** GTK 4 can't switch an open window to another theme reliably: the
  Arc themes (Arc, Arc-Dark, Arc-Lighter) lost their whole style and the window showed the wallpaper through it
  (seen on the VM after Nord Frost with 26.11-07). The app now restarts itself on the page you were on when the GTK
  theme changes, once a look or a password prompt has finished. Same fix as the KiroTux premium apps (written anew).
- Every look's description now ends with dark or light, where the bar sits and whether it hides itself ("Dark, bar
  at the top, hides itself."), one whole sentence per combination so translators can order it.
- **18 looks.** New: **Rose Quill** (the Rosé Pine rose borders, dark, the bar at the top hiding after 3 s, on the
  paper-quilled rose and lavender swirls) and **Snow Leopard** (Solarized blue borders, the art deco snow leopard,
  the bar at the bottom hiding itself). Even number, so the last row is full; 9 looks have the bar at the top, 9 at
  the bottom. **Kiro stays top left, the rest are alphabetical** by the name shown in your language.
- **Apply button with a spinner under every picture**, as in the KiroTux premium apps: the busy look is visible on its
  own tile (the status line at the bottom is often out of view). The picture is still clickable. While a look
  applies, every Apply waits.
- **Every tile is the same size.** Short descriptions made narrow tiles and long ones wide tiles (Kiro and Nord Frost
  were smaller than the rest); now every picture is 300 x 169 and the text wraps at that width.
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
  Kiro Atelier paintings by subject (any style or version) and reads `SchemeSelbr` from the bar theme for the tile
  frame: the focused window border (`col_borderbar` is only the frame around the bar). Every name was checked with
  `pacman -Qo` against the ISO's `packages.x86_64`. On the ISO the only icon sets
  are Surfn-Kiro and neo-candy-icons; the `or-`/`al-` candy and beautyline dirs are hidden layers, not choices.
- `ott_apply.apply_look()`: the Look page's apply worker moved here unchanged, so Look and Themes share one path and
  one pkexec. New: `bar=(theme, font, border)` with `KEEP`, `force=None` (leave `/etc/environment` alone) and
  `sddm_background`. Themes keeps the user's font, cursor size and bar font, rewrites GTK_THEME only when it is
  already forced, and drops the THEME_BORDER override for the Kiro look (the theme's own width).
- `ott_root.py --sddm-background PATH`: only an image under `/usr/share/backgrounds` (realpath, no newline), written
  as `[General] background=` to `theme.conf.user` beside the SDDM theme in use. Only `edu-simplicity` reads it,
  from kiro-sddm-simplicity 2026.11.20, whose `Main.qml` now takes `config.background`. Other themes are skipped
  with a note, and the check box then only offers the cursor. The same happens with an older kiro-sddm-simplicity
  whose `Main.qml` doesn't read `config.background` yet, so the page never promises a wallpaper SDDM would ignore.
- `ott_apply._bar_text` text-tested on a copy of config.def.h: the Look path gives the same text as before; KEEP
  keeps font and border; `border=None` drops only THEME_BORDER; a Bar page gaps override survives every case.
- Keyboard page: `_azerty_now` is set before the first `refresh()`. Selecting the current layout fired
  `_update_hint()` before it existed (AttributeError traceback in the log; the hint itself was right).
- Translations: the 34 new strings are translated in all 13 languages (look names kept as names), merged with
  `msgmerge --compendium`. The old fuzzy "{tool} not configured, skipped" had a wrong placeholder; it is now empty
  (English).
- Rendered on GTK Broadway with a fake HOME: 10 tiles, two per row in the default window, thumbnails loaded off-thread.
- Tested on the v26.11.20 VM in an Ohmychadwm session, from a copy of the source (root helper through sudo, as SSH
  has no polkit agent; the SDDM wallpaper write pointed at a scratch theme because the VM still has the old one).
  Dracula Night (dark) and Rosé Pine (light) wrote all nine user targets, the wallpaper, the bar theme + border block,
  the system and SDDM cursor and `theme.conf.user`, and installed a rebuilt binary that carries the new colours. Thunar
  showed the light theme and neo-candy icons. The Look page's Apply after the refactor wrote only the user files
  (nothing to rebuild, no password) and kept the border override. On the real, old SDDM theme the page offers the
  cursor only. Every file, gsettings, xfconf and xrdb value was put back exactly afterwards.
- Live test (`tests/live_ohmychadwm.py`, run with `tests/run-live-ohmychadwm.sh` on the test box): new Themes steps
  click a dark and a light look, through the real pkexec path, and read every target back. That covers GTK in
  gtk3/gsettings/xfconf, icons, cursor, light/dark, the bar theme and border, the installed rebuild, the wallpaper,
  the system and SDDM cursor, `theme.conf.user` (or INFO when the SDDM theme can't show a wallpaper), a forced
  GTK_THEME, the In use mark and a fresh GTK 3 window's brightness. Then Restart, and greyed-out tiles for looks with
  missing parts. Each step only counts its own status lines, so the light look can't finish on the dark look's
  "Applied.". The runner now also backs up qt5ct/qt6ct (written by Apply since 2026.11.06) and `theme.conf.user`,
  and on restore removes what a first Apply creates (`.gtkrc-2.0`, `.Xresources`, `.icons/default`).
- Live test on the VM with the 26.11-07 build and kiro-sddm-simplicity 26.11-02: 70 pass, 3 fail, 4 info. All 22
  Themes checks pass through the real pkexec path, login wallpaper included. The 3 failures are the Look page's
  "style light" step: the Kiro tile was activated in the middle of it (status log: "Applying “Kiro”" right after the
  Look page's Apply) and set the dark theme back. The test never touches that tile, and the screenshots show the VM's
  pointer over the tiles, so most likely a click into the VM window. To be re-run hands-off.
- `ott_root._write_file(backup=False)` for `theme.conf.user`: the second look made a `.oma-bak` of the first look's
  file, a stray file under `/usr/share/sddm/themes`. The runner's `.oma-bak` sweep now includes that folder.
- 16 looks: a colour comparison of the 45 bar themes (CIELAB distance over bar background, focused border, selected
  tag and tag colours) found everforest = gruvchad (0.0), celestial ≈ dracul, nord-polarnight ≈ nord-frost and the
  five planet themes as near copies. Desert now uses meditation, Celestial Ocean faraway; the six new looks use bar
  themes that differ clearly from all others and six unused Kiro Atelier paintings (still one painting per look).
- Each look sets `top`; `_bar_options()` writes THEME_TOPBAR / THEME_BORDER only where they differ from the bar theme,
  so switching theme later on the Look page doesn't keep a stale override. `ott_apply` takes a dict of THEME_*
  overrides (None = drop) instead of only a border.
- Descriptions are written from the paintings themselves: the Kiro Atelier file names often say something else
  (the "shark at night" is people walking through a blue cave, the "whale" is sea swirls), checked on a contact sheet
  of all 16. Seven descriptions and three names changed.
- Automatic restart: after a rebuild the page sends the restart key, waits 3 s and reads the running binary
  (`ott_chadwm.running_binary()`). If it is still `/usr/bin/ohmychadwm` (run.sh from before ohmychadwm's `hash -r`
  fix), the status asks for one logout. The Restart button is gone from this page. Live test: restart and spinner
  checks moved into the look steps, and the bar check reads the effective border and position.
- VM check of this version (from a copy of the source, root through sudo): Neptune Deep moved the bar to the bottom
  in navy with yellow, Ohmychadwm restarted by itself 3 s after the install and ran the new `/usr/local/bin` binary,
  the status said "restarted with the new bar", both spinners stopped, and the Look page showed no "out of sync"
  banner afterwards. The VM was put back on the look Erik had picked (Desert Gruv), login wallpaper included.
- Look page `refresh()` (it had none, so the sidebar never refreshed it): `_files_now()` is a fingerprint of every
  settings target, the system/SDDM cursor and the bar theme + font. When it differs from what the pickers were filled
  from, `_load()` sets every picker from `ott_targets.current()` (the Style switch under `_resetting`, so it doesn't
  swap the theme for its light/dark sibling); otherwise only the drift banner is re-checked. Its own Apply updates
  the fingerprint.
- Full VM run of this version (session started from `/usr/bin/ohmychadwm`, `/usr/local/bin/ohmychadwm` moved aside,
  new run.sh with `hash -r`, one fresh login): all 16 looks, one after another, pass every check. That covers bar
  theme, effective border and bar position, GTK in settings.ini and gsettings, icons, cursor in the session, system
  and SDDM, light/dark, wallpaper, login wallpaper, automatic restart into the new `/usr/local/bin` build (the first
  one too: the `hash -r` fix works), spinners off, In use, and no out-of-sync banner after a Look page visit. An
  unsaved Look edit survives a revisit. Screenshots show the bar at the top or bottom as each description says. The
  first run of the same check found the banner on 15 of 16 looks. Everything on the VM was put back and compared
  byte for byte afterwards.
- Restart on a theme change (`ohmychadwm-tweak-tool.py`): gsettings `changed::gtk-theme` that differs from the
  theme at start → poll every 500 ms until no page has `_busy` set and no pkexec child runs → save the window size
  → `os.execv` with `--page <shown page>`. A light/dark change under a gresource theme (Arc*: `gtk-4.0/gtk.gresource`)
  restarts too instead of switching live (GTK 4.24 drops their stylesheet). At start `GTK_THEME` is set from
  `/etc/environment` (or dropped when nothing is forced), so a restart never inherits the login's stale value.
  `ott_gui.build` keeps `window.ott_pages` / `window.ott_stack` for it. The live test harness runs its own
  Gtk.Application, so it never restarts. Tested on the VM with the app started in the session (an app started over
  SSH has no polkit agent: pkexec fails with "Error creating textual authentication agent"): Venom with 26.11-08
  (no theme change, no restart needed), Nord Frost (same Arc-Dark, no restart, correct), Paper Day (Arc-Dark →
  Arc-Lighter, dark → light): "GTK theme changed: restarting on the themes page", back light and solid.
- Equal tiles: `_Thumb` (Gtk.Picture) and `_TileText` (Gtk.Label) override `do_measure` to report exactly
  `_THUMB_W` wide (the label still computes its height for that width). Measured on Broadway: the FlowBox lays rows
  out height-first, and for a given row height a Picture keeping its aspect and a wrapped Label wanting fewer lines
  both asked for more width (tiles 308 vs 464 px). `max_width_chars` alone didn't help.
- Looks have an optional `hide` (THEME_AUTOHIDE seconds); `ott_themes.hides()` gives the effective value (the look's,
  else the bar theme's) for the description. Rose Pine, Monokai House, Neptune Deep, Rose Quill and Snow Leopard hide
  their bar (3 s), Dragon Fire after 1 s. The live test checks the effective auto-hide too.
- Tested on the VM from a copy of the source started in the session: Rose Quill (rose borders, bar hidden, app
  restarted dark) and Snow Leopard (blue `#268bd2` in the rebuilt binary, solarized, snow leopard wallpaper).
- Found on the VM: on the very first install of `/usr/local/bin/ohmychadwm`, Restart still runs `/usr/bin/ohmychadwm`
  until the next login, because the `run.sh` loop's bash remembers the old path. Same for the Look page; not changed
  here (it is ohmychadwm's `run.sh`).

### Files Modified
- `usr/share/ohmychadwm-tweak-tool/ott_search.py`, `ott_keyboard.py`, `ott_page_keyboard.py`, `ott_update.py`,
  `ott_page_update.py` (new)
- `usr/share/ohmychadwm-tweak-tool/ott_gui.py`, `ott_root.py`, `ott.css`
- `po/*.po`, `po/ohmychadwm-tweak-tool.pot`, `usr/share/locale/*/LC_MESSAGES/ohmychadwm-tweak-tool.mo`
- `README.md`, `CLAUDE.md`
- `usr/share/ohmychadwm-tweak-tool/ott_targets.py`
- `usr/share/ohmychadwm-tweak-tool/ott_themes.py`, `ott_page_themes.py`, `ott_apply.py` (new)
- `usr/share/ohmychadwm-tweak-tool/ott_page_look.py`, `ott_system.py`, `ott_search.py`
- `usr/share/ohmychadwm-tweak-tool/ohmychadwm-tweak-tool.py`, `ott_gui.py`
- `tests/live_ohmychadwm.py`, `tests/run-live-ohmychadwm.sh`

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
