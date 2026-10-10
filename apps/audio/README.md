# Workstation audio

## Khaos Lab controls

Open **Audio** in the Khaos Lab control panel to see the current default output,
its volume and mute state, and whether the local speaker EQ profile is present.
The Status workspace also shows a live sound-output tile.

The panel volume slider is capped at 100%. Dragging it only selects a level;
**Apply level** changes the output. Mute and unmute are explicit actions. If a
muted output is above 100%, lower it before unmuting from the panel. These
controls change the shared default output, so notifications routed to that
output follow its volume and mute state too. The panel does not change the
microphone, edit audio configuration, or start/restart audio services.

Use **Open full audio mixer** for per-application routing and **Open hardware
mixer** for the ALSA device switches.

## Speaker EQ

The current speaker clarity profile is a local PipeWire filter-chain at:

`~/.config/pipewire/pipewire.conf.d/60-speaker-studio-eq.conf`

PipeWire manages that profile. The panel validates its known node layout and
reports live processing only after an explicit apply and graph check. It does
not measure the speakers. The EQ is a gentle starting curve, not a room or
speaker calibration.

The Audio view exposes the five known bands (bass, body, clarity, presence, and
air) as preview sliders from -3 to +3 dB. **Apply EQ** writes only those gain
values and a conservative headroom multiplier; it saves the original profile
once under `~/.local/state/khaos-lab/eq/` so **Reset to original** can restore it.
The panel refuses profiles whose node layout or controls have changed. Applying
asks before writing and restarts PipeWire only if its user service is already
active. That restart may briefly pause all sound on the shared output,
including notifications. An inactive service stays inactive and reads the new
profile the next time it starts.

EasyEffects was removed on 2026-10-06. The versioned
`khaos-speaker-clarity.json` file is a legacy EasyEffects preset and is not the
active profile. The shared LV2 audio plugins remain installed for other audio
tools.

## Keyboard volume controls

`volume-ctl` remains the F10 mute / F11 down / F12 up handler. It controls the
default output and shows a single updating volume notification. It does not
change the microphone. Keyboard volume steps can reach 150%; the Khaos Lab
slider deliberately stays at or below 100% for a safer direct adjustment.
