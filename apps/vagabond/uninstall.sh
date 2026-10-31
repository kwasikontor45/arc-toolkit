#!/bin/sh
# uninstall.sh — remove Vagabond app files; preserves settings/state.
set -eu
home=${HOME:?HOME is not set}
opt_root=${XDG_DATA_HOME:-"$home/.local/share"}/applications
install_root="$home/.local/opt/vagabond"
autostart_root="${XDG_CONFIG_HOME:-$home/.config}/autostart"
unit_root="${XDG_CONFIG_HOME:-$home/.config}/systemd/user"

systemctl --user stop vagabond.service >/dev/null 2>&1 || true
rm -f "$opt_root/studio.kontor.Vagabond.desktop" \
      "$autostart_root/vagabond-resume.desktop" \
      "$home/.local/bin/vagabond" \
      "$unit_root/vagabond.service"
rm -rf "$install_root"
systemctl --user daemon-reload >/dev/null 2>&1 || true
printf '%s\n' 'Vagabond app files removed. Settings/state preserved at ~/.config/vagabond and ~/.local/state/vagabond.'
