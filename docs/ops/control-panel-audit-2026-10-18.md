# Khaos Lab control-panel audit · 2026-10-18

Owner: architect-of-chaos. Scope: the local desktop panel in `bin/khaos-lab`, installed through `~/.local/bin/khaos-lab`. Session: `01a14bff-1e10-70f2-b498-e63794826f60`.

## 1. Structure and operating boundaries — scoped review complete

The panel is a single Python/Tk application with 25 workspaces. `Runner` launches commands, `UiBridge` delivers worker results to Tk, `Poller` owns view refresh jobs, and `ConfirmPolicy` controls action confirmation. Operational buttons delegate to existing tools. Calendar and inventory consume separate local data contracts.

The installed launcher resolves to this repository. The checkout already contained substantial shared modifications, including this panel. The audit preserved those bytes and applied only scoped additional hunks. It did not stage, commit, push, start a service, alter network state, execute a cloud action, or type into an active user window.

Existing architecture coupling: `_arc_ui` is a required custom import, and the panel delegates to Arc/LT and several project scripts. This is an existing exception to the standalone-object principle, recorded here rather than silently redesigned. Mobile helper/guide availability and broader dependency packaging need a separate architecture decision.

## 2. Behavior and failure paths — findings patched in the local source

| Finding | Impact | Correction |
| --- | --- | --- |
| Explicit confirmation skipped for detached actions | A button labeled “confirm” could launch a sensitive console/route helper immediately | Share one confirmation rule between row labels and execution; check SOP before opening the confirmation dialog and again immediately before launch |
| Calendar completion bypassed the panel SOP check | A locked session could still submit a completion change | Check before starting the save worker; restore checkbox when denied |
| Timeout stopped the shell but could leave a TERM-resistant child alive | A timed-out action could continue after the panel reported failure | Finish the entire original process group with KILL even if the shell exits on TERM |
| Mobile Access assumed Tailnet and Waydroid results arrived together | Tailnet failure plus valid Waydroid output raised an unbound-variable error; missing service text raised an attribute error | Initialize independent peer state, check the service match before use, validate peer response shapes |
| Missing status could appear healthy | Failed service checks with empty output said “all healthy”; calendar error payload could say “no overdue” | Explicit unavailable states when checks fail or the calendar contract is absent |
| Preflight validation still led to shell execution | The parser validated arguments but shell expansion could reinterpret raw future callers | Execute approved SOP/help commands as literal argv. Existing compound actions remain shell-backed; their command strings are code-owned, and the command-entry view tokenizes and shell-quotes user input. Do not interpolate user-controlled values into shell-backed actions. |
| Logs clipped at small window heights | Lower log controls were unreachable | Make Logs use the panel’s existing scrollable viewport |
| Notification-history viewing could create a missing SQLite file | A read action could leave an empty database | Open SQLite explicitly read-only |
| Phase-rail minute froze until phase transition | Rail time could lag while the header clock advanced | Refresh the rail timestamp during the existing clock tick |
| Tk variables could be collected on a worker after their workspace closed | Cleanup warnings during navigation/shutdown | Widget-owned registry releases real Tcl variables and traces on the UI thread, then drains pending releases at root destruction |
| Duplicate drill-path constants | Redundant source definitions | Remove the repeated assignments |
| Workbench guide appeared twice in Security | Duplicate button when the guide file existed | Keep a single conditional guide action |

The pre-edit source failed all seven original focused regression cases (five assertions and two errors). The final expanded suite passes nine tests, including malformed peer shapes and unavailable-status truthfulness. The timeout test uses a real disposable process tree; no operational command is used to reproduce these defects.

## 3. Verification and handoff — scoped verification complete; release gates remain

Review anchor: repository base `5a056ad`; runtime used for the recorded checks was Python 3.14.7 and Tk 8.6. The reviewed panel source and regression harness were local working-tree files at audit time, not part of that base commit.

- Nine focused regression tests pass against the installed source.
- Six existing word-of-day tests pass.
- The offline GUI harness passes all 25 workspace builds, search/filter behavior, 1/2/3-column tile layouts, adaptive navigation, hidden-menu routing, fullscreen restoration, installed project wiring, and SOP-denial fixtures. Scheduled poll chains are cancelled when leaving a view; an in-flight worker may finish, but its result is discarded after the view stops.
- At 650×480, Logs scrolls to its bottom controls. A final virtual-display screenshot was visually inspected after repaint; the bottom log labels and view/purge buttons are readable and reachable.
- Source parsing and scoped Git whitespace checks pass. The installed launcher remains linked to the reviewed source.
- Static source review found and removed a duplicate conditional Workbench guide action; one action constructor remains (the other text occurrence is the self-test wiring check). The existing regression suite does not assert that menu count.
- The GUI harness replaces command execution, detached launchers, the policy result and Calendar HTTP with fixtures. Passing it establishes rendering/control-flow behavior, not live cloud/service integration or actual policy acceptance. It never launches operational actions.
- Closeout rerun: the focused and word-of-day tests passed in this environment. The GUI rerun could not start because `xvfb-run` could not connect to its allocated display (`:113`); no Xvfb process remained afterward. The prior successful virtual-display run is recorded above, but this closeout did not reproduce it.

- Follow-up completed: the Tk `Variable.__del__` cleanup defect is repaired. Panel variables now have explicit widget ownership; actual Tcl variables and trace callbacks are released on the UI thread after the current callback. Root destruction drains pending cleanup. A real-Tk regression checks worker collection, deferred dialog-value reads, trace removal and shutdown with pending cleanup. The full 25-workspace run passes with zero cleanup warnings; unraisable cleanup errors fail the harness. No warning suppression or global GC change is used.

Reproduce from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/test-control-panel.py
PYTHONDONTWRITEBYTECODE=1 xvfb-run -a python3 tests/test-control-panel.py --gui
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_word_of_day.py
```

Remaining limits:

- Full assistive-technology and physical desktop checks were not performed. The small-height log barrier was repaired; this audit is not a blanket accessibility certification. Accessibility remains an open release gate until supported core tasks receive surface-specific checks. Existing keyboard/navigation selftest checks passed.
- Live destructive/privileged actions, cloud calls, network changes, service restarts and actual Calendar writes were deliberately not exercised. Their downstream implementations are outside this panel audit.
- This is a targeted code and fault-path audit, not proof that every possible panel behavior or dependency is defect-free.
- The general action runner still supports shell-backed compound commands. The audit covers the preflight and command-entry paths described above, not a formal proof of every action string; future actions must keep user-controlled values out of shell strings or use argv-based execution.

Local source changes load on the next panel launch. An already-open process retains its loaded code; it was not forcibly restarted. The source changes, test harness, and report need to travel together; a report-only commit would not publish the panel implementation. No deployment was performed.

Exact pre-edit rollback copy: `~/.local/state/khaos-lab/audit-backups/2026-10-18-control-panel.py` (owner-only). Compare newer shared edits before restoring; replace only the panel file when safe. Removing `tests/test-control-panel.py` and this report does not affect runtime operation.

Tk repair rollback (source and tests, owner-only): `~/.local/state/khaos-lab/audit-backups/2026-10-18-tk-cleanup/`. This preserves the earlier audit fixes; compare newer edits before restoring.
