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

`arc day` gives a short startup reminder when today's SOP acknowledgment is missing, then continues
the readiness checks without waiting for keyboard input. Start each work session with
`arc-sop start "<task>"`. If the session is new or policy changed, the gate shows the exact current
SHA-256 acceptance command after the full GAMEPLAN, SOT, and MO have been read. Reuse that printed
digest exactly; an older digest is explained as stale and cannot unlock the session. The accepted
task is logged before work begins. Interactive Bash/zsh terminals use the shared shell guard;
Codex uses its PreToolUse hook, and the Khaos Lab panel checks the same session-scoped gate.
In Konsole, tabs in one running app instance share the same human acceptance; closing and
reopening Konsole or restarting the workstation starts a fresh session. A locked shell prints a
short prompt. `arc-sop start "<task>"` shows the policy file paths and a dark, paged `batcat`
reader command; the complete GAMEPLAN, SOT, and all current MOs still need to be read before
accepting. The gate no longer dumps policy text into terminal scrollback. Its title, local time,
and lock state are separate, color-coded lines; the full MO sequence appears automatically after
acceptance.
The Khaos Lab panel checks that same session-scoped gate before running action buttons, opening the
inventory editor, or clearing logs. Read-only dashboards and document views stay available while
locked. The SOP workspace can read the latest GAMEPLAN/SOT, run compliance checks, and use
`arc sop start "<task>"` to log and acknowledge the session.

## Using it

`arc help` opens the short command map. Drill into a workspace with `arc help network`
or `arc help security`, search command names and descriptions with `arc help find backup`,
or open the full legacy reference with `arc help all`. The index stays compact as the
command catalog grows; topic pages reuse the detailed reference entries. See
[HELP-CHEATSHEET.md](HELP-CHEATSHEET.md) for a quick-start card covering the CLI,
khaos-lab navigation, and Glow pager.

In Khaos Lab, click the current **WORKSPACE / … ▾** label in the lower status rail
to jump directly to any section while the sidebar is hidden. Click **Full screen · F11**
in the title row to expand the control panel; press **F11** or **Escape** to restore its
previous window size. The split workspace, menu, and output pane continue to resize with
the available display.

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

`arc-heal` checks inventory drift and script symlink integrity on its normal cadence, so a broken
link is caught and repaired without a manual `arc sot status`. Inventory probes include the
Kataleya and kontor.studio live URLs. It also verifies Waydroid's persistent manual-start mask
and restores the mask if another action removes it; it never stops an active Android session.
**One deliberate exception:** a script missing entirely from `~/.local/bin` is *flagged*, never
auto-recreated — "missing" is genuinely ambiguous (accidentally deleted vs. deliberately retired),
and resurrecting something that was intentionally killed off is worse than leaving a gap for a
human to look at once. This was a real bug caught during testing, not a hypothetical.

### Waydroid from Khaos Lab

The **Waydroid** workspace in `khaos-lab` provides status, open, stop, installed-app, recent-log, and ADB connect/disconnect actions. Its system unit stays persistently masked, blocking boot and D-Bus activation; only the explicit Open action temporarily unmasks, starts, and re-masks the service. Open idempotently restores UFW rules scoped to `waydroid0` for guest DHCP and forwarding through the host's current route, so changing the host's network interface does not strand Android without an IP. Stop shuts down the container and restores the persistent mask. Open creates a nested Weston window on X11 when no Wayland compositor is available, starts the Android session, and opens the launcher. ADB connects only to Waydroid's private IP on port 5555; Stop disconnects that saved target before shutting down. After connecting, use the existing **Phone** menu for ADB tools and UAD-ng. Device-specific Phone commands require one connected target to avoid ambiguous ADB commands; UAD-ng has its own multi-device selector. The standalone `arc-waydroid status|open|stop|apps|logs|adb-connect|adb-disconnect` command is also available in a terminal.

The Status dashboard also shows Waydroid beside the notification-stack tile. It polls the read-only operator status every 15 seconds and reports the container, Android session, and Khaos-owned Weston window without starting anything.

### Screen share from Khaos Lab

The **Display** workspace separates Google Cast from the Insignia Fire TV's Miracast path. It can check local readiness, discover only `_googlecast._tcp` receivers through Avahi, open Chromium's Cast controls, and open the TV connection guide. `arc-cast status|discover|open|guide` also works from a terminal. Discovery is local and read-only; it never starts Avahi or changes VPN, DNS, firewall, or Wi-Fi. The existing Fire TV is not a Google Cast target, and the workstation's BCM4331 adapter lacks the Wi-Fi P2P needed for Miracast. The documented Mini DisplayPort-to-HDMI adapter remains the reliable route.

### Personal LT board

The **LT** workspace is a live view of the existing `lt · architect-of-chaos` board at `~/.local/share/lt/`; it is separate from the Calendar workspace and Khaos Hub's shared events/to-dos. The panel reads the current focus, pending queue, completed count, and latest note directly from LT's local files, refreshes every five seconds, and keeps no second copy. **Add task** and **Mark focus done** call the existing `lt` command; task changes stay behind the same-session SOP gate, and completion requires an explicit confirmation. The Status dashboard has a compact LT summary and a shortcut into the board. No daemon or network connection is added.

The **Commands** workspace completes the panel's command coverage. It builds a searchable list from `arc help all`, includes every documented LT command, and accepts an exact `arc …` or `lt …` invocation when a command has arguments. The two documented `arc-dns-hot`/`arc-dns-cold` profiles are allowed too. It never accepts arbitrary executables or evaluates shell syntax. Every invocation goes through the same-session SOP gate and an explicit confirmation; choose **Run in panel** for short commands or **Open in terminal** for interactive prompts, long jobs, and workstation actions. Commands that can print private connection URLs are terminal-only. Existing purpose-built workspaces remain the fast path for common operations.

### Studio from Khaos Lab

The **Studio** workspace is centered on **Studio Foundations**, one eight-unit beginner course for listening, beat-making, editing, mixing, DJ practice, and small-event sound. It opens as a local Notes Site web app and printable PDF; progress saves only in that browser. The source guide lives at `~/khaos-lab/studio-khaos/projects/studio/library/guides/studio-music-production-course.md`; `arc site build` generates the Notes Site page and refreshes its indexed lesson links. The Notes Site nav and dashboard link to the course. LMMS, Audacity, Mixxx, the Reborn starter, cue sheet, and detailed tutorials remain on-demand tools/resources linked from the course. The tagged PDF refresh steps are in the Studio cabinet README. No new service or cloud host was added. The outline is inspired by public topic areas in the Los Angeles Film School Audio Production and Music Production Associate catalogs; it is independent, non-credit material and is not an equivalent program. See `docs/studio/quick-start.md` for the short operator path.

The command center adapts its workspace cards and status tiles from one to three columns as the content width changes. Its menu can be tucked away for a narrow window, and action-heavy workspaces have a local filter in addition to global quick-jump. Output remains in a user-resizable lower pane.

### Shared desktop design

`bin/_arc_ui.py` owns shared Tk design tokens and primitives: circadian colors, rounded
surfaces, buttons, and pill scrollbars. Keep app state and each workspace's layout in its
own view; add reusable visual behavior here so apps share one implementation without
depending on one another. Resting edges stay still; on hover, keyboard focus, or press,
interactive outlines briefly swell and pick up a faint circadian tint. No highlight travels
around the edge. Khaos Lab workspace cards use these shared surfaces, while status colors
remain semantic and stable. Arc Pine's independent Cairo bubble renderer keeps a static rim
and animates only its arrival, hover, pause, and dismissal states. The optional
`config/gtk-3.0/whisker-mercury.css` removes the Whisker menu's selected-row block and visible
scrollbar without disabling scrolling. Install it as
`~/.config/gtk-3.0/whisker-mercury.css` and import it near the top of `gtk.css` with
`@import url("whisker-mercury.css");`.

### Offline word of the day

`arc word` displays one locally bundled, short-form word entry; `arc word --json` is the
read-only data interface used by Khaos Lab. The terminal greeting and Status workspace share
that interface. Entries are locally authored plain text, selected deterministically by local
calendar date, with `algid` anchored to 2026-10-10. There is no runtime network access, telemetry,
notification, or system/user-data access. The command validates the small JSON catalog and emits
nothing if it is absent or malformed. `arc sot install-autostart` installs/refreshes the catalog
alongside the terminal greeting.

The six-line butterfly/heart/angel mark in `config/greeting.sh` is fixed logo artwork, restored
from the August repository snapshot. Preserve its glyphs and line breaks exactly; keep identity,
date, method, and status copy below it.

`sudoers/arc-waydroid` grants only the exact Waydroid unit start/stop/mask/unmask commands and fixed device-mode restoration commands used by Stop. Waydroid is a shared-kernel container, not a VM; while it runs, its standard startup widens access to host device nodes. The vanilla image has no Google apps, and no shared host folders are configured.

GVM database exports from `arc gvm cloud-stop` are stored on the encrypted USB vault at `/mnt/storage/Persistent/khaos-lab/gvm-lab/backups/`. The command refuses to stop the cloud lab when that backup destination is unavailable, so large cloud dumps do not accumulate on the workstation disk.

### Arc Pine notification audio

Arc Pine keeps its notification audio under its own named PipeWire client. In Arc Pine → Settings, enable **sound on new notification**, use **test** to preview it, and adjust **Arc Pine alert level** (25–100%). Chimes do not change the system sink volume or mute other applications; speech retains its existing duck-and-restore behavior. Volume-control and power OSD notifications remain muted even when the chime is enabled.

Suricata severity 1/2 alerts and Nmap/port-scan signatures also sound during scheduled DND so time-sensitive network detections are not silent overnight. The local watcher also raises immediate alert-only notifications for an ARP sweep (20 distinct LAN targets in 5 seconds) and for Suricata's configured TCP/UDP/ICMP reconnaissance thresholds; see [the detection notes](docs/ops/realtime-recon-alerts.md). Sagan and Fail2ban security alerts follow the same DND exception. Explicit Arc Pine Snooze still silences them; ordinary informational Suricata traffic stays in the IDS log without a popup.

The scheduled YARA scanner uses its installed ruleset snapshot at `~/.local/share/arc-toolkit/yara-rules/`; this keeps the rule data available without retaining the upstream rules repository checkout. Refresh the data from the Yara-Rules/rules remote when you intentionally update signatures.

### Standalone Arc Break taskbar app

`apps/arc-break-taskbar/` is a portable GTK timer with its own installer, desktop launcher, settings, and state. It does not call the `arc` command, the legacy `arc-break` daemon, Genmon, or systemd. On Debian/Ubuntu, install GTK 3 Python bindings, then run `apps/arc-break-taskbar/install.sh`; its own README covers removal and the separate state directory. It minimizes into the normal taskbar and keeps the countdown in the window title, so no tray extension or Genmon panel setup is needed. The legacy `arc break start|stop|status` commands remain available for existing workflows. Run one timer at a time.

### Cloud and release management

Khaos Lab → **Cloud** now groups the read-only AWS guardrail audit (`arc aws-guardrails`), current-egress versus SSH allowlist check (`arc aws-ip-check`), inventory drift, CloudTrail, and start/stop/status/dashboard controls for GVM, Splunk, and Wazuh. The IP check compares two public-IP services with SSH rules on the configured lab security groups, flags tunnel/unknown routing, and never repairs or changes AWS. Every cloud start/stop remains behind the same-session SOP gate and explicit confirmation; GVM and Splunk stop actions back up before stopping. Cloudflare Workers usage, Git mirror status, SSH-agent fingerprints, and public-key inventory are alongside them. The optional `arc aws-keep <box> <on|off>` tag is available through the confirmed Commands workspace; it bypasses only Arc's six-hour backstop, while CloudWatch idle-stop alarms remain active. **Dev** has Git/source-of-truth audits plus confirmed Cloudflare Pages deploy actions for Athena and Kontor Studio/Kataleya.

`arc deploy` now refuses a dirty checkout, a branch other than `main`, a failed fresh `origin/main` fetch, or a local commit that does not exactly match that remote. It never deploys uncommitted files. Phoenix deployment is blocked to preserve its completed retirement. See [`cloud-management-operator-guide-2026-10-09.md`](../refs/cloud-management-operator-guide-2026-10-09.md) for current guardrail evidence and the map for credentials, SSH keys, and operator references. Credentials remain outside this repository.

The old `arc aws` SSH/status/push route for py-bite's terminated EC2 instance now fails closed; it no longer reads its leftover local config or attempts SSH.

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

Future agent adapters should set `ARC_SESSION_ID` (or `AGENT_SESSION_ID`) to a stable unique
session ID and call `arc-sop gate-check` before operational tools. Before acknowledgment, only
standalone SOP setup, recovery, and read-only discovery commands pass; shell chains do not.

If the owner must act during a real emergency, `arc-sop emergency "reason"` opens an audited,
owner-only 30-minute window that expires on its own. Agents cannot activate it. Run
`arc-sop gate-enable` to close it sooner. The separate `arc-sop gate-bypass` remains an owner-only
manual override; use the timed emergency command for a temporary opening.

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
