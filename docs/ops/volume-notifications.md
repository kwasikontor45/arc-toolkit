# Silent volume notifications

Volume-key notifications use app name volume. Arc Pine now has app_rules.volume.mute set to true in the owner config; its daemon reloads rules per notification, so no restart was needed. The volume controller also supplies the standard boolean:suppress-sound:true hint for the desktop notification server.

The visual progress OSD and its replacement ID remain enabled. Five-percent steps, the 150-percent upper limit, mute toggle and microphone isolation are unchanged. Other applications retain their notification audio policies.

Verification used mocked up/down/mute actions and the actual Arc Pine rule-decision functions. No physical volume, notification playback or unrelated service was changed during testing. Audible silence and physical key responsiveness remain for normal owner use.

Recovery: remove only the volume mute rule and the controller's suppress-sound hint. The immediate owner-only config backup is ~/.config/arc-pine/config.json.before-silent-volume-20261018.
