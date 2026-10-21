# Health alert freshness

`arc-heal` records its full result in `~/khaos-lab/arc-heal-log/latest-status.md` and `history.log`. The Arc Pine popup summary now includes the check time and expires after 120 seconds if it is still waiting in the bubble queue. Expiry suppresses only the late popup; it does not remove the audit record. Identical unresolved summaries remain rate-limited by the existing alert fingerprint.

This prevents a queued summary from appearing long after its check, but it does not make every check real-time. The `arc-heal` history shows full runs on a three-hour cadence. Inventory scanning is separately configured for every 30 minutes, and the VPN watcher is configured for a 60-second cadence. To deliver current-state alerts at those faster rates, each monitor needs to emit only on state transitions (including a clear event) and re-check the condition immediately before presenting it. AWS backup availability has no event source in this local watcher and would need its own bounded poll or cloud event integration.

When an alert appears, use its displayed check time and confirm the current state with the command named in the alert. The logs remain the detailed record; a popup is a short-lived prompt to inspect state, not proof that the condition is still active.
