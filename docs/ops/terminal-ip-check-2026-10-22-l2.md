# Terminal IP-check status wording

2026-10-22 · LT-two (L2)

## Change

The `LOCAL_IP` line now explains the safety reason when Arc Heal deferred its cached home-IP check. Example: `LOCAL_IP <address> · IP_CHECK deferred · VPN/tunnel active · checked 13m ago`.

The greeting maps known guard messages to short explanations: VPN/tunnel active, not on saved home Wi-Fi, direct Wi-Fi unavailable, custom DNS active, home network not configured, no active network route, or IP-check source unavailable. Unknown deferred reasons appear as `safety guard active`. Stale and unavailable report states remain explicit.

The greeting reads only the existing owner-only report. It does not trigger an IP check or display the report’s interface names, addresses, SSID, gateway, or raw diagnostic text. No VPN, DNS, routing, or cloud setting was read or changed as part of this wording fix.

## Verification and installation

- `python3 -m unittest local-cloud-hub/apps/arc-toolkit/tests/test_terminal_greeting.py`: 17 tests passed, including Bash/Zsh rendering, deferred-reason mapping, stale reports, and suppression of raw route details.
- Bash syntax passed. The installed `~/.config/arc/greeting.sh` matches the reviewed source SHA-256 `d2384142915b43297ebe0018c0d47adcdc5808b0ce714513fb72701aaed7f510` and remains mode `0700`.
- Rollback copy: `~/.config/arc/greeting.sh.before-ip-reason-20261022`.
- The focused greeting change was reviewed against the current canonical `main` and released without including the unrelated in-progress worktree edits. The terminal greeting is local-only; no cloud hosts or services were changed.
