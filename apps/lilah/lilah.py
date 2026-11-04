#!/usr/bin/python3
"""Lilah — the circadian timepiece for GTK desktops.

The timer is local to this process and has no Arc CLI, Genmon, network, or
systemd dependency. While running, closing the window minimizes it to the taskbar.
"""
from __future__ import annotations

import json
import math
import cairo
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


APP_ID = "studio.kontor.Lilah"
APP_NAME = "Lilah"
TIMER_FACE_FILE = Path(__file__).resolve().with_name('mechanical-timer.svg')
LOGO_FILE = TIMER_FACE_FILE
CONFIG_ROOT = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "lilah"
STATE_ROOT = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "lilah"
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
    """Round mechanical movement — vintage tower-clock style. Real hour,
    minute and sweeping second hands on a roman ring. The face has a cover
    that OPENS like a pocket-watch lid when a focus/rest block starts,
    revealing the phase and remaining time beneath."""

    ROMAN = ("XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI")

    def __init__(self):
        super().__init__()
        self.set_size_request(420, 420)
        self._progress = 0.0
        self._color_hex = ACCENT
        self._phase_text = ""
        self._time_text = ""
        self.connect("draw", self._draw)
        GLib.timeout_add(80, self._sweep)

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

    @staticmethod
    def _mercury(cr, x, y0, y1, top="#E9F1F5", mid="#9FB4BE", a=1.0):
        g = cairo.LinearGradient(x, y0, x, y1)
        g.add_color_stop_rgba(0, *DialArea._col(top, a))
        g.add_color_stop_rgba(0.6, *DialArea._col(mid, a * 0.72))
        g.add_color_stop_rgba(1, *DialArea._col(mid, a * 0.18))
        return g

    def _hand(self, cr, cx, cy, angle, length, tail, width, color, ornate=False):
        """Baroque tapered hand: brushed-brass gradient, pierced tip, ringed
        counterweight — mercury on metal, dressed for the dark."""
        ux, uy = math.cos(angle), math.sin(angle)
        px, py = -uy, ux
        w_base = width; w_tip = max(1.2, width * 0.30)
        bx, by = cx + length*ux, cy + length*uy
        # cast shadow first (offset down-right), then the hand floats above it
        cr.save()
        cr.translate(1.6, 2.2)
        cr.move_to(cx - tail*ux + w_base*px*0.4, cy - tail*uy + w_base*py*0.4)
        cr.line_to(bx + w_tip*px, by + w_tip*py)
        cr.line_to(bx - w_tip*px, by - w_tip*py)
        cr.line_to(cx - tail*ux - w_base*px*0.4, cy - tail*uy - w_base*py*0.4)
        cr.close_path()
        cr.set_source_rgba(0, 0, 0, .32); cr.fill()
        cr.restore()
        grad = cairo.LinearGradient(cx - tail*ux, cy - tail*uy, bx, by)
        grad.add_color_stop_rgba(0, *self._col("#8A6B3E"))
        grad.add_color_stop_rgba(0.55, *self._col(color))
        grad.add_color_stop_rgba(1, *self._col("#F2E3C2"))
        cr.set_source(grad)
        cr.move_to(cx - tail*ux + w_base*px*0.4, cy - tail*uy + w_base*py*0.4)
        cr.line_to(bx + w_tip*px, by + w_tip*py)
        cr.line_to(bx - w_tip*px, by - w_tip*py)
        cr.line_to(cx - tail*ux - w_base*px*0.4, cy - tail*uy - w_base*py*0.4)
        cr.close_path(); cr.fill()
        if ornate:
            # pierced diamond near the tip
            dpos = length * 0.72; dw = width * 0.9
            dx, dy = cx + dpos*ux, cy + dpos*uy
            cr.set_source_rgba(*self._col("#0B0D10", .85))
            cr.move_to(dx + dw*ux, dy + dw*uy)
            cr.line_to(dx + dw*px*0.7, dy + dw*py*0.7)
            cr.line_to(dx - dw*ux, dy - dw*uy)
            cr.line_to(dx - dw*px*0.7, dy - dw*py*0.7)
            cr.close_path(); cr.fill()
        # ringed counterweight
        ccx, ccy = cx - (tail + width)*ux, cy - (tail + width)*uy
        cr.arc(ccx, ccy, width*1.25, 0, 6.2832)
        cr.set_source_rgba(*self._col(color)); cr.fill()
        cr.arc(ccx, ccy, width*0.55, 0, 6.2832)
        cr.set_source_rgba(*self._col("#0B0D10", .8)); cr.fill()

    def _draw(self, _widget, cr):
        w = self.get_allocated_width(); h = self.get_allocated_height()
        cx, cy = w/2.0, h/2.0
        R = min(w, h)/2.0 - 6
        now = time.localtime()
        pal = ui.circadian()
        face_bg = pal.get("bg", BG); face_surface = pal.get("surface", SURFACE)
        face_fg = pal.get("fg", TEXT)
        phase_name = str(pal.get("phase", "")).upper().replace("-", " ")
        phase_accent = ui.PHASE_ACCENT.get(str(pal.get("phase", "")), "#9FB4BE")

        # soft cast shadow under the movement — a pool, not a ring
        sh = cairo.RadialGradient(cx, cy + 9, R*0.5, cx, cy + 9, R + 16)
        sh.add_color_stop_rgba(0, 0, 0, 0, .38)
        sh.add_color_stop_rgba(1, 0, 0, 0, 0)
        cr.set_source(sh)
        cr.arc(cx, cy + 9, R + 16, 0, 6.2832); cr.fill()

        # face — tucked inside the silhouette so the rim stays open skeleton
        cr.arc(cx, cy, R*0.90, 0, 6.2832)
        pat = cairo.RadialGradient(cx - R*0.28, cy - R*0.32, R*0.1, cx, cy, R*0.92)
        pat.add_color_stop_rgba(0, *self._col(face_surface, 1))
        pat.add_color_stop_rgba(1, *self._col(face_bg, 1))
        cr.set_source(pat); cr.fill()

        # minute track, tucked at the rim
        for i in range(60):
            a = i * 6.2832 / 60 - 1.5708
            big = i % 5 == 0
            r0 = R*0.90 - 8; r1 = R*0.90 - (20 if big else 15)
            cr.set_source_rgba(*(self._col("#D4B27A", .7) if big else self._col("#96A0AC", .35)))
            cr.set_line_width(1.6 if big else 1)
            cr.move_to(cx + r0*math.cos(a), cy + r0*math.sin(a))
            cr.line_to(cx + r1*math.cos(a), cy + r1*math.sin(a)); cr.stroke()

        # THE SHELL — three wheels meshed as one movement, each carrying 1-12.
        def big_gear(gx, gy, gr, ang):
            cr.save()
            cr.translate(gx, gy); cr.rotate(ang)
            teeth = 20
            cr.set_source_rgba(*self._col("#454E5A"))
            for i in range(teeth):
                a = i * 6.2832 / teeth
                cr.save(); cr.rotate(a)
                cr.rectangle(gr - 4, -2.6, 8.5, 5.2)
                cr.fill()
                cr.restore()
            cr.arc(0, 0, gr - 4, 0, 6.2832)
            cr.set_source_rgba(*self._col("#272D36", .95)); cr.fill_preserve()
            cr.set_source_rgba(*self._col("#59636F", .9)); cr.set_line_width(2); cr.stroke()
            for i in range(5):
                a = i * 6.2832 / 5
                cr.set_source_rgba(*self._col("#3E4650", .85))
                cr.set_line_width(3.4)
                cr.move_to(0, 0)
                cr.line_to((gr - 14)*math.cos(a), (gr - 14)*math.sin(a)); cr.stroke()
            cr.arc(0, 0, 8, 0, 6.2832)
            cr.set_source_rgba(*self._col("#59636F")); cr.fill()
            cr.arc(0, 0, 4, 0, 6.2832)
            cr.set_source_rgba(*self._col("#20252C")); cr.fill()
            cr.restore()
            # the wheel's own 1-12 chapter, upright, quiet
            cr.select_font_face("DejaVu Sans", 0, 0)
            cr.set_font_size(9.5)
            for i in range(12):
                a = i * 6.2832 / 12 - 1.5708
                lab = str(12 if i == 0 else i)
                lx = gx + (gr - 22)*math.cos(a); ly = gy + (gr - 22)*math.sin(a)
                ext = cr.text_extents(lab)
                cr.set_source_rgba(*self._col(face_fg, .5))
                cr.move_to(lx - ext.width/2 - ext.x_bearing, ly - ext.height/2 - ext.y_bearing)
                cr.show_text(lab)

        tt2 = time.time()
        mesh = 0.22
        for gi in range(3):
            ga = gi * 2.0944 - 1.5708
            gxr = R*0.53
            gx = cx + gxr*math.cos(ga); gy = cy + gxr*math.sin(ga)
            gr = R*0.52
            big_gear(gx, gy, gr, (1 if gi % 2 == 0 else -1) * tt2 * mesh + gi * 0.31)

        # phase complication at 3 o'clock — the hour of day, mechanically
        order = ["choice", "desire", "still-pine", "nyx"]
        phase = str(pal.get("phase", "nyx"))
        pidx = order.index(phase) if phase in order else 3
        sx = cx + (R - 96); sy = cy
        sr = 20
        cr.arc(sx, sy, sr, 0, 6.2832)
        cr.set_source_rgba(*self._col("#A88452", .8)); cr.set_line_width(2); cr.stroke()
        for i in range(4):
            a = i * 1.5708 - 1.5708
            big = i == pidx
            cr.arc(sx + (sr-6)*math.cos(a), sy + (sr-6)*math.sin(a), 2.4 if big else 1.4, 0, 6.2832)
            cr.set_source_rgba(*(self._col("#D4B27A", .95) if big else self._col("#6E6858", .7)))
            cr.fill()
        cr.select_font_face("DejaVu Serif", 0, 1)
        cr.set_font_size(7)
        for i, lab in enumerate(("I", "II", "III", "IV")):
            a = i * 1.5708 - 1.5708
            lx, ly = sx + (sr+6)*math.cos(a), sy + (sr+6)*math.sin(a)
            ext = cr.text_extents(lab)
            cr.set_source_rgba(*self._col("#8E8468", .75))
            cr.move_to(lx - ext.width/2 - ext.x_bearing, ly - ext.height/2 - ext.y_bearing)
            cr.show_text(lab)
        pa = pidx * 1.5708 - 1.5708
        cr.set_source_rgba(*self._col("#E8A33D" if self._progress > 0 else "#9A917E"))
        cr.set_line_width(2); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(sx - 5*math.cos(pa), sy - 5*math.sin(pa))
        cr.line_to(sx + (sr-9)*math.cos(pa), sy + (sr-9)*math.sin(pa)); cr.stroke()
        cr.arc(sx, sy, 2.4, 0, 6.2832)
        cr.set_source_rgba(*self._col("#D4B27A")); cr.fill()

        # hands at the true center
        m = now.tm_min + now.tm_sec/60.0
        hr = (now.tm_hour % 12) + m/60.0
        self._hand(cr, cx, cy, hr*6.2832/12 - 1.5708, R*0.40, R*0.09, 6.5, "#E8E2D4", ornate=True)
        self._hand(cr, cx, cy, m*6.2832/60 - 1.5708, R*0.60, R*0.11, 4.5, "#D9D2C0", ornate=True)
        seca = (time.time() % 60) * 6.2832/60 - 1.5708
        self._hand(cr, cx, cy, seca, R*0.70, R*0.16, 1.8, "#E8A33D")
        for i in range(8):
            a = i * 6.2832/8
            cr.arc(cx + 11*math.cos(a), cy + 11*math.sin(a), 2.1, 0, 6.2832)
            cr.set_source_rgba(*self._col("#A88452", .8)); cr.fill()
        cr.arc(cx, cy, 8, 0, 6.2832)
        cr.set_source_rgba(*self._col("#D4B27A")); cr.fill()
        cr.arc(cx, cy, 3.2, 0, 6.2832)
        cr.set_source_rgba(*self._col("#1A1409")); cr.fill()

        # glass register — countdown + block together, framed, unmistakable
        pw2, ph3 = 156, 64
        py2 = cy + 34
        cr.arc(cx - pw2/2 + 10, py2 + 10, 10, 3.1416, 4.7124)
        cr.arc(cx + pw2/2 - 10, py2 + 10, 10, 4.7124, 0)
        cr.arc(cx + pw2/2 - 10, py2 + ph3 - 10, 10, 0, 1.5708)
        cr.arc(cx - pw2/2 + 10, py2 + ph3 - 10, 10, 1.5708, 3.1416)
        cr.close_path()
        cr.set_source_rgba(*self._col(face_bg, .6)); cr.fill_preserve()
        cr.set_source_rgba(*self._col("#DFE9EE", .3)); cr.set_line_width(1); cr.stroke()
        digits = self._time_text or "--:--"
        cr.select_font_face("DejaVu Sans Mono", 0, 0)
        cr.set_font_size(25)
        ext = cr.text_extents(digits)
        cr.set_source(self._mercury(cr, cx, py2 + 2, py2 + 38, a=.95))
        cr.move_to(cx - ext.width/2 - ext.x_bearing, py2 + 30)
        cr.show_text(digits)


        # the circadian hour — top, wearing the engine's phase color
        cr.select_font_face("DejaVu Sans Light,DejaVu Sans", 0, 0)
        cr.set_font_size(12.5)
        ext = cr.text_extents(phase_name)
        g = cairo.LinearGradient(cx, cy - R*0.40 - 12, cx, cy - R*0.40 + 8)
        g.add_color_stop_rgba(0, *self._col(phase_accent, .95))
        g.add_color_stop_rgba(1, *self._col(phase_accent, .30))
        cr.set_source(g)
        cr.move_to(cx - ext.width/2 - ext.x_bearing, cy - R*0.40)
        cr.show_text(phase_name)

        # the signature — "lilah" is the face of the watch: calligraphic,
        # phase-aware, calm. Morning flows, day reads warm, dusk leans,
        # night whispers.
        sig_fonts = {
            "choice": ("Z003", 21),
            "desire": ("URW Bookman", 16),
            "still-pine": ("URW Bookman", 16),
            "nyx": ("DejaVu Serif", 15),
        }
        sig_face, sig_size = sig_fonts.get(str(pal.get("phase", "")), ("DejaVu Serif", 15))
        cr.select_font_face(sig_face, 0, 1)
        cr.set_font_size(sig_size)
        mark = "lilah"
        ext = cr.text_extents(mark)
        lx = cx - ext.width/2 - ext.x_bearing; ly = cy + R*0.62
        cr.set_source_rgba(0, 0, 0, .55)
        cr.move_to(lx + 0.7, ly + 1.0)
        cr.show_text(mark)
        g2 = cairo.LinearGradient(cx, ly - sig_size, cx, ly + 4)
        g2.add_color_stop_rgba(0, *self._col("#F3E7C8", .95))
        g2.add_color_stop_rgba(1, *self._col(phase_accent, .55))
        cr.set_source(g2)
        cr.move_to(lx, ly)
        cr.show_text(mark)


class Bubble(Gtk.Window):
    """Lilah's own notification: a glossy gum-drop balloon that drops in
    beside the watch, settles, and floats away. Not a system notification."""

    def __init__(self, text, accent, origin=(80, 120)):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_app_paintable(True)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_size_request(200, 128)
        self._text, self._accent = text, accent
        self._op = 1.0
        self._ty = 0
        area = Gtk.DrawingArea()
        area.connect("draw", self._draw)
        self.add(area)
        self._ox, self._oy = origin
        self.move(self._ox, self._oy - 26)
        self.show_all()
        GLib.timeout_add(60, self._drop)
        GLib.timeout_add(3400, self._leave)
        GLib.timeout_add_seconds(7, self._hard_destroy)

    @staticmethod
    def _col(hex_color, alpha=1.0):
        v = hex_color.lstrip('#')
        return (int(v[0:2],16)/255, int(v[2:4],16)/255, int(v[4:6],16)/255, alpha)

    def _draw(self, _w, cr):
        w = self.get_allocated_width(); h = self.get_allocated_height()
        cx, cy = w/2.0, h/2.0 - 6
        r = min(w, h)/2.0 - 12
        a = self._accent
        cr.set_source_rgba(*self._col(a, .30))
        cr.arc(cx + 3, cy + 7, r, 0, 6.2832)
        cr.arc(cx, cy + r + 4, 7, 0, 6.2832)   # little tail
        cr.fill()
        body = cairo.RadialGradient(cx - r*0.4, cy - r*0.5, r*0.15, cx, cy, r + 4)
        body.add_color_stop_rgba(0, *self._col("#F4F7F9", .97))
        body.add_color_stop_rgba(0.55, *self._col("#DDE6EC", .96))
        body.add_color_stop_rgba(1, *self._col(a, .90))
        cr.set_source(body)
        cr.arc(cx, cy, r, 0, 6.2832)
        cr.arc(cx, cy + r + 2, 6, 0, 6.2832)
        cr.fill()
        cr.set_source_rgba(1, 1, 1, .5)
        cr.arc(cx - r*0.38, cy - r*0.45, r*0.30, 0, 6.2832)
        cr.fill()
        cr.select_font_face("DejaVu Sans", 0, 1)
        cr.set_font_size(12.5)
        lines = self._text.split("\n")
        for i, line in enumerate(lines):
            ext = cr.text_extents(line)
            cr.set_source_rgba(*self._col("#1A222B", .92))
            cr.move_to(cx - ext.width/2 - ext.x_bearing, cy - 4 + i*16)
            cr.show_text(line)

    def _drop(self):
        self._ty += 4
        self.move(self._ox, self._oy - 26 + self._ty)
        if self._ty < 26:
            return True
        return False

    def _hard_destroy(self):
        try:
            self.destroy()
        except Exception:
            pass
        return False

    def _leave(self):
        self._op -= 0.08
        if self._op <= 0:
            self.destroy()
            return False
        self.set_opacity(self._op)
        self._oy -= 2
        self.move(self._ox, self._oy)
        return True


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
        if self.phase in ("focus", "break"):
            GLib.timeout_add_seconds(2, self._announce_resume)
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

    def _taskbar_pixbuf(self, progress, color, size):
        """Miniature of the watch for the panel: bronze ring, the block's arc,
        a phase hub. Present, not loud."""
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        cr = cairo.Context(surf)
        s = size; c = s / 2.0
        R = s / 2.0 - 1
        pal = ui.circadian()
        accent = ui.PHASE_ACCENT.get(str(pal.get("phase", "")), "#9FB4BE")
        muted = pal.get("fg_muted", "#8E8468")
        def col(hexs, a=1.0):
            v = hexs.lstrip('#')
            return (int(v[0:2],16)/255, int(v[2:4],16)/255, int(v[4:6],16)/255, a)
        # outer ring — wears the hour's accent
        cr.arc(c, c, R, 0, 6.2832)
        cr.set_source_rgba(*col(accent, .85)); cr.set_line_width(max(1.6, s*0.06)); cr.stroke()
        # dim full track — the hour's muted tone
        cr.arc(c, c, R - s*0.09, 0, 6.2832)
        cr.set_source_rgba(*col(muted, .6)); cr.set_line_width(max(1.2, s*0.075)); cr.stroke()
        if progress > 0:
            frac = 1.0 - progress
            cr.arc(c, c, R - s*0.09, -1.5708, -1.5708 + frac*6.2832)
            cr.set_source_rgba(*col(color)); cr.set_line_width(max(1.2, s*0.075)); cr.stroke()
        else:
            # stopped: a quiet breathing dot in the hour's muted tone
            cr.arc(c, c, s*0.16, 0, 6.2832)
            cr.set_source_rgba(*col(muted, .85)); cr.fill()
        # phase hub — the hour's accent while running
        cr.arc(c, c, s*0.10, 0, 6.2832)
        cr.set_source_rgba(*col(accent if progress > 0 else muted))
        cr.fill()
        return Gdk.pixbuf_get_from_surface(surf, 0, 0, s, s)

    def _set_taskbar_icon(self, progress, color):
        if self.window is None:
            return
        key = (self.phase, round(progress, 3), color, bool(self.paused_left), ui.circadian().get("phase"))
        if key == self._taskbar_icon_key:
            return
        pixbuf = self._taskbar_pixbuf(progress, color, 64)
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
        edge = self._rgba(TEXT, .30)
        sheen = self._rgba("#ffffff", .10)
        self.css.load_from_data(f"""
          window.lilah {{ background-color: transparent; color: {TEXT}; }}
          window.lilah > box {{
            background-image: linear-gradient(145deg, {self._rgba(SURFACE, .74)}, {self._rgba(BG, .82)});
            border: 1px solid {edge}; border-top-color: {sheen}; border-radius: 14px;
            box-shadow: inset 0 1px {sheen}, 0 10px 30px {self._rgba("#000000", .30)};
            padding: 7px;
          }}
          scrollbar {{ background: transparent; }}
          scrollbar trough {{ border-radius: 999px; }}
          scrollbar slider {{ border-radius: 999px; min-width: 10px; min-height: 28px; background: {ACCENT}; }}
          .arc-title {{ color: {TEXT}; font-size: 20px; font-weight: 600; }}
          .arc-clock {{ color: {ACCENT}; font-size: 42px; font-weight: 300; }}
          .arc-subtle {{ color: {MUTED}; font-size: 12px; }}
          button.arc-action {{ background-image: linear-gradient(145deg, {self._rgba(SURFACE, .96)}, {self._rgba(BG, .96)});
            color: {TEXT}; border: 1px solid {edge}; border-top-color: {sheen};
            border-radius: 999px; padding: 7px 15px; min-height: 24px; box-shadow: inset 0 1px {self._rgba("#ffffff", .08)}, 0 1px 4px {self._rgba("#000000", .16)}; }}
          button.arc-primary {{ background-image: linear-gradient(145deg, {self._rgba(ACCENT, .42)}, {self._rgba(ACCENT, .18)});
            color: {TEXT}; border-color: {self._rgba(ACCENT, .65)}; }}
          button.arc-action:hover {{ border-color: {self._rgba(ACCENT, .6)}; }}
          spinbutton, spinbutton entry {{ background: {SURFACE}; color: {TEXT}; border-radius: 10px; }}
          checkbutton, label {{ color: {TEXT}; }}
          window.lilah dialog {{ background-color: {BG}; color: {TEXT}; }}
          window.lilah dialog > box {{ background-image: linear-gradient(145deg, {self._rgba(SURFACE, .80)}, {self._rgba(BG, .88)});
            border: 1px solid {edge}; border-top-color: {sheen}; border-radius: 14px; padding: 7px; }}
          window.lilah dialog button {{ background-image: linear-gradient(145deg, {self._rgba(SURFACE, .95)}, {self._rgba(BG, .96)});
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
        self.window.set_app_paintable(True)
        self.window.set_default_size(448, 428)
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        if LOGO_FILE.exists():
            try:
                self.window.set_icon_from_file(str(LOGO_FILE))
            except GLib.Error:
                self.window.set_icon_name("preferences-system-time")
        else:
            self.window.set_icon_name("preferences-system-time")
        self.window.get_style_context().add_class("lilah")
        self.window.connect("delete-event", self._close_window)
        self.window.connect("key-press-event", self._key_press)
        self.dial = DialArea()
        self.dial.set_tooltip_text(
            "Lilah · left-click starts or pauses · right-click for menu · Esc hides · Alt+drag moves")
        self.dial.connect("button-press-event", self._face_click)
        accessible = self.dial.get_accessible()
        accessible.set_name("Lilah timepiece")
        accessible.set_description(
            "A round mechanical clock with hour, minute and second hands. "
            "Left click starts or pauses the focus and rest timer. "
            "When a block begins, the face opens to reveal the phase and remaining time.")
        self.window.add(self.dial)
        self.face_image = None
        self.window.show_all()
        self.window.present()
        GLib.idle_add(self._apply_round_shape)

    def _apply_round_shape(self):
        w = self.window.get_allocated_width()
        h = self.window.get_allocated_height()
        if min(w, h) < 80:            # not laid out yet — retry shortly
            GLib.timeout_add(200, self._apply_round_shape)
            return False
        R = min(w, h) / 2.0 - 6
        if R < 40:
            R = 200.0
        cx, cy = w / 2.0, h / 2.0
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surf)
        # the silhouette is the train: three solid wheel-discs + the center
        # disc. The drawn teeth ride this edge; the gaps are see-through.
        for gi in range(3):
            ga = gi * 2.0944 - 1.5708
            cr.arc(cx + R * 0.53 * math.cos(ga), cy + R * 0.53 * math.sin(ga), R * 0.52 + 6, 0, 6.2832)
        cr.arc(cx, cy, R * 0.72, 0, 6.2832)
        cr.fill()
        region = Gdk.cairo_region_create_from_surface(surf)
        self.window.shape_combine_region(region)
        self.window.input_shape_combine_region(region)
        return False

    def _face_click(self, _widget, event):
        if event.button == 1:
            if event.state & Gdk.ModifierType.MOD1_MASK:  # Alt+left: move the watch
                self.window.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            else:
                self._primary_action()
        elif event.button == 3:
            self._context_menu(event)
        return True

    def _context_menu(self, event):
        menu = Gtk.Menu()

        settings_item = Gtk.MenuItem(label="Settings…")
        settings_item.connect("activate", lambda *_: self._open_settings())
        menu.append(settings_item)
        menu.append(Gtk.SeparatorMenuItem())

        hide_item = Gtk.MenuItem(label="Hide watch  ·  Esc")
        hide_item.connect("activate", lambda *_: self.window.iconify())
        menu.append(hide_item)

        stop_item = Gtk.MenuItem(label="Stop timer")
        stop_item.set_sensitive(self.phase != "stopped")
        stop_item.connect("activate", lambda *_: self.stop())
        menu.append(stop_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Exit Lilah")
        quit_item.connect("activate", lambda *_: self.app.quit())
        menu.append(quit_item)

        menu.show_all()
        menu.popup_at_pointer(event)

    def _key_press(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.window.iconify()
            return True
        return False

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

    def _announce_resume(self):
        remaining = self.paused_left or max(0, int(self.deadline - time.time()))
        mins = max(1, (remaining + 59) // 60)
        state = "paused" if self.paused_left else "resumed"
        # if the watch is already on screen, she IS the announcement — no balloon
        if self.window and self.window.is_visible() and not self.window.is_iconified():
            return False
        self._notify("Lilah", f"{state} — {mins} minute{'s' if mins != 1 else ''} remaining on the {self.phase}.")
        return False

    def _open_settings(self, *_args):
        dlg = Gtk.Dialog(title="Lilah · settings", transient_for=self.window, modal=True)
        dlg.set_default_size(300, -1)
        box = dlg.get_content_box()
        box.set_spacing(8); box.set_border_width(14)

        def row(label, widget):
            r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            l = Gtk.Label(label=label, xalign=0); l.set_hexpand(True)
            r.pack_start(l, True, True, 0); r.pack_start(widget, False, False, 0)
            box.pack_start(r, False, False, 0)
            return widget

        adj_f = Gtk.Adjustment(value=self.work_minutes, lower=5, upper=180, step_increment=1)
        spin_f = Gtk.SpinButton(adjustment=adj_f, climb_rate=1, digits=0)
        row("Focus minutes", spin_f)
        adj_b = Gtk.Adjustment(value=self.break_minutes, lower=1, upper=60, step_increment=1)
        spin_b = Gtk.SpinButton(adjustment=adj_b, climb_rate=1, digits=0)
        row("Rest minutes", spin_b)
        chk_auto = Gtk.CheckButton(label="Auto-continue to next block")
        chk_auto.set_active(self.auto_continue)
        box.pack_start(chk_auto, False, False, 0)
        chk_alerts = Gtk.CheckButton(label="Announce blocks (bubble + voice)")
        chk_alerts.set_active(self.alerts_enabled)
        box.pack_start(chk_alerts, False, False, 0)

        dlg.add_button("Close", Gtk.ResponseType.CLOSE)
        dlg.show_all()
        dlg.connect("response", lambda d, _r: d.destroy())
        def save(*_a):
            self.work_minutes = self._bounded(spin_f.get_value_as_int(), 40, 5, 180)
            self.break_minutes = self._bounded(spin_b.get_value_as_int(), 18, 1, 60)
            self.auto_continue = chk_auto.get_active()
            self.alerts_enabled = chk_alerts.get_active()
            import json as _j
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(_j.dumps({"work_minutes": self.work_minutes, "break_minutes": self.break_minutes,
                                             "auto_continue": self.auto_continue, "alerts_enabled": self.alerts_enabled}) + "\n")
            self._update()
        spin_f.connect("value-changed", save); spin_b.connect("value-changed", save)
        chk_auto.connect("toggled", save); chk_alerts.connect("toggled", save)

    def _advance(self, notify=True):
        self.phase = "break" if self.phase == "focus" else "focus"
        minutes = self.break_minutes if self.phase == "break" else self.work_minutes
        self.deadline = time.time() + minutes * 60
        self.paused_left = 0
        self._save()
        if notify:
            label = "Rest time" if self.phase == "break" else "Focus time"
            self._notify(label, f"{minutes} minutes. Take the next small step.")
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
            if self.phase == "stopped":
                self.window.set_title(APP_NAME)
            else:
                self.window.set_title(f"Lilah · {phase_text.title()} · {time_text}")
            self._set_taskbar_icon(progress, color)
        if getattr(self, "status_label", None):
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
        if getattr(self, "dial", None) is not None:
            self._set_timer_face(progress, color, phase_text, time_text)
            self.dial.get_accessible().set_description(
                f"{phase_text}. The face opens when a block runs; remaining time is {time_text or 'not started'}.")

    def _notify(self, title, body):
        if not self.alerts_enabled:
            return
        accent = ui.PHASE_ACCENT.get(str(ui.circadian().get("phase", "")), "#E8A33D")
        pos = (80, 120)
        if self.window:
            pos = (self.window.get_position()[0] + self.window.get_size()[0] + 12,
                   self.window.get_position()[1] + 60)
        Bubble(f"{title}\n{body}", accent, pos)
        try:
            import subprocess
            subprocess.Popen(["arc-pine-speak", f"lilah · {title}. {body}."])
        except OSError:
            pass

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
