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
  printf '%s\n' "$_location"
}

_arc_greeting_motto_body() {
  local _phase="$1" _rose='\033[38;2;245;198;215m' _glint _reset='\033[0m'
  local _width _line _before _body='E Pluribus Unum  · ☠  · In God We Trust' _glints='✧'
  _width=$(_arc_greeting_width)
  (( _width < 52 )) || _glints='✧ ✧'
  _arc_greeting_phase_colors "$_phase"
  _glint="$_ARC_GREETING_PHASE_BEAD"
  if ! _arc_greeting_has_color; then
    _rose=''; _glint=''; _reset=''
  fi
  while IFS= read -r _line; do
    if [[ "$_line" == *'✧'* ]]; then
      _before=${_line%%✧*}
      printf '  %b%s%b%b%s%b\n' "$_rose" "$_before" "$_reset" "$_glint" "${_line#"$_before"}" "$_reset"
    else
      printf '  %b%s%b\n' "$_rose" "$_line" "$_reset"
    fi
  done < <(_arc_greeting_wrap "$_body $_glints" "$((_width - 4))")
}

# One bounded, left-aligned divider for the complete greeting.
_arc_greeting_rule() {
  if [[ "${ARC_GREETING_STYLE:-cockpit}" == plain ]]; then printf '\n'; return 0; fi
  local _width _hull
  _width=$(_arc_greeting_width)
  if [[ "${_ARC_GREETING_SHIP:-0}" == 1 ]]; then
    _hull=$(printf '%*s' "$_width" '' | tr ' ' '_')
    printf '  %b\\%s/%b\n' "$MUTED" "$_hull" "$N"
    _hull=$(printf '%*s' "$((_width - 4))" '' | tr ' ' '_')
    printf '    %b\\%s/%b\n' "$MUTED" "$_hull" "$N"
    printf '      %b~    ~    ~    ~    ~%b\n\n' "$MUTED" "$N"
  else
    _hull=$(printf '%*s' "$((_width - 8))" '' | tr ' ' '_')
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
          disk) _valueTint="$_ARC_GREETING_CHOICE_COLOR" ;;
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

  local profile="${ARC_GREETING_PROFILE:-station}" host_name now session_state radar_label origin_name
  local SYSTEM_BULLET=''
  [[ -n "$N" ]] && SYSTEM_BULLET="$_ARC_GREETING_DESIRE_COLOR"
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
  _arc_greeting_capture_row 'IDENTITY' "lt · $(whoami) · arc" "$TEXT"
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

  local _memSnapshot _rootSnapshot
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

  local disk_used disk_free disk_pct sw_used sw_total shell_name shell_ver omz_tag=''
  disk_used=$(printf '%s\n' "$_rootSnapshot" | awk 'NR==2 {print $3}')
  disk_free=$(printf '%s\n' "$_rootSnapshot" | awk 'NR==2 {print $4}')
  disk_pct=$(printf '%s\n' "$_rootSnapshot" | awk 'NR==2 {print $5}')
  sw_used=$(printf '%s\n' "$_memSnapshot" | awk '/Swap:/ {print $3}')
  sw_total=$(printf '%s\n' "$_memSnapshot" | awk '/Swap:/ {print $2}')
  shell_name=$(basename "${SHELL:-zsh}")
  shell_ver=$("$SHELL" --version 2>/dev/null | head -1 | awk '{print $2}' | cut -d. -f1,2)
  [[ -d "$HOME/.oh-my-zsh" ]] && omz_tag='/omz'

  disk_used=${disk_used:-unknown}; disk_free=${disk_free:-unknown}; disk_pct=${disk_pct:-unknown}
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
  _arc_greeting_capture_row 'FOCUS' "${focus}" "$TEXT"
  _arc_greeting_capture_row 'TASKS' "${tasks_text}" "${tasks_color}"
  local ops_color="$snap_color"
  [[ "$sop_ack_str" == acked && "$sop_gp_str" == 'plan ✓' ]] || ops_color="$Y"
  _arc_greeting_capture_row 'SNAP' "${snap_text} · SOP ${sop_ack_str} · ${sop_gp_str} · TS ${ts_date} ${ts_tag}" "$ops_color"

  _arc_greeting_capture_section 'SYSTEMS'
  local network_color="$vpn_color"
  [[ "$dns_color" == "$Y" ]] && network_color="$Y"
  _arc_greeting_capture_row 'NET' "VPN ${vpn_text} · DNS ${dns_text}" "$network_color" "$SYSTEM_BULLET"
  local security_color="$G"
  [[ "$ufw_text$f2b_text$aa_text" == *✗* ]] && security_color="$R"
  [[ "$ufw_text$f2b_text$aa_text" != *"?"* ]] || security_color="$Y"
  [[ "$luks_text" == stale ]] && security_color="$R"
  _arc_greeting_capture_row 'SEC' "UFW ${ufw_text} · F2B ${f2b_text} · AA ${aa_text} · LUKS ${luks_text}" "$security_color" "$SYSTEM_BULLET"
  _arc_greeting_capture_row 'LOCAL_IP' "$local_ip" "$TEXT" "$SYSTEM_BULLET"
  local storage_color="$C"
  [[ "$usb_color" == "$Y" || "$fortress_color" == "$Y" ]] && storage_color="$Y"
  [[ "$usb_color" == "$D" && "$fortress_color" == "$D" ]] && storage_color="$D"
  _arc_greeting_capture_row 'STORE' "USB ${usb_text} · Fortress ${fortress_text}" "$storage_color" "$SYSTEM_BULLET"
  _arc_greeting_capture_row 'HOST' "disk ${disk_used}/${disk_free} free (${disk_pct}) · swap ${sw_used}/${sw_total} · shell ${shell_name} ${shell_ver}${omz_tag}" "$TEXT" "$SYSTEM_BULLET"
  _arc_greeting_capture_footer "$_phase" "$radar_label" "$session_state" "$routePairOne" "$routePairTwo" "$now" "$C"
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
  local _now _day _key _cacheRoot _cacheDir _cache _stamp _storedKey _payload _mode _terminalWidth _ttl=10 _temp=''
  _now=$(_arc_greeting_clock '%s')
  _day=$(_arc_greeting_clock '%F')
  _terminalWidth=$(_arc_greeting_width)
  _key="cockpit-v1|$_day|$(_arc_greeting_current_phase)|$_terminalWidth|${TERM:-dumb}|$_ARC_GREETING_COLOR|$ARC_GREETING_STYLE|$_ascii"
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
    _payload=$(python3 -c 'import sys; t=sys.stdin.read(); m={"●":"*","·":".","✓":"+","✗":"x","—":"-","–":"-","☠":"X","✧":"*"}; sys.stdout.write("".join(m.get(c,c) if ord(c)<128 or c in m else "?" for c in t))' < "$_temp" 2>/dev/null) || _payload='Greeting unavailable'
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
          printf '%s\n' "$_now" "$_key" "${_ARC_GREETING_PHASE:-nyx}" "${_ARC_GREETING_RADAR_LABEL:-LOCAL_RADAR}" "${_ARC_GREETING_SESSION_STATE:-[ UNKNOWN ]}" "${_ARC_GREETING_RADAR_ROUTE_ONE:-}" "${_ARC_GREETING_RADAR_ROUTE_TWO:-}" "${_ARC_GREETING_RADAR_DNS_LABEL:-DNS_RADAR}"
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
  _arc_greeting_capture_row LOCAL_TIME "$6 · $1"
  _arc_greeting_capture_row '@MOTTO' 'E Pluribus Unum · ☠ · In God We Trust ✧ ✧'
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
import sys,re,unicodedata
from pathlib import Path
dataPath,widthText,phase,colorText,style=sys.argv[1:]
width=max(24,min(96,int(widthText))); color=colorText=="1"; plain=style=="plain"
palette={"nyx":(234,154,151),"choice":(94,200,237),"desire":(246,193,119),"still-pine":(196,167,231)}
phaseAccent=palette.get(phase,palette["nyx"]); accent=(164,194,139)
neutral=(226,229,233); muted=(112,124,132); roseQuartz=(245,198,215)
reset="\x1b[0m" if color else ""
def paint(text,tint,bold=False,italic=False):
 style=[]
 if bold:style.append("1")
 if italic:style.append("3")
 style.append("38;2;%d;%d;%d"%tint)
 return ("\x1b["+";".join(style)+"m"+text+reset) if color else text
def cells(text):
 return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ("W","F") else 1 for c in text)
def safe(text):
 text=re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]","",text)
 return "".join(c for c in text if c>=" " and c!="\x7f")
def coloredChars(key,text,base):
 group=0; current=base; result=[]
 for token in re.findall(r"\s+|\S+",text):
  tint=base
  if key=="METHOD" and token==">":tint=accent
  elif key=="HOST":
   if token in ("disk","swap","shell"):current=palette[{"disk":"choice","swap":"desire","shell":"still-pine"}[token]]
   tint=current
  elif key=="RAM":tint=palette["desire" if group==0 else "choice"]
  elif key=="FOCUS":tint=palette["choice"]
  elif key=="MO":tint=palette["still-pine"]
  elif key in ("IDENTITY","I–III","IV–V","VI–VII"):tint=list(palette.values())[group%4]
  elif key=="WOD":tint=list(palette.values())[min(group,3)]
  elif key=="LOCAL_TIME" and token==phase:tint=phaseAccent
  elif key=="@MOTTO":tint=phaseAccent if "✧" in token else roseQuartz
  if token=="·" or (key=="WOD" and token=="/"):
   tint=muted;group+=1
  result.extend((c,tint) for c in token)
 return result
def wrapChars(chars,limit):
 lines=[];part=[];used=0
 for char,tint in chars:
  count=cells(char)
  if used+count>limit and part:
   spaces=[i for i,(c,_) in enumerate(part) if c==" "]
   cut=spaces[-1] if spaces else len(part)
   if cut:
    lines.append(part[:cut]);part=part[cut+1:] if cut<len(part) else []
   else:lines.append(part);part=[]
   used=sum(cells(c) for c,_ in part)
   if used+count>limit and part:lines.append(part);part=[];used=0
  if not part and char==" ":continue
  part.append((char,tint));used+=count
 if part or not lines:lines.append(part)
 return lines
def encoded(chars):
 if not color:return "".join(c for c,_ in chars)
 out=[];run="";last=None
 for char,tint in chars:
  if last is not None and tint!=last:
   out.append(paint(run,last));run=""
  run+=char;last=tint
 if run:out.append(paint(run,last))
 return "".join(out)
def visible(line):return cells(re.sub(r"\x1b\[[0-9;]*m","",line))
groups={};section="COMMAND";words=[]
for line in Path(dataPath).read_text(encoding="utf-8").splitlines():
 fields=line.split("\t",2)
 if len(fields)<2:continue
 key,text=safe(fields[0]),safe(fields[1]);tag=fields[2] if len(fields)>2 else ""
 if key=="@SECTION":
  section={"IDENTITY & INTENT":"COMMAND","OPERATIONS":"OPERATIONS","SYSTEMS":"SYSTEMS","RADAR & NAV":"RADAR"}.get(text,text)
  continue
 base=neutral
 tagPalette={"234;154;151":palette["nyx"],"94;200;237":palette["choice"],"246;193;119":palette["desire"],"196;167;231":palette["still-pine"],"164;194;139":accent,"128;137;145":(128,137,145),"112;124;132":muted,"226;229;233":neutral}
 for marker,tint in tagPalette.items():
  if marker in tag:base=tint;break
 if key=="WOD":words.append((key,text,base))
 else:groups.setdefault(section,[]).append((key,text,base))
def rows(records,inner):
 out=[]
 labelWidth=min(11,max((cells(key) for key,_,_ in records if key!="@MOTTO"),default=11))
 for key,text,base in records:
  if key=="@MOTTO":
   if out:out.append("")
   for chunk in wrapChars(coloredChars(key,text,base),inner-2):out.append(" "+encoded(chunk))
   continue
  if inner>=34:
   label=" "+key.ljust(labelWidth)+"  "; indent=" "*(labelWidth+3);limit=inner-labelWidth-4
   chunks=wrapChars(coloredChars(key,text,base),limit)
   for i,chunk in enumerate(chunks):out.append((paint(label,neutral) if i==0 else indent)+encoded(chunk))
  else:
   out.append(paint(" "+key,accent))
   for chunk in wrapChars(coloredChars(key,text,base),inner-4):out.append("   "+encoded(chunk))
 return out
def panel(title,records,size):
 inner=size-2
 title=" "+title+" "
 if cells(title)>inner:title=" HUD / WOD " if "WORD" in title else title[:inner]
 top="-"*max(0,inner-cells(title))+"+"
 result=[paint("+",muted)+paint(title,accent)+paint(top,muted)]
 for line in rows(records,inner):
  result.append(paint("|",muted)+line+" "*max(0,inner-visible(line))+paint("|",muted))
 result.append(paint("+"+"-"*inner+"+",muted))
 return result
def output(line=""):print("  "+line if line else "")
output()
measure=width-4
rightLabel="[ "+phase.upper()+" ]"; red=(255,68,92)
if plain:
 for label in ("COMMAND","OPERATIONS","SYSTEMS","RADAR"):
  for line in rows((words if label=="COMMAND" else [])+groups.get(label,[]),measure):output(line)
else:
 if measure>=52:
  prefix="[ KHAOS-LAB / "; code="418"; suffix=" / DEV-STUDIO ]"
 elif measure>=24:
  prefix="[ KHAOS-LAB / "; code="418"; suffix=" ]"
 else:
  prefix="[ KH / "; code="418"; suffix=" ]"
 leftLabel=prefix+code+suffix
 left=paint(prefix,accent)+paint(code,red,True)+paint(suffix,accent)
 if measure>=52:
  output(left+" "*max(1,measure-cells(leftLabel)-cells(rightLabel))+paint(rightLabel,phaseAccent))
 else:output(left)
 output()
 if words:
  for line in panel("HUD / WORD OF THE DAY",words,measure):output(line)
  output()
 for line in panel("01 / COMMAND",groups.get("COMMAND",[]),measure):output(line)
 output()
 if width>=96:
  # Give SYSTEMS a slight width bias; per-panel labels already reclaim space.
  # A quiet spacer row preserves one clean shared baseline when content wraps unevenly.
  paneWidth=measure-2
  leftWidth=paneWidth*49//100;rightWidth=paneWidth-leftWidth
  ops=list(groups.get("OPERATIONS",[]))
  values={key:text for records in groups.values() for key,text,_ in records}
  def quantity(value,unit):
   head=unit[:1].upper();power="KMGTPE".find(head)+1 if head else 0
   return float(value)*(1024**power)
  match=re.search(r"([\d.]+)([KMGTPE]?i?B?)/([\d.]+)([KMGTPE]?i?B?)",values.get("RAM",""),re.I)
  gauges=[]
  if match:
   total=quantity(match[3],match[4])
   if total>0:gauges.append(("ram-load",round(quantity(match[1],match[2])*100/total),palette["desire"]))
  match=re.search(r"\((\d+)%\)",values.get("HOST",""))
  if match:gauges.append(("disk-load",int(match[1]),palette["choice"]))
  for label,percent,tint in gauges:
   filled=max(0,min(10,round(percent/10)))
   meter=("#"*filled+"."*(10-filled)) if plain else ("█"*filled+"░"*(10-filled))
   ops.append((label,str(percent)+"% used  ["+meter+"]",tint))
  left=panel("02 / OPERATIONS",ops,leftWidth)
  rightLines=panel("03 / SYSTEMS",groups.get("SYSTEMS",[]),rightWidth)
  height=max(len(left),len(rightLines))
  while len(left)<height:left.insert(-1,paint("|"+" "*(leftWidth-2)+"|",muted))
  while len(rightLines)<height:rightLines.insert(-1,paint("|"+" "*(rightWidth-2)+"|",muted))
  for i in range(height):
   a=left[i] if i<len(left) else "";b=rightLines[i] if i<len(rightLines) else ""
   output(a+" "*max(0,leftWidth-visible(a))+"  "+b)
 else:
  for label,title in (("OPERATIONS","02 / OPERATIONS"),("SYSTEMS","03 / SYSTEMS")):
   for line in panel(title,groups.get(label,[]),measure):output(line)
   output()
 output()
 for line in panel("04 / RADAR & NAV",groups.get("RADAR",[]),measure):output(line)
output()

ARC_COCKPIT_PY
}
