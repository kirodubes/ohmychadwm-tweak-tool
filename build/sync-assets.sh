#!/bin/bash
set -euo pipefail
#####################################################################
# Author    : Erik Dubois
# Website   : https://kiroproject.be
#####################################################################
#
#   DO NOT JUST RUN THIS. EXAMINE AND JUDGE. RUN AT YOUR OWN RISK.
#
#   Purpose:
#   - Fetch the Kiro wallpaper as pushed to kiro-system-files on GitHub
#     and, when it differs, replace the app's own copy and regenerate
#     the Kiro look's Themes thumbnail. up.sh runs it before committing.
#
#   Why: the app ships a copy of the Kiro wallpaper for systems without
#   kiro-system-files (pure Arch); fetching it on every up keeps that
#   copy and its thumbnail in sync with the real one.
#
#####################################################################

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname -- "${SCRIPT_DIR}")"
WALLPAPER_URL="https://raw.githubusercontent.com/kirodubes/kiro-system-files/main/usr/share/backgrounds/kiro/kiro-wallpaper.jpg"
WALLPAPER_COPY="${REPO_DIR}/usr/share/backgrounds/ohmychadwm-tweak-tool/kiro-wallpaper.jpg"
THUMB="${REPO_DIR}/usr/share/ohmychadwm-tweak-tool/thumbs/kiro.jpg"

#####################################################################
# Colors
#####################################################################
if command -v tput >/dev/null 2>&1 && [[ -t 1 ]]; then
    RED="$(tput setaf 1)"
    GREEN="$(tput setaf 2)"
    YELLOW="$(tput setaf 3)"
    BLUE="$(tput setaf 4)"
    CYAN="$(tput setaf 6)"
    RESET="$(tput sgr0)"
else
    RED="" GREEN="" YELLOW="" BLUE="" CYAN="" RESET=""
fi

#####################################################################
# Logging
#####################################################################
log_section() {
    echo
    echo "${GREEN}############################################################################${RESET}"
    echo "$1"
    echo "${GREEN}############################################################################${RESET}"
    echo
}

log_info() {
    echo
    echo "${BLUE}############################################################################${RESET}"
    echo "$1"
    echo "${BLUE}############################################################################${RESET}"
    echo
}

log_warn() {
    echo
    echo "${YELLOW}############################################################################${RESET}"
    echo "$1"
    echo "${YELLOW}############################################################################${RESET}"
    echo
}

log_error() {
    echo
    echo "${RED}############################################################################${RESET}"
    echo "$1"
    echo "${RED}############################################################################${RESET}"
    echo
}

log_success() {
    echo
    echo "${GREEN}############################################################################${RESET}"
    echo "$1"
    echo "${GREEN}############################################################################${RESET}"
    echo
}

#####################################################################
# Error handling
#####################################################################
on_error() {
    local lineno="$1"
    local cmd="$2"
    echo
    echo "${RED}ERROR on line ${lineno}: ${cmd}${RESET}"
    echo
    sleep 10
}

trap 'on_error "$LINENO" "$BASH_COMMAND"' ERR

#####################################################################
# Functions
#####################################################################
sync_kiro_wallpaper() {
    local tmp
    tmp="$(mktemp)"
    # shellcheck disable=SC2064
    trap "rm -f '${tmp}'" RETURN

    if ! curl -fsSL -o "${tmp}" "${WALLPAPER_URL}"; then
        log_warn "Could not fetch the Kiro wallpaper — keeping the current copy"
        return 0
    fi

    if cmp -s "${tmp}" "${WALLPAPER_COPY}"; then
        log_info "Kiro wallpaper already in sync"
        return 0
    fi

    install -Dm644 "${tmp}" "${WALLPAPER_COPY}"
    log_section "Kiro wallpaper updated from kiro-system-files"

    if command -v magick >/dev/null 2>&1; then
        # same size and stretch as the other Themes thumbnails (CLAUDE.md)
        magick "${WALLPAPER_COPY}" -resize "300x169!" -strip -quality 82 "${THUMB}"
        log_info "Thumbnail thumbs/kiro.jpg regenerated"
    else
        log_warn "imagemagick missing — regenerate thumbs/kiro.jpg by hand"
    fi
}

main() {
    sync_kiro_wallpaper
    log_success "$(basename "$0") done"
}

main "$@"
