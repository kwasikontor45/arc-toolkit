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

`arc help` opens the short command map. Drill into a workspace with `arc help network`
or `arc help security`, search command names and descriptions with `arc help find backup`,
or open the full legacy reference with `arc help all`. The index stays compact as the
command catalog grows; topic pages reuse the detailed reference entries. See
[HELP-CHEATSHEET.md](HELP-CHEATSHEET.md) for a quick-start card covering the CLI,
khaos-lab navigation, and Glow pager.

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

### Waydroid from Khaos Lab

The **Waydroid** workspace in `khaos-lab` provides status, open, stop, installed-app, recent-log, and ADB connect/disconnect actions. It stays manual-start: Open starts the container, creates a nested Weston window on X11 when no Wayland compositor is available, starts the Android session, and opens the launcher. ADB connects only to Waydroid's private IP on port 5555; Stop disconnects that saved target before shutting down. After connecting, use the existing **Phone** menu for ADB tools and UAD-ng. Device-specific Phone commands require one connected target to avoid ambiguous ADB commands; UAD-ng has its own multi-device selector. The standalone `arc-waydroid status|open|stop|apps|logs|adb-connect|adb-disconnect` command is also available in a terminal.

The Status dashboard also shows Waydroid beside the notification-stack tile. It polls the read-only operator status every 15 seconds and reports the container, Android session, and Khaos-owned Weston window without starting anything.

`sudoers/arc-waydroid` grants only the exact Waydroid unit start/stop commands and fixed device-mode restoration commands used by Stop. Waydroid is a shared-kernel container, not a VM; while it runs, its standard startup widens access to host device nodes. The vanilla image has no Google apps, and no shared host folders are configured.

GVM database exports from `arc gvm cloud-stop` are stored on the encrypted USB vault at `/mnt/storage/Persistent/khaos-lab/gvm-lab/backups/`. The command refuses to stop the cloud lab when that backup destination is unavailable, so large cloud dumps do not accumulate on the workstation disk.

## Offline / no-internet

The source machine never depends on the network for day-to-day use — every script is a local
file, nothing is fetched at runtime. Internet is only touched by `arc sot snapshot` (push) and
`arc sot pull`/`bootstrap` (pull). For a brand-new machine with no internet at all, `arc sot
snapshot` also mirrors the full repo (real git history, not just a file copy) to the encrypted
USB vault — `arc sot bootstrap /path/to/mirror` clones from that instead of GitHub.

The Khaos Lab Inventory view reads `arc-inv`'s generated report. Drift rows have a **fix guide**
that explains recorded goal vs. latest probe, offers a read-only record inspection, and never
changes a resource or inventory entry by itself. A failed reachability probe is not proof that a
provider resource is absent.

For Codex SOP gating, `arc-sop` uses Codex's injected `CODEX_SESSION_ID`. The PreToolUse hook
passes its authoritative payload `session_id` to `arc-sop gate-check`; keep both sides aligned so
an acknowledgment from one session cannot silently authorize another.

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
