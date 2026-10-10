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
import fcntl
import logging
import os
import subprocess
import sqlite3
import tempfile
import threading
import time
import wave
from datetime import datetime, time as dtime
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
    "audio_volume_percent": 50,
    "speak_enabled": True,
    "app_rules": {"arc-break": {"speak": True}, "orage": {"speak": True}},
    "bubble_theme": "circadian",
    "bubble_max_visible": 4,
    "bubble_duration_ms": 12000,
    "bubble_width": 340,
    "dnd_enabled": False,
    "dnd_start": "23:00",
    "dnd_end": "07:00",
}

# Arc Pine identifies its own PulseAudio-compatible stream to PipeWire so
# per-stream mute/volume state cannot stick to the generic `paplay` client.
PAPLAY_CLIENT = "ArcPine"
_AUDIO_LOCK = threading.Lock()


def _migrate_app_rules(cfg, file_data):
    """v1 configs stored two flat lists (ignored_apps, speak_apps) that had
    to be kept in sync by hand across two separate widgets/edits. v2 uses
    one per-app rules dict instead -- single source of truth for "what does
    arc-pine do when app X notifies." Runs on every load; a no-op once the
    config *file itself* already has app_rules (checked against file_data,
    not the merged cfg -- cfg always has an app_rules key already, seeded
    from DEFAULT_CONFIG, so checking cfg here would make this permanently
    no-op and never actually migrate an old on-disk config). Old keys are
    left in the file afterward (harmless, nothing reads them anymore)
    rather than deleted, so a downgrade or manual inspection isn't
    surprised by a missing key."""
    if "app_rules" in file_data:
        return
    rules = {}
    for app in file_data.get("ignored_apps", []) or []:
        rules.setdefault(app, {})["mute"] = True
    for app in file_data.get("speak_apps", []) or []:
        rules.setdefault(app, {})["speak"] = True
    if rules:
        cfg["app_rules"] = rules


def load_config():
    cfg = DEFAULT_CONFIG.copy()
    file_data = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                file_data = json.load(f)
        except Exception:
            file_data = {}
    cfg.update(file_data)
    _migrate_app_rules(cfg, file_data)
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


def app_rule(cfg, app_name):
    rules = cfg.get("app_rules", {})
    # Gio's standalone taskbar timer reports its script name, rather than
    # the old daemon's arc-break identity. Inherit the user's break policy
    # unless they have explicitly configured the taskbar app separately.
    if app_name not in rules and app_name in (
        "arc_break_taskbar.py", "studio.kontor.ArcBreakTaskbar", "Arc Break",
    ):
        app_name = "arc-break"
    if app_name not in rules and app_name in ("Orage", "orage-calendar", "org.xfce.Orage", "org.xfce.orage"):
        app_name = "orage"
    return rules.get(app_name, {})


def is_muted(cfg, app_name):
    # Honor the old ignored_apps list even when an existing app_rules object
    # prevented the one-time migration. This keeps volume/power OSD notices
    # quiet when Arc Pine's own chime is enabled.
    return bool(app_rule(cfg, app_name).get("mute", False)) or app_name in cfg.get("ignored_apps", [])


def should_speak(cfg, app_name):
    return bool(app_rule(cfg, app_name).get("speak", False))


def set_app_rule(cfg, app_name, **flags):
    """Update (not replace) the rule dict for one app, dropping keys set to
    False/None so config.json doesn't accumulate `"mute": false` noise for
    every app that was only ever toggled the other way. Returns cfg for
    chaining; caller still owns calling save_config()."""
    rules = cfg.setdefault("app_rules", {})
    rule = rules.setdefault(app_name, {})
    for k, v in flags.items():
        if v:
            rule[k] = v
        else:
            rule.pop(k, None)
    if not rule:
        rules.pop(app_name, None)
    return cfg


def in_dnd_window(cfg):
    """True if we're currently inside the configured quiet-hours window.
    Suppresses sound/speech only -- logging and the (silent) bubble still
    happen, so DND never costs you the actual record of what fired."""
    if not cfg.get("dnd_enabled", False):
        return False
    try:
        start = dtime.fromisoformat(cfg.get("dnd_start", "23:00"))
        end = dtime.fromisoformat(cfg.get("dnd_end", "07:00"))
    except Exception:
        return False
    now = datetime.now().time()
    if start <= end:
        return start <= now < end
    return now >= start or now < end  # window wraps past midnight


def is_snoozed(cfg):
    """True if an on-demand snooze (set via arc-pine-snooze, distinct from
    the scheduled DND window above) is currently active. Snooze is the
    stronger of the two on purpose -- it's a deliberate, active "leave me
    alone right now" rather than a passive schedule, so it suppresses the
    bubble too, not just sound/speech. Logging still always happens
    regardless -- the one thing this project has never let any quiet mode
    cost you is the actual record of what fired."""
    until = cfg.get("snooze_until", 0)
    try:
        return time.time() < float(until)
    except (TypeError, ValueError):
        return False


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
    """Mute every other active audio stream (e.g. Brave/YouTube Music) so a
    spoken alert is heard clearly, restoring exact prior mute state after.
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
        props = s.get("properties", {})
        node_name = props.get("node.name", "").lower()
        # Never mute an effects processor's output: it carries our speech too.
        if (props.get("application.id") == "com.github.wwmm.easyeffects"
                or props.get("application.name", "").lower() in ("easyeffects", "easy effects", "arcpine")
                or node_name.startswith("effect_output.")):
            continue
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


def _paplay_force_unmuted(path, volume="65536", stream_name="Arc Pine alert"):
    """subprocess.run(["paplay", ...]) reporting success is NOT proof of
    audible output -- real incident, 2026-08-26: WirePlumber's own
    stream-restore state (~/.local/state/wireplumber/stream-properties)
    once remembered application.name:paplay as mute:true, so every generic
    paplay invocation reported success while producing silence. Arc Pine now
    sets its own client/stream names; immediately force-unmute only its stream
    via wpctl, then wait for playback to finish. This avoids changing other
    programs that use paplay. Falls back to a plain blocking call if the
    unmute step itself fails -- never worse than before.
    """
    proc = subprocess.Popen([
        "paplay", f"--client-name={PAPLAY_CLIENT}", f"--stream-name={stream_name}",
        f"--property=application.name={PAPLAY_CLIENT}",
        f"--volume={volume}", path,
    ],
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
                if stripped.endswith(stream_name) and ". " in stripped:
                    candidate = stripped.split(".", 1)[0]
                    if candidate.isdigit():
                        stream_id = candidate
                        break
            if stream_id:
                subprocess.run(["wpctl", "set-mute", stream_id, "0"], capture_output=True, timeout=2)
                break
    except Exception:
        pass
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise
    if proc.returncode:
        raise RuntimeError('Audio playback failed')


def _volume_arg(volume_percent):
    try:
        percent = max(25, min(100, int(volume_percent)))
    except (TypeError, ValueError):
        percent = 50
    return str(round(65536 * percent / 100))


def play_sound(sound_file, volume_percent=50):
    if not sound_file or not Path(sound_file).exists():
        return
    stream_name = f"Arc Pine chime {os.getpid()}-{threading.get_ident()}"
    _paplay_force_unmuted(sound_file, _volume_arg(volume_percent), stream_name)


def _wake_sink():
    """Open the Arc Pine output stream before the first chime or speech.

    PipeWire can leave the hardware sink SUSPENDED after boot or idle. A
    generic, fire-and-forget paplay did not reliably wake it, so use Arc
    Pine's own client identity and wait for the short silent stream to finish.
    The bounded wait happens on the audio worker, never the notification
    monitor's D-Bus loop.
    """
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            path = tmp.name
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(22050)
            w.writeframes(b"\x00\x00" * 11025)
        stream_name = f"Arc Pine silent wake {os.getpid()}-{threading.get_ident()}"
        result = subprocess.run(
            ["paplay", f"--client-name={PAPLAY_CLIENT}", f"--stream-name={stream_name}",
             f"--property=application.name={PAPLAY_CLIENT}", path],
            capture_output=True, timeout=5,
        )
        if result.returncode:
            raise RuntimeError("silent output wake failed")
        return True
    except Exception as error:
        logging.warning('Arc Pine output wake failed: %s', type(error).__name__)
        return False
    finally:
        if path:
            Path(path).unlink(missing_ok=True)


def speak(text, volume_percent=50, *, sink_ready=False):
    if not PIPER_BIN.exists() or not PIPER_VOICE.exists():
        logging.warning('Arc Pine speech unavailable: Piper binary or voice missing')
        return
    if not text.strip():
        return
    wake_thread = None
    if not sink_ready:
        wake_thread = threading.Thread(target=_wake_sink, daemon=True)
        wake_thread.start()
    wav_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        subprocess.run(
            [str(PIPER_BIN), "-m", str(PIPER_VOICE), "-f", wav_path],
            input=text.encode(), capture_output=True, timeout=15, check=True,
        )
        if Path(wav_path).stat().st_size <= 44:
            raise RuntimeError('Speech synthesis produced no audio')
        if wake_thread is not None:
            # Keep Piper synthesis parallel with the wake, but never race the
            # actual speech against a sink that has not finished waking.
            wake_thread.join()
        stream_name = f"Arc Pine speech {os.getpid()}-{threading.get_ident()}"
        _paplay_force_unmuted(wav_path, _volume_arg(volume_percent), stream_name)
    except Exception as error:
        logging.warning('Arc Pine speech failed: %s', type(error).__name__)
    finally:
        if wav_path:
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass


def emit_audio(sound_file, speak_text, audio_volume_percent=50):
    """Play Arc Pine's short chime on its own stream without muting other
    applications. Speech retains the older duck/restore behavior so spoken
    alerts remain clear; the finally path restores every stream Arc Pine muted."""
    # Serialize notifications across both watcher threads and one-shot alarm
    # processes. One alert must not restore playback during another's speech.
    DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    with _AUDIO_LOCK, (DATA_DIR / 'audio.lock').open('a') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        try:
            has_sound = bool(sound_file and Path(sound_file).exists())
            if has_sound or speak_text:
                _wake_sink()
            if sound_file:
                try:
                    play_sound(sound_file, audio_volume_percent)
                except Exception:
                    pass
            if speak_text:
                muted = _duck_other_streams()
                try:
                    speak(speak_text, audio_volume_percent, sink_ready=True)
                finally:
                    _restore_ducked(muted)
        finally:
            fcntl.flock(guard, fcntl.LOCK_UN)


def emit_audio_async(sound_file, speak_text, audio_volume_percent=50):
    """Fire emit_audio() in a background thread and return it -- both
    callers need this (arc-pined so a slow duck/play never blocks the
    D-Bus loop, arc-pine-notify so it can still join before exiting, since
    it's a one-shot CLI process, not a persistent daemon). Returns None if
    there's nothing to play."""
    if not (sound_file or speak_text):
        return None
    t = threading.Thread(target=emit_audio, args=(sound_file, speak_text, audio_volume_percent))
    t.start()
    return t
