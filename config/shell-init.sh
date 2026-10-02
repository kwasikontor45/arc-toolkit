# arc shell integration — sourced by both ~/.bashrc and ~/.zshrc
# Keeps `arc shell` / `arc reload` behavior identical across bash and zsh.

# nvm — was only ever sourced in .bashrc, never .zshrc, despite zsh being the
# actual login shell (same class of bug as the arc()/greeting one fixed
# earlier: something that worked "because bash happened to have it" while
# the real shell silently didn't). Without this, npm/npx don't exist at all
# in an interactive zsh session, and plain `node` falls through to the
# system apt package instead of nvm's managed version.
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

alias reload='if [ -n "$ZSH_VERSION" ]; then source ~/.zshrc; else source ~/.bashrc; fi'

# Glow otherwise prints a whole document into terminal scrollback. Make the
# everyday `glow file.md` path open a stable, scrollable reader instead.
# To opt out for one call, use `command glow --pager=false ...`.
glow() {
  command glow --pager "$@"
}

arc() {
  case "${1:-}" in
    shell)
      case "${2:-}" in
        bash) exec bash ;;
        zsh)  exec zsh ;;
        *)    echo "usage: arc shell [bash|zsh]"; return 1 ;;
      esac ;;
    reload)
      if [ -n "$ZSH_VERSION" ]; then source ~/.zshrc; else source ~/.bashrc; fi ;;
    fix)
      case "${2:-}" in
        screen) reset; exec "$SHELL" ;;
        *)      command arc "$@" ;;
      esac ;;
    *) command arc "$@" ;;
  esac
}

# ── Terminal greeting ────────────────────────────────────────────
source "$HOME/.config/arc/greeting.sh"
_arc_greeting

# ── Interactive terminal SOP gate ─────────────────────────────────
# Install after startup hooks/greeting so they never become gate casualties.
# Only interactive shells are filtered; scripts use an agent adapter and must
# pass `arc-sop gate-check` with a stable session ID before operational tools.
_arc_sop_refresh_gate() {
  if command arc-sop gate-check >/dev/null 2>&1; then
    _ARC_SOP_GATE_OPEN=1
  else
    _ARC_SOP_GATE_OPEN=0
  fi
}

_arc_sop_debug_guard() {
  [ "${_ARC_SOP_GATE_OPEN:-0}" = 1 ] && return 0
  command "$HOME/.local/bin/arc-sop-shell-guard" "$BASH_COMMAND" || return 1
}

if [ -n "${BASH_VERSION:-}" ] && [[ $- == *i* ]]; then
  _arc_sop_refresh_gate
  shopt -s extdebug
  set +o functrace
  # Correct the old newline hook (it assigned PROMPT_COMMAND instead of
  # running echo), then append one gate refresh for every prompt.
  [ "${PROMPT_COMMAND:-}" = "PROMPT_COMMAND=echo" ] && PROMPT_COMMAND=echo
  case ";${PROMPT_COMMAND:-};" in
    *";_arc_sop_refresh_gate;"*) ;;
    *) PROMPT_COMMAND="${PROMPT_COMMAND:+${PROMPT_COMMAND};}_arc_sop_refresh_gate" ;;
  esac
  trap '_arc_sop_debug_guard' DEBUG
elif [ -n "${ZSH_VERSION:-}" ]; then
  _arc_sop_refresh_gate
  autoload -Uz add-zsh-hook
  add-zsh-hook precmd _arc_sop_refresh_gate
  _arc_sop_accept_line() {
    if [ "${_ARC_SOP_GATE_OPEN:-0}" = 1 ] || command "$HOME/.local/bin/arc-sop-shell-guard" "$BUFFER"; then
      zle .accept-line
    else
      BUFFER=""
      CURSOR=0
      zle redisplay
    fi
  }
  zle -N _arc_sop_accept_line
  bindkey -M main '^M' _arc_sop_accept_line
  bindkey -M main '^J' _arc_sop_accept_line
fi
