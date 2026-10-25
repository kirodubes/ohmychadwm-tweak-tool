# Ohmychadwm Tweak Tool

One window for the settings of an **ohmychadwm** desktop: the look (GTK theme, icons, cursor, font, light/dark, bar
theme), the bar and window gaps, the wallpaper, displays, mouse and touchpad, startup apps, default apps, and a list
of every key binding.

It replaces **Ohmychadwm Appearance**: everything that app did is the **Look** page here. When you upgrade, pacman
asks to replace `ohmychadwm-appearance` with `ohmychadwm-tweak-tool`. Answer **Y**. The `oma` command keeps working,
so Ctrl+Alt+X still opens it.

## Pages

| Page | What it does | Where it is saved |
|---|---|---|
| **Look** | GTK theme, icons, cursor + size, font, light/dark, bar theme, optional bar font. An **out of sync** banner with **Fix all** when the settings files disagree | GTK 2/3/4 files, gsettings, the XFCE `xsettings` channel, `~/.icons/default`, `~/.Xresources`, `config.def.h`; optionally `GTK_THEME` in `/etc/environment` and the system/login-screen cursor |
| **Bar & windows** | Window border, gaps, smart gaps, bar at the top or bottom, system tray, bar autohide | a managed block in `~/.config/ohmychadwm/chadwm/config.def.h`, then a rebuild |
| **Wallpaper** | Ohmychadwm wallpapers, Variety downloads/favourites or any folder, with a preview, fill mode and Previous/Next through Variety | `~/.fehbg` (feh), which ohmychadwm loads at login |
| **Displays** | Resolution, refresh rate, on/off and primary per screen. Used right away; keep it within 15 seconds or the old layout comes back | `~/.screenlayout/<user>.sh` (arandr format), which ohmychadwm runs at login |
| **Mouse & touchpad** | Pointer speed, natural scrolling, left-handed; tap to click and off-while-typing for touchpads. Changes show right away | `/etc/X11/xorg.conf.d/30-ohmychadwm-input.conf` |
| **Startup apps** | Switch the programs ohmychadwm starts at login on or off, add your own | the `run …` lines of `~/.config/ohmychadwm/scripts/run.sh` |
| **Default apps** | The terminal and file manager on Super+Enter / Super+Shift+Enter, and the app per file type (browser, editor, images, video, music, PDF, mail) | `~/.config/ohmychadwm/sxhkd/sxhkdrc` (sxhkd reloads it) and xdg-mime |
| **Keys** | A searchable list of every key binding, read from sxhkdrc and ohmychadwm's own `config.def.h` | read only |
| **Status** | Session, config, the bar build and the tools each page needs | read only |

Before it changes a file for the first time, the app keeps a copy of the original next to it as `<file>.oma-bak`.
Root is only needed for `/etc/environment`, the system cursor, the input file and installing the rebuilt bar. Each
Apply asks for your password **once** (pkexec).

## The system-wide theme (GTK_THEME)

Kiro sets `GTK_THEME` in `/etc/environment`, and that beats every settings file: GTK 3 and GTK 4 apps use it
whatever the files say. On the Look page:

- **Force this theme on every app (system-wide)**: the Kiro default. A theme change rewrites the `GTK_THEME` line
  and shows after you log out and back in.
- **Untick it** to comment the line out. Apps then follow your personal settings; some GTK 4 / libadwaita apps may
  keep their own look. Ticking it again brings the line back.

**Reset to Kiro default** loads the look Kiro ships for everything on the Look page. **Use the theme's values** on
Bar & windows hands those options back to the bar theme.

## The ohmychadwm bar

ohmychadwm's bar is compiled into the window manager. When you change the bar theme, bar font or anything on Bar &
windows, the app recompiles ohmychadwm as your user and installs it. With `xdotool` installed it can then restart
ohmychadwm for you; otherwise press **Super+Shift+R**.

## Install

On Kiro, from the Kiro repositories:

```bash
sudo pacman -S ohmychadwm-tweak-tool
```

Launch it from the menu (**Ohmychadwm Tweak Tool**), or run `ohmychadwm-tweak-tool` (short: `ott`, or the old
`oma`). `--page NAME` opens a page directly (`look`, `bar`, `wallpaper`, `displays`, `mouse`, `startup`, `apps`,
`keys`, `status`); `--debug` prints more to the console.

## Requirements

`ohmychadwm`, `python-gobject`, `gtk4`, `xfconf`, `polkit` (plus a running polkit agent), `arandr` (pulls in
`xorg-xrandr`), `xorg-xinput`, `feh`, `xdg-utils`. Optional: `xdotool` for the restart button, `xorg-xrdb` to apply
the cursor live, `variety` for the Variety wallpaper sources.

<!-- KIRO-FUNDING-FOOTER:START — managed by Kiro-HQ/cascade-readme-footer.sh -->
## Help fund Kiro

Everything I build here stays free and open — always. If Kiro or any of these
tools have ever saved you time or taught you something, a small monthly
contribution helps keep the work going. Donations target break-even, nothing
more — the core always stays free for everyone.

- GitHub Sponsors: https://github.com/sponsors/erikdubois
- Patreon: https://www.patreon.com/c/kiroproject
- YouTube memberships: https://www.youtube.com/@ErikDubois/join
- Ko-fi: https://ko-fi.com/erikdubois
- PayPal: https://www.paypal.me/erikdubois
<!-- KIRO-FUNDING-FOOTER:END -->

## License

GPL-3.0. See [LICENSE](LICENSE).
