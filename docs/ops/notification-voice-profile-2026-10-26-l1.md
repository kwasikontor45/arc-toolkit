# Notification voice profile · L1

**Date:** 2026-10-26
**Scope:** existing local Arc Pine/Piper speech only

Kataleya has no text-to-speech path. Its breathing and interaction feedback stays visual, optional WebAudio, and haptic where supported; no browser speech or external voice service was added. This keeps Kataleya quiet by default and avoids sending sensitive words to a browser voice provider.

Arc Pine routes every opted-in spoken notification through one local Piper model. The shared path now uses a separate speech level of 58% and a modest 1.10 length scale for a calmer, slightly slower cadence. Existing alert chimes retain `audio_volume_percent`, so security and timer chimes are not softened by the voice adjustment. Per-app speech/mute rules, DND, explicit snooze, stream ducking, and restore behavior remain in place.

This is a delivery adjustment, not a voice-cloning change. The current installed model remains `en_US-lessac-medium`; no model was downloaded and no service restart was needed. Kataleya itself has no spoken timer to retune. If spoken prompts are added there later, they should be explicit opt-in, locally processed, and tested on iPhone/Safari before release.

Verification: `tests/test_notification_audio.py` covers separation of speech level/cadence from alert-chime level and preserves duck/restore behavior. Deployment status depends on the scoped commit push; no workstation restart was performed.
