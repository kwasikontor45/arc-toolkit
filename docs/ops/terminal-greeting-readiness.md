# Ship greeting readiness audit

17 October 2026 · owner-local daily driver · candidate prepared; prior installed greeting restored; strict sign-off remains open

## Changes verified

- A private 10-second startup snapshot reuses rendered facts across matching tabs. Directory 0700 and file 0600 are checked; writes replace the snapshot atomically. The cache is read as data, never sourced or evaluated.
- Cache keys distinguish date, phase, pane width, color capability, locale fallback, and plain/ship style. Changes to the greeting, focus/tasks, MOTD, WOD data, MO, GAMEPLAN, and SOP database invalidate a snapshot.
- A cold snapshot invokes free once and df at most once per examined filesystem. Local filesystem/service probes have short deadlines; failures render unknown or a degraded state.
- Direct routing, no carrier, and an inaccessible network query have distinct radar states. A ready label is a sampled interface state, not a comprehensive security or connectivity attestation.
- Non-UTF-8 locales use ASCII and omit the ship. Unknown non-ASCII text uses a replacement marker in this fallback. UTF-8 field text remains intact and wraps; long ASCII focus names are covered by tests.
- ARC_GREETING_STYLE=plain removes the ornament. ARC_GREETING_CACHE=0 forces a fresh startup snapshot. These affect a new shell invocation, e.g. ARC_GREETING_STYLE=plain zsh.
- Color capability is established before internal redirection, retaining all four WOD colors while redirected/dumb/NO_COLOR output stays plain. Phase updates reset colors properly.
- Full rails start at 90 columns; smaller panes use the compact ship. The existing 96-column maximum remains.

## Performance evidence and limits

The initial implementation measured approximately 602 ms for a local-only opening snapshot. The candidate measured approximately 550 ms cold and a 20.9 ms median over five warm cached invocations. Sourcing the candidate plus five unchanged phase-hook calls measured 17.8 ms median including the subprocess shell itself.

These are isolated zsh -f measurements of this greeting. Public-IP lookup and the provider CLI location probe were stubbed out; this is not a claim about complete .zshrc startup time or the cost of a cold network lookup. Existing egress lookups remain bounded to two seconds and retain their separate route-sensitive cache (VPN five minutes; direct thirty minutes).

The pasted cold <80 ms requirement is NOT met. A cache hit meets its warm <30 ms target in this measurement. Claiming all latency gates passed would be incorrect. Reaching the cold target requires a separate design decision: defer/omit provider and public-IP work, and reduce the cold collector/renderer path further. No background polling or new refresh hook was introduced in this task.

The greeting is printed on shell startup, not on every prompt. Its precmd hook checks only the clock/phase, then redraws stored radar facts at a boundary. It is not a live network monitor, and a phase-only radar update does not refresh the stored addresses. The SOP row is a daily acknowledgment/plan summary, not proof that the current interactive policy gate is open.

## Verification

Eight standalone Python unittest cases cover Bash/zsh cache reuse without repeated probes, one memory snapshot, degraded/all-failed fixture states, long fields, widths 24–160, C-locale/plain output, cache expiration/permissions/truncation/invalidation, missing temporary storage, cloud privacy boundaries, and set -e / pipefail survival. They use disposable home directories and mock executables; they do not stop services, change VPN/DNS, or unmount drives.

Additional checks exercised real Bash/zsh PTYs, all four WOD accents through the internal frame, and an isolated real tmux pane at 96 columns. Bash/zsh syntax and scoped whitespace checks passed. Physical terminal/font behavior and an actual SSH session were not tested. strace is not installed; probe reuse was verified with mock call logs instead.

Run the persistent tests from the Arc Toolkit root:

    python3 -B tests/test_terminal_greeting.py

## Recovery and publication boundary

The immediate owner-only pre-readiness copy is ~/.config/arc/greeting.sh.before-readiness-20261017. To restore both the installed and matching source bytes after normal policy acceptance:

    tee ~/.config/arc/greeting.sh ~/khaos-lab/local-cloud-hub/apps/arc-toolkit/config/greeting.sh < ~/.config/arc/greeting.sh.before-readiness-20261017 > /dev/null

The cache is automatically invalidated by a newer greeting; cache failure never authorizes a service action. The repository already provides version history, so no nested Git repository was created in ~/.config/arc.

The hardened candidate remains in the local Arc Toolkit source for review. The installed daily-driver greeting was restored from the immediate pre-readiness copy because the strict cold-start gate is unmet. No commit, push, cloud-host rollout, remote exposure, reboot, or production deployment to an external destination is included. The strict cold-start budget and physical-terminal/SSH acceptance remain open.

## 18 October design follow-up

The source-only cockpit redesign now uses one embedded renderer and derived resource bars. See terminal-cockpit.md for the design and new tests. The installed greeting remains the prior ship version. The earlier timing measurements belong to the ship implementation; they do not qualify the cockpit candidate against the cold-start gate.

## 18 October activation clarification

The cockpit was activated locally after correcting the agent's overinterpretation of pasted latency advice as a mandatory owner release rule. Source and installed greeting match. The 80 ms cold target is still not claimed to pass, and the previous measurements remain implementation-specific historical evidence. The tested cache/fallback safeguards remain enabled. No remote push, cloud deployment, service restart or network change was included.
