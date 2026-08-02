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
