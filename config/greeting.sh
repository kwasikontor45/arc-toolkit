#!/bin/bash
# ~/.config/arc/greeting.sh — terminal greeting
# Sourced by .bashrc and .zshrc on shell start
# No sudo calls — process checks only for security stack

# Cached, bounded public-egress lookup. The cache is one fixed owner-only file;
# opening several shells does not repeatedly query the network.
_arc_greeting_public_ipv4() {
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/arc"
  local cache_file="$cache_dir/greeting-public-ip-v4" now cached_at='' cached_ip='' age fetched temp
  now=$(date +%s)
  if [[ -r "$cache_file" ]]; then
    IFS=' ' read -r cached_at cached_ip < "$cache_file" || true
  fi
  if [[ "$cached_at" =~ ^[0-9]+$ && "$cached_ip" =~ ^[0-9.]+$ ]]; then
    age=$((now - cached_at))
    if (( age >= 0 && age < 1800 )); then
      printf '%s\n' "$cached_ip"
      return 0
    fi
  else
    cached_at=''; cached_ip=''
  fi

  if command -v curl >/dev/null 2>&1; then
    fetched=$(curl -4fsS --connect-timeout 1 --max-time 2 https://checkip.amazonaws.com 2>/dev/null | tr -d '[:space:]')
    if [[ "$fetched" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] \
        && python3 -c 'import ipaddress,sys; raise SystemExit(ipaddress.ip_address(sys.argv[1]).version != 4)' "$fetched" 2>/dev/null; then
      if mkdir -p -m 700 "$cache_dir" 2>/dev/null; then
        chmod 700 "$cache_dir" 2>/dev/null || true
        temp=$(mktemp "$cache_dir/.greeting-ip.XXXXXX" 2>/dev/null || true)
        if [[ -n "$temp" ]]; then
          printf '%s %s\n' "$now" "$fetched" > "$temp"
          chmod 600 "$temp" 2>/dev/null || true
          mv -f -- "$temp" "$cache_file" 2>/dev/null || rm -f -- "$temp"
        fi
      fi
      printf '%s\n' "$fetched"
      return 0
    fi
  fi

  if [[ "$cached_ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] \
      && python3 -c 'import ipaddress,sys; raise SystemExit(ipaddress.ip_address(sys.argv[1]).version != 4)' "$cached_ip" 2>/dev/null; then
    printf '%s · cached\n' "$cached_ip"
  else
    printf 'unavailable\n'
  fi
}

# Shared, width-aware renderers for the architecture banner and status rows.
_arc_greeting_line() {
  local _text="$1" _color="$2" _width="${COLUMNS:-80}" _part
  [[ "$_width" =~ ^[0-9]+$ ]] || _width=$(tput cols 2>/dev/null || printf '80')
  (( _width >= 24 )) || _width=24
  while IFS= read -r _part; do
    printf '  %b%s%b\n' "$_color" "$_part" "$N"
  done < <(printf '%s\n' "$_text" | fmt -w "$((_width - 2))" -s | fold -w "$((_width - 2))" -s)
}

# The divider begins under the motto's E and ends under the last visible
# character of the wrapped LOCAL_TIME value (the phase name's final letter).
_arc_greeting_rule() {
  local _time_value="$1" _width="${COLUMNS:-80}" _value_width _start_col _last_line _end_col _dash_count _dashes
  [[ "$_width" =~ ^[0-9]+$ ]] || _width=$(tput cols 2>/dev/null || printf '80')
  (( _width >= 24 )) || _width=24
  if (( _width >= 52 )); then
    _value_width=$((_width - 20)); _start_col=19
  else
    _value_width=$((_width - 8)); _start_col=7
  fi
  (( _value_width >= 12 )) || _value_width=12
  _last_line=$(printf '%s\n' "$_time_value" | fmt -w "$_value_width" -s | fold -w "$_value_width" -s | tail -n 1)
  _end_col=$((_start_col - 1 + ${#_last_line}))
  _dash_count=$((_end_col - 4))
  (( _dash_count >= 0 )) || _dash_count=0
  _dashes=$(printf '%*s' "$_dash_count" '' | tr ' ' '-')
  printf '  %b#%s#%b\n' "$MUTED" "$_dashes" "$N"
}

_arc_greeting_section() {
  local _title="$1" _spaced="${2:-1}"
  (( _spaced )) && printf '\n'
  printf '  %b●%b  %b%s%b\n' "$ART" "$N" "$ART" "$_title" "$N"
}

# Key, value, and continuation columns stay aligned as the terminal narrows.
_arc_greeting_item() {
  local _label="$1" _text="$2" _color="${3:-$TEXT}"
  local _width="${COLUMNS:-80}" _line _first=1 _value_width _indent
  [[ "$_width" =~ ^[0-9]+$ ]] || _width=$(tput cols 2>/dev/null || printf '80')
  (( _width >= 24 )) || _width=24
  if [[ -n "$_label" && $_width -ge 52 ]]; then
    _value_width=$((_width - 20)); _indent='                  '
  elif [[ -n "$_label" ]]; then
    _value_width=$((_width - 8)); _indent='      '
  else
    _value_width=$((_width - 7)); _indent='     '
  fi
  (( _value_width >= 12 )) || _value_width=12
  while IFS= read -r _line; do
    if (( _first )); then
      if [[ -n "$_label" ]]; then
        if (( _width >= 52 )); then
          printf '  %b·%b  %b%-11s%b  %b%s%b\n' \
            "$C" "$N" "$ART" "$_label" "$N" "$_color" "$_line" "$N"
        else
          printf '  %b·%b  %b%s%b\n' "$C" "$N" "$ART" "$_label" "$N"
          printf '%s%b%s%b\n' "$_indent" "$_color" "$_line" "$N"
        fi
      else
        printf '  %b·%b  %b%s%b\n' "$C" "$N" "$_color" "$_line" "$N"
      fi
      _first=0
    else
      printf '%s%b%s%b\n' "$_indent" "$_color" "$_line" "$N"
    fi
  done < <(printf '%s\n' "$_text" | fmt -w "$_value_width" -s | fold -w "$_value_width" -s)
}

_arc_greeting() {
  # Canonical Circadian accents; copy stays readable on monochrome terminals.
  local G='\033[38;2;164;194;139m'
  local R='\033[38;2;234;154;151m'
  local Y='\033[38;2;246;193;119m'
  local D='\033[38;2;128;137;145m'
  local TEXT='\033[38;2;226;229;233m'
  local MUTED='\033[38;2;112;124;132m'
  local N='\033[0m'
  local CG='Recognize > construct > visualize > analyze > interpret'
  if [[ ! -t 1 || -n "${NO_COLOR:-}" || "${TERM:-dumb}" == dumb ]]; then
    G=''; R=''; Y=''; D=''; TEXT=''; MUTED=''; N=''
  fi

  # Circadian Canonical Hours and accents: Nyx 21–06, Choice 06–11,
  # Desire 11–17, Still-Pine 17–21. The mark carries the prior/current phase.
  local _h _phase C GOLD ART
  _h=$(date +%-H)
  if   (( _h >= 6 && _h < 11 )); then
    _phase='choice'
    C='\033[38;2;94;200;237m'; GOLD='\033[38;2;234;154;151m'; ART='\033[1;38;2;94;200;237m'
  elif (( _h >= 11 && _h < 17 )); then
    _phase='desire'
    C='\033[38;2;246;193;119m'; GOLD='\033[38;2;94;200;237m'; ART='\033[1;38;2;246;193;119m'
  elif (( _h >= 17 && _h < 21 )); then
    _phase='still-pine'
    C='\033[38;2;196;167;231m'; GOLD='\033[38;2;246;193;119m'; ART='\033[1;38;2;196;167;231m'
  else
    _phase='nyx'
    C='\033[38;2;234;154;151m'; GOLD='\033[38;2;196;167;231m'; ART='\033[1;38;2;234;154;151m'
  fi
  [[ -t 1 && -z "${NO_COLOR:-}" && "${TERM:-dumb}" != dumb ]] || { C=''; GOLD=''; ART=''; }

  local profile="${ARC_GREETING_PROFILE:-station}" host_name now session_state radar_label origin_name
  host_name=$(hostname -s 2>/dev/null || hostname 2>/dev/null || printf 'unknown-node')
  now=$(date '+%a, %d %b %Y · %H:%M:%S %Z')
  if [[ "$profile" == cloud ]]; then
    if [[ -n "${SSH_CONNECTION:-}" ]]; then session_state='[ SSH_SESSION_ACTIVE ]'
    else session_state='[ CLOUD_NODE_READY ]'; fi
    radar_label='REMOTE_RADAR'
    origin_name="${ARC_GREETING_TARGET:-AWS EC2} · $host_name"
  else
    session_state='[ STATION_READY ]'
    radar_label='LOCAL_RADAR'
    origin_name="$host_name · workstation"
  fi

  printf '  %bSYSTEM%b: %bARCHITECTURE_LOGS%b\n' "$ART" "$N" "$TEXT" "$N"
  printf '  %b%sSTATE%b: %bADAPTIVE_SYNC%b  %b☿⚕%b\n' "$C" "$_phase" "$N" "$ART" "$N" "$C"
  printf '             %b%s%b\n' "$GOLD" ')(  )(' "$N"
  printf '           %b%s%b\n' "$GOLD" '/  \  /  \' "$N"
  printf '          %b%s%b\n' "$GOLD" '| \      / |' "$N"
  printf '           %b%s%b\n' "$ART" '\ \    / /' "$N"
  printf '             %b%s%b\n' "$ART" '\\  //' "$N"
  printf '              %b%s%b\n' "$ART" '\/\/' "$N"
  if [[ "$profile" == cloud ]]; then
    _arc_greeting_item "$radar_label" "$session_state" "$G"
    _arc_greeting_item 'ORIGIN' "$origin_name" "$TEXT"
  else
    _arc_greeting_item 'LOCAL_RADAR' "$session_state" "$G"
    _arc_greeting_item 'EXT_IP' "$(_arc_greeting_public_ipv4)" "$TEXT"
  fi
  local time_value="$now · ${_phase}"
  _arc_greeting_item 'LOCAL_TIME' "$time_value" "$TEXT"
  _arc_greeting_line 'E Pluribus Unum  ·  ☠  ·  In God We Trust' "$C"
  _arc_greeting_rule "$time_value"

  _arc_greeting_section 'IDENTITY & INTENT' 0
  _arc_greeting_item 'IDENTITY' "lt · $(whoami) · arc" "$TEXT"
  _arc_greeting_item 'METHOD' "$CG" "$TEXT"
  # The local word helper is optional; the greeting still stands alone without it.
  if [[ "$profile" != cloud ]] && command -v arc >/dev/null 2>&1; then
    local word_line
    word_line=$(command arc word --compact 2>/dev/null || true)
    word_line=${word_line/ · adjective · / · adj. · }
    [[ -n "$word_line" ]] && _arc_greeting_item 'WOD' "$word_line" "$TEXT"
  fi

  # ── Principles and policy source ───────────────────────────────────────────
  local MOTD_FILE="$HOME/.config/arc/motd"
  if [[ -f "$MOTD_FILE" ]]; then
    local motd_line
    while IFS= read -r motd_line || [[ -n "$motd_line" ]]; do
      if [[ "$motd_line" == MO:* ]]; then
        if [[ "$profile" == cloud ]]; then
          _arc_greeting_item 'MO' 'workstation policy · local reference' "$MUTED"
        else
          _arc_greeting_item 'MO' "${motd_line#MO: }" "$TEXT"
        fi
      elif [[ "$motd_line" == *:* ]]; then
        _arc_greeting_item "${motd_line%%:*}" "${motd_line#*: }" "$TEXT"
      else
        _arc_greeting_item 'PRINCIPLES' "$motd_line" "$TEXT"
      fi
    done < "$MOTD_FILE"
  fi

  if [[ "$profile" == cloud ]]; then
    local cloud_mem_used cloud_mem_total cloud_disk cloud_uptime cloud_shell='bash'
    [[ -n "${ZSH_VERSION:-}" ]] && cloud_shell='zsh'
    cloud_mem_used=$(free -h | awk '/Mem:/ {print $3}')
    cloud_mem_total=$(free -h | awk '/Mem:/ {print $2}')
    cloud_disk=$(df -h / | awk 'NR==2 {print $3 " used / " $4 " free (" $5 ")"}')
    cloud_uptime=$(uptime -p 2>/dev/null || printf 'unknown')
    _arc_greeting_section 'OPERATIONS'
    _arc_greeting_item 'RAM' "${cloud_mem_used:-unknown} / ${cloud_mem_total:-unknown}" "$TEXT"
    _arc_greeting_item 'ROOT_FS' "${cloud_disk:-unknown}" "$TEXT"
    _arc_greeting_item 'UPTIME' "$cloud_uptime" "$TEXT"
    _arc_greeting_section 'SYSTEMS'
    _arc_greeting_item 'NODE' "$host_name · AWS EC2 · $(uname -sr 2>/dev/null || printf 'Linux')" "$TEXT"
    _arc_greeting_item 'SESSION' "$session_state · $cloud_shell" "$G"
    printf '\n'
    return
  fi

  # ── Compact local status ───────────────────────────────────────────────────
  local mem_used mem_free mem_total
  mem_used=$(free -h | awk '/Mem:/ {print $3}')
  mem_free=$(free -h | awk '/Mem:/ {print $7}')
  mem_total=$(free -h | awk '/Mem:/ {print $2}')

  local LT_FOCUS="$HOME/.local/share/lt/focus" focus="—"
  [[ -s "$LT_FOCUS" ]] && focus=$(cat "$LT_FOCUS")
  local LT_TASKS="$HOME/.local/share/lt/tasks" pending=0 tasks_text tasks_color
  if [[ -f "$LT_TASKS" ]]; then
    pending=$(grep -c '^pending ' "$LT_TASKS" 2>/dev/null || true)
    pending=${pending:-0}
  fi
  tasks_text='clear'; tasks_color="$G"
  if (( pending > 0 )); then tasks_text="${pending} pending"; tasks_color="$Y"; fi

  # Timeshift cache is the same source used by the dedicated status row.
  local STAMP="/var/cache/timeshift-last-snapshot" snap_text snap_color
  local snap_date last_epoch now_epoch days_ago
  if [[ -f "$STAMP" ]]; then
    snap_date=$(grep -oP '\d{4}-\d{2}-\d{2}' "$STAMP" 2>/dev/null | head -1)
    last_epoch=$(date -d "$snap_date" +%s 2>/dev/null || echo 0)
    now_epoch=$(date +%s)
    days_ago=$(( (now_epoch - last_epoch) / 86400 ))
    if (( days_ago >= 1 )); then snap_text="${days_ago}d · arc snap"; snap_color="$Y"
    else snap_text='today ✓'; snap_color="$G"; fi
  else
    snap_text='none · arc snap'; snap_color="$Y"
  fi

  # SOP status — fast sqlite3 + grep, no subprocess overhead
  local sop_today sop_ack_count sop_gp_ok sop_ack_str sop_gp_str
  sop_today=$(date '+%Y-%m-%d')
  sop_ack_count=0
  if command -v python3 &>/dev/null && [[ -f "$HOME/.config/arc/sop/arc-sop.db" ]]; then
    sop_ack_count=$(python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('$HOME/.config/arc/sop/arc-sop.db')
    print(conn.execute(\"SELECT COUNT(*) FROM acks WHERE timestamp LIKE ?\", ('${sop_today}%',)).fetchone()[0])
except Exception:
    print(0)
" 2>/dev/null || echo 0)
  fi
  local sop_gp_ok=0
  grep -q "${sop_today}.*\[STARTING\]" "$HOME/dev-notes/intel-ops/GAMEPLAN.md" 2>/dev/null && sop_gp_ok=1
  sop_ack_str='acked'; sop_ack_color="$G"
  (( sop_ack_count > 0 )) || { sop_ack_str='no ack'; sop_ack_color="$Y"; }
  sop_gp_str='plan ✓'; sop_gp_color="$G"
  (( sop_gp_ok )) || { sop_gp_str='no plan'; sop_gp_color="$Y"; }

  # VPN/DNS checks are local and read-only; no state is changed.
  local vpn_ip vpn_text vpn_color dns_text dns_color
  vpn_ip=$(ip -br addr show proton0 2>/dev/null | awk '{print $3}' | cut -d/ -f1)
  if [[ -n "$vpn_ip" ]]; then vpn_text="up ${vpn_ip}"; vpn_color="$G"
  else vpn_text='down · arc vpn connect'; vpn_color="$Y"; fi
  if systemctl is-active --quiet nextdns 2>/dev/null; then dns_text='NextDNS'; dns_color="$G"
  else dns_text='local · arc dns on'; dns_color="$Y"; fi

  local ufw_text ufw_color f2b_text f2b_color aa_text aa_color luks_text luks_color
  if systemctl is-active --quiet ufw 2>/dev/null; then ufw_text='✓'; ufw_color="$G"; else ufw_text='✗'; ufw_color="$R"; fi
  if pgrep -x 'fail2ban-server' &>/dev/null; then f2b_text='✓'; f2b_color="$G"; else f2b_text='✗'; f2b_color="$R"; fi
  if systemctl is-active --quiet apparmor 2>/dev/null; then aa_text='✓'; aa_color="$G"; else aa_text='✗'; aa_color="$R"; fi
  if [[ -b /dev/mapper/storage_crypt ]]; then
    if ls /mnt/storage/ >/dev/null 2>&1; then luks_text='open'; luks_color="$G"; else luks_text='stale'; luks_color="$Y"; fi
  else luks_text='closed'; luks_color="$D"; fi

  local local_ip
  local_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  local_ip=${local_ip:-offline}

  # Storage checks include actual mount I/O to avoid reporting a stale mount as healthy.
  local usb_text fortress_text uu uf fu ff
  if mountpoint -q /mnt/storage 2>/dev/null && ls /mnt/storage/ >/dev/null 2>&1; then
    uu=$(df -h /mnt/storage | awk 'NR==2 {print $3}')
    uf=$(df -h /mnt/storage | awk 'NR==2 {print $4}')
    usb_text="${uu} used / ${uf} free"; usb_color="$TEXT"
  elif mountpoint -q /mnt/storage 2>/dev/null; then usb_text='stale · arc mount'; usb_color="$Y"
  else usb_text='not mounted'; usb_color="$D"; fi
  if mountpoint -q /fortress 2>/dev/null && ls /fortress/ >/dev/null 2>&1; then
    fu=$(df -h /fortress | awk 'NR==2 {print $3}')
    ff=$(df -h /fortress | awk 'NR==2 {print $4}')
    fortress_text="${fu} used / ${ff} free"; fortress_color="$TEXT"
  elif mountpoint -q /fortress 2>/dev/null; then fortress_text='stale'; fortress_color="$Y"
  else fortress_text='not mounted'; fortress_color="$D"; fi

  local disk_used disk_free disk_pct sw_used sw_total shell_name shell_ver omz_tag=''
  disk_used=$(df -h / | awk 'NR==2 {print $3}')
  disk_free=$(df -h / | awk 'NR==2 {print $4}')
  disk_pct=$(df / | awk 'NR==2 {print $5}')
  sw_used=$(free -h | awk '/Swap:/ {print $3}')
  sw_total=$(free -h | awk '/Swap:/ {print $2}')
  shell_name=$(basename "${SHELL:-zsh}")
  shell_ver=$("$SHELL" --version 2>/dev/null | head -1 | awk '{print $2}' | cut -d. -f1,2)
  [[ -d "$HOME/.oh-my-zsh" ]] && omz_tag='/omz'

  local ts_name ts_date ts_manual ts_tag
  ts_date='none'; ts_tag='auto'
  if [[ -f /var/cache/timeshift-last-snapshot ]]; then
    ts_name=$(cat /var/cache/timeshift-last-snapshot 2>/dev/null)
    ts_date=$(grep -oP '\d{4}-\d{2}-\d{2}' <<<"$ts_name" | head -1)
    [[ -f /var/cache/timeshift-last-run-manual ]] && ts_manual=$(tr -d '[:space:]' < /var/cache/timeshift-last-run-manual)
    [[ "$ts_manual" == '1' ]] && ts_tag='manual'
    [[ -n "$ts_date" ]] || ts_date='unknown'
  fi

  _arc_greeting_section 'OPERATIONS'
  _arc_greeting_item 'RAM' "${mem_used}/${mem_total} used · ${mem_free} free" "$TEXT"
  _arc_greeting_item 'FOCUS' "${focus}" "$TEXT"
  _arc_greeting_item 'TASKS' "${tasks_text}" "${tasks_color}"
  local ops_color="$snap_color"
  [[ "$sop_ack_str" == acked && "$sop_gp_str" == 'plan ✓' ]] || ops_color="$Y"
  _arc_greeting_item 'SNAP' "${snap_text} · SOP ${sop_ack_str} · ${sop_gp_str} · TS ${ts_date} ${ts_tag}" "$ops_color"

  _arc_greeting_section 'SYSTEMS'
  local network_color="$vpn_color"
  [[ "$dns_color" == "$Y" ]] && network_color="$Y"
  _arc_greeting_item 'NET' "VPN ${vpn_text} · DNS ${dns_text}" "$network_color"
  local security_color="$G"
  [[ "$ufw_text$f2b_text$aa_text" == *✗* ]] && security_color="$R"
  [[ "$luks_text" == stale ]] && security_color="$R"
  _arc_greeting_item 'SEC' "UFW ${ufw_text} · F2B ${f2b_text} · AA ${aa_text} · LUKS ${luks_text}" "$security_color"
  _arc_greeting_item 'LOCAL_IP' "$local_ip" "$TEXT"
  local storage_color="$C"
  [[ "$usb_color" == "$Y" || "$fortress_color" == "$Y" ]] && storage_color="$Y"
  [[ "$usb_color" == "$D" && "$fortress_color" == "$D" ]] && storage_color="$D"
  _arc_greeting_item 'STORE' "USB ${usb_text} · Fortress ${fortress_text}" "$storage_color"
  _arc_greeting_item 'HOST' "disk ${disk_used}/${disk_free} free (${disk_pct}) · swap ${sw_used}/${sw_total} · shell ${shell_name} ${shell_ver}${omz_tag}" "$TEXT"
  printf '\n'
}
