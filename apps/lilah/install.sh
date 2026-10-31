#!/bin/sh
# install.sh — install Lilah (circadian timepiece). No network, no root.
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
home=${HOME:?HOME is not set}
opt_root=${XDG_DATA_HOME:-"$home/.local/share"}/applications
install_root="$home/.local/opt/lilah"
bin_root="$home/.local/bin"
autostart_root="${XDG_CONFIG_HOME:-$home/.config}/autostart"
unit_root="${XDG_CONFIG_HOME:-$home/.config}/systemd/user"
desktop_file="$opt_root/studio.kontor.Lilah.desktop"
resume_file="$autostart_root/lilah-resume.desktop"
legacy_opt="$home/.local/opt/arc-break-taskbar"
legacy2_opt="$home/.local/opt/vagabond"

if ! /usr/bin/python3 -c 'import gi; gi.require_version("Gtk", "3.0")' >/dev/null 2>&1; then
  printf '%s\n' 'Missing GTK 3 Python bindings.' \
    'On Debian or Ubuntu: sudo apt install python3-gi gir1.2-gtk-3.0'
  exit 1
fi
shared_ui="$script_dir/../../bin/_arc_ui.py"
if [ ! -f "$shared_ui" ]; then
  printf '%s\n' "Missing shared circadian UI engine: $shared_ui" >&2
  exit 1
fi

mkdir -p "$install_root" "$opt_root" "$bin_root"

# migrate existing settings/state so the timepiece keeps its memory
for pair in "arc-break-taskbar vagabond" "vagabond lilah"; do
  set -- $pair
  for base in ".config" ".local/state"; do
    old="$home/$base/$1"; new="$home/$base/$2"
    if [ -d "$old" ] && [ ! -d "$new" ]; then
      mv "$old" "$new"
      printf 'migrated %s -> %s\n' "$old" "$new"
    fi
  done
done

# legacy cleanup: old install, launchers, desktop entries, units
rm -rf "$legacy_opt" "$legacy2_opt"
rm -f "$bin_root/arc-break-taskbar" "$bin_root/vagabond"
rm -f "$opt_root/arc-break.desktop" "$opt_root/arc-break-taskbar.desktop" \
      "$opt_root/studio.kontor.Vagabond.desktop" \
      "$autostart_root/arc-break-resume.desktop" "$autostart_root/vagabond-resume.desktop"
rm -f "$unit_root/arc-break-taskbar.service" "$unit_root/lilah.service"
rm -f "$install_root/arc-break.desktop.previous" "$install_root/arc-break-resume.desktop.previous"

install -m 0755 "$script_dir/lilah.py" "$install_root/lilah.py"
install -m 0644 "$script_dir/README.md" "$install_root/README.md"
install -m 0644 "$script_dir/mechanical-timer.svg" "$install_root/mechanical-timer.svg"
install -m 0644 "$shared_ui" "$install_root/_arc_ui.py"

install -m 0644 "$script_dir/lilah.service" "$unit_root/lilah.service"
command -v systemctl >/dev/null 2>&1 && systemctl --user daemon-reload >/dev/null 2>&1 || true

cat > "$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=Lilah
Comment=Circadian timepiece — a small focus and rest timer in the taskbar
Exec="$install_root/lilah.py"
Icon=/home/architect-of-chaos/.local/share/icons/khaos-brand/lilah.png
Terminal=false
Categories=Utility;Clock;X-KhaosLab;
StartupNotify=true
EOF
chmod 0644 "$desktop_file"

cat > "$bin_root/lilah" <<EOF
#!/bin/sh
exec "$install_root/lilah.py" "\$@"
EOF
chmod 0755 "$bin_root/lilah"

cat > "$resume_file" <<EOF
[Desktop Entry]
Type=Application
Name=Lilah (resume active timer)
Comment=Resume the saved focus/rest timer after login; explicit Stop stays stopped
Exec="$install_root/lilah.py" --resume-only
Icon=/home/architect-of-chaos/.local/share/icons/khaos-brand/lilah.png
X-GNOME-Autostart-Delay=5
NoDisplay=true
EOF
chmod 0644 "$resume_file"

printf 'Installed Lilah in %s\nLauncher: %s\nCommand: %s/lilah\n' \
  "$install_root" "$desktop_file" "$bin_root"
