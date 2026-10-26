#!/usr/bin/env bash
set -euo pipefail
readonly source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly data_root="${XDG_DATA_HOME:-$HOME/.local/share}/khaos-hub-native"
readonly app_dir="$data_root/app"
readonly state_root="${XDG_STATE_HOME:-$HOME/.local/state}/khaos-hub-native"
readonly bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
readonly launcher="$bin_dir/khaos-hub-window"
readonly desktop="$HOME/.local/share/applications/khaos-hub.desktop"
readonly theme_icon_dir="$HOME/.local/share/icons/hicolor/512x512/apps"
readonly stamp="$(date +%Y%m%dT%H%M%S)"
[[ -r "$source_dir/app.py" && -r "$source_dir/launch" && -r "$source_dir/runtime/girepository-1.0/WebKit2-4.1.typelib" ]] || { echo 'Native package source is incomplete.' >&2; exit 1; }
install -d -m 700 "$app_dir" "$state_root/backups" "$(dirname "$launcher")"
install -d -m 755 "$theme_icon_dir"
if [[ -e "$launcher" ]]; then install -m 600 "$launcher" "$state_root/backups/khaos-hub-window-$stamp.sh"; fi
if [[ -f "$desktop" ]]; then install -m 600 "$desktop" "$state_root/backups/khaos-hub.desktop-$stamp"; fi
stage="$(mktemp -d "${TMPDIR:-/tmp}/khaos-hub-native-install.XXXXXX")"
trap 'rm -rf -- "$stage"' EXIT
cp -a "$source_dir/." "$stage/"
chmod 700 "$stage/launch" "$stage/install-user.sh" "$stage/uninstall-user.sh"
chmod 700 "$stage/app.py"
rm -rf -- "$app_dir/runtime" "$app_dir/app.py" "$app_dir/launch" "$app_dir/README.md" "$app_dir/icon-kimi-round-512.png" "$app_dir/icon-kimi-64.bmp" "$app_dir/icon-kimi-64.rgba" "$app_dir/install-user.sh" "$app_dir/uninstall-user.sh" "$app_dir/tests"
cp -a "$stage/." "$app_dir/"
install -m 644 "$app_dir/icon-kimi-round-512.png" "$theme_icon_dir/khaos-hub.png"
cat > "$launcher.tmp" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec "$app_dir/launch" "\$@"
EOF
chmod 700 "$launcher.tmp"
mv -f -- "$launcher.tmp" "$launcher"
if [[ -f "$desktop" ]]; then
  python3 - "$desktop" "$app_dir/icon-kimi-round-512.png" <<'PYDESKTOP'
from pathlib import Path
import sys
p=Path(sys.argv[1]); out=[]
for line in p.read_text().splitlines():
    if line.startswith('Icon='): line='Icon='+sys.argv[2]
    elif line.startswith('StartupWMClass='): line='StartupWMClass=KhaosHub'
    out.append(line)
p.write_text('\n'.join(out)+'\n')
PYDESKTOP
fi
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
printf 'Installed per-user Khaos Hub native window at %s\n' "$app_dir"
