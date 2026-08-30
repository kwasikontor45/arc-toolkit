"""
_arc_watch_common — shared, rotation-safe log-follow helper for the
arc-*-watch family (fail2ban/suricata/sagan/clamav).

Not a standalone command (leading underscore, no execute bit). Extracted
2026-08-26: all four watchers had independently written the identical
`with open(path) as f: f.seek(0, 2); while True: line = f.readline()...`
tailing loop, and all four shared the same real, latent bug as a result --
none of them detected log rotation. logrotate renames the old file and
creates a fresh one at the same path; a plain open() handle keeps reading
the renamed, no-longer-written-to file forever, so a watcher that's been
running continuously across a rotation goes silently deaf to new events
until it happens to be restarted for an unrelated reason. Confirmed this
isn't theoretical: fail2ban.log rotates weekly, suricata's eve.json is
logrotate'd too, and both had already rotated once this week by the time
this was found -- only dormant right now because today's own reboot
happened to restart every watcher after the last rotation.
"""

import os
import time


def follow(path, poll_interval=0.5, rotation_check_interval=5.0):
    """Generator yielding new lines appended to `path`, or None on every
    empty poll (a heartbeat) -- every caller needs that: each watcher does
    its own periodic "should I flush pending events yet" check on the same
    cadence it polls for new lines, not only when a line actually arrives.
    `for item in follow(path): if item: handle(item) ; <periodic check>`
    reproduces each script's original loop timing exactly.

    Reopens the file transparently if its inode changes underneath
    (rotation). Starts at EOF -- never replays history on (re)start,
    matching every caller's prior behavior. Only stats the path for
    rotation every `rotation_check_interval` seconds (checking on literally
    every empty poll would mean a stat() syscall twice a second forever for
    no reason -- rotation is a rare, slow event, no need to check for it at
    the same cadence as new lines)."""
    f = open(path, "r")
    f.seek(0, 2)
    try:
        current_ino = os.fstat(f.fileno()).st_ino
    except Exception:
        current_ino = None
    last_check = time.time()
    while True:
        line = f.readline()
        if line:
            yield line
            continue
        time.sleep(poll_interval)
        now = time.time()
        if now - last_check >= rotation_check_interval:
            last_check = now
            try:
                real_ino = os.stat(path).st_ino
            except FileNotFoundError:
                real_ino = current_ino  # mid-rotation gap -- next check catches it
            if real_ino != current_ino:
                try:
                    new_f = open(path, "r")
                except Exception:
                    new_f = None  # couldn't reopen yet -- try again next check
                if new_f is not None:
                    f.close()
                    f = new_f
                    current_ino = os.fstat(f.fileno()).st_ino
        yield None
