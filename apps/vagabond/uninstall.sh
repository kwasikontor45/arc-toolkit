#!/bin/sh
set -eu
home=${HOME:?HOME is not set}
install_root="$home/.local/opt/arc-break-taskbar"
desktop_root=${XDG_DATA_HOME:-"$home/.local/share"}/applications
bin_root="$home/.local/bin"
desktop_file="$desktop_root/arc-break.desktop"
backup_file="$install_root/arc-break.desktop.previous"
old_desktop_file="$desktop_root/arc-break-taskbar.desktop"
resume_file="${XDG_CONFIG_HOME:-$home/.config}/autostart/arc-break-resume.desktop"
unit_file="${XDG_CONFIG_HOME:-$home/.config}/systemd/user/arc-break-taskbar.service"
if [ -f "$unit_file" ] && grep -Fq 'Arc Break taskbar timer' "$unit_file"; then
  systemctl --user stop arc-break-taskbar.service 2>/dev/null || true
  rm -f "$unit_file"
  systemctl --user daemon-reload 2>/dev/null || true
fi
if [ -f "$resume_file" ] && grep -Fq "$install_root/arc_break_taskbar.py" "$resume_file"; then
  if [ -f "$install_root/arc-break-resume.desktop.previous" ]; then
    cp -p "$install_root/arc-break-resume.desktop.previous" "$resume_file"
  else
    rm -f "$resume_file"
  fi
fi
exec_line="Exec=\"$install_root/arc_break_taskbar.py\""
if [ -f "$backup_file" ]; then
  if [ ! -L "$desktop_file" ] && [ -f "$desktop_file" ] && grep -Fq "$exec_line" "$desktop_file"; then
    cp -p "$backup_file" "$desktop_file"
  else
    printf '%s\n' 'The Arc Break desktop entry changed after installation; left it untouched.'
  fi
else
  if [ -f "$desktop_file" ] && grep -Fq "$exec_line" "$desktop_file"; then
    rm -f "$desktop_file"
  fi
fi
if [ -f "$old_desktop_file" ] && { grep -Fq "$exec_line" "$old_desktop_file" || grep -Fq "Exec=\"$install_root/arc_break_tray.py\"" "$old_desktop_file"; }; then
  rm -f "$old_desktop_file"
fi
if [ -f "$bin_root/arc-break-taskbar" ] && grep -Fq 'arc_break_taskbar.py' "$bin_root/arc-break-taskbar"; then
  rm -f "$bin_root/arc-break-taskbar"
fi
rm -rf -- "$install_root"
printf '%s\n' 'Arc Break app files removed; the prior desktop launcher was restored. Timer settings/state were preserved.'
