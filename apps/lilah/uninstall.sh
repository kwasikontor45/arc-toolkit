#!/bin/sh
# uninstall.sh — remove Vagabond app files; preserves settings/state.
set -eu
home=${HOME:?HOME is not set}
opt_root=${XDG_DATA_HOME:-"$home/.local/share"}/applications
install_root="$home/.local/opt/lilah"
autostart_root="${XDG_CONFIG_HOME:-$home/.config}/autostart"
unit_root="${XDG_CONFIG_HOME:-$home/.config}/systemd/user"

systemctl --user stop lilah.service >/dev/null 2>&1 || true
rm -f "$opt_root/studio.kontor.Lilah.desktop" \
      "$autostart_root/lilah-resume.desktop" \
      "$home/.local/bin/lilah" \
      "$unit_root/lilah.service"
rm -rf "$install_root"
systemctl --user daemon-reload >/dev/null 2>&1 || true
printf '%s\n' 'Lilah app files removed. Settings/state preserved at ~/.config/lilah and ~/.local/state/lilah.'
