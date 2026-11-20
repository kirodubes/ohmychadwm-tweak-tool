"""One apply for a whole look: user files, the bar rebuild and one pkexec for every root change (Look and Themes)."""

import log
import ott_chadwm
import ott_env
import ott_root
import ott_targets
from ott_i18n import _

# bar font or bar options: leave what config.def.h has
KEEP = object()


def _bar_text(text, theme, font, options):
    new = ott_chadwm.set_theme(text, theme)
    if font is not KEEP:
        new = ott_chadwm.set_bar_font(new, *font) if font else ott_chadwm.clear_bar_font(new)
    if options is not KEEP:
        # other overrides (the Bar page's gaps, …) stay; a value of None drops that override
        merged = {**ott_chadwm.bar_options(new), **options}
        new = ott_chadwm.set_bar_options(new, {k: v for k, v in merged.items() if v is not None})
    return new


# bar: None or (theme, font, options). font: KEEP, None (the theme's own) or (family, size). options: KEEP or
# {THEME_*: value, or None for the theme's own}. force: True writes GTK_THEME, False releases it, None leaves it.
def apply_look(sel, bar=None, force=None, sys_cursor=False, sddm_background=None, status=lambda _text: None):
    """Apply sel everywhere; return (results, bar_result, notes). Call from a thread."""
    log.log_section("Apply")
    results = ott_targets.apply(sel)
    for label, ok, msg in results:
        (log.log_success if ok else log.log_error)(f"{label}: {msg}")

    root_args, notes, bar_result = [], [], None
    env_theme, env_active = ott_env.read()
    if force and (not env_active or env_theme != sel.theme):
        root_args += ["--gtk-theme", sel.theme]
        notes.append("theme")
    elif force is False and env_active:
        root_args.append("--release-gtk-theme")
        notes.append("theme")
    if sys_cursor:
        root_args += ["--system-cursor", sel.cursor, "--cursor-size", str(sel.cursor_size)]
    if sddm_background:
        root_args += ["--sddm-background", sddm_background]

    compiled = False
    if bar is not None:
        try:
            text = ott_chadwm.read_config()
            new = _bar_text(text, *bar)
            if new != text:
                status(_("Recompiling Ohmychadwm…"))
                ott_chadwm.write_config(new)
                compiled, msg = ott_chadwm.compile_wm()
                if compiled:
                    root_args += ["--install", ott_chadwm.BUILT_BINARY]
                else:
                    bar_result = (False, msg)
        except (OSError, ValueError) as e:
            # the caller must still get a result, or its Apply stays greyed out until restart
            bar_result = (False, _("Ohmychadwm bar: {error}").format(error=e))

    if root_args:
        # one pkexec for everything that needs root, so at most one password prompt
        status(_("Waiting for your password…"))
        ok, err = ott_root.run_root(root_args)
        if not ok:
            results.append((_("System changes"), False, _("cancelled or failed: {error}").format(error=err) if err
                            else _("cancelled or failed")))
            notes.clear()
        elif compiled:
            bar_result = (True, "Ohmychadwm rebuilt and installed")
    if compiled:
        ott_chadwm.clean()
    if bar_result is not None:
        (log.log_success if bar_result[0] else log.log_error)(bar_result[1])
    return results, bar_result, notes
