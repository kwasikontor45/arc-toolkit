# Clean speaker output

EasyEffects 8.2.8 uses the installed Khaos-Speaker-Clarity output preset:
five gentle stereo EQ bands, -3 dB input headroom and a -2 dB limiter ceiling.
Shelf type names are Lo-shelf / Hi-shelf for this version. The physical
speaker sink is 100%, replacing the previous 220% software amplification.
Default playback uses easyeffects_sink; the processor outputs to built-in audio.
Arc Pine speech never ducks the processor output or its own speech streams.

The service starts at login and EasyEffects remembers the last loaded preset.
Copy khaos-speaker-clarity.json to
~/.local/share/easyeffects/output/Khaos-Speaker-Clarity.json, then load it with
`easyeffects -l Khaos-Speaker-Clarity` and disable bypass with `easyeffects -b 2`.
The previous preset is preserved locally as
Khaos-Speaker-Clarity.before-2026-10-05.json.

To bypass processing: `easyeffects -b 1`. To stop it permanently, disable
easyeffects.service and choose built-in audio as the default sink.
The EQ is a gentle starting curve, not a measured speaker calibration.
