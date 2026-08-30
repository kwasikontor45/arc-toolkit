# arc-toolkit

The canonical single source of truth for this user's personal tooling — every `arc*` script,
`khaos-lab` (the Tkinter control-panel GUI), crontab, the systemd units and sudoers fragments
that make it all work without prompting, and the XDG autostart/desktop entries. This is not a
curated public subset anymore (it was, until 2026-08-29) — it's the real, live thing.

**Every script in `bin/` is symlinked from `~/.local/bin/<name>` on the source machine.** This
repo isn't a copy of the live tooling, it *is* the live tooling — editing a script through either
path edits the same file, and `git status` in here always tells the truth about uncommitted
changes. Nothing here can silently drift out of sync with what's actually running, except the
three things that genuinely can't be symlinks (crontab isn't a file; systemd units and sudoers
fragments live under `/etc`, root-owned) — those need an explicit `arc sot snapshot` to re-capture.

## Using it

| Command | What it does |
|---|---|
| `arc sot` | Show this help |
| `arc sot status` | Drift check — uncommitted edits, broken symlinks, cron drift. Read-only. |
| `arc sot snapshot` | Capture live state, commit, push (both GitHub accounts), mirror to the USB vault |
| `arc sot pull` | Bring this machine's scripts up to date with the repo |
| `arc sot bootstrap [source]` | Fresh machine: clone (GitHub by default, or a local path — e.g. the USB mirror, for a machine with no internet) + install |
| `arc sot install-crontab` | Review + install `crontab.txt` (always shows a diff first, never silently overwrites) |
| `arc sot install-sudoers` | Install `sudoers/*` fragments — every file validated with `visudo -c` before it touches disk |
| `arc sot install-systemd` | Install + enable `systemd/*` units, matching the source machine's enabled/disabled state |
| `arc sot install-autostart` | Install XDG autostart entries + khaos-lab's app-menu icon/entry |

`arc-heal` runs the drift check on its normal cadence too (`check_arc_hq_drift`), so a broken
symlink gets caught and repaired within hours even if nobody thinks to run `arc sot status`.
**One deliberate exception:** a script missing entirely from `~/.local/bin` is *flagged*, never
auto-recreated — "missing" is genuinely ambiguous (accidentally deleted vs. deliberately retired),
and resurrecting something that was intentionally killed off is worse than leaving a gap for a
human to look at once. This was a real bug caught during testing, not a hypothetical.

## Offline / no-internet

The source machine never depends on the network for day-to-day use — every script is a local
file, nothing is fetched at runtime. Internet is only touched by `arc sot snapshot` (push) and
`arc sot pull`/`bootstrap` (pull). For a brand-new machine with no internet at all, `arc sot
snapshot` also mirrors the full repo (real git history, not just a file copy) to the encrypted
USB vault — `arc sot bootstrap /path/to/mirror` clones from that instead of GitHub.

## What's NOT in here, on purpose

Credential files, API tokens, LUKS keyfiles, SQLite state/history databases, `.env` files docker
labs read (e.g. `soc-lab/.env`) — anything secret. These scripts read that kind of thing from
external config paths at runtime; nothing is hardcoded, and `.gitignore` backs this up structurally
for the obvious patterns. `arc sot bootstrap` prints an explicit checklist of what has to be set
up by hand on a new machine (SSH keys, GitHub auth, VPN credentials, the USB vault's LUKS
passphrase) — none of it is something a repo should ever hold.

## Permissions

`perms.txt` records the exact octal mode for every script — git only tracks the executable bit
(755 vs 644), not exact modes, so a handful of deliberately-locked-down personal scripts
(`arc-mic`, `arc-sudo-session`, `kbd-backlight`, `volume-ctl` — all `700`, owner-only) would come
back world-readable after a fresh clone without this. `arc sot pull`/`bootstrap` applies it
automatically.

## Requirements

Varies by script — mostly bash + coreutils, some Python 3 + tkinter (`khaos-lab`, `arc-pine`),
`sqlite3`, `cryptsetup`, `rsync`, `docker`. A few are optional-dependency: `suricata` for
`arc-suricata-watch`, `rkhunter` for `arc-rkhunter-check`, `owasp-zap`/`kismet` for their
respective wrappers.
