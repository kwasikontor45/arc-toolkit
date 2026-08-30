"""
_arc_pine_common — shared audio/config/logging core for the arc-pine family.

Not a standalone command (leading underscore, no execute bit) -- imported
by arc-pined (passive D-Bus notification watcher) and arc-pine-notify (the
active entry point arc-pine's own trusted watcher family calls instead of
notify-send). Extracted 2026-08-26: both scripts had carried a near-verbatim
copy of this whole module for a while -- same functions, same bug-workaround
comments, same constants -- which is exactly the kind of duplication that
makes a fix need to be remembered and reapplied in two places instead of
one (it already happened once, for real, with the WirePlumber mute-state
bug below). One shared implementation now; both callers import it.

Owns: config load, the notifications.db logging call, and the whole
sound/speech-playback subsystem (ducking other streams, the paplay
force-unmute workaround, Piper TTS). Does NOT own anything about *how*
each caller decides whether/what to play -- that stays in each script,
since arc-pined's decision (is this app in speak_apps) and arc-pine-notify's
(same check, plus pushing a bubble) are genuinely different call sites, not
duplicated logic.
"""

import json
import os
import subprocess
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

# Real bug found 2026-08-26: this process's own environment can come up
# essentially empty (no XDG_RUNTIME_DIR, no DISPLAY, nothing) depending on
# how/when it gets launched -- for arc-pine-notify specifically, root-run
# watchers invoke it via `su architect-of-chaos -c "..."`, which doesn't
# reliably carry XDG_RUNTIME_DIR even when DISPLAY/DBUS_SESSION_BUS_ADDRESS
# are set explicitly. D-Bus monitoring (arc-pined) still works without it --
# dbus-python has its own session-bus discovery fallback -- but paplay has
# no such fallback and needs XDG_RUNTIME_DIR to find the PipeWire/PulseAudio
# socket at all. Without it, paplay fails to connect and exits silently, and
# since play_sound()/speak() run it with output captured, that failure had
# zero trace anywhere, looking exactly like "nothing happened." setdefault()
# only fills in what's actually missing, never overrides an already-correct
# value.
os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{os.getuid()}/bus")

CONFIG_DIR  = Path.home() / ".config/arc-pine"
CONFIG_PATH = CONFIG_DIR / "config.json"
DATA_DIR    = Path.home() / ".local/share/arc-pine"
DB_PATH     = DATA_DIR / "history.db"

PIPER_BIN   = Path.home() / ".local/bin/piper"
PIPER_VOICE = Path.home() / ".local/share/piper/voices/en_US-lessac-medium.onnx"

DEFAULT_CONFIG = {
    "sound_enabled": True,
    "sound_file": "/usr/share/sounds/freedesktop/stereo/bell.oga",
    "speak_enabled": True,
    "speak_apps": ["arc-break"],
    "ignored_apps": [],
    "bubble_theme": "rose-pine-moon",
    "bubble_max_visible": 4,
    "bubble_duration_ms": 12000,
    "bubble_width": 340,
}

# Notification playback volume, linear scale per paplay's --volume (65536 = 100%).
# 96000 =~ 146% -- headroom above unity since the default sink itself isn't maxed
# (91% as of the 2026-08-25 audit) and other app streams (e.g. Brave) are routinely
# boosted well above 100% on their own, making a plain 100% notification easy to miss.
NOTIFY_VOLUME = "96000"


def load_config():
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def write_default_config_if_missing():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)


def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def log_notification(app_name, summary, body, urgency_int):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT,
            summary TEXT,
            body TEXT,
            urgency INTEGER,
            timestamp TEXT
        )
    """)
    conn.execute(
        "INSERT INTO notifications (app_name, summary, body, urgency, timestamp) VALUES (?, ?, ?, ?, ?)",
        (app_name, summary, body, urgency_int, time.strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def _duck_other_streams():
    """Mute every other active audio stream (e.g. Brave/YouTube Music) so the
    notification is heard clearly, restoring exact prior mute state after.
    Returns the list of sink-input indexes muted, for _restore_ducked()."""
    try:
        out = subprocess.run(
            ["pactl", "-f", "json", "list", "sink-inputs"],
            capture_output=True, text=True, timeout=3,
        )
        streams = json.loads(out.stdout)
    except Exception:
        return []
    muted = []
    for s in streams:
        idx = s.get("index")
        if idx is None or s.get("mute"):
            continue
        try:
            subprocess.run(["pactl", "set-sink-input-mute", str(idx), "1"], capture_output=True, timeout=2)
            muted.append(idx)
        except Exception:
            pass
    return muted


def _restore_ducked(muted):
    for idx in muted:
        try:
            subprocess.run(["pactl", "set-sink-input-mute", str(idx), "0"], capture_output=True, timeout=2)
        except Exception:
            pass


def _paplay_force_unmuted(path):
    """subprocess.run(["paplay", ...]) reporting success is NOT proof of
    audible output -- real incident, 2026-08-26: WirePlumber's own
    stream-restore state (~/.local/state/wireplumber/stream-properties)
    had application.name:paplay permanently remembered as mute:true (most
    likely set by an accidental cross-thread duck during this same day's
    earlier ducking-feature testing), so every paplay invocation kept
    reporting rc=0 while producing total silence -- for hours, across a
    reboot, with zero error trace anywhere. Belt-and-suspenders fix here:
    launch paplay non-blocking, immediately force-unmute whatever stream
    it just created via wpctl (which also corrects WirePlumber's saved
    preference going forward, not just this one playback), then wait for
    it to actually finish. Falls back to a plain blocking call if the
    unmute step itself fails for any reason -- never worse than before.
    """
    proc = subprocess.Popen(["paplay", f"--volume={NOTIFY_VOLUME}", path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(10):
            time.sleep(0.05)
            out = subprocess.run(["wpctl", "status"], capture_output=True, text=True, timeout=2).stdout
            stream_id = None
            for line in out.splitlines():
                stripped = line.strip()
                # Streams-section lines look like "73. paplay" (id, dot,
                # space, name, all on one line) -- distinct from the
                # Clients-section entry, which has trailing [version,...].
                if stripped.endswith("paplay") and ". " in stripped:
                    candidate = stripped.split(".", 1)[0]
                    if candidate.isdigit():
                        stream_id = candidate
                        break
            if stream_id:
                subprocess.run(["wpctl", "set-mute", stream_id, "0"], capture_output=True, timeout=2)
                break
    except Exception:
        pass
    proc.wait(timeout=30)


def play_sound(sound_file):
    if not sound_file or not Path(sound_file).exists():
        return
    _paplay_force_unmuted(sound_file)


def speak(text):
    if not PIPER_BIN.exists() or not PIPER_VOICE.exists():
        return
    if not text.strip():
        return
    wav_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        subprocess.run(
            [str(PIPER_BIN), "-m", str(PIPER_VOICE), "-f", wav_path],
            input=text.encode(), capture_output=True, timeout=15,
        )
        _paplay_force_unmuted(wav_path)
    except Exception:
        pass
    finally:
        if wav_path:
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass


def emit_audio(sound_file, speak_text):
    """Duck (mute) every other audio stream for the duration of the
    notification sound/speech, then restore -- guaranteed via finally even
    if playback errors out, so nothing is ever left muted."""
    muted = _duck_other_streams()
    try:
        threads = []
        if sound_file:
            t = threading.Thread(target=play_sound, args=(sound_file,))
            t.start()
            threads.append(t)
        if speak_text:
            t = threading.Thread(target=speak, args=(speak_text,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=20)
    finally:
        _restore_ducked(muted)


def emit_audio_async(sound_file, speak_text):
    """Fire emit_audio() in a background thread and return it -- both
    callers need this (arc-pined so a slow duck/play never blocks the
    D-Bus loop, arc-pine-notify so it can still join before exiting, since
    it's a one-shot CLI process, not a persistent daemon). Returns None if
    there's nothing to play."""
    if not (sound_file or speak_text):
        return None
    t = threading.Thread(target=emit_audio, args=(sound_file, speak_text))
    t.start()
    return t
