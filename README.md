# arc-toolkit

A personal ops toolkit for a Linux workstation with an encrypted, USB-carried vault. Extracted
from a larger private `arc` CLI ecosystem — these are the pieces that are genuinely
self-contained and useful independent of any specific person's projects or accounts.

## What's in here

- **Vault backup**: `bakup-usb` / `bakup-local` — bidirectional sync between a working directory
  and a LUKS-encrypted USB volume, with checksummed manifests.
- **SOP gate**: `arc-sop` / `arc-sop-gate-hook` — a SQLite-backed "did I actually log what I'm
  about to do" gate, wired as a Claude Code `PreToolUse` hook so agent sessions can't silently
  skip it.
- **DNS/security status**: `arc-dns` (+`-cold`/`-hot`), `arc-rkhunter-check`, `arc-suricata-watch`
  (batches IDS alerts instead of firing one desktop notification per event), `arc-quiet-clean`.
- **Cloud guardrails**: `arc-aws-killswitch` (budget-triggered EC2 kill switch), `arc-cf-watch`.
- **Misc**: `arc-heal` (self-check/repair sweep), `arc-ip-sync`, `arc-gate-bypass`,
  `auto-move-large-files`, `build-notes-site` (static dashboard generator), `sync-mirrors`,
  `arc-vpn`, `lt` (a Claude Code subagent definition for read-only research tasks).
- `config/greeting.sh` — a terminal login banner showing live system status (memory, SOP gate
  state, DNS/firewall/IDS status, storage health).
- `config/shell-init.sh` — shell integration glue.

## Not in here on purpose

The actual `arc` orchestrator CLI that ties these together is not included — it's tightly coupled
to one person's specific projects and accounts. Everything above is independently useful without
it; wire them into your own dispatcher or run standalone.

Also not included, and never should be, in this or any repo: credential files, API tokens, LUKS
keyfiles, SQLite state/history databases, or anything under a `.gitignore`'d pattern. These
scripts all read that kind of thing from external config paths at runtime — nothing is hardcoded.

## Requirements

Varies by script — mostly bash + coreutils. Some need `python3`, `sqlite3`, `cryptsetup`,
`rsync`. A few are optional-dependency: `suricata` for `arc-suricata-watch`, `rkhunter` for
`arc-rkhunter-check`, the AWS CLI for `arc-aws-killswitch`.
