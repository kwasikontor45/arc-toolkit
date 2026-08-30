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
  local CG='Recognize, construct, visualize, analyze, interpret.'

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

  # ── Butterfly ────────────────────────────────────────────────────────────────
  echo -e "  ${D}${CG}${N}"
  echo -e "             ${GOLD})(  )(${N}        "
  echo -e "           ${GOLD}/  \\\\  /  \\\\${N}      "
  echo -e "          ${GOLD}| \\\\      / |${N}     "
  echo -e "           ${ART}\\ \\\\    / /${N}      "
  echo -e "             ${ART}\\\\\\\\  //${N}        "
  echo -e "              ${ART}\\/\\/${N}          "

  # ── Identity ─────────────────────────────────────────────────────────────────
  echo -e "  ${C}${B}lt${N}  ${D}·${N}  ${M}$(whoami)${N}  ${D}·${N}  ${ART}arc${N}"
  echo -e "      ${M}$(date '+%a %d %b %Y')${N}  ${D}·${N}  ${C}$(date '+%H:%M')${N}  ${D}·${N}  ${ART}${_phase}${N}"

  # ── Motd ─────────────────────────────────────────────────────────────────────
  local MOTD_FILE="$HOME/.config/arc/motd"
  if [[ -f "$MOTD_FILE" ]]; then
    local motd
    motd=$(cat "$MOTD_FILE" 2>/dev/null)
    echo -e "  ${D}${motd}${N}"
  fi

  echo ""

  # ── Workflow ─────────────────────────────────────────────────────────────────

  # Memory
  local mem_used mem_free mem_total
  mem_used=$(free -h | awk '/Mem:/ {print $3}')
  mem_free=$(free -h | awk '/Mem:/ {print $7}')
  mem_total=$(free -h | awk '/Mem:/ {print $2}')
  echo -e "  ${D}[✧]${N} ${C}memory${D}·················${N}${M}${mem_used}${N} used ${D}·${N} ${M}${mem_free}${N} free ${D}/ ${mem_total}${N}"

  # Focus
  local LT_FOCUS="$HOME/.local/share/lt/focus"
  if [[ -f "$LT_FOCUS" ]] && [[ -s "$LT_FOCUS" ]]; then
    echo -e "  ${D}[✧]${N} ${C}focus${D}··················${N}${M}$(cat "$LT_FOCUS")${N}"
  fi

  # Tasks
  local LT_TASKS="$HOME/.local/share/lt/tasks"
  if [[ -f "$LT_TASKS" ]]; then
    local pending
    pending=$(grep -c '^pending ' "$LT_TASKS" 2>/dev/null || echo 0)
    if (( pending > 0 )); then
      echo -e "  ${D}[✧]${N} ${C}tasks${D}··················${N}${Y}${pending} pending${N}"
    else
      echo -e "  ${D}[✧]${N} ${C}tasks${D}··················${N}${D}clear${N}"
    fi
  fi

  # Snap reminder
  # Bug fixed 2026-08-13: this used to read ~/.usb-bakup/.last-sync (the
  # unrelated bakup-usb stamp), which could show e.g. "1d since last
  # snapshot" even with zero Timeshift snapshots ever taken. `arc snap` is
  # just `timeshift-check --manual` (cmd_snap), so check the same
  # /var/cache/timeshift-last-snapshot the timeshift status line below uses.
  local STAMP="/var/cache/timeshift-last-snapshot"
  if [[ -f "$STAMP" ]]; then
    local snap_date last_epoch now_epoch days_ago
    snap_date=$(cat "$STAMP" 2>/dev/null | grep -oP '\d{4}-\d{2}-\d{2}' | head -1)
    last_epoch=$(date -d "$snap_date" +%s 2>/dev/null || echo 0)
    now_epoch=$(date +%s)
    days_ago=$(( (now_epoch - last_epoch) / 86400 ))
    if (( days_ago >= 1 )); then
      echo -e "  ${D}[✧]${N} ${C}snap${D}···················${N}${Y}arc snap${N} ${D}— ${days_ago}d since last snapshot${N}"
    else
      echo -e "  ${D}[✧]${N} ${C}snap${D}···················${N}${D}today ✓${N}"
    fi
  else
    echo -e "  ${D}[✧]${N} ${C}snap${D}···················${N}${Y}arc snap${N} ${D}— trigger snapshot + MEGA sync${N}"
  fi

  # SOP status — fast sqlite3 + grep, no subprocess overhead
  local sop_today sop_ack_count sop_gp_ok sop_ack_str sop_gp_str
  sop_today=$(date '+%Y-%m-%d')
  sop_ack_count=0
  if command -v python3 &>/dev/null && [[ -f "$HOME/.config/arc/sop/arc-sop.db" ]]; then
    sop_ack_count=$(python3 -c "
import sqlite3, sys
try:
    conn = sqlite3.connect('$HOME/.config/arc/sop/arc-sop.db')
    print(conn.execute(\"SELECT COUNT(*) FROM acks WHERE timestamp LIKE ?\", ('${sop_today}%',)).fetchone()[0])
except Exception:
    print(0)
" 2>/dev/null || echo 0)
  fi
  sop_gp_ok=0
  grep -q "${sop_today}.*\[STARTING\]" "$HOME/dev-notes/intel-ops/GAMEPLAN.md" 2>/dev/null && sop_gp_ok=1

  (( sop_ack_count > 0 )) && sop_ack_str="${G}acked${N}" || sop_ack_str="${Y}no ack${N}"
  (( sop_gp_ok ))         && sop_gp_str="${G}gameplan ✓${N}" || sop_gp_str="${Y}no gameplan entry${N}"
  echo -e "  ${D}[✧]${N} ${C}sop${D}·····················${N}${sop_ack_str}  ${D}·${N}  ${sop_gp_str}"

  # vpn — proton0 interface presence, no sudo, no live protonvpn CLI round-trip
  # (same "cheap local check only" philosophy as the security-stack rows below).
  # Replaced the old "mirrors" row 2026-08-22 (stale-looking, last-sync timestamp
  # from 2026-08-18 sitting there for days) with something that actually changes
  # and matters day to day. `arc mirrors` still exists for the real repo-sync
  # status if needed, just not on this always-visible banner anymore.
  local vpn_ip
  vpn_ip=$(ip -br addr show proton0 2>/dev/null | awk '{print $3}' | cut -d/ -f1)
  if [[ -n "$vpn_ip" ]]; then
    echo -e "  ${D}[✧]${N} ${C}vpn${D}····················${N}${G}connected${N}  ${D}· ${vpn_ip}${N}"
  else
    echo -e "  ${D}[✧]${N} ${C}vpn${D}····················${N}${Y}disconnected${N}  ${D}— arc vpn connect${N}"
  fi

  echo ""

  # ── Security stack — no sudo, process checks only ─────────────────────────

  # DNS
  if systemctl is-active --quiet nextdns 2>/dev/null; then
    echo -e "  ${D}[✧]${N} ${C}dns${D}····················${N}${G}nextdns active${N}"
  else
    echo -e "  ${D}[✧]${N} ${C}dns${D}····················${N}${D}local ${D}·${N} ${Y}arc dns on${N} to activate${N}"
  fi

  # UFW — systemctl check, no sudo
  if systemctl is-active --quiet ufw 2>/dev/null; then
    echo -e "  ${D}[✧]${N} ${C}ufw${D}····················${N}${G}✓${N}"
  else
    echo -e "  ${D}[✧]${N} ${C}ufw${D}····················${N}${R}✗  inactive${N}"
  fi

  # Fail2ban — pgrep only, no sudo
  if pgrep -x "fail2ban-server" &>/dev/null; then
    echo -e "  ${D}[✧]${N} ${C}fail2ban${D}·············${N}${G}✓${N}"
  else
    echo -e "  ${D}[✧]${N} ${C}fail2ban${D}·············${N}${R}✗  not running${N}"
  fi

  # AppArmor
  if systemctl is-active --quiet apparmor 2>/dev/null; then
    echo -e "  ${D}[✧]${N} ${C}apparmor${D}·············${N}${G}✓${N}"
  else
    echo -e "  ${D}[✧]${N} ${C}apparmor${D}·············${N}${R}✗${N}"
  fi

  # LUKS — mapper device stays alive after USB unplug; check I/O too
  if [[ -b /dev/mapper/storage_crypt ]]; then
    if ls /mnt/storage/ >/dev/null 2>&1; then
      echo -e "  ${D}[✧]${N} ${C}luks${D}···················${N}${G}✓${N}"
    else
      echo -e "  ${D}[✧]${N} ${C}luks${D}···················${N}${Y}stale${N}  ${D}(USB unplugged?)${N}"
    fi
  else
    echo -e "  ${D}[✧]${N} ${C}luks${D}···················${N}${D}closed${N}"
  fi

  echo ""

  # ── Network ──────────────────────────────────────────────────────────────────

  # Local IP — fast, no network call
  local local_ip
  local_ip=$(hostname -I 2>/dev/null | awk '{print $1}')

  # External IP — timeout 2s, graceful fallback
  local ext_ip
  ext_ip=$(curl -s --max-time 2 https://api.ipify.org 2>/dev/null)
  [[ -z "$ext_ip" ]] && ext_ip="${D}offline${N}"

  echo -e "  ${D}[✧]${N} ${C}ip${D}·····················${N}${M}${local_ip}${N}  ${D}·  ext${N}  ${M}${ext_ip}${N}"

  echo ""

  # ── Storage ───────────────────────────────────────────────────────────────────

  # USB — real I/O test so a stale dm-crypt mount doesn't lie
  if mountpoint -q /mnt/storage 2>/dev/null && ls /mnt/storage/ >/dev/null 2>&1; then
    local uu uf
    uu=$(df -h /mnt/storage | awk 'NR==2 {print $3}')
    uf=$(df -h /mnt/storage | awk 'NR==2 {print $4}')
    echo -e "  ${D}[✧]${N} ${C}usb${D}····················${N}${G}✓${N}  ${M}${uu}${N} used ${D}·${N} ${M}${uf}${N} free"
  elif mountpoint -q /mnt/storage 2>/dev/null; then
    echo -e "  ${D}[✧]${N} ${C}usb${D}····················${N}${Y}stale${N}  ${D}— arc mount to repair${N}"
  else
    echo -e "  ${D}[✧]${N} ${C}usb${D}····················${N}${D}not mounted${N}"
  fi

  # Fortress (Timeshift snapshot partition) -- same real I/O test as usb above
  if mountpoint -q /fortress 2>/dev/null && ls /fortress/ >/dev/null 2>&1; then
    local fu ff
    fu=$(df -h /fortress | awk 'NR==2 {print $3}')
    ff=$(df -h /fortress | awk 'NR==2 {print $4}')
    echo -e "  ${D}[✧]${N} ${C}fortress${D}·············${N}${G}✓${N}  ${M}${fu}${N} used ${D}·${N} ${M}${ff}${N} free"
  elif mountpoint -q /fortress 2>/dev/null; then
    echo -e "  ${D}[✧]${N} ${C}fortress${D}·············${N}${Y}stale${N}  ${D}— check mount${N}"
  else
    echo -e "  ${D}[✧]${N} ${C}fortress${D}·············${N}${D}not mounted${N}"
  fi

  # Disk
  local disk_used disk_free disk_pct
  disk_used=$(df -h / | awk 'NR==2 {print $3}')
  disk_free=$(df -h / | awk 'NR==2 {print $4}')
  disk_pct=$(df / | awk 'NR==2 {print $5}')
  echo -e "  ${D}[✧]${N} ${C}disk${D}···················${N}${M}${disk_used}${N} used ${D}·${N} ${M}${disk_free}${N} free  ${D}(${disk_pct})${N}"

  # Shell
  local shell_name shell_ver omz_tag=""
  shell_name=$(basename "${SHELL:-zsh}")
  shell_ver=$("$SHELL" --version 2>/dev/null | head -1 | awk '{print $2}' | cut -d. -f1,2)
  [[ -d "$HOME/.oh-my-zsh" ]] && omz_tag=" ${D}· omz${N}"
  echo -e "  ${D}[✧]${N} ${C}shell${D}··················${N}${M}${shell_name} ${shell_ver}${N}${omz_tag}"

  # Swap
  local sw_used sw_total
  sw_used=$(free -h | awk '/Swap:/ {print $3}')
  sw_total=$(free -h | awk '/Swap:/ {print $2}')
  echo -e "  ${D}[✧]${N} ${C}swap${D}···················${N}${M}${sw_used}${N} ${D}/${N} ${M}${sw_total}${N}"

  # Timeshift
  local ts_name="" ts_date="" ts_manual=""
  if [[ -f "/var/cache/timeshift-last-snapshot" ]]; then
    ts_name=$(cat /var/cache/timeshift-last-snapshot 2>/dev/null)
    ts_date=$(echo "$ts_name" | grep -oP '\d{4}-\d{2}-\d{2}' | head -1)
    [[ -f "/var/cache/timeshift-last-run-manual" ]] && ts_manual=$(cat /var/cache/timeshift-last-run-manual 2>/dev/null | tr -d '[:space:]')
  fi

  if [[ -n "$ts_date" ]]; then
    local ts_tag=""
    [[ "$ts_manual" == "1" ]] && ts_tag=" ${D}·${N} ${C}manual${N}"
    echo -e "  ${D}[✧]${N} ${C}timeshift${D}·············${N}${D}${ts_date}${ts_tag}${N}"
  else
    echo -e "  ${D}[✧]${N} ${C}timeshift${D}·············${N}${D} · manual${N}"
  fi

  echo ""
}
