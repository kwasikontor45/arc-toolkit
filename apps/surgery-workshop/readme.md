# Garage · Khaos Lab

Garage is a portable, single-file guide for understanding a Khaos Hub behavior.
Open `garage.html` directly, or launch it from **Khaos Lab → Garage**. The Hub's
`/garage/` route serves this same file; the app itself does not need the Hub
service, Arc commands, Python packages, or an installer.

## Use

Pick the symptom: a stale calendar, a completed check mark, or a status tile.
Garage shows the short behavior path, its change boundary, and the relevant
source paths. The selected view follows the question; details stay collapsed
until needed. Colors follow Khaos Lab's Circadian phase names and accents.

## Security and privacy

- One self-contained HTML file; no network, remote fonts, images, or dependencies.
- Strict CSP allows only the file's hashed inline style and script. No fetch, host
  access, shell, calendar/database reads, persistence, or repair actions.
- Source paths are references for developers; Garage never opens or serves them.
- Sample status values are explained as fixtures, never live workstation state.
- Keyboard operation, visible focus, reflow, and reduced-motion support are built in.

Copy `garage.html` anywhere and open it in a modern browser for portable,
offline use. Khaos Lab's launcher is optional and points to the file beside the
Arc Toolkit checkout. The local Hub route is also optional.

## Workbench boundary

The existing work-order schema and case records remain separate scaffolding.
Garage does not provide a repair queue, diagnostics, or control surface. Any
future live diagnostics or repair action needs its own scoped review, explicit
authorization, and safe verification path.
