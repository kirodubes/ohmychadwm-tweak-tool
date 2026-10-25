#!/bin/bash
set -euo pipefail
##################################################################################################################
# Author : Erik Dubois
# Website : https://kiroproject.be
##################################################################################################################
#
#   DO NOT JUST RUN THIS. EXAMINE AND JUDGE. RUN AT YOUR OWN RISK.
#
##################################################################################################################
#
# Purpose: live test of the installed ohmychadwm-tweak-tool on a machine logged in to an ohmychadwm session.
#          Backs up every user and system file the app writes, lets pkexec through without a password for the
#          duration of the run (a temporary polkit rule), runs live_ohmychadwm.py (it drives the real GUI and
#          reads every change back: settings files, gsettings, xfconf, xrdb, xrandr, xinput, feh, sxhkd, the
#          rebuilt bar), then restores the backup, the screen layout and the bar. Run it ON the test box, from
#          SSH or a terminal: bash run-live-ohmychadwm.sh   (OTT_SUDO_PASS=<pw> to answer sudo from SSH)
# Why:     the headless smoke test never presses a button; this shows whether every setting really changes.
#
##################################################################################################################

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUT="${OTT_OUT:-/tmp/ott-live}"
BACKUP="${OUT}/backup"
APP_DIR="${OTT_APP_DIR:-/usr/share/ohmychadwm-tweak-tool}"
POLKIT_RULE="/etc/polkit-1/rules.d/00-ott-livetest.rules"
ROOT_FILES=(/etc/environment /usr/share/icons/default/index.theme /usr/local/bin/ohmychadwm
            /etc/X11/xorg.conf.d/40-ohmychadwm-input.conf)

if [[ -t 1 ]] && command -v tput >/dev/null 2>&1; then
    RED="$(tput setaf 1 2>/dev/null || true)"
    GREEN="$(tput setaf 2 2>/dev/null || true)"
    YELLOW="$(tput setaf 3 2>/dev/null || true)"
    BLUE="$(tput setaf 4 2>/dev/null || true)"
    CYAN="$(tput setaf 6 2>/dev/null || true)"
    RESET="$(tput sgr0 2>/dev/null || true)"
else
    RED="" GREEN="" YELLOW="" BLUE="" CYAN="" RESET=""
fi

log_section() { echo "${GREEN}############################################################${RESET}"; echo "${GREEN}  $1${RESET}"; echo "${GREEN}############################################################${RESET}"; }
log_info() { echo "${BLUE}############ $1${RESET}"; }
log_warn() { echo "${YELLOW}############ $1${RESET}"; }
log_error() { echo "${RED}############ $1${RESET}"; }
log_success() { echo "${GREEN}############ $1${RESET}"; }

on_error() {
    echo "${RED}ERROR on line $1: $2${RESET}"
    sleep 10
}
trap 'on_error "$LINENO" "$BASH_COMMAND"' ERR

# ── Functions ────────────────────────────────────────────────────────────────

as_root() {
    if [[ -n "${OTT_SUDO_PASS:-}" ]]; then
        printf '%s\n' "$OTT_SUDO_PASS" | sudo -S -p '' "$@"
    else
        sudo "$@"
    fi
}

session_env() {
    local pid var
    pid="$(pgrep -u "$(id -u)" -x ohmychadwm | head -1 || true)"
    [[ -n "$pid" ]] || { log_error "No running ohmychadwm session for $(id -un)"; exit 1; }
    # what an app started from the session gets
    for var in DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR GTK_THEME XDG_CURRENT_DESKTOP DESKTOP_SESSION; do
        unset "$var"
        local val
        val="$(tr '\0' '\n' < "/proc/${pid}/environ" | sed -n "s/^${var}=//p" | head -1)"
        [[ -n "$val" ]] && export "${var}=${val}"
    done
    export DISPLAY="${DISPLAY:-:0}"
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"
    log_info "ohmychadwm pid ${pid} on ${DISPLAY}"
}

sddm_conf() {
    python3 -c "import sys; sys.path.insert(0, '${APP_DIR}'); import ott_system; print(ott_system.sddm_conf())"
}

backup() {
    log_section "Backup"
    rm -rf "$OUT"
    mkdir -p "${BACKUP}/root" "${OUT}/shots"
    local items=() i
    for i in .config/gtk-3.0 .config/gtk-4.0 .config/ohmychadwm .config/mimeapps.list .config/ohmychadwm-tweak-tool \
             .gtkrc-2.0 .icons/default .Xresources .fehbg .screenlayout; do
        [[ -e "${HOME}/${i}" ]] && items+=("$i")
    done
    tar -C "$HOME" --exclude=.config/ohmychadwm/chadwm/ohmychadwm --exclude='*.o' -cf "${BACKUP}/home.tar" "${items[@]}"
    printf '%s\n' "${items[@]}" > "${BACKUP}/home-items"
    dconf dump /org/gnome/desktop/interface/ > "${BACKUP}/dconf-interface.ini"
    for i in /Net/ThemeName /Net/IconThemeName /Gtk/CursorThemeName /Gtk/CursorThemeSize /Gtk/FontName; do
        printf '%s\t%s\n' "$i" "$(xfconf-query -c xsettings -p "$i" 2>/dev/null || true)" >> "${BACKUP}/xfconf"
    done
    xdg-mime query default text/plain > "${BACKUP}/mime-text" || true
    python3 -c "import sys; sys.path.insert(0, '${APP_DIR}'); import ott_display as d; print(d.build_script(d.query()) or '')" \
        > "${BACKUP}/xrandr.sh"
    xinput list --short | sed -n 's/.*id=\([0-9]*\).*slave  pointer.*/\1/p' | while read -r i; do
        printf '%s\t%s\n' "$i" "$(xinput list-props "$i" 2>/dev/null | sed -n 's/.*libinput Accel Speed ([0-9]*):\s*//p')"
    done > "${BACKUP}/accel"
    ROOT_FILES+=("$(sddm_conf)")
    local n=0
    : > "${BACKUP}/root-index"
    : > "${BACKUP}/root-absent"
    for i in "${ROOT_FILES[@]}"; do
        if [[ -e "$i" ]]; then
            n=$((n + 1))
            as_root cp -a "$i" "${BACKUP}/root/${n}"
            printf '%s\t%s\n' "$n" "$i" >> "${BACKUP}/root-index"
        else
            echo "$i" >> "${BACKUP}/root-absent"
        fi
    done
    as_root chown -R "$(id -u):$(id -g)" "${BACKUP}/root"
    log_success "Backup in ${BACKUP}"
}

allow_pkexec() {
    log_info "Temporary polkit rule: pkexec without a password for $(id -un)"
    printf 'polkit.addRule(function(action, subject) {\n    if (action.id == "org.freedesktop.policykit.exec" && subject.user == "%s") {\n        return polkit.Result.YES;\n    }\n});\n' \
        "$(id -un)" | as_root tee "$POLKIT_RULE" >/dev/null
    sleep 1
}

restore() {
    log_section "Restore"
    as_root rm -f "$POLKIT_RULE"
    pkill -f "live_ohmychadwm[.]py" 2>/dev/null || true
    local i
    while read -r i; do
        [[ -n "$i" ]] && rm -rf "${HOME:?}/${i}"
    done < "${BACKUP}/home-items"
    rm -rf "${HOME}/.config/ohmychadwm-tweak-tool"
    tar -C "$HOME" -xf "${BACKUP}/home.tar"
    dconf load /org/gnome/desktop/interface/ < "${BACKUP}/dconf-interface.ini"
    while IFS=$'\t' read -r prop value; do
        [[ -n "$value" ]] && xfconf-query -c xsettings -p "$prop" -s "$value" 2>/dev/null || true
    done < "${BACKUP}/xfconf"
    [[ -s "${BACKUP}/mime-text" ]] && xdg-mime default "$(cat "${BACKUP}/mime-text")" text/plain || true
    local n target
    while IFS=$'\t' read -r n target; do
        as_root cp -a "${BACKUP}/root/${n}" "$target"
        as_root chown root:root "$target"
    done < "${BACKUP}/root-index"
    while read -r i; do
        [[ -n "$i" ]] && as_root rm -f "$i"
    done < "${BACKUP}/root-absent"
    [[ -s "${BACKUP}/xrandr.sh" ]] && sh "${BACKUP}/xrandr.sh" || true
    while IFS=$'\t' read -r i value; do
        [[ -n "$value" ]] && xinput set-prop "$i" "libinput Accel Speed" "$value" 2>/dev/null || true
    done < "${BACKUP}/accel"
    [[ -f "${HOME}/.Xresources" ]] && xrdb -merge "${HOME}/.Xresources" || true
    [[ -f "${HOME}/.fehbg" ]] && sh "${HOME}/.fehbg" || true
    pkill -USR1 -x sxhkd || true
    (cd "${HOME}/.config/ohmychadwm/chadwm" && make clean >/dev/null 2>&1) || true
    xdotool key --clearmodifiers super+shift+r || true
    log_success "Restored; Ohmychadwm restarted with the original bar"
}

main() {
    session_env
    pkill -f "ohmychadwm-tweak-tool[.]py" 2>/dev/null && log_warn "Closed the running app" || true
    backup
    trap 'restore' EXIT
    allow_pkexec
    log_section "Live test"
    OTT_OUT="$OUT" OTT_APP_DIR="$APP_DIR" timeout 1200 python3 "${SCRIPT_DIR}/live_ohmychadwm.py" \
        || log_error "live_ohmychadwm.py exited with $?"
    log_success "$(basename "$0") done — report ${OUT}/report.json, screenshots ${OUT}/shots"
}

main "$@"
