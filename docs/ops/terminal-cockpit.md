# Terminal cockpit

The station greeting is a compact, open MFD with a Circadian accent. Its centered Khaos-Lab / Dev-Studio signature sits beneath a centered masthead reading `RIG 418 · B6ones6aw · ARCHITECT-OF-CHAOS`; `418` is the red identifier and the active phase badge uses the current canonical phase accent. The command identity is portable: the node comes from the live hostname and the user comes from the current login, so a copied script does not carry the previous machine's identity.

The presentation uses open corner-bracket HUD zones and phase-lit rules instead of boxes, aligned label/value rows, and a RAM readout and a compact root-disk capacity row (total · used · free), without percentage or load bars; USB and Fortress mounted/free status remains because it reports recovery-volume availability. Nominal, caution, and fault states use green, amber, and red. The full `RIG 418 · B6ones6aw · ARCHITECT-OF-CHAOS` masthead and the `KHAOS-LAB · DEV-STUDIO` signature are centered. At narrow widths, each wraps into centered, readable lines. The live phase badge remains on the `LOCAL_TIME` row. The phase palette remains Nyx `#ea9a97`, Choice `#5ec8ed`, Desire `#f6c177`, and Still-Pine `#c4a7e7`; phase color is ambient while the WOD and principles retain their established content colors. The local-time row and motto sit directly below the two centered identity lines, before WOD and the status panels; the motto retains the filled `☠️💀☠️` mark. The decorative hull rule uses dots instead of underscores. The OPERATIONS pane includes one short Sun Tzu quote, selected deterministically from a local three-quote set by the workstation date; no quote network lookup runs. Narrow panes wrap labels and values, wrap the RAM value, and keep the header readable. ASCII/plain output uses ASCII meters and does not emit ANSI styling.

This is a **pilot-centered MFD**, not a lowlife surveillance terminal. Keep familiar labels (`RAM`, `NET`, `SEC`), plain-language status, local human-readable time, and the existing motto. Use restrained section colors and semantic green/amber/red health states; do not add `TRACE`/`COMPROMISED` theatrics, forced ISO timestamps, hostile directives, corrupted bars, or glitch effects. The interface supports the pilot and never implies it is watching them.

Circadian state is temporal and uses the workstation's local clock: Nyx 21:00–06:00 `#ea9a97`, Choice 06:00–11:00 `#5ec8ed`, Desire 11:00–17:00 `#f6c177`, Still-Pine 17:00–21:00 `#c4a7e7`. The active phase colors the masthead badge, section markers, phase word, radar bead, and phase-aware method accents. New greetings use the current phase; the existing prompt hook emits a phase update on the first prompt after a boundary. No polling timer or background process is added.

The renderer remains embedded in `config/greeting.sh`. It adds no helper process, runtime package, background refresh, service action, or network probe. Existing collectors and their bounded private snapshot remain responsible for live values; the 10-second cache key includes the current node and user to prevent stale identity after a port. Bash and zsh are supported.

## Verification and release state

The focused greeting suite covers both shells, ANSI/plain output, degraded states, six terminal widths, cache permissions and expiry, and identity changes. Bash and zsh syntax checks pass. Fixture output uses reserved example IPs and is not a live station-health report.

Activated locally at `~/.config/arc/greeting.sh`; the source and installed copy are verified identical. The greeting is shown in new interactive shells. Existing owner-only rollback copies are retained, with an immediate pre-activation copy named `greeting.sh.before-circadian-mfd-20261021`.

Konsole's `Clean` profile uses a steady underline cursor (`CursorShape=2`, `BlinkingCursorEnabled=false`). This is a user-profile setting and takes effect in new Konsole sessions. No workstation restart or unrelated service change is needed.

This is a local workstation interface. No cloud deployment or remote service change is involved. Record Git push status separately from local activation.
