# Local Khaos Hub calendar

Open http://127.0.0.1:8766/ or Khaos Lab → Calendar → Open Khaos Hub.
The browser and desktop control panel share events, to-dos and persistent check
marks, refreshed every two seconds. Checking and unchecking saves immediately;
stale simultaneous writes are rejected and the view refreshes.

The calendar reads `~/.local/share/orage/orage.ics`. It lists to-dos, including
undated ones, and events for today and the next two weeks. Daily/weekly/monthly
recurrence uses python-dateutil with COUNT, UNTIL, EXDATE and recurrence overrides.
Repeated event occurrences have separate marks. Check marks are Hub/Lab tracking
state in `~/.local/share/khaos-hub/checks.db`; they do not change Orage STATUS,
appointments, native task completion or reminder alarms. Descriptions are not exposed.

Only the calendar is live. The seven system tiles remain clearly labeled samples.
This local browser app is separate from the permission-free Android fixture
preview in `~/khaos-lab/khaos-hub-mobile`. It does not enable phone or Waydroid
network access or change Tailscale policy.

Install: link `bin/khaos-hub` into `~/.local/bin`, copy
`systemd/user/khaos-hub.service` into `~/.config/systemd/user`, then run
`systemctl --user daemon-reload` and
`systemctl --user enable --now khaos-hub.service`. Requires system Python and
python-dateutil. The service binds only 127.0.0.1:8766. Exact Host, Origin,
Fetch Metadata and a random per-process write token prevent cross-origin writes.
The service's data files use owner-only permissions.

Stop/remove: disable `khaos-hub.service`, remove the unit and command link.
Khaos Lab then shows an unavailable calendar message; its other views and Orage
continue working. Preserve checks.db to retain marks.
