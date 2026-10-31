"""Translations: gettext catalogs from usr/share/locale, in the user's chosen language or the system's, else English."""

import gettext
import os
from pathlib import Path

import ott_config

DOMAIN = "ohmychadwm-tweak-tool"
# usr/share/<app>/ -> usr/share/locale: /usr/share/locale once installed, the repo's own copy when run from git
LOCALE_DIR = Path(__file__).resolve().parent.parent / "locale"

# Each language in its own name, so someone stuck in a language they can't read still finds theirs.
NAMES = {
    "en": "English", "nl": "Nederlands", "de": "Deutsch", "es": "Español", "fr": "Français",
    "pt_BR": "Português (Brasil)", "ru": "Русский", "hu": "Magyar", "it": "Italiano", "tr": "Türkçe",
    "pl": "Polski", "ro": "Română", "zh_CN": "简体中文", "ja": "日本語",
}


def available():
    """Return the language codes the app can show: English, then every language with a catalog."""
    return ["en", *sorted(p.parent.parent.name for p in LOCALE_DIR.glob(f"*/LC_MESSAGES/{DOMAIN}.mo"))]


def name(code):
    """Return the language's own name for code (nl_BE -> Nederlands), or the code itself."""
    return NAMES.get(code) or NAMES.get(code.split("_")[0]) or code


def chosen():
    """Return the language saved in the app, or None to follow the system."""
    code = ott_config.load_prefs().get("language")
    return code if code in available() else None


def save_choice(code):
    """Save the app's language; None follows the system again. Shows after the next start."""
    ott_config.update_prefs({"language": code})


def _system_language():
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "").split(":")[0].split(".")[0]
        if value:
            return value
    return "en"


def _shown(code):
    # the language the app really shows for a system code: its catalog (nl_BE -> nl), else English
    codes = available()
    for candidate in (code, code.split("_")[0]):
        if candidate in codes:
            return candidate
    return "en"


SYSTEM = _shown(_system_language())
# OTT_LANGUAGE (the live test pins English with it) beats the saved choice, which beats the system language
ACTIVE = os.environ.get("OTT_LANGUAGE") or chosen()
_SYSTEM_LANGUAGE_VAR = os.environ.get("LANGUAGE")
if ACTIVE:
    # GTK's own dialogs and the app names from Gio read LANGUAGE too, so they follow the choice
    os.environ["LANGUAGE"] = ACTIVE


def restore_environment():
    """Put LANGUAGE back as the session set it, so a restarted app sees the real system language again."""
    if _SYSTEM_LANGUAGE_VAR is None:
        os.environ.pop("LANGUAGE", None)
    else:
        os.environ["LANGUAGE"] = _SYSTEM_LANGUAGE_VAR

_translation = gettext.translation(DOMAIN, localedir=LOCALE_DIR, languages=[ACTIVE] if ACTIVE else None, fallback=True)
_ = _translation.gettext
ngettext = _translation.ngettext


def N_(text):
    """Mark text for translation without translating it (a lookup key that is translated where it is shown)."""
    return text
