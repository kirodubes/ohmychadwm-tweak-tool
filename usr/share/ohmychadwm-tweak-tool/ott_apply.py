"""One apply for a whole look: user files, the bar rebuild and one pkexec for every root change (Look and Themes)."""

import log
import ott_chadwm
import ott_env
import ott_root
import ott_targets
from ott_i18n import _

# bar font or border: leave what config.def.h has
KEEP = object()


def _bar_text(text, theme, font, border):
    new = ott_chadwm.set_theme(text, theme)
    if font is not KEEP:
        new = ott_chadwm.set_bar_font(new, *font) if font else ott_chadwm.clear_bar_font(new)
    if border is not KEEP:
        options = {k: v for k, v in ott_chadwm.bar_options(new).items() if k != "THEME_BORDER"}
        if border is not None:
            options["THEME_BORDER"] = border
        new = ott_chadwm.set_bar_options(new, options)
    return new


def apply_look(sel, bar=None, force=None, sys_cursor=False, sddm_background=None, status=lambda _text: None):
    """Apply sel everywhere; return (results, bar_result, notes). Call from a thread.

    bar is None or (theme, font, border): font KEEP / None (theme's own) / (family, size); border KEEP / None
    (theme's own) / pixels. force True writes GTK_THEME, False releases it, None leaves /etc/environment alone.
    """
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
