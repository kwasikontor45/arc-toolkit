# Notification voice profile · L1

**Date:** 2026-10-27
**Scope:** existing local Arc Pine/Piper speech only

Kataleya has no text-to-speech path. Its breathing and interaction feedback stays visual, optional WebAudio, and haptic where supported; no browser speech or external voice service was added. This keeps Kataleya quiet by default and avoids sending sensitive words to a browser voice provider.

Arc Pine routes every opted-in spoken notification through one local Piper model. The shared path uses a separate speech level of 85% and a modest 1.10 length scale for a clearer, slightly slower cadence. Existing alert chimes retain `audio_volume_percent`, so security and timer chimes are not softened by the voice adjustment. Per-app speech/mute rules, DND, explicit snooze, stream ducking, and restore behavior remain in place.

This is a delivery adjustment, not a voice-cloning change. The current model remains `en_US-lessac-medium`; no model was downloaded. A cold CLI launch took about 5–6 seconds for even a short timer phrase. The long-running `arc-pined` warms Piper in the background when speech is enabled and reuses the loaded process for later announcements. A local timer line dropped from 6.5 seconds cold to 0.72 seconds warm. That trades roughly 150 MiB resident memory while the daemon is active for lower alert latency. Speech audio stays in an owner-only cache directory and is removed after playback; stale WAVs in that dedicated directory are cleared when the worker starts. One-shot notifications retain the old nonresident fallback. The warm-up cleanup now treats Piper's returned path as a filesystem path, avoiding a startup-thread exception. Restart `arc-pined` once after updating so the new worker is loaded. Kataleya itself has no spoken timer; any future spoken prompts should stay opt-in and local.

Verification: `tests/test_notification_audio.py` and `tests/test_arc_pine_alert_expiry.py` cover speech/chime separation and alert handling; focused tests pass. Browser preview and physical iPhone review remain separate release checks.
