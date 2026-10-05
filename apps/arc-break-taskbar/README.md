# Arc Break taskbar timer

A small GTK 3 timer for XFCE and other GTK desktops. Start it from the desktop menu, click **Start timer**, and it minimizes into the normal taskbar. Its taskbar icon shows the remaining minutes in a phase-colored progress ring; the live title carries the exact countdown. Click the taskbar item to restore its controls. It needs no tray plugin or panel setup.

The work cycle starts at **40 minutes focus / 18 minutes rest**, matching this workstation's current timer settings. Edit `~/.config/arc-break-taskbar/settings.json` after first launch to choose other durations (`work_minutes`: 5–180, `break_minutes`: 1–60), then restart the app.

## Install

On Debian/Ubuntu, install the GTK bindings once if needed:

```sh
sudo apt install python3-gi gir1.2-gtk-3.0
```

Then clone this repository and run:

```sh
./apps/arc-break-taskbar/install.sh
```

The installer copies only this app into `~/.local/opt/arc-break-taskbar`, updates the existing Arc Break desktop-menu entry, and creates a `~/.local/bin/arc-break-taskbar` launcher. If a prior Arc Break menu entry exists, the installer preserves a copy so uninstall can restore it. It uses no network, privilege escalation, Genmon, Arc command, tray extension, or systemd unit.

## Local data and behavior

- A new timer starts only when the user starts it. At login, a previously active timer resumes minimized with its saved remainder; explicit Stop prevents resuming. A paused timer stays paused. Powered-off time does not consume focus/rest time; state checkpoints every five seconds and at normal shutdown. Uninstall restores the previous login-resume entry.
- Settings and resumable timer state are stored under `~/.config/arc-break-taskbar/` and `~/.local/state/arc-break-taskbar/`; files are written atomically with owner-only permissions.
- The countdown uses a one-second GTK callback, sends desktop notifications at phase changes, and stores no account or personal data.
- When Arc Pine is running, taskbar notifications inherit its `arc-break` sound, speech, and mute policy. Speech also respects Arc Pine's global speech toggle, snooze, and quiet hours. A separate app rule for `arc_break_taskbar.py` overrides the inherited policy. Without Arc Pine, desktop notifications continue normally.
- Closing the window while the timer runs minimizes it to the taskbar, so it remains visible and keeps timing. Close the app after stopping the timer to exit.
- Removing the app with `./apps/arc-break-taskbar/uninstall.sh` removes only its own launcher and installed app files; it preserves the settings and state directories.

## Uninstall

```sh
./apps/arc-break-taskbar/uninstall.sh
```

The older `arc break start|stop|status` commands still control the supervised daemon, which keeps separate state and timing. `arc break gui` opens this standalone app. The daemon no longer configures Genmon; run only one timer at a time.

Official logo: the unchanged https://kwasikontor.dev/favikon.png, installed as icon.png. The live countdown overlays that image; the launcher/window/header retain the same identity.

The optional user unit owns a running timer independently of tool sessions and restarts after a crash. Login resume remains conditional on saved active state. Arc Heal restores a missing process only for an active saved phase, and respects explicit Stop. Lab status/start/stop/open controls use this taskbar timer. CLI: --status, --start, --stop, --resume-only.
