# Terminal architecture greeting

Current 18 October state: the cockpit is installed locally and matches config/greeting.sh. New terminal tabs load it. See terminal-cockpit.md for the current design; the earlier ship sections below describe the preceding versions. Cold-start timing remains documented without treating the pasted 80 ms suggestion as an owner-imposed permission gate.

The local greeting renders from `config/greeting.sh` and `config/motd`. Its presentation is a restrained cockpit: `[ KHAOS-LAB / 418 / DEV-STUDIO ]` with the live phase at right, framed WOD and COMMAND panels, paired OPERATIONS/SYSTEMS panes, and a full-width RADAR & NAV footer. The identifier `418` is red; the motto sits below a framed spacer row. It uses compact, section-sized label columns (up to eleven cells), aligned value continuations, muted metal tones, and the existing Circadian accents. All information and the IDENTITY & INTENT / OPERATIONS / SYSTEMS order are retained.

The renderer uses the shell's live `COLUMNS`, then the controlling TTY and `tput`. It caps the reading measure at 96 columns, leaving two-character side margins. At 96 columns and wider, OPERATIONS and SYSTEMS share a near-even row with a slight width bias toward SYSTEMS; each section sizes its own label column and retains a one-cell value gutter. Below 96, the panes stack. Values align under their labels and wrap without clipping. Unicode labels such as I–III use terminal-cell-aware padding. Static decoration never replaces data.

`arc word --compact` supplies the offline word entry. WOD fields keep Nyx rose, Choice cyan, Desire amber, and Still-Pine lavender. Section titles and radar beads track the current phase; timestamp text is neutral and its phase name carries the phase accent. Radar values use sage, ordinary labels use neutral light text, and status values retain their independent colors. The rose-quartz motto and phase-colored glints remain. Plain text labels and explicit status words remain usable with NO_COLOR, redirected output, or a dumb terminal.

The LOCAL_RADAR row retains station state and EXT / TUN; DNS_RADAR retains station state and EXIT / DNS. Existing route comparison, cached lookup, resolver checks, and cloud-profile privacy behavior are unchanged. The ISP baseline stays in the private `~/.config/arc/greeting-isp-ip` file. Public egress lookup follows the existing default route, uses a two-second bound, and caches direct results for 30 minutes and VPN results for five minutes. Cloud profiles do not read that baseline or query the public-IP service.

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

METHOD keeps neutral words and active-phase arrows. HOST uses Choice cyan for disk, Desire amber for swap, and Still-Pine lavender for shell. RAM uses amber for used and cyan for free; FOCUS is cyan. IDENTITY and principle groups cycle through the canonical accents; MO is lavender. These are field distinctions, not resource-pressure alarms. Value group colors continue over wrapped lines. Separators are muted; NO_COLOR/dumb/redirected normal greeting output stays plain. Colors are applied after wrapping, preserving the grid and every text field.

## Greeting order and outer spacing

One blank line precedes WOD. Identity, operations, and systems follow. After HOST, the closing strip shows LOCAL_RADAR, DNS_RADAR when present, LOCAL_TIME, the motto, and the tapered hull/wake; one blank line follows the ship before the prompt. Cloud profiles use the same footer after their final SESSION row. Phase-boundary radar updates retain their existing prompt hook.

## Cockpit renderer and recovery

The cockpit exists only inside the initial greeting. Prompt-time phase radar updates remain plain. Panel wrapping measures visible terminal cells after removing ANSI color sequences. All value-color rules remain unchanged. The immediate pre-cockpit copy is ~/.config/arc/greeting.sh.candidate-before-cockpit-20261018 (owner-only); restore it to source and the installed greeting to roll back this presentation. No cloud host is updated automatically.

## Daily-driver safeguards

The installed greeting reuses an owner-only 10-second startup snapshot, bounds local probes, preserves colors through internal rendering, and offers ASCII and plain fallbacks. It remains startup-only; phase hooks do not repeat disk/RAM/service probes. The earlier readiness audit records cache semantics, measured timings, and recovery; its pasted 80 ms figure was not an owner-set release gate.

## 18 October cockpit readability update · active locally

The cockpit uses a HUD/word strip, full-width COMMAND and RADAR & NAV panels, and paired OPERATIONS/SYSTEMS panes at 96 columns and wider. The pair gives SYSTEMS slightly more room; when wrapping leaves pane heights uneven, a muted blank spacer keeps their bottom edges aligned. Narrower terminals stack the panes. RAM/disk bars derive from existing values. See [the cockpit design and preview](terminal-cockpit.md). The greeting is installed locally; it has not been pushed to cloud hosts.

The readability pass rollback copy is `~/.config/arc/greeting.sh.before-readability-20261018` (owner-only, mode 0600). Restore it to the installed path to undo that pass while preserving the earlier pre-cockpit candidate below.
