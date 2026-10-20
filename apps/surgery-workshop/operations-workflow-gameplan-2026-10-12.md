# Garage / System Explorer — gameplan

**State:** M1 is the portable, offline behavior guide. M2 adds a local read-only Arc Heal health feed. M3 integrates Garage into the Khaos Lab Control Panel with a searchable app catalog and links to the existing Hub calendar, health, and resource ledger views. Garage adds no checks, repairs, persistence, network access, or service controls.

## Intent

Help an intern or owner understand an unfamiliar owned app: start at a user-visible behavior, trace the code and data it touches, show its trust boundary, and point to a safe way to verify it. Keep the offline map and health bay independently removable. Use Khaos Lab's Circadian visual language. The target is an evidence-linked mechanic's workbench, not a binary disassembler or replica of another product.

## Priority order

1. **M0 — behavior-map contract:** preserve source-of-truth ownership, provenance, review dates, and clear live/sample/planned labels.
2. **M1 — Khaos Hub anatomy (local):** one compact, context-aware HTML file with three behavior paths. It is runnable offline without the Hub, and linked from both Khaos Lab and the Hub. No service or data access is added.
3. **M2 — health signal (implemented locally):** Arc Heal publishes a sanitized report; Garage reads and flags stale or unhealthy results without running checks or repairs.
4. **M3 — unified desktop workbench (implemented locally):** bring the searchable app catalog, Arc Heal summary, inventory drift/ledger, and Hub calendar navigation into one Khaos Lab Control Panel workspace without copying state or moving canonical checkouts.
5. **M4 — app-owned self-checks:** add narrow, read-only checks with a clear owner, reviewed inputs, bounded output, and useful failure evidence; no custom-script chain.
6. **M5 — change-impact map:** link a behavior to reviewed dependencies and relevant tests; show only verified relationships.
7. **M6 — approved repair/update actions:** keep the draft work-order schema for specific repairs. Each action needs exact scope, preview, confirmation, audit, tests, and recovery. Phone access remains gated on reviewed Tailnet policy/threat model; remote actions stay out by default.

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

## 2026-10-20 · Arc Heal health feed (M2)

- Arc Heal writes `~/khaos-lab/arc-heal-log/garage-health.json` atomically with owner-only permissions after a full sweep. The `--ip-only` run keeps its separate status and does not replace the full report.
- The contract contains a schema version, UTC generation time, counts, and validated component/state pairs only. Raw finding details are deliberately omitted because they may contain IPs, URLs, hostnames, or operational commands.
- `garage-health.py` is an optional local reader: it polls the report, validates file ownership/mode/size/schema, prioritizes attention and repaired items, and marks reports older than six hours stale. Until the first JSON snapshot is emitted, it sanitizes the existing Markdown report to component/state fields only. If no report exists, it shows “No health report yet.”
- Khaos Lab launches the health bay and the independent offline guide from its Garage category. The Hub-served HTML remains network-denied and unchanged.
- This is early-warning visibility based on Arc Heal's existing checks and cadence, not prediction. The next milestone is reviewed app-owned self-checks; repair/update actions stay out until each has an explicit allowlist, approval, audit, and tested recovery path.

## 2026-10-20 · Unified Garage workbench (M3)

- Garage is a first-class Khaos Lab Control Panel workspace. It lists registered app/site/repository records from the current inventory snapshot, provides search/type filters and allowlisted local-home buttons, and summarizes Arc Heal, resource drift, scan freshness, and ledger verification.
- The existing **Health detail**, **Resource review**, and **Hub calendar** navigation opens the panel's Status, Inventory, and Calendar views. These remain the owners of their data and actions; Garage keeps no duplicate ledger or calendar state.
- The app catalog is read-only. It opens only fixed local homes under `~/khaos-lab`; it never executes paths from the inventory. Health details are reduced to validated component/state counts. No app self-check, live sweep, repair, service action, remote API, cloud call, or new listener was added.
- No source checkout was physically moved. Kataleya's canonical `kontor-studio` checkout stays under `android-mobile-ios/apps`; Py-Bite has no canonical local checkout, and its SOC training directory is not promoted as source. Arc Toolkit/Hub/Garage stay under `local-cloud-hub/apps/arc-toolkit` until a complete consumer/path map supports a safe move.
- At the implementation pass, the saved inventory snapshot was dated 2026-10-20 11:31 PDT: 146 assets, 3 drift, 2 attention, and a verified 7,280-entry ledger. The Arc Heal JSON snapshot was absent, so the view falls back to the sanitized legacy report. These are saved-snapshot values, not a fresh scan.
- Audit tightened three edges: a malformed existing JSON report now shows “report unavailable” instead of masking it with older Markdown; the catalog loads in bounded pages; and old or unknown inventory scan age is labeled stale in text. Arc Heal also warns when it cannot refresh the Garage snapshot.
- Verification: 13 focused health/workspace checks, Python and Bash syntax checks, and `git diff --check` passed. The full Khaos Lab Xvfb self-test could not create a display (`TclError: couldn't connect to display :113`), so direct GUI rendering and click-through remain unverified.
- Release uses the existing local source link for Khaos Lab; Garage adds no server, network route, live repair action, or provider access. Exact commit and publication evidence are recorded in the session GAMEPLAN.
- No source checkout was physically moved. Kataleya remains in `android-mobile-ios/apps`; Py-Bite has no canonical local checkout. The next milestone is app-owned self-checks with bounded outputs; repair actions remain gated by explicit scope, preview, approval, audit, and tested recovery.
