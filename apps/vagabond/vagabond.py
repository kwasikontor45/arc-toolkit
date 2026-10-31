#!/usr/bin/python3
"""Vagabond — a small, standalone wandering break timer for GTK desktops.

The timer is local to this process and has no Arc CLI, Genmon, network, or
systemd dependency. While running, closing the window minimizes it to the taskbar.
"""
from __future__ import annotations

import json
import math
import os
import signal
import sys
import time
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

# Arc Break ships with the exact same circadian engine as Khaos Lab and
# Arc Pine. The installer copies this one source beside the installed timer;
# running directly from the checkout resolves it from ../../bin.
_here = Path(__file__).resolve().parent
_shared_ui = _here / "_arc_ui.py"
if not _shared_ui.is_file():
    _shared_ui = _here.parents[1] / "bin" / "_arc_ui.py"
sys.path.insert(0, str(_shared_ui.parent))
import _arc_ui as ui


APP_ID = "studio.kontor.Vagabond"
APP_NAME = "Vagabond"
TIMER_FACE_FILE = Path(__file__).resolve().with_name('mechanical-timer.svg')
LOGO_FILE = TIMER_FACE_FILE
CONFIG_ROOT = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "vagabond"
STATE_ROOT = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "vagabond"
CONFIG_FILE = CONFIG_ROOT / "settings.json"
STATE_FILE = STATE_ROOT / "timer.json"
_INITIAL_PALETTE = ui.circadian()
ACCENT = ui.PHASE_ACCENT[_INITIAL_PALETTE["phase"]]
BG = _INITIAL_PALETTE["bg"]
SURFACE = _INITIAL_PALETTE["surface"]
TEXT = _INITIAL_PALETTE["fg"]
MUTED = _INITIAL_PALETTE["fg_muted"]
WORK = "#f6c177"
REST = "#ebbcba"


class DialArea(Gtk.DrawingArea):
    """Circular mechanical dial: bronze ring, minute ticks, phase progress arc,
    phase and remaining time at the hub, and a live sweeping seconds hand.
    Redraws at 10 Hz while mapped."""

    def __init__(self):
        super().__init__()
        self.set_size_request(300, 300)
        self._progress = 0.0
        self._color_hex = ACCENT
        self._phase_text = "READY"
        self._time_text = ""
        self.connect("draw", self._draw)
        GLib.timeout_add(100, self._sweep)

    def set_state(self, progress, color_hex, phase_text, time_text):
        self._progress = progress
        self._color_hex = color_hex
        self._phase_text = phase_text
        self._time_text = time_text
        self.queue_draw()

    def _sweep(self):
        if self.get_mapped():
            self.queue_draw()
        return True

    @staticmethod
    def _col(hex_color, alpha=1.0):
        v = hex_color.lstrip('#')
        return (int(v[0:2], 16)/255, int(v[2:4], 16)/255, int(v[4:6], 16)/255, alpha)

    def _center(self, cr, cx, y, text, size, color, bold=False):
        cr.select_font_face("DejaVu Sans", 0, 1 if bold else 0)
        cr.set_font_size(size)
        ext = cr.text_extents(text)
        cr.move_to(cx - ext.width/2 - ext.x_bearing, y)
        cr.set_source_rgba(*self._col(color))
        cr.show_text(text)

    def _draw(self, _widget, cr):
        w = self.get_allocated_width(); h = self.get_allocated_height()
        cx, cy = w/2.0, h/2.0
        R = min(w, h)/2.0 - 10
        cr.arc(cx, cy, R, 0, 6.2832)
        cr.set_source_rgba(*self._col(BG, .96)); cr.fill_preserve()
        cr.set_source_rgba(*self._col("#A88452", .95)); cr.set_line_width(7); cr.stroke()
        cr.arc(cx, cy, R - 9, 0, 6.2832)
        cr.set_source_rgba(*self._col("#D4B27A", .55)); cr.set_line_width(2); cr.stroke()
        for i in range(60):
            a = i * 6.2832 / 60 - 1.5708
            big = i % 5 == 0
            r0 = R - 16; r1 = R - (34 if big else 26)
            cr.set_source_rgba(*(self._col("#D4B27A", .9) if big else self._col("#96A0AC", .5)))
            cr.set_line_width(3 if big else 2)
            cr.move_to(cx + r0*math.cos(a), cy + r0*math.sin(a))
            cr.line_to(cx + r1*math.cos(a), cy + r1*math.sin(a)); cr.stroke()
        if self._progress > 0:
            frac = 1.0 - self._progress
            cr.arc(cx, cy, R - 46, -1.5708, -1.5708 + frac * 6.2832)
            cr.set_source_rgba(*self._col(self._color_hex, .95))
            cr.set_line_width(9); cr.stroke()
        self._center(cr, cx, cy - 14, self._phase_text, 15, TEXT)
        self._center(cr, cx, cy + 30, self._time_text or "--:--", 30, self._color_hex, bold=True)
        sec = time.time() % 60
        a = sec * 6.2832 / 60 - 1.5708
        cr.set_source_rgba(*self._col("#E8A33D", .95)); cr.set_line_width(3)
        cr.move_to(cx - 18*math.cos(a), cy - 18*math.sin(a))
        cr.line_to(cx + (R - 56)*math.cos(a), cy + (R - 56)*math.sin(a)); cr.stroke()
        cr.arc(cx, cy, 7, 0, 6.2832)
        cr.set_source_rgba(*self._col("#D4B27A")); cr.fill()


def boot_id():
    try:
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except OSError:
        return ''


def restore_timer(saved, work_minutes, break_minutes, now, current_boot):
    phase = saved.get('phase')
    if phase not in ('focus', 'break'):
        return 'stopped', 0, 0
    duration = (work_minutes if phase == 'focus' else break_minutes) * 60
    try:
        paused = max(0, min(duration, int(saved.get('paused_left', 0) or 0)))
        deadline = float(saved.get('deadline', 0) or 0)
        remaining = float(saved.get('remaining', max(1, deadline - now)) or duration)
        if not math.isfinite(deadline) or not math.isfinite(remaining):
            raise ValueError('Invalid timer state')
    except (ValueError, TypeError, OverflowError):
        return 'stopped', 0, 0
    if paused:
        return phase, 0, paused
    if saved.get('boot_id') != current_boot:
        # Powered-off time is not focus/rest time; pick up the saved remainder.
        if 'remaining' not in saved and deadline <= now:
            remaining = duration
        return phase, now + max(1, min(duration, remaining)), 0
    if deadline <= now:
        phase = 'break' if phase == 'focus' else 'focus'
        return phase, now + (work_minutes if phase == 'focus' else break_minutes) * 60, 0
    return phase, deadline, 0


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def read_json(path: Path, fallback: dict) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else fallback.copy()
    except (OSError, ValueError, TypeError):
        return fallback.copy()


class ArcBreak:
    def __init__(self, app: Gtk.Application):
        self.app = app
        cfg = read_json(CONFIG_FILE, {"work_minutes": 40, "break_minutes": 18,
                                      "auto_continue": True, "alerts_enabled": True})
        self.work_minutes = self._bounded(cfg.get("work_minutes"), 40, 5, 180)
        self.break_minutes = self._bounded(cfg.get("break_minutes"), 18, 1, 60)
        self.auto_continue = cfg.get("auto_continue", True) is True
        self.alerts_enabled = cfg.get("alerts_enabled", True) is True
        self.popup_on_transition = cfg.get("popup_on_transition", True) is True
        if not CONFIG_FILE.exists():
            atomic_json(CONFIG_FILE, {"work_minutes": self.work_minutes,
                                      "break_minutes": self.break_minutes,
                                      "auto_continue": self.auto_continue,
                                      "alerts_enabled": self.alerts_enabled,
                                      "popup_on_transition": self.popup_on_transition})
        saved = read_json(STATE_FILE, {})
        self.phase = saved.get("phase") if saved.get("phase") in ("focus", "break") else "stopped"
        try:
            self.deadline = float(saved.get("deadline", 0) or 0)
            if not math.isfinite(self.deadline):
                self.deadline = 0
        except (TypeError, ValueError, OverflowError):
            self.deadline = 0
        try:
            self.paused_left = max(0, min(3 * 60 * 60, int(saved.get("paused_left", 0) or 0)))
        except (TypeError, ValueError, OverflowError):
            self.paused_left = 0
        self.phase, self.deadline, self.paused_left = restore_timer(
            saved, self.work_minutes, self.break_minutes, time.time(), boot_id())
        self._last_save = 0
        self._save()
        self.window = None
        self._window_timer_mode = self.phase != "stopped"
        self.clock_label = None
        self.status_label = None
        self.primary_button = None
        self.controls_row = None
        self.settings_button = None
        self.cycle_hint = None
        self.face_image = None
        self._last_palette_minute = None
        self._taskbar_icon_key = None
        self._face_image_key = None
        try:
            self._timer_svg = TIMER_FACE_FILE.read_text(encoding="utf-8")
        except OSError:
            self._timer_svg = ""
        self._style()
        self._update()
        GLib.timeout_add_seconds(1, self._tick)
        GLib.timeout_add_seconds(60, self._refresh_circadian)
        self._quit_source = GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._quit_signal)

    @staticmethod
    def _bounded(value, default, low, high):
        try:
            return max(low, min(high, int(value)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _color(value):
        color = Gdk.RGBA()
        color.parse(value)
        return color

    def _timer_pixbuf(self, progress, color, size):
        if not self._timer_svg:
            return None
        progress = max(0.0, min(1.0, float(progress)))
        elapsed = 0.0 if self.phase == "stopped" else 1.0 - progress
        circumference = 213.63
        arc = elapsed * circumference
        svg = self._timer_svg
        svg = svg.replace('stroke="#f6c177"', f'stroke="{color}"', 2)
        svg = svg.replace('stroke-dasharray="0 213.63"',
                          f'stroke-dasharray="{arc:.2f} {circumference - arc:.2f}"', 1)
        svg = svg.replace('transform="rotate(0 64 69)"',
                          f'transform="rotate({elapsed * 360:.2f} 64 69)"', 1)
        try:
            loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
            loader.set_size(size, size)
            loader.write(svg.encode("utf-8"))
            loader.close()
            return loader.get_pixbuf()
        except (GLib.Error, TypeError, ValueError):
            return None

    def _set_taskbar_icon(self, progress, color):
        if self.window is None:
            return
        key = (self.phase, round(progress, 4), color, bool(self.paused_left))
        if key == self._taskbar_icon_key:
            return
        pixbuf = self._timer_pixbuf(progress, color, 64)
        if pixbuf is not None:
            self.window.set_icon(pixbuf)
            self._taskbar_icon_key = key

    def _set_timer_face(self, progress, color, phase_text="", time_text=""):
        if getattr(self, "dial", None) is None:
            return
        self.dial.set_state(progress, color, phase_text, time_text)

    def _style(self):
        self.css = Gtk.CssProvider()
        self._load_style()
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    @staticmethod
    def _rgba(hex_color, alpha):
        value = hex_color.lstrip('#')
        return f"rgba({int(value[0:2],16)},{int(value[2:4],16)},{int(value[4:6],16)},{alpha})"

    def _load_style(self):
        edge = self._rgba(TEXT, .2)
        sheen = self._rgba("#ffffff", .16)
        self.css.load_from_data(f"""
          window.vagabond {{ background-color: {BG}; color: {TEXT}; }}
          window.vagabond > box {{
            background-image: linear-gradient(145deg, {self._rgba(SURFACE, .97)}, {self._rgba(BG, .98)});
            border: 1px solid {edge}; border-top-color: {sheen}; border-radius: 22px;
            box-shadow: inset 0 1px {sheen}, 0 12px 36px {self._rgba("#000000", .28)};
            padding: 8px;
          }}
          scrollbar {{ background: transparent; }}
          scrollbar trough {{ border-radius: 999px; }}
          scrollbar slider {{ border-radius: 999px; min-width: 10px; min-height: 28px; background: {ACCENT}; }}
          .arc-title {{ color: {TEXT}; font-size: 20px; font-weight: 600; }}
          .arc-clock {{ color: {ACCENT}; font-size: 42px; font-weight: 300; }}
          .arc-subtle {{ color: {MUTED}; font-size: 12px; }}
          button.arc-action {{ background-image: linear-gradient(145deg, {self._rgba(SURFACE, .96)}, {self._rgba(BG, .96)});
            color: {TEXT}; border: 1px solid {edge}; border-top-color: {sheen};
            border-radius: 999px; padding: 8px 16px; min-height: 25px; box-shadow: inset 0 1px {self._rgba("#ffffff", .12)}, 0 2px 6px {self._rgba("#000000", .18)}; }}
          button.arc-primary {{ background-image: linear-gradient(145deg, {self._rgba(ACCENT, .42)}, {self._rgba(ACCENT, .18)});
            color: {TEXT}; border-color: {self._rgba(ACCENT, .65)}; }}
          button.arc-action:hover {{ border-color: {self._rgba(ACCENT, .6)}; }}
          spinbutton, spinbutton entry {{ background: {SURFACE}; color: {TEXT}; border-radius: 10px; }}
          checkbutton, label {{ color: {TEXT}; }}
          window.vagabond dialog {{ background-color: {BG}; color: {TEXT}; }}
          window.vagabond dialog > box {{ background-image: linear-gradient(145deg, {self._rgba(SURFACE, .98)}, {self._rgba(BG, .98)});
            border: 1px solid {edge}; border-top-color: {sheen}; border-radius: 22px; padding: 8px; }}
          window.vagabond dialog button {{ background-image: linear-gradient(145deg, {self._rgba(SURFACE, .95)}, {self._rgba(BG, .96)});
            color: {TEXT}; border: 1px solid {edge}; border-top-color: {sheen}; border-radius: 999px;
            padding: 8px 16px; min-height: 25px; }}
        """.encode())

    def _refresh_circadian(self):
        """Refresh the shared local-time palette without recreating the window."""
        global BG, SURFACE, TEXT, MUTED, ACCENT
        minute = int(time.time() // 60)
        if minute != self._last_palette_minute:
            colors = ui.circadian()
            BG, SURFACE = colors["bg"], colors["surface"]
            TEXT, MUTED = colors["fg"], colors["fg_muted"]
            ACCENT = ui.PHASE_ACCENT[colors["phase"]]
            self._last_palette_minute = minute
            self._load_style()
            self._update()
        return GLib.SOURCE_CONTINUE

    def show(self, *_args):
        if self.window is None:
            self._build_window()
        self.window.show_all()
        self.window.present()

    def _build_window(self):
        self.window = Gtk.ApplicationWindow(application=self.app, title=APP_NAME)
        self.window.set_opacity(0.985)
        self.window.set_default_size(580, 400 if self._window_timer_mode else 360)
        self.window.set_resizable(True)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        if LOGO_FILE.exists():
            try:
                self.window.set_icon_from_file(str(LOGO_FILE))
            except GLib.Error:
                self.window.set_icon_name("preferences-system-time")
        else:
            self.window.set_icon_name("preferences-system-time")
        self.window.get_style_context().add_class("vagabond")
        self.window.connect("delete-event", self._close_window)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        box.set_border_width(16)
        self.window.add(box)
        face_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        face_column.set_halign(Gtk.Align.CENTER)
        face_column.set_valign(Gtk.Align.CENTER)
        self.dial = DialArea()
        self.dial.set_tooltip_text("Mechanical timer dial · the hand sweeps every second; the arc tracks this block.")
        accessible = self.dial.get_accessible()
        accessible.set_name("Mechanical focus and rest timer")
        accessible.set_description("A circular dial. The amber hand sweeps each second; the colored arc tracks the elapsed part of the current block; remaining time sits at the hub.")
        face_column.pack_start(self.dial, False, False, 0)
        self.face_image = None
        box.pack_start(face_column, False, False, 0)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content.set_valign(Gtk.Align.CENTER)
        content.set_hexpand(True)
        box.pack_start(content, True, True, 0)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title = Gtk.Label(label="VAGABOND", xalign=0)
        title.get_style_context().add_class("arc-title")
        header.pack_start(title, True, True, 0)
        self.status_label = Gtk.Label(xalign=1)
        self.status_label.get_style_context().add_class("arc-subtle")
        header.pack_end(self.status_label, False, False, 0)
        content.pack_start(header, False, False, 0)
        self.clock_label = Gtk.Label(label="Ready when you are")
        self.clock_label.get_style_context().add_class("arc-clock")
        self.clock_label.set_xalign(0)
        content.pack_start(self.clock_label, False, False, 0)
        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        content.pack_start(action_row, False, False, 0)
        self.primary_button = Gtk.Button(label="Start timer")
        self.primary_button.get_style_context().add_class("arc-action")
        self.primary_button.get_style_context().add_class("arc-primary")
        self.primary_button.set_can_default(True)
        self.primary_button.connect("clicked", self._primary_action)
        self.window.set_default(self.primary_button)
        action_row.pack_start(self.primary_button, True, True, 0)
        self.settings_button = Gtk.Button(label="⚙  Timer settings")
        self.settings_button.get_style_context().add_class("arc-action")
        self.settings_button.connect("clicked", self._open_settings)
        action_row.pack_start(self.settings_button, False, False, 0)
        self.controls_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        content.pack_start(self.controls_row, False, False, 0)
        for label, callback in (("Stop", self.stop), ("Skip", self.skip)):
            button = Gtk.Button(label=label)
            button.get_style_context().add_class("arc-action")
            button.connect("clicked", lambda _button, cb=callback: cb())
            self.controls_row.pack_start(button, True, True, 0)
        self.cycle_hint = Gtk.Label()
        self.cycle_hint.set_xalign(0)
        self.cycle_hint.set_line_wrap(True)
        self.cycle_hint.set_max_width_chars(36)
        self.cycle_hint.get_style_context().add_class("arc-subtle")
        content.pack_start(self.cycle_hint, False, False, 0)
        self.window.show_all()
        self._update()

    def _open_settings(self, *_args):
        dialog = Gtk.Dialog(title="Vagabond · settings", transient_for=self.window,
                            modal=True, destroy_with_parent=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save settings", Gtk.ResponseType.OK)
        dialog.set_default_size(390, 360)
        body = dialog.get_content_area()
        body.set_border_width(20)
        body.set_spacing(12)
        heading = Gtk.Label(label="Shape your focus rhythm", xalign=0)
        heading.get_style_context().add_class("arc-title")
        body.pack_start(heading, False, False, 0)
        hint = Gtk.Label(label="Changes are saved locally and take effect on the next cycle.", xalign=0)
        hint.set_line_wrap(True)
        hint.get_style_context().add_class("arc-subtle")
        body.pack_start(hint, False, False, 0)

        grid = Gtk.Grid(column_spacing=14, row_spacing=12)
        body.pack_start(grid, False, False, 4)
        focus = Gtk.SpinButton.new_with_range(5, 180, 1)
        focus.set_value(self.work_minutes)
        rest = Gtk.SpinButton.new_with_range(1, 60, 1)
        rest.set_value(self.break_minutes)
        auto = Gtk.Switch()
        auto.set_active(self.auto_continue)
        alerts = Gtk.Switch()
        alerts.set_active(self.alerts_enabled)
        rows = (
            ("Focus block", "minutes", focus),
            ("Rest block", "minutes", rest),
            ("Start the next block automatically", "", auto),
            ("Send desktop alerts at transitions", "", alerts),
        )
        for row, (title, unit, control) in enumerate(rows):
            label = Gtk.Label(label=title, xalign=0)
            grid.attach(label, 0, row, 1, 1)
            if unit:
                unit_label = Gtk.Label(label=unit, xalign=0)
                unit_label.get_style_context().add_class("arc-subtle")
                grid.attach(control, 1, row, 1, 1)
                grid.attach(unit_label, 2, row, 1, 1)
            else:
                control.set_halign(Gtk.Align.END)
                grid.attach(control, 2, row, 1, 1)
        dialog.show_all()

        def save_settings(window, response):
            if response == Gtk.ResponseType.OK:
                self.work_minutes = self._bounded(focus.get_value_as_int(), 40, 5, 180)
                self.break_minutes = self._bounded(rest.get_value_as_int(), 18, 1, 60)
                self.auto_continue = auto.get_active()
                self.alerts_enabled = alerts.get_active()
                saved = read_json(CONFIG_FILE, {})
                saved.update({"work_minutes": self.work_minutes,
                              "break_minutes": self.break_minutes,
                              "auto_continue": self.auto_continue,
                              "alerts_enabled": self.alerts_enabled})
                atomic_json(CONFIG_FILE, saved)
                self._update()
            window.destroy()
        dialog.connect("response", save_settings)

    def _close_window(self, *_args):
        if self.phase != "stopped":
            self.window.iconify()
            return True
        self.app.quit()
        return False

    def _primary_action(self, *_args):
        if self.phase == "stopped":
            self.start()
            self.window.iconify()
        else:
            self.toggle_pause()

    def start(self, *_args):
        if self.phase != "stopped":
            return
        self.phase = "focus"
        self.deadline = time.time() + self.work_minutes * 60
        self.paused_left = 0
        self._save()
        self._notify("Focus started", f"{self.work_minutes} minutes on the clock.")
        self._update()

    def toggle_pause(self, *_args):
        if self.phase == "stopped":
            return
        if self.paused_left:
            self.deadline = time.time() + self.paused_left
            self.paused_left = 0
        else:
            self.paused_left = max(1, int(self.deadline - time.time()))
            self.deadline = 0
        self._save()
        self._update()

    def stop(self, *_args):
        self.phase, self.deadline, self.paused_left = "stopped", 0, 0
        self._save()
        self._update()

    def skip(self, *_args):
        if self.phase == "stopped":
            return
        self._advance(notify=False)

    def _clear_urgency(self):
        if self.window:
            self.window.set_urgency_hint(False)
        return False

    def _popup_on_transition(self):
        if not self.popup_on_transition or not self.window:
            return
        self.window.present()
        self.window.set_urgency_hint(True)
        GLib.timeout_add_seconds(8, self._clear_urgency)

    def _advance(self, notify=True):
        self.phase = "break" if self.phase == "focus" else "focus"
        minutes = self.break_minutes if self.phase == "break" else self.work_minutes
        self.deadline = time.time() + minutes * 60
        self.paused_left = 0
        self._save()
        if notify:
            label = "Rest time" if self.phase == "break" else "Focus time"
            self._notify(label, f"{minutes} minutes. Take the next small step.")
        self._popup_on_transition()
        self._update()

    def _tick(self):
        if self.phase != "stopped" and not self.paused_left and time.time() >= self.deadline:
            if self.auto_continue:
                self._advance()
            else:
                self.phase, self.deadline, self.paused_left = "stopped", 0, 0
                self._save()
                self._notify("Cycle complete", "The timer stopped at the end of this block.")
                self._update()
        if self.phase != 'stopped' and time.monotonic() - self._last_save >= 5:
            self._save()
        self._update()
        return GLib.SOURCE_CONTINUE

    def _save(self):
        atomic_json(STATE_FILE, {"phase": self.phase, "deadline": self.deadline,
                                 "paused_left": self.paused_left,
                                 "remaining": max(0, self.deadline - time.time()) if not self.paused_left else self.paused_left,
                                 "boot_id": boot_id()})
        self._last_save = time.monotonic()

    def _update(self):
        if self.phase == "stopped":
            phase_text, color, time_text = "READY", ACCENT, ""
            primary_text = "Start timer"
            progress = 0.0
        elif self.paused_left:
            phase_text, color = f"{self.phase.upper()} · PAUSED", MUTED
            duration = (self.work_minutes if self.phase == "focus" else self.break_minutes) * 60
            remaining = self.paused_left
            mins, secs = divmod(remaining, 60)
            time_text, primary_text = f"{mins:02d}:{secs:02d}", "Resume timer"
            progress = remaining / duration
        else:
            phase_text = "FOCUS" if self.phase == "focus" else "REST"
            color = WORK if self.phase == "focus" else REST
            remaining = max(0, int(self.deadline - time.time()))
            duration = (self.work_minutes if self.phase == "focus" else self.break_minutes) * 60
            mins, secs = divmod(remaining, 60)
            time_text, primary_text = f"{mins:02d}:{secs:02d}", "Pause timer"
            progress = remaining / duration
        if self.window:
            timer_mode = self.phase != "stopped"
            if timer_mode != self._window_timer_mode:
                self.window.resize(580, 400 if timer_mode else 360)
                self._window_timer_mode = timer_mode
            if self.phase == "stopped":
                self.window.set_title(APP_NAME)
            else:
                self.window.set_title(f"Vagabond · {phase_text.title()} · {time_text}")
            self._set_taskbar_icon(progress, color)
        if self.status_label:
            self.controls_row.set_visible(self.phase != "stopped")
            self.clock_label.set_visible(self.phase != "stopped")
            self.status_label.set_text(phase_text)
            self.status_label.override_color(Gtk.StateFlags.NORMAL, self._color(color))
            self.clock_label.set_text(time_text)
            self.clock_label.override_color(Gtk.StateFlags.NORMAL, self._color(color))
            self.primary_button.set_label(primary_text)
            self.cycle_hint.set_text(
                f"Focus {self.work_minutes} min  ·  Rest {self.break_minutes} min  ·  "
                f"{'auto-continue' if self.auto_continue else 'manual next'}  ·  "
                f"{'alerts on' if self.alerts_enabled else 'alerts off'}")
            self._set_timer_face(progress, color, phase_text, time_text)
            self.dial.get_accessible().set_description(
                f"{phase_text}. The dial hand tracks the elapsed part of this block; remaining time is {time_text or 'not started'}.")

    def _notify(self, title, body):
        if not self.alerts_enabled:
            return
        note = Gio.Notification.new(title)
        note.set_body(body)
        self.app.send_notification(None, note)

    def _quit_signal(self):
        self._save()
        self.app.quit()
        return GLib.SOURCE_REMOVE

    def quit(self, *_args):
        self.stop()
        self.app.quit()


def main():
    if '--status' in sys.argv[1:]:
        saved = read_json(STATE_FILE, {})
        phase = saved.get('phase', 'stopped')
        if phase not in ('focus', 'break'):
            print('stopped · explicitly stopped or not started')
        else:
            left = saved.get('paused_left') or max(0, int(saved.get('deadline', 0) - time.time()))
            minutes, seconds = divmod(int(left), 60)
            print(f"{phase} · {'paused · ' if saved.get('paused_left') else ''}{minutes:02d}:{seconds:02d}")
        return 0
    resume_only = '--resume-only' in sys.argv[1:]
    if resume_only and read_json(STATE_FILE, {}).get('phase') not in ('focus', 'break'):
        return 0
    app = Gtk.Application.new(APP_ID, Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
    holder = {}

    def activate(application):
        if "controller" not in holder:
            holder["controller"] = ArcBreak(application)
        holder["controller"].show()

    app.connect("activate", activate)
    def command_line(application, command):
        args = list(command.get_arguments())[1:]
        if '--stop' in args:
            if 'controller' in holder:
                holder['controller'].stop()
            else:
                atomic_json(STATE_FILE, {'phase': 'stopped', 'deadline': 0, 'paused_left': 0})
                application.quit()
            return 0
        activate(application)
        if '--start' in args:
            holder['controller'].start()
            holder['controller'].window.iconify()
        elif '--resume-only' in args:
            holder['controller'].window.iconify()
        return 0
    app.connect('command-line', command_line)
    app.connect('shutdown', lambda *_args: holder.get('controller') and holder['controller']._save())
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
