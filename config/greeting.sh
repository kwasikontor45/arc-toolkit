#!/bin/bash
# ~/.config/arc/greeting.sh — terminal greeting
# Sourced by .bashrc and .zshrc on shell start
# No sudo calls — process checks only for security stack

# Cached, bounded public-egress lookup. The cache is one fixed owner-only file;
# opening several shells does not repeatedly query the network.
_arc_greeting_public_ipv4() {
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/arc"
  local cache_file="$cache_dir/greeting-public-ip-v4" now cached_at='' cached_scope='' cached_ip='' age fetched temp
  local scope="${1:-direct}" ttl=1800
  [[ "$scope" == vpn ]] || scope='direct'
  [[ "$scope" == vpn ]] && ttl=300
  now=$(date +%s)
  if [[ -r "$cache_file" ]]; then
    IFS=' ' read -r cached_at cached_scope cached_ip < "$cache_file" || true
  fi
  if [[ "$cached_at" =~ ^[0-9]+$ && "$cached_scope" == "$scope" && "$cached_ip" =~ ^[0-9.]+$ ]]; then
    age=$((now - cached_at))
    if (( age >= 0 && age < ttl )); then
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
          printf '%s %s %s\n' "$now" "$scope" "$fetched" > "$temp"
          chmod 600 "$temp" 2>/dev/null || true
          mv -f -- "$temp" "$cache_file" 2>/dev/null || rm -f -- "$temp"
        fi
      fi
      printf '%s\n' "$fetched"
      return 0
    fi
  fi

  if [[ "$cached_scope" == "$scope" && "$cached_ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] \
      && python3 -c 'import ipaddress,sys; raise SystemExit(ipaddress.ip_address(sys.argv[1]).version != 4)' "$cached_ip" 2>/dev/null; then
    printf '%s · cached\n' "$cached_ip"
  else
    printf 'unavailable\n'
  fi
}

# Optional, owner-only ISP baseline used only to compare the routed VPN egress.
_arc_greeting_configured_isp_ip() {
  local config="$HOME/.config/arc/greeting-isp-ip" ip=''
  [[ -r "$config" ]] || return 0
  IFS= read -r ip < "$config" || true
  [[ "$ip" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || return 0
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import ipaddress,sys; raise SystemExit(ipaddress.ip_address(sys.argv[1]).version != 4)' "$ip" 2>/dev/null || return 0
  fi
  printf '%s\n' "$ip"
}

# Remember the caller's color capability before ship renderers use pipes.
_arc_greeting_has_color() {
  [[ -z "${NO_COLOR:-}" && "${TERM:-dumb}" != dumb ]] || return 1
  [[ "${_ARC_GREETING_COLOR:-auto}" != 0 ]] || return 1
  [[ "${_ARC_GREETING_COLOR:-auto}" == 1 || -t 1 ]]
}

_arc_greeting_clock() {
  if [[ -n "${ZSH_VERSION:-}" ]]; then
    zmodload zsh/datetime 2>/dev/null && strftime "$1" && return 0
  elif [[ -n "${BASH_VERSION:-}" ]]; then
    printf "%($1)T" -1 && return 0
  fi
  date +"$1"
}

_arc_greeting_service_state() {
  local _state
  _state=$(timeout 0.3s systemctl is-active "$1" 2>/dev/null || true)
  case "$_state" in
    active) printf '✓' ;;
    inactive|failed|deactivating) printf '✗' ;;
    *) printf '?' ;;
  esac
}

# Report the configured timezone's city, never infer physical location or use IP geolocation.
_arc_greeting_local_zone() {
  local _zone=''
  _zone=$(readlink -f /etc/localtime 2>/dev/null || true)
  _zone=${_zone#*/zoneinfo/}
  case "$_zone" in
    America/Los_Angeles) printf 'Los Angeles, United States' ;;
    '') printf 'unknown' ;;
    *) printf '%s' "$_zone" ;;
  esac
}

# Read only the phone peer's online bit from the local Tailscale daemon; never print peer IPs.
_arc_greeting_tailscale_phone_state() {
  local _status=''
  command -v tailscale >/dev/null 2>&1 || { printf 'unavailable'; return; }
  command -v python3 >/dev/null 2>&1 || { printf 'unknown'; return; }
  _status=$(timeout 1s tailscale status --json 2>/dev/null) || { printf 'unavailable'; return; }
  printf '%s' "$_status" | python3 -c '
import json, sys
try:
    peers = json.load(sys.stdin).get("Peer") or {}
    phones = [p for p in peers.values() if "iphone" in (p.get("HostName", "") + " " + p.get("DNSName", "")).lower()]
    print("online" if any(p.get("Online") for p in phones) else "offline" if phones else "not listed")
except Exception:
    print("unknown")
' 2>/dev/null || printf 'unknown'
}

# Shared, width-aware renderers for the architecture banner and status rows.
_arc_greeting_width() {
  # Bash and zsh update COLUMNS to the active pane width after SIGWINCH. Prefer
  # it over /dev/tty: split-pane emulators can expose the parent window there.
  local _width="${COLUMNS:-}" _terminal_size=''
  if [[ ! "$_width" =~ ^[0-9]+$ && -r /dev/tty ]] && command -v stty >/dev/null 2>&1; then
    _terminal_size=$(stty size 2>/dev/null </dev/tty || true)
    _width=${_terminal_size##* }
  fi
  if [[ ! "$_width" =~ ^[0-9]+$ ]] && command -v tput >/dev/null 2>&1; then
    _width=$(tput cols 2>/dev/null || true)
  fi
  [[ "$_width" =~ ^[0-9]+$ ]] || _width=80
  (( _width >= 24 )) || _width=24
  (( _width <= 96 )) || _width=96
  [[ "${_ARC_GREETING_SHIP:-0}" != 1 ]] || _width=$((_width - 4))
  printf '%s\n' "$_width"
}

# Plain-text wrapping preserves every character, including long path tokens.
_arc_greeting_wrap() {
  local _text="$1" _limit="$2" _token _line='' _head
  while IFS= read -r _token; do
    [[ -n "$_token" ]] || continue
    if [[ -n "$_line" ]] && (( ${#_line} + 1 + ${#_token} > _limit )); then
      printf '%s\n' "$_line"; _line=''
    fi
    while (( ${#_token} > _limit )); do
      _head=${_token:0:_limit}
      printf '%s\n' "$_head"
      _token=${_token:_limit}
    done
    [[ -n "$_token" ]] && _line="${_line:+$_line }$_token"
  done < <(printf '%s\n' "$_text" | tr -s '[:space:]' '\n')
  [[ -z "$_line" ]] || printf '%s\n' "$_line"
}

# Ship ornament is local to the greeting; prompt-time radar updates stay plain.
_arc_greeting_ship_rail() {
  local _width _rail
  _width=$(_arc_greeting_width)
  _rail=$(printf '%*s' "$_width" '' | tr ' ' '-')
  printf '  %b+%s+%b\n' "$MUTED" "$_rail" "$N"
}

_arc_greeting_ship_frame() {
  local _line _plain _padding _width _head _tail
  _width=$(_arc_greeting_width)
  while IFS= read -r _line; do
    _plain="$_line"
    while [[ "$_plain" == *$'\033['*m* ]]; do
      _head=${_plain%%$'\033['*}
      _tail=${_plain#*$'\033['}
      _plain="$_head${_tail#*m}"
    done
    _padding=$((_width - ${#_plain}))
    (( _padding >= 0 )) || _padding=0
    printf '  %b|%b%s%*s%b|%b\n' "$MUTED" "$N" "$_line" "$_padding" '' "$MUTED" "$N"
  done
}

_arc_greeting_ship_blank() {
  if [[ "${_ARC_GREETING_SHIP:-0}" == 1 ]]; then
    printf '\n' | _arc_greeting_ship_frame
  else
    printf '\n'
  fi
}

_arc_greeting_ship_header() {
  [[ "${ARC_GREETING_STYLE:-cockpit}" != plain ]] || return 0
  local _width _mast _rail
  _width=$(_arc_greeting_width)
  if [[ "${_ARC_GREETING_SHIP:-0}" == 1 ]]; then
    _mast=$((_width / 2))
  else
    _mast=8
  fi
  printf '%*s%b|\\%b\n' "$_mast" '' "$MUTED" "$N"
  printf '%*s%b| \\%b\n' "$_mast" '' "$MUTED" "$N"
  printf '%*s%b|  \\%b\n' "$_mast" '' "$MUTED" "$N"
  printf '%*s%b|___\\%b\n' "$_mast" '' "$MUTED" "$N"
  if [[ "${_ARC_GREETING_SHIP:-0}" == 1 ]]; then
    _rail=$(printf '%*s' "$_width" '' | tr ' ' '-')
    printf '  %b.%s.%b\n' "$MUTED" "$_rail" "$N"
    _arc_greeting_ship_blank
  else
    printf '\n'
  fi
}

_arc_greeting_line() {
  local _text="$1" _color="$2" _width _part
  _width=$(_arc_greeting_width)
  while IFS= read -r _part; do
    printf '  %b%s%b\n' "$_color" "$_part" "$N"
  done < <(_arc_greeting_wrap "$_text" "$((_width - 4))")
}

# Lead word header: each word field uses one fixed Circadian accent; continuation
# lines align under its text.
_arc_greeting_word_body() {
  local _text="$1" _label_color="$2" _width
  local _field=0 _column=18 _line_empty=1 _line_limit _token _token_color _token_width
  local _nyx _choice _desire _pine _separator='\033[38;2;112;124;132m' _reset='\033[0m'
  _width=$(_arc_greeting_width)
  _arc_greeting_palette
  _nyx="$_ARC_GREETING_NYX_COLOR"
  _choice="$_ARC_GREETING_CHOICE_COLOR"
  _desire="$_ARC_GREETING_DESIRE_COLOR"
  _pine="$_ARC_GREETING_STILL_PINE_COLOR"
  if ! _arc_greeting_has_color; then
    _nyx=''; _choice=''; _desire=''; _pine=''; _separator=''; _reset=''
  fi
  _line_limit=$((_width - 2))
  local _word_indent='                  '
  if (( _width >= 52 )); then
    printf '  %b·%b  %b%-11s%b  ' "$_separator" "$_reset" "$_label_color" WOD "$_reset"
  else
    printf '  %b·%b  %bWOD%b\n    ' "$_separator" "$_reset" "$_label_color" "$_reset"
    _column=4; _word_indent='    '
  fi
  while IFS= read -r _token; do
    [[ -z "$_token" ]] && continue
    if [[ "$_token" == / && $_field -eq 0 ]]; then
      _field=1; _token_color="$_separator"
    elif [[ "$_token" == '·' ]] && (( _field > 0 && _field < 3 )); then
      _field=$((_field + 1)); _token_color="$_separator"
    else
      case $_field in
        0) _token_color="$_nyx" ;;
        1) _token_color="$_choice" ;;
        2) _token_color="$_desire" ;;
        *) _token_color="$_pine" ;;
      esac
    fi
    _token_width=${#_token}
    if (( ! _line_empty && _column + 1 + _token_width > _line_limit )); then
      printf '\n%s' "$_word_indent"
      _column=${#_word_indent}
      _line_empty=1
    fi
    if (( ! _line_empty )); then
      printf ' '
      _column=$((_column + 1))
    fi
    printf '%b%s%b' "$_token_color" "$_token" "$_reset"
    _column=$((_column + _token_width))
    _line_empty=0
  done < <(printf '%s\n' "$_text" | tr -s ' ' '\n')
  printf '\n'
}

_arc_greeting_current_phase() {
  local _hour
  _hour=$(_arc_greeting_clock '%H')
  _hour=$((10#$_hour))
  if   (( _hour >= 6 && _hour < 11 )); then printf 'choice\n'
  elif (( _hour >= 11 && _hour < 17 )); then printf 'desire\n'
  elif (( _hour >= 17 && _hour < 21 )); then printf 'still-pine\n'
  else printf 'nyx\n'; fi
}

_arc_greeting_palette() {
  _ARC_GREETING_NYX_COLOR='\033[38;2;234;154;151m'
  _ARC_GREETING_CHOICE_COLOR='\033[38;2;94;200;237m'
  _ARC_GREETING_DESIRE_COLOR='\033[38;2;246;193;119m'
  _ARC_GREETING_STILL_PINE_COLOR='\033[38;2;196;167;231m'
  _ARC_GREETING_NYX_BEAD='\033[1;38;2;234;154;151m'
  _ARC_GREETING_CHOICE_BEAD='\033[1;38;2;94;200;237m'
  _ARC_GREETING_DESIRE_BEAD='\033[1;38;2;246;193;119m'
  _ARC_GREETING_STILL_PINE_BEAD='\033[1;38;2;196;167;231m'
}

_arc_greeting_phase_colors() {
  _arc_greeting_palette
  case "$1" in
    choice)
      _ARC_GREETING_PHASE_COLOR="$_ARC_GREETING_CHOICE_COLOR"
      _ARC_GREETING_PHASE_BEAD="$_ARC_GREETING_CHOICE_BEAD" ;;
    desire)
      _ARC_GREETING_PHASE_COLOR="$_ARC_GREETING_DESIRE_COLOR"
      _ARC_GREETING_PHASE_BEAD="$_ARC_GREETING_DESIRE_BEAD" ;;
    still-pine)
      _ARC_GREETING_PHASE_COLOR="$_ARC_GREETING_STILL_PINE_COLOR"
      _ARC_GREETING_PHASE_BEAD="$_ARC_GREETING_STILL_PINE_BEAD" ;;
    *)
      _ARC_GREETING_PHASE_COLOR="$_ARC_GREETING_NYX_COLOR"
      _ARC_GREETING_PHASE_BEAD="$_ARC_GREETING_NYX_BEAD" ;;
  esac
}

_arc_greeting_radar_line() {
  local _phase="$1" _label="$2" _state="$3" _details="${4:-}"
  local _radarText='\033[38;2;164;194;139m' _bead
  _arc_greeting_phase_colors "$_phase"
  _bead="$_ARC_GREETING_PHASE_BEAD"
  if ! _arc_greeting_has_color; then
    _radarText=''; _bead=''
  fi
  local _symbol='●' _join='·' _radarLocale="${LC_ALL:-${LC_CTYPE:-${LANG:-C}}}"
  case "$_radarLocale" in
    *UTF-8*|*utf8*|*utf-8*|*UTF8*) ;;
    *) _symbol='*'; _join='.'; _details="${_details//·/.}" ;;
  esac
  _arc_greeting_item "$_label" "$_state${_details:+ $_join $_details}" "$_radarText" "$_bead" "$_symbol"
}

# Update once when the prompt returns after a phase boundary; no timer runs.
_arc_greeting_phase_watch() {
  local N='' TEXT='' MUTED='' SYSTEM_BULLET='' ART=''
  if _arc_greeting_has_color; then
    N='\033[0m'; TEXT='\033[38;2;226;229;233m'; MUTED='\033[38;2;112;124;132m'
  fi
  local _phase
  _phase=$(_arc_greeting_current_phase)
  [[ -n "${_ARC_GREETING_PHASE:-}" && "$_phase" == "$_ARC_GREETING_PHASE" ]] && return 0
  _ARC_GREETING_PHASE="$_phase"
  printf '\n'
  if [[ -n "${_ARC_GREETING_RADAR_ROUTE_ONE:-}" || -n "${_ARC_GREETING_RADAR_ROUTE_TWO:-}" ]]; then
    _arc_greeting_radar_line "$_phase" \
      "${_ARC_GREETING_RADAR_LABEL:-LOCAL_RADAR}" \
      "${_ARC_GREETING_SESSION_STATE:-[ STATION_READY ]}" \
      "${_ARC_GREETING_RADAR_ROUTE_ONE:-}"
    if [[ -n "${_ARC_GREETING_RADAR_ROUTE_TWO:-}" ]]; then
      _arc_greeting_radar_line "$_phase" \
        "${_ARC_GREETING_RADAR_DNS_LABEL:-DNS_RADAR}" \
        "${_ARC_GREETING_SESSION_STATE:-[ STATION_READY ]}" \
        "$_ARC_GREETING_RADAR_ROUTE_TWO"
    fi
  else
    _arc_greeting_radar_line "$_phase" \
      "${_ARC_GREETING_RADAR_LABEL:-LOCAL_RADAR}" \
      "${_ARC_GREETING_SESSION_STATE:-[ STATION_READY ]}"
  fi
  if [[ -n "${_ARC_GREETING_RADAR_LOCAL_IP:-}" ]]; then
    _arc_greeting_radar_line "$_phase" 'LOCAL_IP' "$_ARC_GREETING_RADAR_LOCAL_IP"
  fi
}

# Show the provider's human-readable city/country, never its server identifier.
# Bound the call so a terminal greeting stays light. If ProtonVPN omits the
# city, decode the country from its ID or the active NetworkManager profile.
_arc_greeting_vpn_location() {
  local _location='' _server=''
  if command -v protonvpn >/dev/null 2>&1 && command -v timeout >/dev/null 2>&1; then
    _server=$(timeout 1 protonvpn status 2>/dev/null |
      awk -F: 'tolower($1) == "server" {
        value = $2
        sub(/^[[:space:]]+/, "", value)
        if (value ~ / in /) {
          sub(/^.* in /, "", value)
          print "location:" value
        } else print "id:" value
        exit
      }')
  fi
  if [[ "$_server" == location:* ]]; then
    _location=${_server#location:}
  else
    _server=${_server#id:}
    if [[ -z "$_server" ]] && command -v nmcli >/dev/null 2>&1; then
      _server=$(timeout 0.5s nmcli -t -f NAME,DEVICE connection show --active 2>/dev/null |
        awk -F: '$2 == "proton0" { print $1; exit }')
      _server=${_server#ProtonVPN }
      _server=${_server#ProtonVPN-}
      _server=$(printf '%s\n' "$_server" | sed -e 's/^[(]//' -e 's/[)]$//')
    fi
    local _country_code=''
    _country_code=$(printf '%s' "$_server" | awk -F '[-#]' \
      '$1 ~ /^[[:alpha:]][[:alpha:]]$/ { print toupper($1); exit }')
    if [[ -n "$_country_code" && -r /usr/share/zoneinfo/iso3166.tab ]]; then
      _location=$(awk -F '\t' -v code="$_country_code" \
        'toupper($1) == code { print $2; exit }' /usr/share/zoneinfo/iso3166.tab)
    fi
  fi
  _location=$(LC_ALL=C printf '%s' "$_location" | LC_ALL=C tr -cd '[:alnum:],. -')
  (( ${#_location} >= 1 && ${#_location} <= 80 )) || return 0
  # ProtonVPN reports locations as "City, Country". Put the country first,
  # while retaining any state/region between the city and country.
  if [[ "$_location" == *,* ]]; then
    local _place="${_location%,*}" _country="${_location##*,}"
    _place="${_place% }"; _country="${_country# }"
    [[ -z "$_place" || -z "$_country" ]] || _location="$_country, $_place"
  fi
  printf '%s\n' "$_location"
}

# Read Arc Heal's owner-only, local IP-check result. Never trigger a check or
# expose route details here; stale, missing, or unrecognized reports fail closed.
_arc_greeting_ip_check() {
  local _file="$HOME/khaos-lab/arc-heal-log/home-ip-latest.md"
  local _modified='' _now='' _age=0 _minutes=0 _hours=0 _age_text='' _line='' _line_lower='' _state='unavailable' _reason=''
  [[ -f "$_file" && ! -L "$_file" && -O "$_file" && -r "$_file" ]] || {
    printf 'unavailable\n'; return 0
  }
  _modified=$(stat -c '%Y' -- "$_file" 2>/dev/null) || _modified=''
  _now=$(date +%s 2>/dev/null) || _now=''
  [[ "$_modified" =~ ^[0-9]+$ && "$_now" =~ ^[0-9]+$ ]] || {
    printf 'unavailable\n'; return 0
  }
  _age=$((_now - _modified))
  (( _age >= 0 )) || { printf 'unavailable\n'; return 0; }
  _minutes=$((_age / 60))
  _hours=$((_age / 3600))
  if (( _hours > 0 )); then _age_text="${_hours}h"
  else _age_text="${_minutes}m"; fi
  # Arc Heal's guarded home-IP check runs on a three-hour cadence.
  if (( _age > 14400 )); then
    printf 'stale · checked %s ago\n' "$_age_text"
    return 0
  fi
  _line=$(awk '/aws-lab-ip/ { sub(/^.*—[[:space:]]*/, ""); print; exit }' "$_file" 2>/dev/null)
  case "$_line" in
    *deferred*|*DEFERRED*)
      _state='deferred'
      # Translate Arc Heal's detailed guard note into a short, safe explanation.
      # Do not print interface names, addresses, SSIDs, or the raw report text.
      _line_lower=$(printf '%s' "$_line" | tr '[:upper:]' '[:lower:]')
      case "$_line_lower" in
        *vpn*|*tunnel*|*proxy*) _reason='VPN/tunnel active' ;;
        *ssid*|*gateway*|*pinned\ home*) _reason='not on saved home Wi-Fi' ;;
        *not\ confirmed\ as\ wi-fi*|*default\ route*) _reason='direct Wi-Fi unavailable' ;;
        *custom\ dns*|*nextdns*|*loopback\ resolver*) _reason='custom DNS active' ;;
        *home\ network\ identity*|*not\ configured*) _reason='home network not configured' ;;
        *no\ active\ ipv4\ route*|*no\ active\ route*) _reason='no active network route' ;;
        *terraform*|*source\ absent*) _reason='IP-check source unavailable' ;;
        *) _reason='safety guard active' ;;
      esac
      ;;
    *HEALED*|*healed*) _state='healed' ;;
    *FLAGGED*|*flagged*|*⚠*) _state='attention' ;;
    *✅*|*'check passed'*) _state='healthy' ;;
    *) _state='unavailable' ;;
  esac
  if [[ -n "$_reason" ]]; then
    printf '%s · %s · checked %s ago\n' "$_state" "$_reason" "$_age_text"
  else
    printf '%s · checked %s ago\n' "$_state" "$_age_text"
  fi
}

_arc_greeting_motto_body() {
  local _phase="$1" _rose='\033[38;2;245;198;215m' _reset='\033[0m'
  local _width _line _pad _body='E Pluribus Unum  · ☠️💀☠️  · In God We Trust'
  _width=$(_arc_greeting_width)
  if ! _arc_greeting_has_color; then
    _rose=''; _reset=''
  fi
  while IFS= read -r _line; do
    _pad=$(( (_width - ${#_line} - 2) / 2 )); (( _pad >= 2 )) || _pad=2
    printf '%*s%b%s%b\n' "$_pad" '' "$_rose" "$_line" "$_reset"
  done < <(_arc_greeting_wrap "$_body" "$((_width - 4))")
}

# One bounded, left-aligned divider for the complete greeting.
_arc_greeting_rule() {
  if [[ "${ARC_GREETING_STYLE:-cockpit}" == plain ]]; then printf '\n'; return 0; fi
  local _width _hull
  _width=$(_arc_greeting_width)
  if [[ "${_ARC_GREETING_SHIP:-0}" == 1 ]]; then
    _hull=$(printf '%*s' "$_width" '' | tr ' ' '.')
    printf '  %b\\%s/%b\n' "$MUTED" "$_hull" "$N"
    _hull=$(printf '%*s' "$((_width - 4))" '' | tr ' ' '.')
    printf '    %b\\%s/%b\n' "$MUTED" "$_hull" "$N"
    printf '      %b~    ~    ~    ~    ~%b\n\n' "$MUTED" "$N"
  else
    _hull=$(printf '%*s' "$((_width - 8))" '' | tr ' ' '.')
    printf '\n   %b\\%s/%b\n     %b~   ~   ~%b\n\n' "$MUTED" "$_hull" "$N" "$MUTED" "$N"
  fi
}

_arc_greeting_section_body() {
  local _title="$1" _spaced="${2:-1}"
  (( _spaced )) && printf '\n'
  local _bead=''
  _arc_greeting_phase_colors "${_ARC_GREETING_PHASE:-nyx}"
  [[ -n "$N" ]] && _bead="$_ARC_GREETING_PHASE_BEAD"
  printf '  %b●%b  %b%s%b\n' "$_bead" "$N" "$ART" "$_title" "$N"
}

# Add color only after wrapping so ANSI sequences cannot shift the grid.
# Group/tint state lives in the parent item and survives continuation lines.
_arc_greeting_value() {
  local _key="$1" _line="$2" _fallback="$3" _token _tint _gap=''
  if [[ -z "$N" || -n "${NO_COLOR:-}" || "${TERM:-dumb}" == dumb ]]; then
    printf '%s\n' "$_line"
    return
  fi
  while IFS= read -r _token; do
    [[ -n "$_token" ]] || continue
    _tint="$_fallback"
    case "$_key" in
      METHOD)
        [[ "$_token" != '>' ]] || _tint="$_ARC_GREETING_PHASE_COLOR" ;;
      HOST)
        case "$_token" in
          swap) _valueTint="$_ARC_GREETING_DESIRE_COLOR" ;;
          shell) _valueTint="$_ARC_GREETING_STILL_PINE_COLOR" ;;
        esac
        _tint="$_valueTint" ;;
      RAM)
        if (( _valueGroup == 0 )); then _tint="$_ARC_GREETING_DESIRE_COLOR"
        else _tint="$_ARC_GREETING_CHOICE_COLOR"; fi ;;
      FOCUS) _tint="$_ARC_GREETING_CHOICE_COLOR" ;;
      MO) _tint="$_ARC_GREETING_STILL_PINE_COLOR" ;;
      IDENTITY|I–III|IV–V|VI–VII)
        case $_valueGroup in
          0) _tint="$_ARC_GREETING_NYX_COLOR" ;;
          1) _tint="$_ARC_GREETING_CHOICE_COLOR" ;;
          2) _tint="$_ARC_GREETING_DESIRE_COLOR" ;;
          *) _tint="$_ARC_GREETING_STILL_PINE_COLOR" ;;
        esac ;;
    esac
    if [[ "$_token" == '·' ]]; then
      _tint="$MUTED"
      _valueGroup=$((_valueGroup + 1))
    fi
    printf '%s%b%s%b' "$_gap" "$_tint" "$_token" "$N"
    _gap=' '
  done < <(printf '%s\n' "$_line" | tr -s ' ' '\n')
  printf '\n'
}

# Key, value, and continuation columns stay aligned as the terminal narrows.
_arc_greeting_item_body() {
  local _label="$1" _text="$2" _color="${3:-$TEXT}" _bullet="${4:-$SYSTEM_BULLET}"
  local _symbol="${5:-·}" _width _line _first=1 _value_width _indent _before _phase _phaseColor _labelPad _valueGroup=0 _valueTint
  _width=$(_arc_greeting_width)
  _phase="${_ARC_GREETING_PHASE:-nyx}"
  _valueTint="$_color"
  _labelPad="$_label"
  while (( ${#_labelPad} < 11 )); do _labelPad="$_labelPad "; done
  _phaseColor=''
  [[ -z "$N" ]] || _phaseColor="$_ARC_GREETING_PHASE_COLOR"
  if [[ -n "$_label" ]] && (( _width >= 52 )); then
    _value_width=$((_width - 20)); _indent='                  '
  else
    _value_width=$((_width - 6)); _indent='    '
  fi
  while IFS= read -r _line; do
    if (( _first )) && [[ -n "$_label" ]]; then
      if (( _width >= 52 )); then
        printf '  %b%s%b  %b%s%b  ' "$_bullet" "$_symbol" "$N" "$TEXT" "$_labelPad" "$N"
      else
        printf '  %b%s%b  %b%s%b\n%s' "$_bullet" "$_symbol" "$N" "$TEXT" "$_label" "$N" "$_indent"
      fi
    else
      printf '%s' "$_indent"
    fi
    if [[ "$_label" == LOCAL_TIME && "$_line" == *"$_phase" ]]; then
      _before=${_line%"$_phase"}
      printf '%b%s%b%b%s%b\n' "$TEXT" "$_before" "$N" "$_phaseColor" "$_phase" "$N"
    else
      _arc_greeting_value "$_label" "$_line" "$_color"
    fi
    _first=0
  done < <(_arc_greeting_wrap "$_text" "$_value_width")
}

_arc_greeting_center_time() {
  # Retain the caller interface; align time with the shared status grid.
  _arc_greeting_item 'LOCAL_TIME' "$1 · $2" "$TEXT"
}

# The closing instrument strip follows the last status row.
_arc_greeting_footer() {
  local _phase="$1" _radar="$2" _state="$3" _routeOne="$4" _routeTwo="$5" _date="$6" _accent="$7"
  if [[ "${_ARC_GREETING_SHIP:-0}" == 1 ]]; then _arc_greeting_ship_rail
  else printf '\n'; fi
  _arc_greeting_radar_line "$_phase" "$_radar" "$_state" "$_routeOne"
  if [[ -n "$_routeTwo" ]]; then
    _arc_greeting_radar_line "$_phase" 'DNS_RADAR' "$_state" "$_routeTwo"
  fi
  _arc_greeting_ship_blank
  _arc_greeting_center_time "$_date" "$_phase" "$_accent"
  _arc_greeting_motto "$_phase"
  _arc_greeting_rule "$_date · $_phase"
}

_arc_greeting_collect_rows() {
  # Canonical Circadian accents; copy stays readable on monochrome terminals.
  local G='\033[38;2;164;194;139m'
  local R='\033[38;2;234;154;151m'
  local Y='\033[38;2;246;193;119m'
  local D='\033[38;2;128;137;145m'
  local TEXT='\033[38;2;226;229;233m'
  local MUTED='\033[38;2;112;124;132m'
  local N='\033[0m'
  local CG='Recognize > construct > visualize > analyze > interpret'
  if ! _arc_greeting_has_color; then
    G=''; R=''; Y=''; D=''; TEXT=''; MUTED=''; N=''
  fi

  # Canonical phase colors: Nyx 21–06, Choice 06–11, Desire 11–17,
  # Still-Pine 17–21. The active phase colors section titles and heading beads;
  # small row bullets use a steady Desire amber accent.
  local _phase C ART
  _phase=$(_arc_greeting_current_phase)
  _ARC_GREETING_PHASE="$_phase"
  _arc_greeting_phase_colors "$_phase"
  C="$_ARC_GREETING_PHASE_COLOR"; ART="$C"
  _arc_greeting_has_color || {
    C=''; CIRCLE=''; ART=''
  }

  local profile="${ARC_GREETING_PROFILE:-station}" host_name login_name now session_state radar_label origin_name
  local SYSTEM_BULLET=''
  _ARC_GREETING_RADAR_LOCAL_IP=''
  [[ -n "$N" ]] && SYSTEM_BULLET="$_ARC_GREETING_DESIRE_COLOR"
  host_name=$(hostname -s 2>/dev/null || hostname 2>/dev/null || printf 'unknown-node')
  login_name=$(id -un 2>/dev/null || printf '%s' "${USER:-unknown-user}")
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
  _ARC_GREETING_RADAR_LABEL="$radar_label"
  _ARC_GREETING_SESSION_STATE="$session_state"

  local vpn_ip='' dns_ip='' isp_ext_ip='' route_text='' route_ip='' compare_ext_ip=''
  local routePairOne='' routePairTwo=''
  if [[ "$profile" != cloud ]]; then
    vpn_ip=$(ip -br addr show proton0 2>/dev/null | awk '$2 != "DOWN" {print $3; exit}' | cut -d/ -f1)
    dns_ip=$(awk '$1 == "nameserver" {print $2; exit}' /etc/resolv.conf 2>/dev/null)
    isp_ext_ip=$(_arc_greeting_configured_isp_ip)
    if [[ -n "$vpn_ip" ]]; then
      route_text=$(_arc_greeting_public_ipv4 vpn)
      compare_ext_ip="$isp_ext_ip"
      if [[ -n "$compare_ext_ip" ]]; then
        routePairOne="EXT $compare_ext_ip"
      else
        routePairOne='EXT unavailable'
      fi
      if [[ -n "$vpn_ip" && "$vpn_ip" != "$compare_ext_ip" ]]; then
        routePairOne+=" · TUN $vpn_ip"
      fi
      route_ip=${route_text%% *}
      if [[ "$route_ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] \
          && [[ -n "$compare_ext_ip" && "$route_ip" != "$compare_ext_ip" ]]; then
        routePairTwo="EXIT $route_text"
      fi
    else
      route_text=$(_arc_greeting_public_ipv4 direct)
      route_ip=${route_text%% *}
      if [[ "$route_ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        compare_ext_ip="$route_ip"
        routePairOne="EXT $route_text"
      elif [[ -n "$isp_ext_ip" ]]; then
        compare_ext_ip="$isp_ext_ip"
        routePairOne="EXT $isp_ext_ip · saved"
      else
        routePairOne='EXT unavailable'
      fi
    fi
    if [[ -n "$dns_ip" && "$dns_ip" != "$compare_ext_ip" ]]; then
      routePairTwo="${routePairTwo:+$routePairTwo · }DNS $dns_ip"
    fi
  fi
  if [[ "$profile" != cloud && -z "$vpn_ip" ]]; then
    session_state='[ DIRECT_ROUTE ]'
    _ARC_GREETING_SESSION_STATE="$session_state"
  fi
  _ARC_GREETING_RADAR_ROUTE_ONE="$routePairOne"
  _ARC_GREETING_RADAR_ROUTE_TWO="$routePairTwo"
  _ARC_GREETING_RADAR_DNS_LABEL='DNS_RADAR'

  local word_line=''
  if [[ "$profile" != cloud ]] && command -v arc >/dev/null 2>&1; then
    word_line=$(timeout 0.6s arc word --compact 2>/dev/null || true)
    word_line=${word_line/ · adjective · / · adj. · }
  fi
  [[ "$profile" == cloud || -n "$word_line" ]] || word_line='unavailable'
  printf '\n'
  [[ -n "$word_line" ]] && _arc_greeting_capture_word "$word_line" "$C"
  [[ -z "$word_line" ]] || true
  if [[ "$profile" == cloud ]]; then
    _arc_greeting_capture_row 'ORIGIN' "$origin_name" "$TEXT"
    fi

  _arc_greeting_capture_section 'IDENTITY & INTENT' 0
  _arc_greeting_capture_row 'IDENTITY' "lt · $host_name · arc" "$TEXT"
  _arc_greeting_capture_row 'USER' "$login_name" "$TEXT"
  _arc_greeting_capture_row 'METHOD' "$CG" "$TEXT"
  # ── Principles and policy source ───────────────────────────────────────────
  local MOTD_FILE="$HOME/.config/arc/motd"
  if [[ -f "$MOTD_FILE" ]]; then
    local motd_line
    while IFS= read -r motd_line || [[ -n "$motd_line" ]]; do
      if [[ "$motd_line" == MO:* ]]; then
        if [[ "$profile" == cloud ]]; then
          _arc_greeting_capture_row 'MO' 'workstation policy · local reference' "$MUTED"
        else
          local _moPath="${motd_line#MO: }"
          _moPath="${_moPath/#\~/$HOME}"
          [[ -f "$_moPath" ]] && _arc_greeting_capture_row 'MO' "${motd_line#MO: }" "$TEXT" || _arc_greeting_capture_row 'MO' 'unavailable' "$Y"
        fi
      elif [[ "$motd_line" == *:* ]]; then
        _arc_greeting_capture_row "${motd_line%%:*}" "${motd_line#*: }" "$TEXT"
      else
        _arc_greeting_capture_row 'PRINCIPLES' "$motd_line" "$TEXT"
      fi
    done < "$MOTD_FILE"
  fi

  local _memSnapshot _rootSnapshot=''
  _memSnapshot=$(timeout 0.3s free -h 2>/dev/null || true)
  _rootSnapshot=$(timeout 0.3s df -h / 2>/dev/null || true)
  if [[ "$profile" == cloud ]]; then
    local cloud_mem_used cloud_mem_total cloud_disk cloud_uptime cloud_shell='bash'
    [[ -n "${ZSH_VERSION:-}" ]] && cloud_shell='zsh'
    cloud_mem_used=$(printf '%s\n' "$_memSnapshot" | awk '/Mem:/ {print $3}')
    cloud_mem_total=$(printf '%s\n' "$_memSnapshot" | awk '/Mem:/ {print $2}')
    cloud_disk=$(printf '%s\n' "$_rootSnapshot" | awk 'NR==2 {print $3 " used / " $4 " free (" $5 ")"}')
    cloud_uptime=$(uptime -p 2>/dev/null || printf 'unknown')
    _arc_greeting_capture_section 'OPERATIONS'
    _arc_greeting_capture_row 'RAM' "${cloud_mem_used:-unknown} / ${cloud_mem_total:-unknown}" "$TEXT"
    _arc_greeting_capture_row 'ROOT_FS' "${cloud_disk:-unknown}" "$TEXT"
    _arc_greeting_capture_row 'UPTIME' "$cloud_uptime" "$TEXT"
    _arc_greeting_capture_section 'SYSTEMS'
    _arc_greeting_capture_row 'NODE' "$host_name · AWS EC2 · $(uname -sr 2>/dev/null || printf 'Linux')" "$TEXT" "$SYSTEM_BULLET"
    _arc_greeting_capture_row 'SESSION' "$session_state · $cloud_shell" "$G" "$SYSTEM_BULLET"
    _arc_greeting_capture_footer "$_phase" "$radar_label" "$session_state" "$routePairOne" "$routePairTwo" "$now" "$C"
    return
  fi

  # ── Compact local status ───────────────────────────────────────────────────
  local mem_used mem_free mem_total
  mem_used=$(printf '%s\n' "$_memSnapshot" | awk '/Mem:/ {print $3}')
  mem_free=$(printf '%s\n' "$_memSnapshot" | awk '/Mem:/ {print $7}')
  mem_total=$(printf '%s\n' "$_memSnapshot" | awk '/Mem:/ {print $2}')

  mem_used=${mem_used:-unknown}; mem_free=${mem_free:-unknown}; mem_total=${mem_total:-unknown}
  local disk_total disk_used disk_free disk_text
  disk_total=$(printf '%s\n' "$_rootSnapshot" | awk 'NR==2 {print $2}')
  disk_used=$(printf '%s\n' "$_rootSnapshot" | awk 'NR==2 {print $3}')
  disk_free=$(printf '%s\n' "$_rootSnapshot" | awk 'NR==2 {print $4}')
  disk_text='unavailable'
  if [[ -n "$disk_total" && -n "$disk_used" && -n "$disk_free" ]]; then
    disk_text="${disk_total} total · ${disk_used} used · ${disk_free} free"
  fi

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
  local vpn_text vpn_color dns_text dns_color
  if [[ -n "$vpn_ip" ]]; then
    vpn_text='up'
    local vpn_location
    vpn_location=$(_arc_greeting_vpn_location)
    [[ -z "$vpn_location" ]] || vpn_text+=" · $vpn_location"
    vpn_color="$G"
  else vpn_text='down · arc vpn connect'; vpn_color="$Y"; fi
  if timeout 0.3s systemctl is-active --quiet nextdns 2>/dev/null; then dns_text='NextDNS'; dns_color="$G"
  else dns_text='local · arc dns on'; dns_color="$Y"; fi
  local network_color="$vpn_color"
  [[ "$dns_color" == "$Y" ]] && network_color="$Y"
  local net_text="VPN ${vpn_text} · DNS ${dns_text}"
  local zone_text phone_state phone_text link_color="$D"
  zone_text=$(_arc_greeting_local_zone)
  phone_state=$(_arc_greeting_tailscale_phone_state)
  phone_text="Tailscale · iPhone ${phone_state}"
  case "$phone_state" in
    online) link_color="$G" ;;
    offline|unavailable|not\ listed) link_color="$Y" ;;
  esac

  local ufw_text ufw_color f2b_text f2b_color aa_text aa_color luks_text luks_color
  ufw_text=$(_arc_greeting_service_state ufw); ufw_color="$G"
  if pgrep -x 'fail2ban-server' &>/dev/null; then f2b_text='✓'; f2b_color="$G"; else f2b_text='✗'; f2b_color="$R"; fi
  aa_text=$(_arc_greeting_service_state apparmor); aa_color="$G"
  if [[ -b /dev/mapper/storage_crypt ]]; then
    if timeout 0.3s ls /mnt/storage/ >/dev/null 2>&1; then luks_text='open'; luks_color="$G"; else luks_text='stale'; luks_color="$Y"; fi
  else luks_text='closed'; luks_color="$D"; fi

  local local_ip _addressList
  if _addressList=$(timeout 0.3s hostname -I 2>/dev/null); then
    local_ip=$(printf '%s\n' "$_addressList" | awk '{print $1}')
    if [[ -z "$local_ip" ]]; then
      local_ip='offline'; session_state='[ NO_CARRIER ]'
    fi
  else
    local_ip='unknown'; session_state='[ NETWORK_UNKNOWN ]'
  fi
  _ARC_GREETING_SESSION_STATE="$session_state"

  local local_ip_display='' ip_check_status=''
  if [[ "$profile" != cloud ]]; then
    local_ip_display="$local_ip"
    ip_check_status=$(_arc_greeting_ip_check)
    [[ -n "$ip_check_status" ]] || ip_check_status='unavailable'
  fi
  _ARC_GREETING_RADAR_LOCAL_IP="${local_ip_display}${ip_check_status:+ · IP_CHECK $ip_check_status}"

  # Storage checks include actual mount I/O to avoid reporting a stale mount as healthy.
  local usb_text fortress_text uu uf fu ff
  if timeout 0.3s mountpoint -q /mnt/storage 2>/dev/null && timeout 0.3s ls /mnt/storage/ >/dev/null 2>&1; then
    local _usbSnapshot
    _usbSnapshot=$(timeout 0.3s df -h /mnt/storage 2>/dev/null || true)
    uu=$(printf '%s\n' "$_usbSnapshot" | awk 'NR==2 {print $3}')
    uf=$(printf '%s\n' "$_usbSnapshot" | awk 'NR==2 {print $4}')
    usb_text="${uu:-unknown} used / ${uf:-unknown} free"; usb_color="$TEXT"
  elif timeout 0.3s mountpoint -q /mnt/storage 2>/dev/null; then usb_text='stale · arc mount'; usb_color="$Y"
  else usb_text='not mounted'; usb_color="$D"; fi
  if timeout 0.3s mountpoint -q /fortress 2>/dev/null && timeout 0.3s ls /fortress/ >/dev/null 2>&1; then
    local _fortressSnapshot
    _fortressSnapshot=$(timeout 0.3s df -h /fortress 2>/dev/null || true)
    fu=$(printf '%s\n' "$_fortressSnapshot" | awk 'NR==2 {print $3}')
    ff=$(printf '%s\n' "$_fortressSnapshot" | awk 'NR==2 {print $4}')
    fortress_text="${fu:-unknown} used / ${ff:-unknown} free"; fortress_color="$TEXT"
  elif timeout 0.3s mountpoint -q /fortress 2>/dev/null; then fortress_text='stale'; fortress_color="$Y"
  else fortress_text='not mounted'; fortress_color="$D"; fi

  local sw_used sw_total shell_name shell_ver omz_tag=''
  sw_used=$(printf '%s\n' "$_memSnapshot" | awk '/Swap:/ {print $3}')
  sw_total=$(printf '%s\n' "$_memSnapshot" | awk '/Swap:/ {print $2}')
  shell_name=$(basename "${SHELL:-zsh}")
  shell_ver=$("$SHELL" --version 2>/dev/null | head -1 | awk '{print $2}' | cut -d. -f1,2)
  [[ -d "$HOME/.oh-my-zsh" ]] && omz_tag='/omz'

  sw_used=${sw_used:-unknown}; sw_total=${sw_total:-unknown}

  local ts_name ts_date ts_manual ts_tag
  ts_date='none'; ts_tag='auto'
  if [[ -f /var/cache/timeshift-last-snapshot ]]; then
    ts_name=$(cat /var/cache/timeshift-last-snapshot 2>/dev/null)
    ts_date=$(grep -oP '\d{4}-\d{2}-\d{2}' <<<"$ts_name" | head -1)
    [[ -f /var/cache/timeshift-last-run-manual ]] && ts_manual=$(tr -d '[:space:]' < /var/cache/timeshift-last-run-manual)
    [[ "$ts_manual" == '1' ]] && ts_tag='manual'
    [[ -n "$ts_date" ]] || ts_date='unknown'
  fi

  _arc_greeting_capture_section 'OPERATIONS'
  _arc_greeting_capture_row 'RAM' "${mem_used}/${mem_total} used · ${mem_free} free" "$TEXT"
  _arc_greeting_capture_row 'DISK' "$disk_text" "$TEXT"
  _arc_greeting_capture_row 'FOCUS' "${focus}" "$TEXT"
  _arc_greeting_capture_row 'TASKS' "${tasks_text}" "${tasks_color}"
  local ops_color="$snap_color"
  [[ "$sop_ack_str" == acked && "$sop_gp_str" == 'plan ✓' ]] || ops_color="$Y"
  _arc_greeting_capture_row 'SNAP' "${snap_text} · SOP ${sop_ack_str} · ${sop_gp_str} · TS ${ts_date} ${ts_tag}" "$ops_color"

  _arc_greeting_capture_section 'SYSTEMS'
  _arc_greeting_capture_row 'ZONE' "$zone_text" "$TEXT" "$SYSTEM_BULLET"
  _arc_greeting_capture_row 'LINK' "$phone_text" "$link_color" "$SYSTEM_BULLET"
  local security_color="$G"
  [[ "$ufw_text$f2b_text$aa_text" == *✗* ]] && security_color="$R"
  [[ "$ufw_text$f2b_text$aa_text" != *"?"* ]] || security_color="$Y"
  [[ "$luks_text" == stale ]] && security_color="$R"
  _arc_greeting_capture_row 'SEC' "UFW ${ufw_text} · F2B ${f2b_text} · AA ${aa_text} · LUKS ${luks_text}" "$security_color" "$SYSTEM_BULLET"
  local storage_color="$C"
  [[ "$usb_color" == "$Y" || "$fortress_color" == "$Y" ]] && storage_color="$Y"
  [[ "$usb_color" == "$D" && "$fortress_color" == "$D" ]] && storage_color="$D"
  _arc_greeting_capture_row 'STORE' "USB ${usb_text} · Fortress ${fortress_text}" "$storage_color" "$SYSTEM_BULLET"
  _arc_greeting_capture_row 'HOST' "swap ${sw_used}/${sw_total} · shell ${shell_name} ${shell_ver}${omz_tag}" "$TEXT" "$SYSTEM_BULLET"
  _arc_greeting_capture_footer "$_phase" "$radar_label" "$session_state" "$routePairOne" "$routePairTwo" "$now" "$C" "$local_ip_display" "$ip_check_status" "$net_text" "$network_color"
}

_arc_greeting_word() {
  if [[ "${_ARC_GREETING_SHIP:-0}" == 1 ]]; then
    _arc_greeting_word_body "$@" | _arc_greeting_ship_frame
  else
    _arc_greeting_word_body "$@"
  fi
}

_arc_greeting_item() {
  if [[ "${_ARC_GREETING_SHIP:-0}" == 1 ]]; then
    _arc_greeting_item_body "$@" | _arc_greeting_ship_frame
  else
    _arc_greeting_item_body "$@"
  fi
}

_arc_greeting_motto() {
  if [[ "${_ARC_GREETING_SHIP:-0}" == 1 ]]; then
    _arc_greeting_motto_body "$@" | _arc_greeting_ship_frame
  else
    _arc_greeting_motto_body "$@"
  fi
}

_arc_greeting_section() {
  if [[ "${_ARC_GREETING_SHIP:-0}" == 1 ]]; then
    _arc_greeting_ship_rail
    _arc_greeting_section_body "$1" 0 | _arc_greeting_ship_frame
  else
    _arc_greeting_section_body "$@"
  fi
}

# A 10-second, owner-only rendered snapshot avoids repeating startup probes
# across tabs. This is data read with read/printf, NEVER sourced or evaluated.
_arc_greeting() {
  local _ARC_GREETING_COLOR=0
  # Determine outer TTY capability directly before any redirection.
  [[ ! -t 1 || -n "${NO_COLOR:-}" || "${TERM:-dumb}" == dumb ]] || _ARC_GREETING_COLOR=1
  local _locale="${LC_ALL:-${LC_CTYPE:-${LANG:-C}}}" _ascii=0
  case "$_locale" in *UTF-8*|*utf8*|*utf-8*|*UTF8*) ;; *) _ascii=1 ;; esac
  local ARC_GREETING_STYLE="${ARC_GREETING_STYLE:-cockpit}"
  (( _ascii == 0 )) || ARC_GREETING_STYLE=plain
  local _source
  if [[ -n "${BASH_VERSION:-}" ]]; then _source="${BASH_SOURCE[0]}"
  else _source="${(%):-%x}"; fi
  local _now _day _quoteHour _quoteWindow _key _cacheRoot _cacheDir _cache _stamp _storedKey _payload _mode _terminalWidth _node _login _ttl=10 _temp=''
  _now=$(_arc_greeting_clock '%s')
  _day=$(_arc_greeting_clock '%F')
  _quoteHour=$(_arc_greeting_clock '%H')
  _quoteWindow=$((10#$_quoteHour / 8))
  _terminalWidth=$(_arc_greeting_width)
  _node=${HOSTNAME:-$(hostname -s 2>/dev/null || hostname 2>/dev/null || printf 'unknown-node')}
  _login=$(id -un 2>/dev/null || printf '%s' "${USER:-unknown-user}")
  _key="cockpit-v5|$_day|$_quoteWindow|$(_arc_greeting_current_phase)|$_terminalWidth|${TERM:-dumb}|$_ARC_GREETING_COLOR|$ARC_GREETING_STYLE|$_ascii|$_node|$_login"
  _cacheRoot="${XDG_CACHE_HOME:-$HOME/.cache}/arc"
  _cacheDir="$_cacheRoot/greeting-snapshots"
  _cache="$_cacheDir/station"
  if [[ "${ARC_GREETING_PROFILE:-station}" != station || "${ARC_GREETING_CACHE:-1}" == 0 ]]; then _ttl=0; fi
  if (( _ttl > 0 )) && [[ -d "$_cacheDir" && ! -L "$_cacheDir" && -O "$_cacheDir" && -f "$_cache" && ! -L "$_cache" && -O "$_cache" ]]; then
    _mode=$(stat -c '%a' -- "$_cacheDir" "$_cache" 2>/dev/null || true)
    if [[ "$_mode" == $'700\n600' && ! "$_source" -nt "$_cache" &&
          ! "$HOME/.local/share/lt/focus" -nt "$_cache" &&
          ! "$HOME/.local/share/lt/tasks" -nt "$_cache" &&
          ! "$HOME/.config/arc/motd" -nt "$_cache" &&
          ! "$HOME/.config/arc/word-of-day.json" -nt "$_cache" &&
          ! "$HOME/dev-notes/intel-ops/MO.md" -nt "$_cache" &&
          ! "$HOME/dev-notes/intel-ops/GAMEPLAN.md" -nt "$_cache" &&
          ! "$HOME/.config/arc/sop/arc-sop.db" -nt "$_cache" ]]; then
      {
        IFS= read -r _stamp || _stamp=''
        IFS= read -r _storedKey || _storedKey=''
        if [[ "$_stamp" =~ ^[0-9]+$ && "$_storedKey" == "$_key" ]] && (( _now >= _stamp && _now - _stamp < _ttl )); then
          if IFS= read -r _ARC_GREETING_PHASE &&
             IFS= read -r _ARC_GREETING_RADAR_LABEL &&
             IFS= read -r _ARC_GREETING_SESSION_STATE &&
             IFS= read -r _ARC_GREETING_RADAR_ROUTE_ONE &&
             IFS= read -r _ARC_GREETING_RADAR_ROUTE_TWO &&
             IFS= read -r _ARC_GREETING_RADAR_DNS_LABEL &&
             IFS= read -r _ARC_GREETING_RADAR_LOCAL_IP &&
             [[ "$_ARC_GREETING_PHASE" == nyx || "$_ARC_GREETING_PHASE" == choice ||
                "$_ARC_GREETING_PHASE" == desire || "$_ARC_GREETING_PHASE" == still-pine ]]; then
            _ARC_GREETING_OBSERVED_AT="$_stamp"
            if IFS= read -r _payload; then
              printf '%s\n' "$_payload"
              while IFS= read -r _payload; do printf '%s\n' "$_payload"; done
              return 0
            fi
          fi
        fi
      } < "$_cache" 2>/dev/null || true
    fi
  fi
  # A private temporary file lets the collector update prompt radar state in
  # this shell. No shell code or credentials are saved in the snapshot.
  _temp=$(umask 077; mktemp "${TMPDIR:-/tmp}/arc-greeting.XXXXXXXX" 2>/dev/null) || {
    printf '\nGreeting unavailable: temporary storage could not be opened.\n\n'
    return 0
  }
  local LC_ALL=C.UTF-8
  _arc_greeting_uncached > "$_temp" || true
  _ARC_GREETING_OBSERVED_AT="$_now"
  if (( _ascii )); then
    _payload=$(python3 -c 'import sys; t=sys.stdin.read(); m={"●":"*","·":".","✓":"+","✗":"x","—":"-","–":"-","☠":"X","💀":"X","️":"","✧":"*"}; sys.stdout.write("".join(m.get(c,c) if ord(c)<128 or c in m else "?" for c in t))' < "$_temp" 2>/dev/null) || _payload='Greeting unavailable'
    printf '%s\n' "$_payload" > "$_temp"
  fi
  while IFS= read -r _payload; do printf '%s\n' "$_payload"; done < "$_temp"
  if (( _ttl > 0 )) && [[ ! -L "$_cacheRoot" && ! -L "$_cacheDir" ]]; then
    if (umask 077; mkdir -p "$_cacheDir") 2>/dev/null &&
       [[ -O "$_cacheDir" && "$(stat -c '%a' -- "$_cacheDir" 2>/dev/null)" == 700 ]]; then
      local _cacheTemp
      _cacheTemp=$(umask 077; mktemp "$_cacheDir/.station.XXXXXXXX" 2>/dev/null) || _cacheTemp=''
      if [[ -n "$_cacheTemp" ]]; then
        if {
          printf '%s\n' "$_now" "$_key" "${_ARC_GREETING_PHASE:-nyx}" "${_ARC_GREETING_RADAR_LABEL:-LOCAL_RADAR}" "${_ARC_GREETING_SESSION_STATE:-[ UNKNOWN ]}" "${_ARC_GREETING_RADAR_ROUTE_ONE:-}" "${_ARC_GREETING_RADAR_ROUTE_TWO:-}" "${_ARC_GREETING_RADAR_DNS_LABEL:-DNS_RADAR}" "${_ARC_GREETING_RADAR_LOCAL_IP:-}"
          while IFS= read -r _payload; do printf '%s\n' "$_payload"; done < "$_temp"
        } > "$_cacheTemp" 2>/dev/null; then
          mv -f -- "$_cacheTemp" "$_cache" 2>/dev/null || rm -f -- "$_cacheTemp"
        else
          rm -f -- "$_cacheTemp"
        fi
      fi
    fi
  fi
  rm -f -- "$_temp"
  return 0
}

# Data records are plain tab-delimited values, never executable shell input.
_arc_greeting_capture_row() {
  local _label="$1" _value="$2"
  _value="${_value//$'\n'/ }"; _value="${_value//$'\t'/ }"
  printf '%s\t%s\t%s\n' "$_label" "$_value" "${3:-}"
}
_arc_greeting_capture_section() { printf '@SECTION\t%s\n' "$1"; }
_arc_greeting_capture_word() { _arc_greeting_capture_row WOD "$1"; }
_arc_greeting_capture_footer() {
  _arc_greeting_capture_section 'RADAR & NAV'
  _arc_greeting_capture_row "$2" "$3${4:+ · $4}"
  [[ -z "$5" ]] || _arc_greeting_capture_row DNS_RADAR "$3 · $5"
  [[ -z "${8:-}" ]] || _arc_greeting_capture_row LOCAL_IP "${8}${9:+ · IP_CHECK $9}" "$TEXT" "$SYSTEM_BULLET"
  [[ -z "${10:-}" ]] || _arc_greeting_capture_row NET "${10}" "${11:-}"
  _arc_greeting_capture_row LOCAL_TIME "$6 · $1"
  _arc_greeting_capture_row '@MOTTO' 'E Pluribus Unum · ☠️💀☠️ · In God We Trust'
}
_arc_greeting_uncached() {
  local _rows _width _color=0 _result=0
  _rows=$(umask 077; mktemp "${TMPDIR:-/tmp}/arc-cockpit.XXXXXXXX" 2>/dev/null) || {
    printf 'Greeting unavailable: temporary storage.\n'; return 0;
  }
  _arc_greeting_collect_rows > "$_rows" || true
  _width=$(_arc_greeting_width)
  _arc_greeting_has_color && _color=1
  _arc_greeting_cockpit_render "$_rows" "$_width" "${_ARC_GREETING_PHASE:-nyx}" "$_color" "${ARC_GREETING_STYLE:-cockpit}" || _result=$?
  rm -f -- "$_rows"
  return "$_result"
}
_arc_greeting_cockpit_render() {
  python3 - "$@" <<'ARC_COCKPIT_PY'
from datetime import datetime
import sys,re,unicodedata
from pathlib import Path
path,widthText,phase,colorText,style=sys.argv[1:]
width=max(24,min(96,int(widthText))); color=colorText=="1"; plain=style=="plain"
palette={"nyx":(234,154,151),"choice":(94,200,237),"desire":(246,193,119),"still-pine":(196,167,231)}
phaseColor=palette.get(phase,palette["nyx"]); sage=(164,194,139); white=(226,229,233); dim=(112,124,132)
rose=(245,198,215); red=(255,68,92); green=(134,210,160); amber=(246,193,119)
methodColor=(94,200,237); quoteColor=(246,193,119)
def paint(s,c,bold=False):
 return ("\x1b["+("1;" if bold else "")+"38;2;%d;%d;%d"%c+"m"+s+"\x1b[0m") if color and s else s
def cells(s):return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ("W","F") else 1 for c in s)
def safe(s):return "".join(c for c in re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]","",s) if c>=" " and c!="\x7f")
def wrap(s,n):
 out=[]
 for para in s.splitlines() or [""]:
  line=""
  for word in para.split():
   if line and cells(line+" "+word)>n:out.append(line);line=word
   else:line=(line+" "+word).strip()
   while cells(line)>n:
    part=""
    for ch in line:
     if cells(part+ch)>n:break
     part+=ch
    if not part:break
    out.append(part);line=line[len(part):]
  out.append(line)
 return out
def clean(s):return re.sub(r"\x1b\[[0-9;]*m","",s)
groups={};section="COMMAND";words=[];studioLabel=""
lookup={"234;154;151":palette["nyx"],"94;200;237":palette["choice"],"246;193;119":palette["desire"],"196;167;231":palette["still-pine"],"164;194;139":sage,"112;124;132":dim,"226;229;233":white}
for raw in Path(path).read_text(encoding="utf-8").splitlines():
 f=raw.split("\t",2)
 if len(f)<2:continue
 key,text=safe(f[0]),safe(f[1]);tag=f[2] if len(f)>2 else ""
 if key=="@SECTION":section={"IDENTITY & INTENT":"COMMAND","OPERATIONS":"OPERATIONS","SYSTEMS":"SYSTEMS","RADAR & NAV":"RADAR"}.get(text,text);continue
 if key=="KHAOS-LAB":
  studioLabel=text
  continue
 base=next((c for marker,c in lookup.items() if marker in tag),white)
 (words if key=="WOD" else groups.setdefault(section,[])).append((key,text,base))
# Complete numbered passages, all 13 chapters: Sun Tzu, The Art of War.
# Lionel Giles (1910), public domain; https://www.gutenberg.org/ebooks/17405
sunTzuQuotes=(
 "The art of war is of vital importance to the State.",
 "It is a matter of life and death, a road either to safety or to ruin. Hence it is a subject of inquiry which can on no account be neglected.",
 "The art of war, then, is governed by five constant factors, to be taken into account in one’s deliberations, when seeking to determine the conditions obtaining in the field.",
 "These are: (1) The Moral Law; (2) Heaven; (3) Earth; (4) The Commander; (5) Method and discipline.",
 "The Moral Law causes the people to be in complete accord with their ruler, so that they will follow him regardless of their lives, undismayed by any danger.",
 "Heaven signifies night and day, cold and heat, times and seasons.",
 "Earth comprises distances, great and small; danger and security; open ground and narrow passes; the chances of life and death.",
 "The Commander stands for the virtues of wisdom, sincerity, benevolence, courage and strictness.",
 "By Method and discipline are to be understood the marshalling of the army in its proper subdivisions, the gradations of rank among the officers, the maintenance of roads by which supplies may reach the army, and the control of military expenditure.",
 "These five heads should be familiar to every general: he who knows them will be victorious; he who knows them not will fail.",
 "Therefore, in your deliberations, when seeking to determine the military conditions, let them be made the basis of a comparison, in this wise:—",
 "(1) Which of the two sovereigns is imbued with the Moral law? (2) Which of the two generals has most ability? (3) With whom lie the advantages derived from Heaven and Earth? (4) On which side is discipline most rigorously enforced? (5) Which army is the stronger? (6) On which side are officers and men more highly trained? (7) In which army is there the greater constancy both in reward and punishment?",
 "By means of these seven considerations I can forecast victory or defeat.",
 "The general that hearkens to my counsel and acts upon it, will conquer: let such a one be retained in command! The general that hearkens not to my counsel nor acts upon it, will suffer defeat:—let such a one be dismissed!",
 "While heeding the profit of my counsel, avail yourself also of any helpful circumstances over and beyond the ordinary rules.",
 "According as circumstances are favourable, one should modify one’s plans.",
 "All warfare is based on deception.",
 "Hence, when able to attack, we must seem unable; when using our forces, we must seem inactive; when we are near, we must make the enemy believe we are far away; when far away, we must make him believe we are near.",
 "Hold out baits to entice the enemy. Feign disorder, and crush him.",
 "If he is secure at all points, be prepared for him. If he is in superior strength, evade him.",
 "If your opponent is of choleric temper, seek to irritate him. Pretend to be weak, that he may grow arrogant.",
 "If he is taking his ease, give him no rest. If his forces are united, separate them.",
 "Attack him where he is unprepared, appear where you are not expected.",
 "These military devices, leading to victory, must not be divulged beforehand.",
 "Now the general who wins a battle makes many calculations in his temple ere the battle is fought. The general who loses a battle makes but few calculations beforehand. Thus do many calculations lead to victory, and few calculations to defeat: how much more no calculation at all! It is by attention to this point that I can foresee who is likely to win or lose.",
 "In the operations of war, where there are in the field a thousand swift chariots, as many heavy chariots, and a hundred thousand mail-clad soldiers, with provisions enough to carry them a thousand li, the expenditure at home and at the front, including entertainment of guests, small items such as glue and paint, and sums spent on chariots and armour, will reach the total of a thousand ounces of silver per day. Such is the cost of raising an army of 100,000 men.",
 "When you engage in actual fighting, if victory is long in coming, the men’s weapons will grow dull and their ardour will be damped. If you lay siege to a town, you will exhaust your strength.",
 "Again, if the campaign is protracted, the resources of the State will not be equal to the strain.",
 "Now, when your weapons are dulled, your ardour damped, your strength exhausted and your treasure spent, other chieftains will spring up to take advantage of your extremity. Then no man, however wise, will be able to avert the consequences that must ensue.",
 "Thus, though we have heard of stupid haste in war, cleverness has never been seen associated with long delays.",
 "There is no instance of a country having benefited from prolonged warfare.",
 "It is only one who is thoroughly acquainted with the evils of war that can thoroughly understand the profitable way of carrying it on.",
 "The skilful soldier does not raise a second levy, neither are his supply-waggons loaded more than twice.",
 "Bring war material with you from home, but forage on the enemy. Thus the army will have food enough for its needs.",
 "Poverty of the State exchequer causes an army to be maintained by contributions from a distance. Contributing to maintain an army at a distance causes the people to be impoverished.",
 "On the other hand, the proximity of an army causes prices to go up; and high prices cause the people’s substance to be drained away.",
 "When their substance is drained away, the peasantry will be afflicted by heavy exactions.",
 "With this loss of substance and exhaustion of strength, the homes of the people will be stripped bare, and three-tenths of their incomes will be dissipated; while Government expenses for broken chariots, worn-out horses, breast-plates and helmets, bows and arrows, spears and shields, protective mantlets, draught-oxen and heavy waggons, will amount to four-tenths of its total revenue.",
 "Hence a wise general makes a point of foraging on the enemy. One cartload of the enemy’s provisions is equivalent to twenty of one’s own, and likewise a single picul of his provender is equivalent to twenty from one’s own store.",
 "Now in order to kill the enemy, our men must be roused to anger; that there may be advantage from defeating the enemy, they must have their rewards.",
 "Therefore in chariot fighting, when ten or more chariots have been taken, those should be rewarded who took the first. Our own flags should be substituted for those of the enemy, and the chariots mingled and used in conjunction with ours. The captured soldiers should be kindly treated and kept.",
 "This is called, using the conquered foe to augment one’s own strength.",
 "In war, then, let your great object be victory, not lengthy campaigns.",
 "Thus it may be known that the leader of armies is the arbiter of the people’s fate, the man on whom it depends whether the nation shall be in peace or in peril.",
 "In the practical art of war, the best thing of all is to take the enemy’s country whole and intact; to shatter and destroy it is not so good. So, too, it is better to capture an army entire than to destroy it, to capture a regiment, a detachment or a company entire than to destroy them.",
 "Hence to fight and conquer in all your battles is not supreme excellence; supreme excellence consists in breaking the enemy’s resistance without fighting.",
 "Thus the highest form of generalship is to baulk the enemy’s plans; the next best is to prevent the junction of the enemy’s forces; the next in order is to attack the enemy’s army in the field; and the worst policy of all is to besiege walled cities.",
 "The rule is, not to besiege walled cities if it can possibly be avoided. The preparation of mantlets, movable shelters, and various implements of war, will take up three whole months; and the piling up of mounds over against the walls will take three months more.",
 "The general, unable to control his irritation, will launch his men to the assault like swarming ants, with the result that one-third of his men are slain, while the town still remains untaken. Such are the disastrous effects of a siege.",
 "Therefore the skilful leader subdues the enemy’s troops without any fighting; he captures their cities without laying siege to them; he overthrows their kingdom without lengthy operations in the field.",
 "With his forces intact he will dispute the mastery of the Empire, and thus, without losing a man, his triumph will be complete. This is the method of attacking by stratagem.",
 "It is the rule in war, if our forces are ten to the enemy’s one, to surround him; if five to one, to attack him; if twice as numerous, to divide our army into two.",
 "If equally matched, we can offer battle; if slightly inferior in numbers, we can avoid the enemy; if quite unequal in every way, we can flee from him.",
 "Hence, though an obstinate fight may be made by a small force, in the end it must be captured by the larger force.",
 "Now the general is the bulwark of the State: if the bulwark is complete at all points; the State will be strong; if the bulwark is defective, the State will be weak.",
 "There are three ways in which a ruler can bring misfortune upon his army:—",
 "(1) By commanding the army to advance or to retreat, being ignorant of the fact that it cannot obey. This is called hobbling the army.",
 "(2) By attempting to govern an army in the same way as he administers a kingdom, being ignorant of the conditions which obtain in an army. This causes restlessness in the soldier’s minds.",
 "(3) By employing the officers of his army without discrimination, through ignorance of the military principle of adaptation to circumstances. This shakes the confidence of the soldiers.",
 "But when the army is restless and distrustful, trouble is sure to come from the other feudal princes. This is simply bringing anarchy into the army, and flinging victory away.",
 "Thus we may know that there are five essentials for victory: (1) He will win who knows when to fight and when not to fight. (2) He will win who knows how to handle both superior and inferior forces. (3) He will win whose army is animated by the same spirit throughout all its ranks. (4) He will win who, prepared himself, waits to take the enemy unprepared. (5) He will win who has military capacity and is not interfered with by the sovereign. Victory lies in the knowledge of these five points.",
 "Hence the saying: If you know the enemy and know yourself, you need not fear the result of a hundred battles. If you know yourself but not the enemy, for every victory gained you will also suffer a defeat. If you know neither the enemy nor yourself, you will succumb in every battle.",
 "The good fighters of old first put themselves beyond the possibility of defeat, and then waited for an opportunity of defeating the enemy.",
 "To secure ourselves against defeat lies in our own hands, but the opportunity of defeating the enemy is provided by the enemy himself.",
 "Thus the good fighter is able to secure himself against defeat, but cannot make certain of defeating the enemy.",
 "Hence the saying: One may know how to conquer without being able to do it.",
 "Security against defeat implies defensive tactics; ability to defeat the enemy means taking the offensive.",
 "Standing on the defensive indicates insufficient strength; attacking, a superabundance of strength.",
 "The general who is skilled in defence hides in the most secret recesses of the earth; he who is skilled in attack flashes forth from the topmost heights of heaven. Thus on the one hand we have ability to protect ourselves; on the other, a victory that is complete.",
 "To see victory only when it is within the ken of the common herd is not the acme of excellence.",
 "Neither is it the acme of excellence if you fight and conquer and the whole Empire says, “Well done!”",
 "To lift an autumn hair is no sign of great strength; to see sun and moon is no sign of sharp sight; to hear the noise of thunder is no sign of a quick ear.",
 "What the ancients called a clever fighter is one who not only wins, but excels in winning with ease.",
 "Hence his victories bring him neither reputation for wisdom nor credit for courage.",
 "He wins his battles by making no mistakes. Making no mistakes is what establishes the certainty of victory, for it means conquering an enemy that is already defeated.",
 "Hence the skilful fighter puts himself into a position which makes defeat impossible, and does not miss the moment for defeating the enemy.",
 "Thus it is that in war the victorious strategist only seeks battle after the victory has been won, whereas he who is destined to defeat first fights and afterwards looks for victory.",
 "The consummate leader cultivates the moral law, and strictly adheres to method and discipline; thus it is in his power to control success.",
 "In respect of military method, we have, firstly, Measurement; secondly, Estimation of quantity; thirdly, Calculation; fourthly, Balancing of chances; fifthly, Victory.",
 "Measurement owes its existence to Earth; Estimation of quantity to Measurement; Calculation to Estimation of quantity; Balancing of chances to Calculation; and Victory to Balancing of chances.",
 "A victorious army opposed to a routed one, is as a pound’s weight placed in the scale against a single grain.",
 "The onrush of a conquering force is like the bursting of pent-up waters into a chasm a thousand fathoms deep. So much for tactical dispositions.",
 "The control of a large force is the same principle as the control of a few men: it is merely a question of dividing up their numbers.",
 "Fighting with a large army under your command is nowise different from fighting with a small one: it is merely a question of instituting signs and signals.",
 "To ensure that your whole host may withstand the brunt of the enemy’s attack and remain unshaken—this is effected by manœuvers direct and indirect.",
 "That the impact of your army may be like a grindstone dashed against an egg—this is effected by the science of weak points and strong.",
 "In all fighting, the direct method may be used for joining battle, but indirect methods will be needed in order to secure victory.",
 "Indirect tactics, efficiently applied, are inexhaustible as Heaven and Earth, unending as the flow of rivers and streams; like the sun and moon, they end but to begin anew; like the four seasons, they pass away but to return once more.",
 "There are not more than five musical notes, yet the combinations of these five give rise to more melodies than can ever be heard.",
 "There are not more than five primary colours (blue, yellow, red, white, and black), yet in combination they produce more hues than can ever be seen.",
 "There are not more than five cardinal tastes (sour, acrid, salt, sweet, bitter), yet combinations of them yield more flavours than can ever be tasted.",
 "In battle, there are not more than two methods of attack—the direct and the indirect; yet these two in combination give rise to an endless series of manœuvers.",
 "The direct and the indirect lead on to each other in turn. It is like moving in a circle—you never come to an end. Who can exhaust the possibilities of their combination?",
 "The onset of troops is like the rush of a torrent which will even roll stones along in its course.",
 "The quality of decision is like the well-timed swoop of a falcon which enables it to strike and destroy its victim.",
 "Therefore the good fighter will be terrible in his onset, and prompt in his decision.",
 "Energy may be likened to the bending of a crossbow; decision, to the releasing of the trigger.",
 "Amid the turmoil and tumult of battle, there may be seeming disorder and yet no real disorder at all; amid confusion and chaos, your array may be without head or tail, yet it will be proof against defeat.",
 "Simulated disorder postulates perfect discipline; simulated fear postulates courage; simulated weakness postulates strength.",
 "Hiding order beneath the cloak of disorder is simply a question of subdivision; concealing courage under a show of timidity presupposes a fund of latent energy; masking strength with weakness is to be effected by tactical dispositions.",
 "Thus one who is skilful at keeping the enemy on the move maintains deceitful appearances, according to which the enemy will act. He sacrifices something, that the enemy may snatch at it.",
 "By holding out baits, he keeps him on the march; then with a body of picked men he lies in wait for him.",
 "The clever combatant looks to the effect of combined energy, and does not require too much from individuals. Hence his ability to pick out the right men and utilise combined energy.",
 "When he utilises combined energy, his fighting men become as it were like unto rolling logs or stones. For it is the nature of a log or stone to remain motionless on level ground, and to move when on a slope; if four-cornered, to come to a standstill, but if round-shaped, to go rolling down.",
 "Thus the energy developed by good fighting men is as the momentum of a round stone rolled down a mountain thousands of feet in height. So much on the subject of energy.",
 "Whoever is first in the field and awaits the coming of the enemy, will be fresh for the fight; whoever is second in the field and has to hasten to battle, will arrive exhausted.",
 "Therefore the clever combatant imposes his will on the enemy, but does not allow the enemy’s will to be imposed on him.",
 "By holding out advantages to him, he can cause the enemy to approach of his own accord; or, by inflicting damage, he can make it impossible for the enemy to draw near.",
 "If the enemy is taking his ease, he can harass him; if well supplied with food, he can starve him out; if quietly encamped, he can force him to move.",
 "Appear at points which the enemy must hasten to defend; march swiftly to places where you are not expected.",
 "An army may march great distances without distress, if it marches through country where the enemy is not.",
 "You can be sure of succeeding in your attacks if you only attack places which are undefended.You can ensure the safety of your defence if you only hold positions that cannot be attacked.",
 "Hence that general is skilful in attack whose opponent does not know what to defend; and he is skilful in defence whose opponent does not know what to attack.",
 "O divine art of subtlety and secrecy! Through you we learn to be invisible, through you inaudible; and hence we can hold the enemy’s fate in our hands.",
 "You may advance and be absolutely irresistible, if you make for the enemy’s weak points; you may retire and be safe from pursuit if your movements are more rapid than those of the enemy.",
 "If we wish to fight, the enemy can be forced to an engagement even though he be sheltered behind a high rampart and a deep ditch. All we need do is attack some other place that he will be obliged to relieve.",
 "If we do not wish to fight, we can prevent the enemy from engaging us even though the lines of our encampment be merely traced out on the ground. All we need do is to throw something odd and unaccountable in his way.",
 "By discovering the enemy’s dispositions and remaining invisible ourselves, we can keep our forces concentrated, while the enemy’s must be divided.",
 "We can form a single united body, while the enemy must split up into fractions. Hence there will be a whole pitted against separate parts of a whole, which means that we shall be many to the enemy’s few.",
 "And if we are able thus to attack an inferior force with a superior one, our opponents will be in dire straits.",
 "The spot where we intend to fight must not be made known; for then the enemy will have to prepare against a possible attack at several different points; and his forces being thus distributed in many directions, the numbers we shall have to face at any given point will be proportionately few.",
 "For should the enemy strengthen his van, he will weaken his rear; should he strengthen his rear, he will weaken his van; should he strengthen his left, he will weaken his right; should he strengthen his right, he will weaken his left. If he sends reinforcements everywhere, he will everywhere be weak.",
 "Numerical weakness comes from having to prepare against possible attacks; numerical strength, from compelling our adversary to make these preparations against us.",
 "Knowing the place and the time of the coming battle, we may concentrate from the greatest distances in order to fight.",
 "But if neither time nor place be known, then the left wing will be impotent to succour the right, the right equally impotent to succour the left, the van unable to relieve the rear, or the rear to support the van. How much more so if the furthest portions of the army are anything under a hundred li apart, and even the nearest are separated by several li!",
 "Though according to my estimate the soldiers of Yüeh exceed our own in number, that shall advantage them nothing in the matter of victory. I say then that victory can be achieved.",
 "Though the enemy be stronger in numbers, we may prevent him from fighting. Scheme so as to discover his plans and the likelihood of their success.",
 "Rouse him, and learn the principle of his activity or inactivity. Force him to reveal himself, so as to find out his vulnerable spots.",
 "Carefully compare the opposing army with your own, so that you may know where strength is superabundant and where it is deficient.",
 "In making tactical dispositions, the highest pitch you can attain is to conceal them; conceal your dispositions, and you will be safe from the prying of the subtlest spies, from the machinations of the wisest brains.",
 "How victory may be produced for them out of the enemy’s own tactics—that is what the multitude cannot comprehend.",
 "All men can see the tactics whereby I conquer, but what none can see is the strategy out of which victory is evolved.",
 "Do not repeat the tactics which have gained you one victory, but let your methods be regulated by the infinite variety of circumstances.",
 "Military tactics are like unto water; for water in its natural course runs away from high places and hastens downwards.",
 "So in war, the way is to avoid what is strong and to strike at what is weak.",
 "Water shapes its course according to the nature of the ground over which it flows; the soldier works out his victory in relation to the foe whom he is facing.",
 "Therefore, just as water retains no constant shape, so in warfare there are no constant conditions.",
 "He who can modify his tactics in relation to his opponent and thereby succeed in winning, may be called a heaven-born captain.",
 "The five elements (water, fire, wood, metal, earth) are not always equally predominant; the four seasons make way for each other in turn. There are short days and long; the moon has its periods of waning and waxing.",
 "In war, the general receives his commands from the sovereign.",
 "Having collected an army and concentrated his forces, he must blend and harmonise the different elements thereof before pitching his camp.",
 "After that, comes tactical manœuvering, than which there is nothing more difficult. The difficulty of tactical manœuvering consists in turning the devious into the direct, and misfortune into gain.",
 "Thus, to take a long and circuitous route, after enticing the enemy out of the way, and though starting after him, to contrive to reach the goal before him, shows knowledge of the artifice of deviation.",
 "Manœuvering with an army is advantageous; with an undisciplined multitude, most dangerous.",
 "If you set a fully equipped army in march in order to snatch an advantage, the chances are that you will be too late. On the other hand, to detach a flying column for the purpose involves the sacrifice of its baggage and stores.",
 "Thus, if you order your men to roll up their buff-coats, and make forced marches without halting day or night, covering double the usual distance at a stretch, doing a hundred li in order to wrest an advantage, the leaders of all your three divisions will fall into the hands of the enemy.",
 "The stronger men will be in front, the jaded ones will fall behind, and on this plan only one-tenth of your army will reach its destination.",
 "If you march fifty li in order to outmanœuver the enemy, you will lose the leader of your first division, and only half your force will reach the goal.",
 "If you march thirty li with the same object, two-thirds of your army will arrive.",
 "We may take it then that an army without its baggage-train is lost; without provisions it is lost; without bases of supply it is lost.",
 "We cannot enter into alliances until we are acquainted with the designs of our neighbours.",
 "We are not fit to lead an army on the march unless we are familiar with the face of the country—its mountains and forests, its pitfalls and precipices, its marshes and swamps.",
 "We shall be unable to turn natural advantages to account unless we make use of local guides.",
 "In war, practise dissimulation, and you will succeed. Move only if there is a real advantage to be gained.",
 "Whether to concentrate or to divide your troops, must be decided by circumstances.",
 "Let your rapidity be that of the wind, your compactness that of the forest.",
 "In raiding and plundering be like fire, in immovability like a mountain.",
 "Let your plans be dark and impenetrable as night, and when you move, fall like a thunderbolt.",
 "When you plunder a countryside, let the spoil be divided amongst your men; when you capture new territory, cut it up into allotments for the benefit of the soldiery.",
 "Ponder and deliberate before you make a move.",
 "He will conquer who has learnt the artifice of deviation. Such is the art of manœuvering.",
 "The Book of Army Management says: On the field of battle, the spoken word does not carry far enough: hence the institution of gongs and drums. Nor can ordinary objects be seen clearly enough: hence the institution of banners and flags.",
 "Gongs and drums, banners and flags, are means whereby the ears and eyes of the host may be focussed on one particular point.",
 "The host thus forming a single united body, is it impossible either for the brave to advance alone, or for the cowardly to retreat alone. This is the art of handling large masses of men.",
 "In night-fighting, then, make much use of signal-fires and drums, and in fighting by day, of flags and banners, as a means of influencing the ears and eyes of your army.",
 "A whole army may be robbed of its spirit; a commander-in-chief may be robbed of his presence of mind.",
 "Now a soldier’s spirit is keenest in the morning; by noonday it has begun to flag; and in the evening, his mind is bent only on returning to camp.",
 "A clever general, therefore, avoids an army when its spirit is keen, but attacks it when it is sluggish and inclined to return. This is the art of studying moods.",
 "Disciplined and calm, to await the appearance of disorder and hubbub amongst the enemy:—this is the art of retaining self-possession.",
 "To be near the goal while the enemy is still far from it, to wait at ease while the enemy is toiling and struggling, to be well-fed while the enemy is famished:—this is the art of husbanding one’s strength.",
 "To refrain from intercepting an enemy whose banners are in perfect order, to refrain from attacking an army drawn up in calm and confident array:—this is the art of studying circumstances.",
 "It is a military axiom not to advance uphill against the enemy, nor to oppose him when he comes downhill.",
 "Do not pursue an enemy who simulates flight; do not attack soldiers whose temper is keen.",
 "Do not swallow a bait offered by the enemy. Do not interfere with an army that is returning home.",
 "When you surround an army, leave an outlet free. Do not press a desperate foe too hard.",
 "Such is the art of warfare.",
 "In war, the general receives his commands from the sovereign, collects his army and concentrates his forces.",
 "When in difficult country, do not encamp. In country where high roads intersect, join hands with your allies. Do not linger in dangerously isolated positions. In hemmed-in situations, you must resort to stratagem. In a desperate position, you must fight.",
 "There are roads which must not be followed, armies which must be not attacked, towns which must not be besieged, positions which must not be contested, commands of the sovereign which must not be obeyed.",
 "The general who thoroughly understands the advantages that accompany variation of tactics knows how to handle his troops.",
 "The general who does not understand these, may be well acquainted with the configuration of the country, yet he will not be able to turn his knowledge to practical account.",
 "So, the student of war who is unversed in the art of war of varying his plans, even though he be acquainted with the Five Advantages, will fail to make the best use of his men.",
 "Hence in the wise leader’s plans, considerations of advantage and of disadvantage will be blended together.",
 "If our expectation of advantage be tempered in this way, we may succeed in accomplishing the essential part of our schemes.",
 "If, on the other hand, in the midst of difficulties we are always ready to seize an advantage, we may extricate ourselves from misfortune.",
 "Reduce the hostile chiefs by inflicting damage on them; and make trouble for them, and keep them constantly engaged; hold out specious allurements, and make them rush to any given point.",
 "The art of war teaches us to rely not on the likelihood of the enemy’s not coming, but on our own readiness to receive him; not on the chance of his not attacking, but rather on the fact that we have made our position unassailable.",
 "There are five dangerous faults which may affect a general: (1) Recklessness, which leads to destruction; (2) cowardice, which leads to capture; (3) a hasty temper, which can be provoked by insults; (4) a delicacy of honour which is sensitive to shame; (5) over-solicitude for his men, which exposes him to worry and trouble.",
 "These are the five besetting sins of a general, ruinous to the conduct of war.",
 "When an army is overthrown and its leader slain, the cause will surely be found among these five dangerous faults. Let them be a subject of meditation.",
 "We come now to the question of encamping the army, and observing signs of the enemy. Pass quickly over mountains, and keep in the neighbourhood of valleys.",
 "Camp in high places, facing the sun. Do not climb heights in order to fight. So much for mountain warfare.",
 "After crossing a river, you should get far away from it.",
 "When an invading force crosses a river in its onward march, do not advance to meet it in mid-stream. It will be best to let half the army get across, and then deliver your attack.",
 "If you are anxious to fight, you should not go to meet the invader near a river which he has to cross.",
 "Moor your craft higher up than the enemy, and facing the sun. Do not move up-stream to meet the enemy. So much for river warfare.",
 "In crossing salt-marshes, your sole concern should be to get over them quickly, without any delay.",
 "If forced to fight in a salt-marsh, you should have water and grass near you, and get your back to a clump of trees. So much for operations in salt-marshes.",
 "In dry, level country, take up an easily accessible position with rising ground to your right and on your rear, so that the danger may be in front, and safety lie behind. So much for campaigning in flat country.",
 "These are the four useful branches of military knowledge which enabled the Yellow Emperor to vanquish four several sovereigns.",
 "All armies prefer high ground to low, and sunny places to dark.",
 "If you are careful of your men, and camp on hard ground, the army will be free from disease of every kind, and this will spell victory.",
 "When you come to a hill or a bank, occupy the sunny side, with the slope on your right rear. Thus you will at once act for the benefit of your soldiers and utilise the natural advantages of the ground.",
 "When, in consequence of heavy rains up-country, a river which you wish to ford is swollen and flecked with foam, you must wait until it subsides.",
 "Country in which there are precipitous cliffs with torrents running between, deep natural hollows, confined places, tangled thickets, quagmires and crevasses, should be left with all possible speed and not approached.",
 "While we keep away from such places, we should get the enemy to approach them; while we face them, we should let the enemy have them on his rear.",
 "If in the neighbourhood of your camp there should be any hilly country, ponds surrounded by aquatic grass, hollow basins filled with reeds, or woods with thick undergrowth, they must be carefully routed out and searched; for these are places where men in ambush or insidious spies are likely to be lurking.",
 "When the enemy is close at hand and remains quiet, he is relying on the natural strength of his position.",
 "When he keeps aloof and tries to provoke a battle, he is anxious for the other side to advance.",
 "If his place of encampment is easy of access, he is tendering a bait.",
 "Movement amongst the trees of a forest shows that the enemy is advancing. The appearance of a number of screens in the midst of thick grass means that the enemy wants to make us suspicious.",
 "The rising of birds in their flight is the sign of an ambuscade. Startled beasts indicate that a sudden attack is coming.",
 "When there is dust rising in a high column, it is the sign of chariots advancing; when the dust is low, but spread over a wide area, it betokens the approach of infantry. When it branches out in different directions, it shows that parties have been sent to collect firewood. A few clouds of dust moving to and fro signify that the army is encamping.",
 "Humble words and increased preparations are signs that the enemy is about to advance. Violent language and driving forward as if to the attack are signs that he will retreat.",
 "When the light chariots come out first and take up a position on the wings, it is a sign that the enemy is forming for battle.",
 "Peace proposals unaccompanied by a sworn covenant indicate a plot.",
 "When there is much running about and the soldiers fall into rank, it means that the critical moment has come.",
 "When some are seen advancing and some retreating, it is a lure.",
 "When the soldiers stand leaning on their spears, they are faint from want of food.",
 "If those who are sent to draw water begin by drinking themselves, the army is suffering from thirst.",
 "If the enemy sees an advantage to be gained and makes no effort to secure it, the soldiers are exhausted.",
 "If birds gather on any spot, it is unoccupied. Clamour by night betokens nervousness.",
 "If there is disturbance in the camp, the general’s authority is weak. If the banners and flags are shifted about, sedition is afoot. If the officers are angry, it means that the men are weary.",
 "When an army feeds its horses with grain and kills its cattle for food, and when the men do not hang their cooking-pots over the camp-fires, showing that they will not return to their tents, you may know that they are determined to fight to the death.",
 "The sight of men whispering together in small knots or speaking in subdued tones points to disaffection amongst the rank and file.",
 "Too frequent rewards signify that the enemy is at the end of his resources; too many punishments betray a condition of dire distress.",
 "To begin by bluster, but afterwards to take fright at the enemy’s numbers, shows a supreme lack of intelligence.",
 "When envoys are sent with compliments in their mouths, it is a sign that the enemy wishes for a truce.",
 "If the enemy’s troops march up angrily and remain facing ours for a long time without either joining battle or taking themselves off again, the situation is one that demands great vigilance and circumspection.",
 "If our troops are no more in number than the enemy, that is amply sufficient; it only means that no direct attack can be made. What we can do is simply to concentrate all our available strength, keep a close watch on the enemy, and obtain reinforcements.",
 "He who exercises no forethought but makes light of his opponents is sure to be captured by them.",
 "If soldiers are punished before they have grown attached to you, they will not prove submissive; and, unless submissive, then will be practically useless. If, when the soldiers have become attached to you, punishments are not enforced, they will still be useless.",
 "Therefore soldiers must be treated in the first instance with humanity, but kept under control by means of iron discipline. This is a certain road to victory.",
 "If in training soldiers commands are habitually enforced, the army will be well-disciplined; if not, its discipline will be bad.",
 "If a general shows confidence in his men but always insists on his orders being obeyed, the gain will be mutual.",
 "We may distinguish six kinds of terrain, to wit: (1) Accessible ground; (2) entangling ground; (3) temporising ground; (4) narrow passes; (5) precipitous heights; (6) positions at a great distance from the enemy.",
 "Ground which can be freely traversed by both sides is called accessible.",
 "With regard to ground of this nature, be before the enemy in occupying the raised and sunny spots, and carefully guard your line of supplies. Then you will be able to fight with advantage.",
 "Ground which can be abandoned but is hard to re-occupy is called entangling.",
 "From a position of this sort, if the enemy is unprepared, you may sally forth and defeat him. But if the enemy is prepared for your coming, and you fail to defeat him, then, return being impossible, disaster will ensue.",
 "When the position is such that neither side will gain by making the first move, it is called temporising ground.",
 "In a position of this sort, even though the enemy should offer us an attractive bait, it will be advisable not to stir forth, but rather to retreat, thus enticing the enemy in his turn; then, when part of his army has come out, we may deliver our attack with advantage.",
 "With regard to narrow passes, if you can occupy them first, let them be strongly garrisoned and await the advent of the enemy.",
 "Should the enemy forestall you in occupying a pass, do not go after him if the pass is fully garrisoned, but only if it is weakly garrisoned.",
 "With regard to precipitous heights, if you are beforehand with your adversary, you should occupy the raised and sunny spots, and there wait for him to come up.",
 "If the enemy has occupied them before you, do not follow him, but retreat and try to entice him away.",
 "If you are situated at a great distance from the enemy, and the strength of the two armies is equal, it is not easy to provoke a battle, and fighting will be to your disadvantage.",
 "These six are the principles connected with Earth. The general who has attained a responsible post must be careful to study them.",
 "Now an army is exposed to six several calamities, not arising from natural causes, but from faults for which the general is responsible. These are: (1) Flight; (2) insubordination; (3) collapse; (4) ruin; (5) disorganisation; (6) rout.",
 "Other conditions being equal, if one force is hurled against another ten times its size, the result will be the flight of the former.",
 "When the common soldiers are too strong and their officers too weak, the result is insubordination. When the officers are too strong and the common soldiers too weak, the result is collapse.",
 "When the higher officers are angry and insubordinate, and on meeting the enemy give battle on their own account from a feeling of resentment, before the commander-in-chief can tell whether or no he is in a position to fight, the result is ruin.",
 "When the general is weak and without authority; when his orders are not clear and distinct; when there are no fixed duties assigned to officers and men, and the ranks are formed in a slovenly haphazard manner, the result is utter disorganisation.",
 "When a general, unable to estimate the enemy’s strength, allows an inferior force to engage a larger one, or hurls a weak detachment against a powerful one, and neglects to place picked soldiers in the front rank, the result must be a rout.",
 "These are six ways of courting defeat, which must be carefully noted by the general who has attained a responsible post.",
 "The natural formation of the country is the soldier’s best ally; but a power of estimating the adversary, of controlling the forces of victory, and of shrewdly calculating difficulties, dangers and distances, constitutes the test of a great general.",
 "He who knows these things, and in fighting puts his knowledge into practice, will win his battles. He who knows them not, nor practises them, will surely be defeated.",
 "If fighting is sure to result in victory, then you must fight, even though the ruler forbid it; if fighting will not result in victory, then you must not fight even at the ruler’s bidding.",
 "The general who advances without coveting fame and retreats without fearing disgrace, whose only thought is to protect his country and do good service for his sovereign, is the jewel of the kingdom.",
 "Regard your soldiers as your children, and they will follow you into the deepest valleys; look on them as your own beloved sons, and they will stand by you even unto death.",
 "If, however, you are indulgent, but unable to make your authority felt; kind-hearted, but unable to enforce your commands; and incapable, moreover, of quelling disorder: then your soldiers must be likened to spoilt children; they are useless for any practical purpose.",
 "If we know that our own men are in a condition to attack, but are unaware that the enemy is not open to attack, we have gone only halfway towards victory.",
 "If we know that the enemy is open to attack, but are unaware that our own men are not in a condition to attack, we have gone only halfway towards victory.",
 "If we know that the enemy is open to attack, and also know that our men are in a condition to attack, but are unaware that the nature of the ground makes fighting impracticable, we have still gone only halfway towards victory.",
 "Hence the experienced soldier, once in motion, is never bewildered; once he has broken camp, he is never at a loss.",
 "Hence the saying: If you know the enemy and know yourself, your victory will not stand in doubt; if you know Heaven and know Earth, you may make your victory complete.",
 "The art of war recognises nine varieties of ground: (1) Dispersive ground; (2) facile ground; (3) contentious ground; (4) open ground; (5) ground of intersecting highways; (6) serious ground; (7) difficult ground; (8) hemmed-in ground; (9) desperate ground.",
 "When a chieftain is fighting in his own territory, it is dispersive ground.",
 "When he has penetrated into hostile territory, but to no great distance, it is facile ground.",
 "Ground the possession of which imports great advantage to either side, is contentious ground.",
 "Ground on which each side has liberty of movement is open ground.",
 "Ground which forms the key to three contiguous states, so that he who occupies it first has most of the Empire at his command, is ground of intersecting highways.",
 "When an army has penetrated into the heart of a hostile country, leaving a number of fortified cities in its rear, it is serious ground.",
 "Mountain forests, rugged steeps, marshes and fens—all country that is hard to traverse: this is difficult ground.",
 "Ground which is reached through narrow gorges, and from which we can only retire by tortuous paths, so that a small number of the enemy would suffice to crush a large body of our men: this is hemmed in ground.",
 "Ground on which we can only be saved from destruction by fighting without delay, is desperate ground.",
 "On dispersive ground, therefore, fight not. On facile ground, halt not. On contentious ground, attack not.",
 "On open ground, do not try to block the enemy’s way. On ground of intersecting highways, join hands with your allies.",
 "On serious ground, gather in plunder. In difficult ground, keep steadily on the march.",
 "On hemmed-in ground, resort to stratagem. On desperate ground, fight.",
 "Those who were called skilful leaders of old knew how to drive a wedge between the enemy’s front and rear; to prevent co-operation between his large and small divisions; to hinder the good troops from rescuing the bad, the officers from rallying their men.",
 "When the enemy’s men were scattered, they prevented them from concentrating; even when their forces were united, they managed to keep them in disorder.",
 "When it was to their advantage, they made a forward move; when otherwise, they stopped still.",
 "If asked how to cope with a great host of the enemy in orderly array and on the point of marching to the attack, I should say: “Begin by seizing something which your opponent holds dear; then he will be amenable to your will.”",
 "Rapidity is the essence of war: take advantage of the enemy’s unreadiness, make your way by unexpected routes, and attack unguarded spots.",
 "The following are the principles to be observed by an invading force: The further you penetrate into a country, the greater will be the solidarity of your troops, and thus the defenders will not prevail against you.",
 "Make forays in fertile country in order to supply your army with food.",
 "Carefully study the well-being of your men, and do not overtax them. Concentrate your energy and hoard your strength. Keep your army continually on the move, and devise unfathomable plans.",
 "Throw your soldiers into positions whence there is no escape, and they will prefer death to flight. If they will face death, there is nothing they may not achieve. Officers and men alike will put forth their uttermost strength.",
 "Soldiers when in desperate straits lose the sense of fear. If there is no place of refuge, they will stand firm. If they are in the heart of a hostile country, they will show a stubborn front. If there is no help for it, they will fight hard.",
 "Thus, without waiting to be marshalled, the soldiers will be constantly on the qui vive; without waiting to be asked, they will do your will; without restrictions, they will be faithful; without giving orders, they can be trusted.",
 "Prohibit the taking of omens, and do away with superstitious doubts. Then, until death itself comes, no calamity need be feared.",
 "If our soldiers are not overburdened with money, it is not because they have a distaste for riches; if their lives are not unduly long, it is not because they are disinclined to longevity.",
 "On the day they are ordered out to battle, your soldiers may weep, those sitting up bedewing their garments, and those lying down letting the tears run down their cheeks. But let them once be brought to bay, and they will display the courage of a Chu or a Kuei.",
 "The skilful tactician may be likened to the shuai-jan. Now the shuai-jan is a snake that is found in the Ch‘ang mountains. Strike at its head, and you will be attacked by its tail; strike at its tail, and you will be attacked by its head; strike at its middle, and you will be attacked by head and tail both.",
 "Asked if an army can be made to imitate the shuai-jan, I should answer, Yes. For the men of Wu and the men of Yüeh are enemies; yet if they are crossing a river in the same boat and are caught by a storm, they will come to each other’s assistance just as the left hand helps the right.",
 "Hence it is not enough to put one’s trust in the tethering of horses, and the burying of chariot wheels in the ground.",
 "The principle on which to manage an army is to set up one standard of courage which all must reach.",
 "How to make the best of both strong and weak—that is a question involving the proper use of ground.",
 "Thus the skilful general conducts his army just as though he were leading a single man, willy-nilly, by the hand.",
 "It is the business of a general to be quiet and thus ensure secrecy; upright and just, and thus maintain order.",
 "He must be able to mystify his officers and men by false reports and appearances, and thus keep them in total ignorance.",
 "By altering his arrangements and changing his plans, he keeps the enemy without definite knowledge. By shifting his camp and taking circuitous routes, he prevents the enemy from anticipating his purpose.",
 "At the critical moment, the leader of an army acts like one who has climbed up a height and then kicks away the ladder behind him. He carries his men deep into hostile territory before he shows his hand.",
 "He burns his boats and breaks his cooking-pots; like a shepherd driving a flock of sheep, he drives his men this way and that, and none knows whither he is going.",
 "To muster his host and bring it into danger:—this may be termed the business of the general.",
 "The different measures suited to the nine varieties of ground; the expediency of aggressive or defensive tactics; and the fundamental laws of human nature: these are things that must most certainly be studied.",
 "When invading hostile territory, the general principle is, that penetrating deeply brings cohesion; penetrating but a short way means dispersion.",
 "When you leave your own country behind, and take your army across neighbourhood territory, you find yourself on critical ground. When there are means of communication on all four sides, the ground is one of intersecting highways.",
 "When you penetrate deeply into a country, it is serious ground. When you penetrate but a little way, it is facile ground.",
 "When you have the enemy’s strongholds on your rear, and narrow passes in front, it is hemmed-in ground. When there is no place of refuge at all, it is desperate ground.",
 "Therefore, on dispersive ground, I would inspire my men with unity of purpose. On facile ground, I would see that there is close connection between all parts of my army.",
 "On contentious ground, I would hurry up my rear.",
 "On open ground, I would keep a vigilant eye on my defences. On ground of intersecting highways, I would consolidate my alliances.",
 "On serious ground, I would try to ensure a continuous stream of supplies. On difficult ground, I would keep pushing on along the road.",
 "On hemmed-in ground, I would block any way of retreat. On desperate ground, I would proclaim to my soldiers the hopelessness of saving their lives.",
 "For it is the soldier’s disposition to offer an obstinate resistance when surrounded, to fight hard when he cannot help himself, and to obey promptly when he has fallen into danger.",
 "We cannot enter into alliance with neighbouring princes until we are acquainted with their designs. We are not fit to lead an army on the march unless we are familiar with the face of the country—its mountains and forests, its pitfalls and precipices, its marshes and swamps. We shall be unable to turn natural advantages to account unless we make use of local guides.",
 "To be ignorant of any one of the following four or five principles does not befit a warlike prince.",
 "When a warlike prince attacks a powerful state, his generalship shows itself in preventing the concentration of the enemy’s forces. He overawes his opponents, and their allies are prevented from joining against him.",
 "Hence he does not strive to ally himself with all and sundry, nor does he foster the power of other states. He carries out his own secret designs, keeping his antagonists in awe. Thus he is able to capture their cities and overthrow their kingdoms.",
 "Bestow rewards without regard to rule, issue orders without regard to previous arrangements; and you will be able to handle a whole army as though you had to do with but a single man.",
 "Confront your soldiers with the deed itself; never let them know your design. When the outlook is bright, bring it before their eyes; but tell them nothing when the situation is gloomy.",
 "Place your army in deadly peril, and it will survive; plunge it into desperate straits, and it will come off in safety.",
 "For it is precisely when a force has fallen into harm’s way that is capable of striking a blow for victory.",
 "Success in warfare is gained by carefully accommodating ourselves to the enemy’s purpose.",
 "By persistently hanging on the enemy’s flank, we shall succeed in the long run in killing the commander-in-chief.",
 "This is called ability to accomplish a thing by sheer cunning.",
 "On the day that you take up your command, block the frontier passes, destroy the official tallies, and stop the passage of all emissaries.",
 "Be stern in the council-chamber, so that you may control the situation.",
 "If the enemy leaves a door open, you must rush in.",
 "Forestall your opponent by seizing what he holds dear, and subtly contrive to time his arrival on the ground.",
 "Walk in the path defined by rule, and accommodate yourself to the enemy until you can fight a decisive battle.",
 "At first, then, exhibit the coyness of a maiden, until the enemy gives you an opening; afterwards emulate the rapidity of a running hare, and it will be too late for the enemy to oppose you.",
 "There are five ways of attacking with fire. The first is to burn soldiers in their camp; the second is to burn stores; the third is to burn baggage-trains; the fourth is to burn arsenals and magazines; the fifth is to hurl dropping fire amongst the enemy.",
 "In order to carry out an attack, we must have means available. The material for raising fire should always be kept in readiness.",
 "There is a proper season for making attacks with fire, and special days for starting a conflagration.",
 "The proper season is when the weather is very dry; the special days are those when the moon is in the constellations of the Sieve, the Wall, the Wing or the Cross-bar; for these four are all days of rising wind.",
 "In attacking with fire, one should be prepared to meet five possible developments:",
 "(1) When fire breaks out inside the enemy’s camp, respond at once with an attack from without.",
 "(2) If there is an outbreak of fire, but the enemy’s soldiers remain quiet, bide your time and do not attack.",
 "(3) When the force of the flames has reached its height, follow it up with an attack, if that is practicable; if not, stay where you are.",
 "(4) If it is possible to make an assault with fire from without, do not wait for it to break out within, but deliver your attack at a favourable moment.",
 "(5) When you start a fire, be to windward of it. Do not attack from the leeward.",
 "A wind that rises in the daytime lasts long, but a night breeze soon falls.",
 "In every army, the five developments connected with fire must be known, the movements of the stars calculated, and a watch kept for the proper days.",
 "Hence those who use fire as an aid to the attack show intelligence; those who use water as an aid to the attack gain an accession of strength.",
 "By means of water, an enemy may be intercepted, but not robbed of all his belongings.",
 "Unhappy is the fate of one who tries to win his battles and succeed in his attacks without cultivating the spirit of enterprise; for the result is waste of time and general stagnation.",
 "Hence the saying: The enlightened ruler lays his plans well ahead; the good general cultivates his resources.",
 "Move not unless you see an advantage; use not your troops unless there is something to be gained; fight not unless the position is critical.",
 "No ruler should put troops into the field merely to gratify his own spleen; no general should fight a battle simply out of pique.",
 "If it is to your advantage, make a forward move; if not, stay where you are.",
 "Anger may in time change to gladness; vexation may be succeeded by content.",
 "But a kingdom that has once been destroyed can never come again into being; nor can the dead ever be brought back to life.",
 "Hence the enlightened ruler is heedful, and the good general full of caution. This is the way to keep a country at peace and an army intact.",
 "Raising a host of a hundred thousand men and marching them great distances entails heavy loss on the people and a drain on the resources of the State. The daily expenditure will amount to a thousand ounces of silver. There will be commotion at home and abroad, and men will drop down exhausted on the highways. As many as seven hundred thousand families will be impeded in their labor.",
 "Hostile armies may face each other for years, striving for the victory which is decided in a single day. This being so, to remain in ignorance of the enemy’s condition simply because one grudges the outlay of a hundred ounces of silver in honours and emoluments, is the height of inhumanity.",
 "One who acts thus is no leader of men, no present help to his sovereign, no master of victory.",
 "Thus, what enables the wise sovereign and the good general to strike and conquer, and achieve things beyond the reach of ordinary men, is foreknowledge.",
 "Now this foreknowledge cannot be elicited from spirits; it cannot be obtained inductively from experience, nor by any deductive calculation.",
 "Knowledge of the enemy’s dispositions can only be obtained from other men.",
 "Hence the use of spies, of whom there are five classes: (1) Local spies; (2) inward spies; (3) converted spies; (4) doomed spies; (5) surviving spies.",
 "When these five kinds of spy are all at work, none can discover the secret system. This is called “divine manipulation of the threads.” It is the sovereign’s most precious faculty.",
 "Having local spies means employing the services of the inhabitants of a district.",
 "Having inward spies, making use of officials of the enemy.",
 "Having converted spies, getting hold of the enemy’s spies and using them for our own purposes.",
 "Having doomed spies, doing certain things openly for purposes of deception, and allowing our own spies to know of them and report them to the enemy.",
 "Surviving spies, finally, are those who bring back news from the enemy’s camp.",
 "Hence it is that with none in the whole army are more intimate relations to be maintained than with spies. None should be more liberally rewarded. In no other business should greater secrecy be preserved.",
 "Spies cannot be usefully employed without a certain intuitive sagacity.",
 "They cannot be properly managed without benevolence and straightforwardness.",
 "Without subtle ingenuity of mind, one cannot make certain of the truth of their reports.",
 "Be subtle! be subtle! and use your spies for every kind of business.",
 "If a secret piece of news is divulged by a spy before the time is ripe, he must be put to death together with the man to whom the secret was told.",
 "Whether the object be to crush an army, to storm a city, or to assassinate an individual, it is always necessary to begin by finding out the names of the attendants, the aides-de-camp, the door-keepers and sentries of the general in command. Our spies must be commissioned to ascertain these.",
 "The enemy’s spies who have come to spy on us must be sought out, tempted with bribes, led away and comfortably housed. Thus they will become converted spies and available for our service.",
 "It is through the information brought by the converted spy that we are able to acquire and employ local and inward spies.",
 "It is owing to his information, again, that we can cause the doomed spy to carry false tidings to the enemy.",
 "Lastly, it is by his information that the surviving spy can be used on appointed occasions.",
 "The end and aim of spying in all its five varieties is knowledge of the enemy; and this knowledge can only be derived, in the first instance, from the converted spy. Hence it is essential that the converted spy be treated with the utmost liberality.",
 "Of old, the rise of the Yin dynasty was due to I Chih who had served under the Hsia. Likewise, the rise of the Chou dynasty was due to Lü Ya who had served under the Yin.",
 "Hence it is only the enlightened ruler and the wise general who will use the highest intelligence of the army for purposes of spying and thereby they achieve great results. Spies are a most important element in war, because on them depends an army’s ability to move.",
)
def sunTzuQuoteAt(moment):
 # Three local civil-time windows; stable across tabs, DST and restarts.
 slot=(moment.toordinal()-1)*3+moment.hour//8
 return sunTzuQuotes[slot%len(sunTzuQuotes)]
sunTzuQuote=sunTzuQuoteAt(datetime.now())
if words:words.append(("SUN TZU","“"+sunTzuQuote+"”",quoteColor))
values={k:t for records in groups.values() for k,t,_ in records}
def emit(s=""):print("  "+s if s else "")
def emit_center(s):
 visible=clean(s)
 emit(" "*max(0,(limit-cells(visible))//2)+s)
def divider(title):
 if plain:title=title.replace("·","-")
 marker,rule=("> ","-") if plain else ("⌜ ","─")
 label=marker+title.upper()
 emit(paint(label,sage,True)+" "+paint(rule*max(2,limit-cells(label)-1),dim))
def record(key,text,base,labelWidth=9):
 tint=base
 labelWidth=min(labelWidth,max(4,limit//3))
 if key in ("NET","SEC","LOCAL_RADAR","DNS_RADAR"):
  tint=green if any(x in text.lower() for x in ("up","station_ready","✓","open")) else red if "no_carrier" in text.lower() else amber
 if key=="TASKS":tint=amber if re.search(r"[1-9]",text) else green
 if key=="FOCUS":tint=palette["choice"]
 chunks=wrap(text,max(8,limit-labelWidth-4))
 return ["  "+paint(key.ljust(labelWidth),dim)+"  "+paint(chunks[0],tint)]+["  "+" "*labelWidth+"  "+paint(x,tint) for x in chunks[1:]]
limit=width-4
headerLeft="RIG 418 ·"
headerRight="b6ones6aw · ARCHITECT-OF-CHAOS"
headerText=headerLeft+"  "+headerRight
def header_left():
 return paint("RIG ",sage)+paint("418",red,True)+paint(" ·",dim)
def header_right():
 return paint("b6ones6aw",sage)+paint(" · ",dim)+paint("ARCHITECT-OF-CHAOS",dim)
if cells(headerText)<=limit:
 emit_center(header_left()+"  "+header_right())
else:
 def header_line(chunk):
  out=""
  for part in re.split(r"(RIG |418|b6ones6aw|ARCHITECT-OF-CHAOS|·)",chunk):
   tint=red if part=="418" else dim if part in ("·","ARCHITECT-OF-CHAOS") else sage
   out+=paint(part,tint,part=="418")
  return out
 for chunk in wrap(headerText,limit):emit_center(header_line(chunk))
if studioLabel:
 brand="KHAOS-LAB · "+studioLabel
 if plain:brand=brand.replace("·","-")
 marker="> " if plain else "⌜ "
 brandLine=marker+"KHAOS-LAB "+("- " if plain else "· ")+studioLabel
 if cells(brandLine)<=limit:
  emit_center(paint(marker+"KHAOS-LAB",phaseColor,True)+" "+paint(("- " if plain else "· ")+studioLabel,dim))
 else:
  emit_center(paint(marker+"KHAOS-LAB",phaseColor,True))
  for chunk in wrap(studioLabel,limit):emit_center(paint(chunk,dim))
# Put identity, brand, and the live local clock before rotating/status content.
for key,text,base in groups.get("RADAR",[]):
 if key=="LOCAL_TIME":
  suffix=" · "+phase
  stamp=text[:-len(suffix)] if text.endswith(suffix) else text
  badge="[ "+phase.upper()+" ]"
  chunks=wrap(stamp,limit)
  if cells(chunks[-1])+2+cells(badge)<=limit:chunks[-1]+="  "+badge
  else:chunks.append(badge)
  for chunk in chunks:
   if chunk==badge:
    emit_center(paint(badge,phaseColor,True))
   elif chunk.endswith(badge):
    emit_center(paint(chunk[:-len(badge)].rstrip(),base)+"  "+paint(badge,phaseColor,True))
   else:emit_center(paint(chunk,base))
 elif key=="@MOTTO":
  for chunk in wrap(text,limit):emit_center(paint(chunk,rose))
# WOD keeps its four established content colors, while the phase remains ambient.
if words:divider("WOD · INTERCEPT")
for key,text,_base in words:
 if key=="SUN TZU":
  for chunk in wrap("SUN TZU  "+text,limit):emit(paint(chunk,quoteColor))
  continue
 parts=re.split(r"( / | · )",text);colored=""
 for i,part in enumerate(parts):colored+=paint(part,dim if part.strip() in ("/","·") else list(palette.values())[min(i//2,3)])
 if cells(text)<=limit:emit(colored)
 else:
  for chunk in wrap(text,limit):emit(paint(chunk,list(palette.values())[min(len(chunk.split()),3)]))
if groups.get("COMMAND"):divider("COMMAND")
identity=values.get("IDENTITY","").split(" · ");node=identity[1] if len(identity)>1 else "unknown-node"
for key,text,base in groups.get("COMMAND",[]):
 if key=="IDENTITY":text=f"lt · {node} · arc"
 elif key=="USER":text=values.get("USER","unknown-user")
 if key=="METHOD":
  colored=re.sub(r" > "," "+paint(">",methodColor,True)+" ",text)
  if cells(text)+13<=limit:emit("  "+paint(key.ljust(9),dim)+"  "+colored)
  else:
   emit("  "+paint(key,dim))
   for chunk in wrap(text,max(5,limit-6)):
    emit("    "+re.sub(r" > "," "+paint(">",methodColor,True)+" ",chunk))
  continue
 for line in record(key,text,base):emit(line)
for title,name in (("OPERATIONS","OPERATIONS"),("SYSTEMS","SYSTEMS")):
 if groups.get(name):divider(title)
 for key,text,base in groups.get(name,[]):
  if key=="RAM":
   for line in record(key,text,base):emit(line)
  else:
   for line in record(key,text,base):emit(line)
if groups.get("RADAR"):divider("RADAR · NAV")
for key,text,base in groups.get("RADAR",[]):
 if key in ("@MOTTO","LOCAL_TIME"):
  continue
 for line in record(key,text,base,11):emit(line)
emit()
ARC_COCKPIT_PY
}
