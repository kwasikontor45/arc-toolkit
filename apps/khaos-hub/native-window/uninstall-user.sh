#!/usr/bin/env bash
set -euo pipefail
readonly data_root="${XDG_DATA_HOME:-$HOME/.local/share}/khaos-hub-native"
readonly app_dir="$data_root/app"
readonly state_root="${XDG_STATE_HOME:-$HOME/.local/state}/khaos-hub-native"
readonly launcher="${XDG_BIN_HOME:-$HOME/.local/bin}/khaos-hub-window"
readonly desktop="$HOME/.local/share/applications/khaos-hub.desktop"
readonly theme_icon="$HOME/.local/share/icons/hicolor/512x512/apps/khaos-hub.png"
backup="$(find "$state_root/backups" -maxdepth 1 -type f -name 'khaos-hub-window-*.sh' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)"
desktop_backup="$(find "$state_root/backups" -maxdepth 1 -type f -name 'khaos-hub.desktop-*' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)"
if [[ -n "$backup" ]]; then install -m 700 "$backup" "$launcher"; else rm -f -- "$launcher"; fi
rm -rf -- "$app_dir"
rm -f -- "$theme_icon"
if [[ -n "$desktop_backup" ]]; then install -m 644 "$desktop_backup" "$desktop"; fi
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
printf 'Removed native package and restored launcher backup: %s\n' "${backup:-none}"
