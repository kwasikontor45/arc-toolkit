#!/bin/bash
# ~/.config/arc/greeting.sh — terminal greeting
# Sourced by .bashrc and .zshrc on shell start
# No sudo calls — process checks only for security stack

_arc_greeting() {
  # ── Colors ───────────────────────────────────────────────────────────────────
  local G='\033[0;32m'
  local R='\033[0;31m'
  local Y='\033[1;33m'
  local D='\033[0;90m'
  local M='\033[38;5;250m'
  local B='\033[1m'
  local N='\033[0m'
  local CG='Recognize > construct > visualize > analyze > interpret'

  # ── Circadian ────────────────────────────────────────────────────────────────
  # C  = current phase accent (all labels)
  # GOLD = previous phase (butterfly top — where you came from)
  # ART  = current phase bold (butterfly bottom — where you are)
  local _h; _h=$(date +%-H)
  local _phase C GOLD ART
  if   (( _h >= 6  && _h < 11 )); then
    _phase="choice"
    C='\033[38;5;80m'         # Midnight Ocean
    GOLD='\033[38;5;210m'     # prev: nyx rose
    ART='\033[1;38;5;80m'     # bold teal
  elif (( _h >= 11 && _h < 17 )); then
    _phase="desire"
    C='\033[38;5;222m'        # Rose Pine Gold
    GOLD='\033[38;5;80m'      # prev: choice teal
    ART='\033[1;38;5;222m'    # bold gold
  elif (( _h >= 17 && _h < 21 )); then
    _phase="still-pine"
    C='\033[38;5;183m'        # Rose Pine Iris
    GOLD='\033[38;5;222m'     # prev: desire gold
    ART='\033[1;38;5;183m'    # bold iris
  else
    _phase="nyx"
    C='\033[38;5;210m'        # Rose Pine Rose
    GOLD='\033[38;5;183m'     # prev: still-pine iris
    ART='\033[1;38;5;210m'    # bold rose
  fi

  # ── Compact mark, identity, method, and clock ────────────────────────────────
  printf '  %b)(  )(%b  %blt%b %b·%b %b%s%b %b·%b %barc%b\n' \
    "$GOLD" "$N" "$C" "$N" "$D" "$N" "$M" "$(whoami)" "$N" "$D" "$N" "$ART" "$N"
  printf '  %b/  \\ /  \\%b  %b%s%b %b·%b %b%s%b %b·%b %b%s%b\n' \
    "$GOLD" "$N" "$M" "$(date '+%a %d %b %Y')" "$N" "$D" "$N" \
    "$C" "$(date '+%H:%M')" "$N" "$D" "$N" "$ART" "${_phase}" "$N"
  printf '  %b\\  V  /%b  %b%s%b\n' "$ART" "$N" "$D" "$CG" "$N"

  # Daily word comes from a small local Arc dataset. Suppress a missing/bad
  # source so it can never disrupt shell startup; no network or user data.
  local word_line
  word_line=$(command arc word --compact 2>/dev/null)
  word_line=${word_line/ · adjective · / · adj. · }
  [[ -n "$word_line" ]] && printf '  %bWOD%b  %s\n' "$C" "$N" "$word_line"

  # ── Motd ─────────────────────────────────────────────────────────────────────
  local MOTD_FILE="$HOME/.config/arc/motd"
  if [[ -f "$MOTD_FILE" ]]; then
    local motd_line
    while IFS= read -r motd_line || [[ -n "$motd_line" ]]; do
      printf '  %b%s%b\n' "$D" "$motd_line" "$N"
    done < "$MOTD_FILE"
  fi

  # ── Compact live status ─────────────────────────────────────────────────────
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

  local local_ip ext_ip ext_color
  local_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  local_ip=${local_ip:-offline}
  ext_ip=$(curl -s --max-time 2 https://api.ipify.org 2>/dev/null)
  if [[ -n "$ext_ip" ]]; then ext_color="$M"; else ext_ip='offline'; ext_color="$D"; fi

  # Storage checks include actual mount I/O to avoid reporting a stale mount as healthy.
  local usb_text fortress_text uu uf fu ff
  if mountpoint -q /mnt/storage 2>/dev/null && ls /mnt/storage/ >/dev/null 2>&1; then
    uu=$(df -h /mnt/storage | awk 'NR==2 {print $3}')
    uf=$(df -h /mnt/storage | awk 'NR==2 {print $4}')
    usb_text="${uu} used / ${uf} free"; usb_color="$M"
  elif mountpoint -q /mnt/storage 2>/dev/null; then usb_text='stale · arc mount'; usb_color="$Y"
  else usb_text='not mounted'; usb_color="$D"; fi
  if mountpoint -q /fortress 2>/dev/null && ls /fortress/ >/dev/null 2>&1; then
    fu=$(df -h /fortress | awk 'NR==2 {print $3}')
    ff=$(df -h /fortress | awk 'NR==2 {print $4}')
    fortress_text="${fu} used / ${ff} free"; fortress_color="$M"
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

  printf '  %bRAM%b %b%s/%s used%b · %b%s free%b  %bfocus%b %b%s%b · %btodo%b %b%s%b\n' \
    "$C" "$N" "$M" "$mem_used" "$mem_total" "$N" "$M" "$mem_free" "$N" \
    "$C" "$N" "$M" "$focus" "$N" "$C" "$N" "$tasks_color" "$tasks_text" "$N"
  printf '  %bsnap%b %b%s%b · %bSOP%b %b%s%b %b%s%b · %bTS%b %s %s\n' \
    "$C" "$N" "$snap_color" "$snap_text" "$N" "$C" "$N" \
    "$sop_ack_color" "$sop_ack_str" "$N" "$sop_gp_color" "$sop_gp_str" "$N" \
    "$C" "$N" "$ts_date" "$ts_tag"
  printf '  %bVPN%b %b%s%b · %bDNS%b %b%s%b\n' \
    "$C" "$N" "$vpn_color" "$vpn_text" "$N" "$C" "$N" "$dns_color" "$dns_text" "$N"
  printf '  %bUFW%b %b%s%b · %bF2B%b %b%s%b · %bAA%b %b%s%b · %bLUKS%b %b%s%b\n' \
    "$C" "$N" "$ufw_color" "$ufw_text" "$N" "$C" "$N" "$f2b_color" "$f2b_text" "$N" \
    "$C" "$N" "$aa_color" "$aa_text" "$N" "$C" "$N" "$luks_color" "$luks_text" "$N"
  printf '  %bIP%b %b%s%b · %bext%b %b%s%b\n' \
    "$C" "$N" "$M" "$local_ip" "$N" "$C" "$N" "$ext_color" "$ext_ip" "$N"
  printf '  %bUSB%b %b%s%b · %bFortress%b %b%s%b\n' \
    "$C" "$N" "$usb_color" "$usb_text" "$N" "$C" "$N" "$fortress_color" "$fortress_text" "$N"
  printf '  %bdisk%b %b%s/%s free (%s)%b · %bswap%b %b%s/%s%b · %bshell%b %b%s %s%s%b\n' \
    "$C" "$N" "$M" "$disk_used" "$disk_free" "$disk_pct" "$N" \
    "$C" "$N" "$M" "$sw_used" "$sw_total" "$N" \
    "$C" "$N" "$M" "$shell_name" "$shell_ver" "$omz_tag" "$N"

}
