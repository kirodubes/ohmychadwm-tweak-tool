"""App preferences for ohmychadwm-tweak-tool (window size) under ~/.config/ohmychadwm-tweak-tool/."""

import json
import os

PREFS_PATH = os.path.expanduser("~/.config/ohmychadwm-tweak-tool/prefs.json")
# Ohmychadwm Appearance, the app this one replaces, kept its prefs here.
_OLD_PREFS_PATH = os.path.expanduser("~/.config/ohmychadwm-appearance/prefs.json")


def load_prefs():
    """Return the saved preferences dict, or an empty dict if none exist."""
    path = PREFS_PATH if os.path.isfile(PREFS_PATH) else _OLD_PREFS_PATH
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def update_prefs(updates):
    """Merge updates into the on-disk prefs and save; return the merged dict."""
    prefs = load_prefs()
    prefs.update(updates)
    os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
    with open(PREFS_PATH, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)
    return prefs
