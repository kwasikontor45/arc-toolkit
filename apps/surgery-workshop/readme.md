# Garage · Khaos Control Panel

The primary Garage is now a first-class workspace in **Khaos Lab Control Panel**. It brings the registered app/project catalog, Arc Heal health summary, and inventory drift/ledger summary into one place. The panel's **Calendar** workspace is the Hub calendar, so desktop operations use one application surface.

The data owners stay independent: Arc Heal produces its health report; `arc inv` owns desired/observed resource state and its tamper-evident ledger; Khaos Hub owns shared calendar check marks. Garage reads those existing reports and links to their current views. It does not keep duplicate status or calendar data.

Two standalone fallbacks remain intentionally lightweight:

- `garage-health.py` is a local read-only health window. It reads Arc Heal's owner-only `~/khaos-lab/arc-heal-log/garage-health.json` snapshot and refreshes every 15 seconds. Until that JSON report exists, it sanitizes `latest-status.md` to component/state fields. Run it directly with `python3 -I garage-health.py`.
- `garage.html` is the portable offline behavior map. Open it directly; the local Hub's `/garage/` route serves the same file.

## Use

The integrated view summarizes the latest Arc Heal sweep, app and site records,
resource drift, and ledger verification. Search and type filters keep the catalog
manageable as it grows; retired items stay tucked away unless requested. Use
**Health detail**, **Resource review**, and **Hub calendar** to continue in the
existing owner views.

The offline guide follows three Khaos Hub behaviors: a stale calendar, a
completed check mark, or a status tile. It shows the short behavior path, its
change boundary, and source references. Details stay collapsed until needed.
The panel and both fallbacks follow Khaos Lab's Circadian phase names and accents.

## Security and privacy

- The HTML guide is one self-contained file; no network, remote fonts, images, or dependencies.
- Strict CSP allows only the file's hashed inline style and script. No fetch, host
  access, shell, calendar/database reads, persistence, or repair actions.
- The offline guide shows source paths only as references. The integrated panel opens
  only fixed, allowlisted local project homes; inventory-supplied paths are never opened.
- Sample status values are explained as fixtures, never live workstation state.
- The health view reads one versioned, size-bounded JSON file. Arc Heal writes only
  component identifiers, result states, counts, and time; it omits raw messages,
  IPs, URLs, and command arguments. Garage rejects symlinks, non-owner files,
  broad permissions, malformed schemas, and oversized reports.
- Garage's integrated catalog and health summary are read-only consumers. Missing or invalid
  reports show a clear unavailable state; old reports are marked stale.
- Keyboard operation, visible focus, reflow, readable status labels, and
  reduced-motion support are built in.

Copy `garage.html` anywhere and open it in a modern browser for portable,
offline use. `garage-health.py` is for the local station and needs Python 3 with
Tkinter; it degrades cleanly if Arc Heal has not produced a report.

## Repair boundary

Garage currently reports Arc Heal results; it does not edit, patch, update, or
restart apps. Future diagnostics should use reviewed per-app self-checks and
publish bounded reports through the same versioned contract. A repair action
must be a named allowlist entry with a preview, confirmation, audit result,
failure path, and recovery evidence. Never add arbitrary shell input or make
Garage patch an app based on a guess. The work-order schema and case records
remain separate scaffolding for tracking authorized repairs.
