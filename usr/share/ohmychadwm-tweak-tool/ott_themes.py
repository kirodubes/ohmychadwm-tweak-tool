"""Themes: ten whole looks (wallpaper, login wallpaper, bar, border, GTK, icons, cursor) built from Kiro ISO packages.

Toolkit-free. Every name below comes from a package on the Kiro ISO (kiro-iso archiso/packages.x86_64):
kiro-atelier-wallpapers and kiro-system-files (pictures), ohmychadwm (bar themes; each sets col_borderbar, the
window border colour), arc-gtk-theme, kiro-arc-dawn, celestial-dawn, adw-gtk-theme, surfn-kiro-icons-git,
neo-candy-icons-git (its or-/al- sets are hidden layers, not choices), bibata-cursor-theme, capitaine-cursors and vimix-cursors. A look whose picture or bar theme is
missing can't be used; icons, cursor and GTK theme fall back along their list.
"""

import glob
import os
import re
from dataclasses import dataclass, field

import ott_chadwm
import ott_scan
from ott_i18n import _

KA_DIR = "/usr/share/backgrounds/kiro-atelier"
KIRO_WALLPAPER = "/usr/share/backgrounds/kiro/kiro-wallpaper.jpg"
_COLOR_RE = re.compile(r'^\s*static\s+const\s+char\s+col_borderbar\[\]\s*=\s*"(#[0-9A-Fa-f]{6})"')

# picture: KIRO_WALLPAPER, or the subject of a Kiro Atelier painting (any style or version of it matches).
# bar None = the bar theme Kiro ships; border None = the bar theme's own width.
BUILTIN = [
    {"key": "kiro", "name": _("Kiro"), "desc": _("The look Kiro ships with."),
     "picture": KIRO_WALLPAPER, "bar": None, "border": None, "dark": True,
     "gtk": ["Arc-Dawn-Dark"], "icons": ["Surfn-Kiro"], "cursor": ["Bibata-Modern-Ice"]},
    {"key": "nord-frost", "name": _("Nord Frost"), "desc": _("A frozen lake in art deco, cool blue, thin borders."),
     "picture": "frozen-lake-with-a-mountain-in-the-background", "bar": "nord-frost", "border": 1, "dark": True,
     "gtk": ["Arc-Dark", "Arc-Dawn-Dark"], "icons": ["Surfn-Kiro"], "cursor": ["Bibata-Modern-Ice"]},
    {"key": "dracula", "name": _("Dracula Night"), "desc": _("Bats around a dark moon, purple and candy icons."),
     "picture": "circle-with-bats-flying-around-it-in-the-dark", "bar": "dracula", "border": 2, "dark": True,
     "gtk": ["Arc-Dawn-Dark"], "icons": ["neo-candy-icons", "Surfn-Kiro"], "cursor": ["Bibata-Modern-Classic"]},
    {"key": "tokyo", "name": _("Tokyo Night"), "desc": _("A starry city in layered paper, deep blue."),
     "picture": "starry-night-over-a-city-skyline", "bar": "tokyonight", "border": 2, "dark": True,
     "gtk": ["Arc-Dawn-Dark"], "icons": ["neo-candy-icons", "Surfn-Kiro"],
     "cursor": ["Vimix-cursors", "Bibata-Modern-Classic"]},
    {"key": "paper-day", "name": _("Paper Day"), "desc": _("A sunset in layered paper, light and calm."),
     "picture": "rock-in-the-middle-of-the-ocean-at-sunset", "bar": "nord-snowstorm", "border": 1, "dark": False,
     "gtk": ["Arc-Lighter", "Arc"], "icons": ["Surfn-Kiro"], "cursor": ["Bibata-Modern-Classic"]},
    {"key": "everforest", "name": _("Everforest"), "desc": _("An origami forest, soft green and wide borders."),
     "picture": "forest-with-trees-in-the-foreground", "bar": "everforest", "border": 3, "dark": True,
     "gtk": ["adw-gtk3-dark", "Arc-Dawn-Dark"], "icons": ["neo-candy-icons", "Surfn-Kiro"],
     "cursor": ["Bibata-Original-Amber", "Bibata-Modern-Amber"]},
    {"key": "desert", "name": _("Desert Gruv"), "desc": _("A car in a monsoon desert, warm gruvbox colours."),
     "picture": "white-sports-car-parked-in-the-middle-of-a-desert", "bar": "gruvchad", "border": 2, "dark": True,
     "gtk": ["Celestial-Dawn-Dark", "Arc-Dawn-Dark"], "icons": ["neo-candy-icons", "Surfn-Kiro"],
     "cursor": ["Bibata-Modern-Amber"]},
    {"key": "rose-pine", "name": _("Rosé Pine"), "desc": _("A pink bird in a dreamscape, light rose tones."),
     "picture": "pink-and-purple-bird-flying-through-the-air", "bar": "rosepine", "border": 2, "dark": False,
     "gtk": ["Celestial-Dawn-Light", "Arc-Lighter"], "icons": ["neo-candy-icons", "Surfn-Kiro"],
     "cursor": ["Vimix-cursors", "Bibata-Modern-Classic"]},
    {"key": "catppuccin", "name": _("Catppuccin Space"), "desc": _("A paper-quilled solar system, pastel on dark."),
     "picture": "solar-system-with-planets-and-stars", "bar": "catppuccin", "border": 2, "dark": True,
     "gtk": ["Arc-Dawn-Dark"], "icons": ["neo-candy-icons", "Surfn-Kiro"],
     "cursor": ["capitaine-cursors-light", "Bibata-Modern-Ice"]},
    {"key": "celestial", "name": _("Celestial Ocean"), "desc": _("A psychedelic whale, bright colours and bold borders."),
     "picture": "humpback-whale-and-a-fish-swimming-in-the-ocean", "bar": "celestial", "border": 4, "dark": True,
     "gtk": ["Celestial-Dawn-Dark", "Arc-Dawn-Dark"], "icons": ["Surfn-Kiro"], "cursor": ["Bibata-Original-Ice"]},
]


@dataclass
class Resolved:
    """A look with the names this computer really has."""

    look: dict
    picture: str | None
    bar: str | None
    gtk: str | None
    icons: str | None
    cursor: str | None
    border_color: str | None
    missing: list = field(default_factory=list)

    @property
    def usable(self):
        """Return True when nothing is missing."""
        return not self.missing


def picture(look):
    """Return the installed picture file of look, or None."""
    pic = look["picture"]
    if pic.startswith("/"):
        return pic if os.path.isfile(pic) else None
    hits = sorted(glob.glob(os.path.join(KA_DIR, f"kiro-atelier-{pic}-*.jpg")))
    return hits[0] if hits else None


def border_color(bar):
    """Return col_borderbar of bar theme bar ('#rrggbb'), or None."""
    try:
        with open(os.path.join(ott_chadwm.CHADWM_DIR, "themes", f"{bar}.h"), encoding="utf-8") as f:
            for line in f:
                m = _COLOR_RE.match(line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return None


def _first(names, installed):
    return next((n for n in names if n in installed), None)


def resolve_all():
    """Return a Resolved for every look in BUILTIN (scans the installed themes once)."""
    gtk, icons, cursors = set(ott_scan.gtk_themes()), set(ott_scan.icon_themes()), set(ott_scan.cursor_themes())
    bars = set(ott_chadwm.themes())
    out = []
    for look in BUILTIN:
        pic = picture(look)
        bar = look["bar"] or ott_chadwm.default_theme()
        r = Resolved(look, pic, bar if bar in bars else None, _first(look["gtk"], gtk), _first(look["icons"], icons),
                     _first(look["cursor"], cursors), border_color(bar))
        if pic is None:
            r.missing.append(_("the wallpaper (kiro-atelier-wallpapers)"))
        if r.bar is None:
            r.missing.append(_("the bar theme {name}").format(name=bar))
        for value, what in ((r.gtk, _("a GTK theme")), (r.icons, _("an icon theme")), (r.cursor, _("a cursor"))):
            if value is None:
                r.missing.append(what)
        out.append(r)
    return out
