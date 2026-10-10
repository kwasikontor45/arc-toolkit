#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin"
export HOME="$tmp/home"
mkdir -p "$HOME/.config/arc"
cat > "$HOME/.config/arc/home-ip-sync.conf" <<'CONF'
ssid=eero-home
gateway=192.168.4.1
CONF

cat > "$tmp/bin/ip" <<'SH'
#!/usr/bin/env bash
if [[ "$*" == "-4 route get 1.1.1.1" ]]; then
  echo '1.1.1.1 dev wlan0 src 192.168.4.144'
elif [[ "$*" == "-4 route show default dev wlan0" ]]; then
  echo 'default via 192.168.4.1 dev wlan0 proto dhcp'
elif [[ "$*" == "-o link show" && -n "${TEST_TUNNEL_IFACE:-}" ]]; then
  echo "3: ${TEST_TUNNEL_IFACE}: <POINTOPOINT,UP>"
fi
SH
cat > "$tmp/bin/nmcli" <<'SH'
#!/usr/bin/env bash
if [[ "$*" == "-g GENERAL.TYPE device show wlan0" ]]; then
  echo wifi
elif [[ "$*" == "-g GENERAL.CONNECTION device show wlan0" ]]; then
  echo home-wifi
elif [[ "$*" == "-g 802-11-wireless.ssid connection show home-wifi" ]]; then
  echo "${TEST_SSID:-eero-home}"
fi
SH
cat > "$tmp/bin/nextdns" <<'SH'
#!/usr/bin/env bash
echo "${TEST_NEXTDNS:-running} (test fixture)"
SH
cat > "$tmp/bin/awk" <<'SH'
#!/usr/bin/env bash
# The fixture models a DHCP resolver rather than the workstation's live local proxy.
if [[ "$*" == -F* ]]; then
  exec /usr/bin/awk "$@"
fi
exit 0
SH
chmod +x "$tmp/bin/"*
PATH="$tmp/bin:$PATH"
export PATH

FINDINGS=()
note() { FINDINGS+=("$1"); }
aws_config_touched=0
_aws_lab_conf_quiet() { aws_config_touched=1; return 0; }
source <(sed -n '/^check_aws_lab_ip_drift()/,/^}/p' "$root/bin/arc-heal")
check_aws_lab_ip_drift || true

result="${FINDINGS[*]}"
[[ "$result" == *"custom DNS is active"* ]]
[[ "$aws_config_touched" == 0 ]]
echo 'pinned eero Wi-Fi plus active NextDNS: deferred before AWS access'

FINDINGS=()
TEST_SSID=coffee-shop TEST_NEXTDNS=stopped
export TEST_SSID TEST_NEXTDNS
check_aws_lab_ip_drift || true
result="${FINDINGS[*]}"
[[ "$result" == *"does not match the pinned home eero network"* ]]
[[ "$aws_config_touched" == 0 ]]
echo 'other Wi-Fi SSID: deferred before AWS access'

FINDINGS=()
TEST_SSID=eero-home TEST_NEXTDNS=stopped
export TEST_SSID TEST_NEXTDNS
http_proxy=http://proxy.invalid:8080
export http_proxy
check_aws_lab_ip_drift || true
result="${FINDINGS[*]}"
[[ "$result" == *"VPN, tunnel, or proxy detected"* ]]
[[ "$aws_config_touched" == 0 ]]
unset http_proxy
echo 'HTTP proxy configured: deferred before AWS access'

FINDINGS=()
TEST_SSID=eero-home TEST_NEXTDNS=stopped
export TEST_SSID TEST_NEXTDNS
TEST_TUNNEL_IFACE=proton0
export TEST_TUNNEL_IFACE
check_aws_lab_ip_drift || true
result="${FINDINGS[*]}"
[[ "$result" == *"interfaces proton0"* ]]
[[ "$aws_config_touched" == 0 ]]
unset TEST_TUNNEL_IFACE
echo 'VPN interface present on Wi-Fi route: deferred before AWS access'

FINDINGS=()
TEST_SSID=eero-home TEST_NEXTDNS=stopped
export TEST_SSID TEST_NEXTDNS
_aws_lab_conf_quiet() { aws_config_touched=1; return 1; }
check_aws_lab_ip_drift || true
[[ "$aws_config_touched" == 1 ]]
echo 'pinned home Wi-Fi with VPN/DNS inactive: reached AWS preflight only'
