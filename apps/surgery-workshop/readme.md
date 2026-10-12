# Surgery Workshop

The Surgery Workshop is the planned local repair workspace for Khaos Lab. It applies a maintenance-control discipline across repair work: show readiness, keep one traceable record per repair, make approval and verification visible, and retain a useful history.

## Design boundary

- Use OOMA as a workflow reference, not as a visual or product template. The relevant public reference describes work orders and a current readiness view; see [NAVAIR NAMP 4790.2E, Chapter 15](https://www.navair.navy.mil/sites/g/files/jejdrs536/files/document/%5Bfilename%5D/NAMP%204790.2E%2028October2024%20%28AMA%202024-04%20attached%29.pdf).
- Use Khaos Lab's own glass/mercury visual system, neutral symbols, mobile-first sizing, and canonical Circadian phases: Nyx 21:00–06:00 `#ea9a97`, Choice 06:00–11:00 `#5ec8ed`, Desire 11:00–17:00 `#f6c177`, Still-Pine 17:00–21:00 `#c4a7e7`.
- This folder is a design scaffold. It contains no service, database, host connector, shell runner, or executable repair action.
- The mobile Work Control screen is a fixture-only preview. Phone access remains gated on device availability and reviewed Tailnet policy.

## Work record lifecycle

`Intake → Triage → Authorized → Work → Verification → Closed`

`Hold` pauses the record at any stage. A hold includes a reason and next safe step. It is not authorization. A record cannot move into `Work` without a scoped approval, and it cannot close until verification is recorded.

Each record references an existing asset identifier rather than copying inventory details. It can link to evidence IDs or local references, but must never store credentials, access tokens, temporary access URLs, or copied personal task lists.

## Keep existing authorities intact

- Inventory owns asset identity and desired/observed state.
- SOP owns policy, acknowledgments, and gate decisions.
- LT owns personal tasks.
- Orage owns calendar events.
- A work order owns the repair narrative, approvals, evidence references, next step, verification, and event history.

The work queue may reference these sources; it does not mirror their records or replace their workflows.

## Planned integration sequence

1. **M0 — workflow and safety contract:** agree on lifecycle, record fields, hold behavior, approvals, verification, source ownership, and threat boundaries. This document and the JSON Schema are the starting proposal, not an implementation approval.
2. **M1 — fixture-only Work Control:** show sample records in Khaos Hub mobile preview. No host/API connection, authentication, persistence, or actions. A UI slice is not a real-phone acceptance.
3. **M2 — local Surgery workspace:** add a desktop case list and record history; use a local, versioned case store. Any diagnostics must be a reviewed allowlist with visible scope and auditable results. No arbitrary shell field or chained-script execution.
4. **M3 — private read-only phone view:** only after phone reachability and Tailnet ACL/SSH policy are reviewed. Expose minimum case/status data with timestamps, stale/offline handling, and no remote actions.
5. **M4 — individually justified actions:** evaluate one action at a time. Require named authorization, scope preview, confirmation, timeout, audit record, and tested recovery. Keep actions out if the complete safety path is not present.
6. **M5 — hardening and operating review:** exercise denial, stale data, partial failure, device loss, backup/restore, and closeout. Ship only after source comparisons and real-device review.

## Minimum record fields

The draft schema at `work-order.schema.json` describes identifiers, stage, priority, asset reference, owner, next step, approval, verification, evidence references, and event history. Append-only event behavior is an implementation invariant; JSON Schema alone cannot enforce it.

## Daily work pattern

1. Read readiness and source freshness.
2. Intake one repair record with provenance and a next safe step.
3. Triage impact and place uncertain or unsafe work on hold with a reason.
4. Record scoped approval before work begins.
5. Capture what changed and the evidence used.
6. Verify against the expected source, preferably with an independent check.
7. Close with a concise result and leave unresolved work in an explicit state.

This checklist is a workflow proposal. It does not replace the existing SOP gate or authorize operational work.
