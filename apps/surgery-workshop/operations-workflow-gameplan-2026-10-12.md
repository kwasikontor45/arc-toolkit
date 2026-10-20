# Garage / System Explorer — gameplan

**State:** M1 is a portable, local-only single-file guide. It opens directly, from Khaos Lab, or through Khaos Hub; no host integration, local diagnostics, persistence, or repair action is shipped.

## Intent

Help a new intern understand an unfamiliar owned app on day one: start at a user-visible behavior, trace the code and data it touches, show its trust boundary, and point to a safe way to verify it. Garage joins Khaos Hub navigation while remaining a static, independently removable module. Use Khaos Lab's own Circadian visual language. The target is an evidence-linked system explorer inspired by reverse-engineering workflows, not a binary disassembler or a replica of another product.

## Priority order

1. **M0 — behavior-map contract:** preserve source-of-truth ownership, provenance, review dates, and clear live/sample/planned labels.
2. **M1 — Khaos Hub anatomy (local):** one compact, context-aware HTML file with three behavior paths. It is runnable offline without the Hub, and linked from both Khaos Lab and the Hub. No service or data access is added.
3. **M2 — first intern project map:** add one more owned application, documenting its user task, entry points, important modules, state/data flow, failure handling, tests, and verification route.
4. **M3 — change-impact explorer:** link a behavior to reviewed dependencies and relevant tests; show only verified relationships and keep the view read-only.
5. **M4 — optional local diagnostics:** introduce narrowly scoped read-only checks only after review, with visible target, allowlist, bounded output, and recovery. No shell runner or hidden script chain.
6. **M5 — repair record and phone lanes:** keep the draft work-order schema for specific repairs, not as a generic queue. Phone access stays gated on a reviewed Tailnet policy and threat model; remote actions remain out of scope by default.

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

## 2026-10-20 · portable Garage refresh

- Replaced the long multi-section page with `garage.html`: one file, three symptom choices, one focused behavior trace, and collapsed source references.
- The Khaos Lab panel launches the file directly. The Hub `/garage/` route serves the same file; neither integration is required for direct offline use.
- The file uses no external requests or dependencies. Its CSP permits only its hashed inline CSS/JavaScript; no host reads, API calls, data persistence, shell, or repair actions exist.
- Current verification and release state are recorded in the session GAMEPLAN entry. Reopen the M1 map if its source paths change; they are references, not live-linked source.
