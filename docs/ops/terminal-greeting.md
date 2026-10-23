# Terminal architecture greeting

Current 21 October state: the pilot-centered circadian MFD is installed locally and matches `config/greeting.sh`; new terminal tabs load it. See `terminal-cockpit.md` for the active design. Earlier ship and boxed-layout notes below are historical. Cold-start timing remains documented without treating the pasted 80 ms suggestion as an owner-imposed release gate.

The local greeting renders from `config/greeting.sh` and `config/motd`. Its centered masthead reads `RIG 418 · b6ones6aw · ARCHITECT-OF-CHAOS`; `418` is red, and the username uses the requested lowercase `b`. The centered signature below it reads `KHAOS-LAB · DEV-STUDIO`. The live Circadian phase appears as a bracketed badge on the `LOCAL_TIME` row. HUD corner-bracket section markers with phase-lit rules, familiar instrument labels, aligned value rows, a concise RAM readout, and the local-time/RADAR footer keep the pilot's current state easy to scan. A compact DISK row reports total, used, and free root-filesystem space; the percentage/load bar stays omitted because a separate system monitor covers it. USB and Fortress availability remain. The local timestamp and motto are retained. Phase names, hours, and colors follow the Circadian Canonical Hours in the active project source.

The renderer uses the shell's live `COLUMNS`, then the controlling TTY and `tput`. It caps the reading measure at 96 columns, leaving two-character side margins. At 96 columns and wider, OPERATIONS and SYSTEMS share a near-even row with a slight width bias toward SYSTEMS; each section sizes its own label column and retains a one-cell value gutter. Below 96, the panes stack. Values align under their labels and wrap without clipping. Unicode labels such as I–III use terminal-cell-aware padding. Static decoration never replaces data.

`arc word --compact` supplies the offline word entry. WOD fields keep Nyx rose, Choice cyan, Desire amber, and Still-Pine lavender. Section titles and radar beads track the current phase; timestamp text is neutral and its phase name carries the phase accent. Radar values use sage, ordinary labels use neutral light text, and status values retain their independent colors. The rose-quartz motto remains without decorative glints. Plain text labels and explicit status words remain usable with NO_COLOR, redirected output, or a dumb terminal.

The LOCAL_RADAR row retains station state and EXT / TUN; DNS_RADAR retains station state and EXIT / DNS. A `LOCAL_IP` row follows them with the LAN address and a concise `IP_CHECK` state, reason, and age from Arc Heal's owner-only cached report. It never starts a check or prints the report's raw route, interface, address, SSID, or gateway details; cloud profiles omit this row. The existing LOCAL_RADAR public-egress display, route comparison, cached lookup, resolver checks, and cloud-profile privacy behavior are unchanged. Public egress lookup follows the existing default route, uses a two-second bound, and caches direct results for 30 minutes and VPN results for five minutes.

NET retains VPN up/down, the human-readable provider city/country when available, and DNS state. The local ProtonVPN status query remains bounded to one second, with local country/profile fallbacks. Storage, security, task/focus, Timeshift, SOP, and host checks are unchanged. Bash PROMPT_COMMAND and zsh precmd still emit one radar update when the prompt returns after a phase boundary; no timer or background process is added.

Local installation: keep the reviewed source and `~/.config/arc/greeting.sh` identical. New terminal shells load it automatically. Validate Bash/zsh syntax and fixture rendering at 24, 36, 51, 52, 64, 80, 96, and 160 columns before installation. Fixture rendering must not invoke the live probes or expose private URLs.

Cloud greeting rollout is available for the three configured on-demand EC2 labs:

```sh
arc greeting push gvm
arc greeting push soclab
arc greeting push wazuh
```

These commands only print the selected target and files. To apply one update, run the exact target with `--apply`, for example:

```sh
arc greeting push gvm --apply
```

An apply requires the SOP gate to be open, AWS credentials, and the selected instance to already be running. It does not start or stop the instance. It copies only the greeting and a cloud-safe MOTD, then updates the remote user's `~/.config/arc/` files and the managed interactive Bash block in `~/.bashrc`. Existing files are backed up once as `.before-arc-greeting`; repeat pushes refresh the managed block without duplicating it. The cloud profile omits the workstation policy path, identifies the selected lab, and shows basic node RAM, disk, and uptime only.

The rollout is per target. Review the preview and explicitly use `--apply` for each EC2 host you want changed.

## Value color map

METHOD keeps neutral stage names and fixed-cyan `>` arrows (`#5ec8ed`), independent of Circadian phase. The centered LOCAL_TIME readout keeps a neutral timestamp and a phase-colored badge. SUN TZU uses a steady amber quote (`#f6c177`), independent of phase. HOST uses Desire amber for swap and Still-Pine lavender for shell; DISK reports total, used, and free as text without a percentage bar. RAM uses amber for used and cyan for free; FOCUS is cyan. IDENTITY and principle groups cycle through the canonical accents; MO is lavender. These are field distinctions, not resource-pressure alarms. Value group colors continue over wrapped lines. Separators are muted; NO_COLOR/dumb/redirected normal greeting output stays plain. Colors are applied after wrapping, preserving the grid and every text field.

## Greeting order and outer spacing

The centered RIG masthead and Khaos-Lab brand lead the greeting. LOCAL_TIME with its active Circadian badge and the centered motto follow immediately, before WOD, COMMAND, OPERATIONS, and SYSTEMS. The WOD block groups the daily Sun Tzu quote under the same heading; the quote rotates daily from a local three-item list and makes no network request. The RADAR section at the bottom lists LOCAL_RADAR and DNS_RADAR, then the local-only LOCAL_IP health row when available. One blank line follows the tapered hull/wake before the prompt. Cloud profiles use the same top identity/time/motto order and finish with their session and radar state. Phase-boundary radar updates retain their existing prompt hook.

## Cockpit renderer and recovery

The cockpit exists only inside the initial greeting. Prompt-time phase radar updates remain plain. Panel wrapping measures visible terminal cells after removing ANSI color sequences. All value-color rules remain unchanged. The immediate pre-cockpit copy is ~/.config/arc/greeting.sh.candidate-before-cockpit-20261018 (owner-only); restore it to source and the installed greeting to roll back this presentation. No cloud host is updated automatically.

## Daily-driver safeguards

The installed greeting reuses an owner-only 10-second startup snapshot, bounds local probes, preserves colors through internal rendering, and offers ASCII and plain fallbacks. It remains startup-only; phase hooks do not repeat disk/RAM/service probes. The earlier readiness audit records cache semantics, measured timings, and recovery; its pasted 80 ms figure was not an owner-set release gate.

## 18 October cockpit readability update · active locally

The cockpit uses a centered Khaos-Lab / Dev-Studio masthead and brand line, a HUD/word strip, full-width COMMAND and RADAR & NAV panels, and paired OPERATIONS/SYSTEMS panes at 96 columns and wider. The pair gives SYSTEMS slightly more room; when wrapping leaves pane heights uneven, a muted blank spacer keeps their bottom edges aligned. Narrower terminals stack the panes. RAM and DISK are concise text rows, with no duplicate load bars. DISK uses the local root-filesystem snapshot; the cloud profile retains its ROOT_FS row. See [the cockpit design and preview](terminal-cockpit.md). The greeting is installed locally; it has not been pushed to cloud hosts.

The readability pass rollback copy is `~/.config/arc/greeting.sh.before-readability-20261018` (owner-only, mode 0600). Restore it to the installed path to undo that pass while preserving the earlier pre-cockpit candidate below.
