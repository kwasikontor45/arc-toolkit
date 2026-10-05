#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
home=${HOME:?HOME is not set}
opt_root=${XDG_DATA_HOME:-"$home/.local/share"}/applications
install_root="$home/.local/opt/arc-break-taskbar"
bin_root="$home/.local/bin"
autostart_root="${XDG_CONFIG_HOME:-$home/.config}/autostart"
unit_root="${XDG_CONFIG_HOME:-$home/.config}/systemd/user"
desktop_file="$opt_root/arc-break.desktop"
old_desktop_file="$opt_root/arc-break-taskbar.desktop"

if ! /usr/bin/python3 -c 'import gi; gi.require_version("Gtk", "3.0")' >/dev/null 2>&1; then
  printf '%s\n' 'Missing GTK 3 Python bindings.' \
    'On Debian or Ubuntu: sudo apt install python3-gi gir1.2-gtk-3.0'
  exit 1
fi
if [ -e "$bin_root/arc-break-taskbar" ] && ! grep -Fq 'arc_break_taskbar.py' "$bin_root/arc-break-taskbar"; then
  if grep -Fq "$home/.local/opt/arc-break-taskbar/arc_break_tray.py" "$bin_root/arc-break-taskbar"; then
    rm -f "$bin_root/arc-break-taskbar"
  else
    printf '%s\n' "$bin_root/arc-break-taskbar already exists and is not this app; refusing to overwrite it." >&2
    exit 1
  fi
fi
if [ -L "$opt_root/arc-break.desktop" ]; then
  printf '%s\n' "$opt_root/arc-break.desktop is a symlink; refusing to replace its target." >&2
  exit 1
fi

mkdir -p "$install_root" "$opt_root" "$bin_root"
if [ -f "$old_desktop_file" ] && { grep -Fq "Exec=\"$install_root/arc_break_taskbar.py\"" "$old_desktop_file" || grep -Fq "Exec=\"$install_root/arc_break_tray.py\"" "$old_desktop_file"; }; then
  rm -f "$old_desktop_file"
fi
rm -f "$install_root/arc_break_tray.py"
if [ -f "$desktop_file" ] && [ ! -f "$install_root/arc-break.desktop.previous" ]; then
  cp -p "$desktop_file" "$install_root/arc-break.desktop.previous"
fi
install -m 0755 "$script_dir/arc_break_taskbar.py" "$install_root/arc_break_taskbar.py"
install -m 0644 "$script_dir/README.md" "$install_root/README.md"
install -m 0644 "$script_dir/icon.png" "$install_root/icon.png"
mkdir -p "$unit_root"
install -m 0644 "$script_dir/arc-break-taskbar.service" "$unit_root/arc-break-taskbar.service"
if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload >/dev/null 2>&1 || true
fi
cat > "$desktop_file" <<EOF
[Desktop Entry]
Type=Application
Name=Arc Break
Comment=Start a small focus and rest timer in the taskbar
Exec="$install_root/arc_break_taskbar.py"
Icon=$install_root/icon.png
Terminal=false
Categories=Utility;Clock;
StartupNotify=true
EOF
chmod 0644 "$desktop_file"
cat > "$bin_root/arc-break-taskbar" <<EOF
#!/bin/sh
exec "$install_root/arc_break_taskbar.py" "\$@"
EOF
chmod 0755 "$bin_root/arc-break-taskbar"
mkdir -p "$autostart_root"
resume_file="$autostart_root/arc-break-resume.desktop"
if [ -f "$resume_file" ] && [ ! -f "$install_root/arc-break-resume.desktop.previous" ]; then
  cp -p "$resume_file" "$install_root/arc-break-resume.desktop.previous"
fi
cat > "$resume_file" <<EOF
[Desktop Entry]
Type=Application
Name=Arc Break (resume active timer)
Comment=Resume the saved focus/rest timer after login; explicit Stop stays stopped
Exec="$install_root/arc_break_taskbar.py" --resume-only
Icon=$install_root/icon.png
X-GNOME-Autostart-Delay=5
NoDisplay=false
EOF
chmod 0644 "$resume_file"
printf 'Installed Arc Break in %s\nLauncher: %s\nCommand: %s/arc-break-taskbar\n' \
  "$install_root" "$desktop_file" "$bin_root"
