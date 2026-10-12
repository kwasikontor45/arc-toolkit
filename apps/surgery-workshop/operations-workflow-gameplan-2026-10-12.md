# Khaos Lab Work Control — gameplan

**State:** design scaffold; no local case store, host integration, or repair action is shipped.

## Intent

Use maintenance control patterns that make readiness, work ownership, authorization, verification, and history clear. Keep Khaos Lab's own Circadian glass/mercury visual language and keep source systems independent. The target is an understandable, secure daily workflow, not a replica of a military system.

## Priority order

1. **M0 — contract and boundary (documented proposal):** define lifecycle, record schema, source-of-truth boundaries, and security limits. Review the proposal before any persistent workflow storage is built.
2. **M1 — mobile fixture slice (implemented locally):** add a static Work Control screen to the existing mobile preview. Show three clearly labeled sample records and lifecycle/hold/approval/verification concepts. Keep CSP network access denied, Android permissions empty, and all actions absent. This does not count as the planned real-phone M1 acceptance.
3. **M2 — local desktop workspace:** inspect existing control-panel window patterns first; add one responsive Surgery/Workshop window with readiness, bounded case list, case history, and links to the existing source records. Agree on local storage/backup behavior before implementation.
4. **M3 — phone read-only access:** remain gated until the phone is online and Tailnet ACL/SSH access policy has been reviewed. Build a small named-data API only after a threat review; no public relay, arbitrary commands, or bundled credentials.
5. **M4 — action review:** keep the first live version read-only. Review any proposed action individually for authority, reversibility, visible impact, confirmation, audit, timeout, and recovery. Reject actions that cannot meet every condition.
6. **M5 — routine use and hardening:** compare the UI with live sources, exercise denied/offline/stale/partial states, validate restore, then decide what should ship as a stable workflow.

## Shared record lifecycle

`Intake → Triage → Authorized → Work → Verification → Closed`

`Hold` pauses any stage and must state why and what safe evidence is needed next. No work starts before scoped approval. No case closes without recorded verification. Every state change creates an event; history is append-only in the future implementation.

## Ownership rules

- Work order: repair summary, approval, evidence references, next step, verification, and history.
- Inventory: asset identity and desired/observed state.
- SOP: required policy, acknowledgment, gate status, and violations.
- LT: personal tasks and completion state.
- Orage: events and reminders.

The hub may present carefully selected summaries and references. It must not create shadow copies of these systems.

## Release evidence / explicit open gates

- The fixture APK must remain permission-free and offline-capable.
- Desktop work must use narrow, independently removable tools and a reviewed allowlist; no arbitrary shell field or hidden script chain.
- Mobile live status requires phone availability plus a reviewed Tailnet policy and data-flow design.
- Any future action requires an individually approved scope, preview, confirmation, audit, failure path, and recovery evidence.
- A successful build is not real-device acceptance or proof of live data accuracy.
