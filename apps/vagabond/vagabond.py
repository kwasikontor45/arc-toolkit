#!/usr/bin/python3
"""Vagabond — a small, standalone wandering break timer for GTK desktops.

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
    """Round mechanical movement — vintage tower-clock style. Real hour,
    minute and sweeping second hands on a roman ring. The face has a cover
    that OPENS like a pocket-watch lid when a focus/rest block starts,
    revealing the phase and remaining time beneath."""

    ROMAN = ("XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI")

    def __init__(self):
        super().__init__()
        self.set_size_request(340, 340)
        self._progress = 0.0
        self._color_hex = ACCENT
        self._phase_text = ""
        self._time_text = ""
        self._lid = 0.0
        self._lid_target = 0.0
        self.connect("draw", self._draw)
        GLib.timeout_add(80, self._sweep)

    def set_state(self, progress, color_hex, phase_text, time_text):
        self._progress = progress
        self._color_hex = color_hex
        self._phase_text = phase_text
        self._time_text = time_text
        self._lid_target = 1.0 if progress > 0 else 0.0
        self.queue_draw()

    def _sweep(self):
        if abs(self._lid - self._lid_target) > 0.008:
            step = 0.05 if self._lid_target > self._lid else -0.05
            self._lid = max(0.0, min(1.0, self._lid + step))
        if self.get_mapped():
            self.queue_draw()
        return True

    @staticmethod
    def _col(hex_color, alpha=1.0):
        v = hex_color.lstrip('#')
        return (int(v[0:2], 16)/255, int(v[2:4], 16)/255, int(v[4:6], 16)/255, alpha)

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
        # 3D: drop shadow lifting the watch off the desk (renders in the band
        # between bezel and window edge; the shape covers it)
        sh = cairo.RadialGradient(cx, cy + 5, R*0.92, cx, cy + 5, R + 18)
        sh.add_color_stop_rgba(0, 0, 0, 0, .55)
        sh.add_color_stop_rgba(0.75, 0, 0, 0, .28)
        sh.add_color_stop_rgba(1, 0, 0, 0, 0)
        cr.set_source(sh)
        cr.arc(cx, cy + 5, R + 18, 0, 6.2832); cr.fill()
        # face — tinted by the live circadian engine
        cr.arc(cx, cy, R, 0, 6.2832)
        pat = cairo.RadialGradient(cx - R*0.3, cy - R*0.35, R*0.1, cx, cy, R)
        pat.add_color_stop_rgba(0, *self._col(face_surface, 1))
        pat.add_color_stop_rgba(1, *self._col(face_bg, 1))
        cr.set_source(pat); cr.fill()
        # soft sheen across the glass
        sheen = cairo.LinearGradient(cx - R, cy - R, cx + R*0.4, cy + R*0.5)
        sheen.add_color_stop_rgba(0, 1, 1, 1, .10)
        sheen.add_color_stop_rgba(0.5, 1, 1, 1, .02)
        sheen.add_color_stop_rgba(1, 1, 1, 1, .07)
        cr.arc(cx, cy, R - 10, 0, 6.2832)
        cr.set_source(sheen); cr.fill()
        # minute track + roman numerals
        for i in range(60):
            a = i * 6.2832 / 60 - 1.5708
            big = i % 5 == 0
            r0 = R - 14; r1 = R - (30 if big else 22)
            cr.set_source_rgba(*(self._col("#D4B27A", .85) if big else self._col("#96A0AC", .45)))
            cr.set_line_width(2 if big else 1)
            cr.move_to(cx + r0*math.cos(a), cy + r0*math.sin(a))
            cr.line_to(cx + r1*math.cos(a), cy + r1*math.sin(a)); cr.stroke()
        cr.select_font_face("DejaVu Serif", 0, 1)
        for i, num in enumerate(self.ROMAN):
            a = i * 6.2832 / 12 - 1.5708
            rr = R - 52
            x, y = cx + rr*math.cos(a), cy + rr*math.sin(a)
            cr.set_font_size(21)
            ext = cr.text_extents(num)
            cr.set_source_rgba(*self._col(face_fg, .9))
            cr.move_to(x - ext.width/2 - ext.x_bearing, y - ext.height/2 - ext.y_bearing)
            cr.show_text(num)
        # chapter ring: minute figures every five, tucked and quiet
        cr.select_font_face("DejaVu Serif", 0, 0)
        cr.set_font_size(10)
        for i in range(12):
            a = i * 6.2832 / 12 - 1.5708
            rr = R - 70
            label = f"{(i*5) if i else 60:02d}"
            ext = cr.text_extents(label)
            cr.set_source_rgba(*self._col("#8E8468", .5))
            cr.move_to(cx + rr*math.cos(a) - ext.width/2 - ext.x_bearing,
                       cy + rr*math.sin(a) - ext.height/2 - ext.y_bearing)
            cr.show_text(label)
        # phase complication — a mechanical sub-dial at 3 o'clock, the way a
        # real movement would carry the hour of day: one small hand, four stops
        order = ["choice", "desire", "still-pine", "nyx"]
        phase = str(pal.get("phase", "nyx"))
        pidx = order.index(phase) if phase in order else 3
        sx = cx + (R - 104); sy = cy
        sr = 21
        cr.arc(sx, sy, sr, 0, 6.2832)
        cr.set_source_rgba(*self._col("#A88452", .8)); cr.set_line_width(2); cr.stroke()
        cr.arc(sx, sy, sr - 3, 0, 6.2832)
        cr.set_source_rgba(*self._col(face_bg, .9)); cr.set_line_width(1); cr.fill()
        for i in range(4):
            a = i * 1.5708 - 1.5708
            big = i == pidx
            cr.arc(sx + (sr-7)*math.cos(a), sy + (sr-7)*math.sin(a), 2.6 if big else 1.5, 0, 6.2832)
            cr.set_source_rgba(*(self._col("#D4B27A", .95) if big else self._col("#6E6858", .7)))
            cr.fill()
        # roman stop labels I–IV
        cr.select_font_face("DejaVu Serif", 0, 1)
        cr.set_font_size(7.5)
        for i, lab in enumerate(("I", "II", "III", "IV")):
            a = i * 1.5708 - 1.5708
            lx, ly = sx + (sr+7)*math.cos(a), sy + (sr+7)*math.sin(a)
            ext = cr.text_extents(lab)
            cr.set_source_rgba(*self._col("#8E8468", .75))
            cr.move_to(lx - ext.width/2 - ext.x_bearing, ly - ext.height/2 - ext.y_bearing)
            cr.show_text(lab)
        # the phase hand
        pa = pidx * 1.5708 - 1.5708
        cr.set_source_rgba(*self._col("#E8A33D" if self._progress > 0 else "#9A917E"))
        cr.set_line_width(2); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(sx - 5*math.cos(pa), sy - 5*math.sin(pa))
        cr.line_to(sx + (sr-10)*math.cos(pa), sy + (sr-10)*math.sin(pa)); cr.stroke()
        cr.arc(sx, sy, 2.6, 0, 6.2832)
        cr.set_source_rgba(*self._col("#D4B27A")); cr.fill()
        # filigree arcs flanking the hinge — baroque whisper, not noise
        for sgn in (-1, 1):
            cr.arc(cx, cy, R - 34, 1.5708 + sgn*0.55 - 0.38, 1.5708 + sgn*0.55 + 0.38)
            cr.set_source_rgba(*self._col("#A88452", .4))
            cr.set_line_width(1.4); cr.stroke()
        # the shell — three great gears meshed as the window's outside outline.
        # No ring, no arcs: the case IS the train, each wheel turning.
        def big_gear(gx, gy, gr, ang, teeth=22):
            cr.save()
            cr.translate(gx, gy); cr.rotate(ang)
            cr.set_source_rgba(*self._col("#454E5A"))
            for i in range(teeth):
                a = i * 6.2832 / teeth
                cr.save(); cr.rotate(a)
                cr.rectangle(gr - 4, -2.6, 8.5, 5.2)
                cr.fill()
                cr.restore()
            cr.arc(0, 0, gr - 4, 0, 6.2832)
            cr.set_source_rgba(*self._col("#272D36", .96)); cr.fill_preserve()
            cr.set_source_rgba(*self._col("#59636F", .95)); cr.set_line_width(2.2); cr.stroke()
            cr.arc(0, 0, gr - 13, 0, 6.2832)
            cr.set_source_rgba(*self._col("#454E5A", .5)); cr.set_line_width(1.2); cr.stroke()
            for i in range(6):
                a = i * 6.2832 / 6
                cr.set_source_rgba(*self._col("#3E4650"))
                cr.set_line_width(6)
                cr.move_to(0, 0)
                cr.line_to((gr - 16)*math.cos(a), (gr - 16)*math.sin(a)); cr.stroke()
            cr.arc(0, 0, 9, 0, 6.2832)
            cr.set_source_rgba(*self._col("#59636F")); cr.fill()
            cr.arc(0, 0, 4.5, 0, 6.2832)
            cr.set_source_rgba(*self._col("#20252C")); cr.fill()
            cr.restore()
        tt2 = time.time()
        mesh = 0.22  # rad/s at the pitch circle; adjacent wheels counter-rotate
        for gi in range(3):
            ga = gi * 2.0944 - 1.5708  # 120° apart, one at 12 o'clock
            gxr = R*0.60
            gx = cx + gxr*math.cos(ga); gy = cy + gxr*math.sin(ga)
            gr = R*0.46
            big_gear(gx, gy, gr, (1 if gi % 2 == 0 else -1) * tt2 * mesh + gi * 0.31)
        # real clock hands: hour, minute, sweeping second
        m = now.tm_min + now.tm_sec/60.0
        hr = (now.tm_hour % 12) + m/60.0
        self._hand(cr, cx, cy, hr*6.2832/12 - 1.5708, R*0.46, R*0.10, 6.5, "#E8E2D4", ornate=True)
        self._hand(cr, cx, cy, m*6.2832/60 - 1.5708, R*0.68, R*0.12, 4.5, "#D9D2C0", ornate=True)
        seca = (time.time() % 60) * 6.2832/60 - 1.5708
        self._hand(cr, cx, cy, seca, R*0.78, R*0.18, 1.8, "#E8A33D")
        for i in range(8):
            a = i * 6.2832/8
            cr.arc(cx + 11*math.cos(a), cy + 11*math.sin(a), 2.1, 0, 6.2832)
            cr.set_source_rgba(*self._col("#A88452", .8)); cr.fill()
        cr.arc(cx, cy, 8, 0, 6.2832)
        cr.set_source_rgba(*self._col("#D4B27A")); cr.fill()
        cr.arc(cx, cy, 3.2, 0, 6.2832)
        cr.set_source_rgba(*self._col("#1A1409")); cr.fill()
        # phase complication (top aperture) — visible through the open lid
        if self._progress > 0:
            frac = 1.0 - self._progress
            cr.arc(cx, cy, R - 88, -1.5708 - 1.05, -1.5708 + 1.05)
            cr.set_source_rgba(*self._col(self._color_hex, .18)); cr.set_line_width(11); cr.stroke()
            cr.arc(cx, cy, R - 88, -1.5708 - 1.05, -1.5708 - 1.05 + frac*2.1)
            cr.set_source_rgba(*self._col(self._color_hex, .95)); cr.stroke()
            ga = -1.5708 - 1.05 + frac*2.1
            cr.arc(cx + (R - 88)*math.cos(ga), cy + (R - 88)*math.sin(ga), 5, 0, 6.2832)
            cr.set_source_rgba(*self._col("#F2E3C2", .98)); cr.fill()
        # TOP of the dial: the circadian hour — the headline
        phase_name = str(pal.get("phase", "")).upper().replace("-", " ")
        cr.select_font_face("DejaVu Sans", 0, 1)
        cr.set_font_size(13)
        ext = cr.text_extents(phase_name)
        cr.set_source_rgba(*self._col(face_fg))
        cr.move_to(cx - ext.width/2 - ext.x_bearing, cy - R*0.40)
        cr.show_text(phase_name)
        # CENTER: the countdown on its own register plaque — unmistakably THE
        # timer, separate from the clockwork around it (the digital/analog mix)
        pw, ph2 = 158, 60
        px, py = cx - pw/2, cy + 2
        cr.arc(px + 10, py + 10, 10, 3.1416, 4.7124)
        cr.arc(px + pw - 10, py + 10, 10, 4.7124, 0)
        cr.arc(px + pw - 10, py + ph2 - 10, 10, 0, 1.5708)
        cr.arc(px + 10, py + ph2 - 10, 10, 1.5708, 3.1416)
        cr.close_path()
        cr.set_source_rgba(*self._col("#10141A", .92)); cr.fill_preserve()
        cr.set_source_rgba(*self._col("#A88452", .95)); cr.set_line_width(2); cr.stroke()
        cr.select_font_face("DejaVu Sans Mono", 0, 1)
        cr.set_font_size(26)
        ext = cr.text_extents(self._time_text or "--:--")
        cr.set_source_rgba(*self._col(self._color_hex if self._progress > 0 else face_fg))
        cr.move_to(cx - ext.width/2 - ext.x_bearing, cy + 30)
        cr.show_text(self._time_text or "--:--")
        cr.select_font_face("DejaVu Sans", 0, 0)
        cr.set_font_size(8)
        ext = cr.text_extents("R E M A I N I N G")
        cr.set_source_rgba(*self._col(face_fg, .5))
        cr.move_to(cx - ext.width/2 - ext.x_bearing, cy + 48)
        cr.show_text("R E M A I N I N G")
        # the lid — a hinged cover at 6 o'clock; span shrinks as the face opens
        span = 5.58 - self._lid * 4.0
        a0 = 1.5708 - span/2
        cr.arc(cx, cy, R - 2, a0, a0 + span)
        cr.close_path()
        lidpat = cairo.LinearGradient(cx - R, cy, cx + R, cy + R)
        lidpat.add_color_stop_rgba(0, *self._col("#232A33", .97))
        lidpat.add_color_stop_rgba(1, *self._col("#12161C", .97))
        cr.set_source(lidpat); cr.fill_preserve()
        cr.set_source_rgba(*self._col("#A88452", .9)); cr.set_line_width(3); cr.stroke()
        # seat shadow under the lid's upper edge, so it reads as a raised cover
        cr.arc(cx, cy, R - 3, a0 - 0.16, a0 + 0.02)
        cr.set_source_rgba(0, 0, 0, .42); cr.set_line_width(5); cr.stroke()
        cr.arc(cx, cy, R - 3, a0 + span - 0.02, a0 + span + 0.16)
        cr.set_source_rgba(0, 0, 0, .28); cr.stroke()
        # the block, engraved on the case-back lid — bottom of the dial
        label = self._phase_text or ""
        if label:
            lx, ly = cx + (R*0.55)*math.cos(1.5708), cy + (R*0.55)*math.sin(1.5708)
            cr.select_font_face("DejaVu Sans", 0, 1)
            cr.set_font_size(11)
            ext = cr.text_extents(label)
            cr.set_source_rgba(0, 0, 0, .45)
            cr.move_to(lx - ext.width/2 - ext.x_bearing + 0.8, ly - ext.height/2 - ext.y_bearing + 1)
            cr.show_text(label)
            cr.set_source_rgba(*self._col("#D4B27A", .9))
            cr.move_to(lx - ext.width/2 - ext.x_bearing, ly - ext.height/2 - ext.y_bearing)
            cr.show_text(label)
        # lid crown nub
        na = a0 + 0.12  # hinge edge
        nx, ny = cx + (R-16)*math.cos(na), cy + (R-16)*math.sin(na)
        cr.arc(nx, ny, 7, 0, 6.2832)
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

    def _taskbar_pixbuf(self, progress, color, size):
        """Miniature of the watch for the panel: bronze ring, the block's arc,
        a phase hub. Present, not loud."""
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        cr = cairo.Context(surf)
        s = size; c = s / 2.0
        R = s / 2.0 - 1
        def col(hexs, a=1.0):
            v = hexs.lstrip('#')
            return (int(v[0:2],16)/255, int(v[2:4],16)/255, int(v[4:6],16)/255, a)
        # outer ring
        cr.arc(c, c, R, 0, 6.2832)
        cr.set_source_rgba(*col("#A88452")); cr.set_line_width(max(1.6, s*0.06)); cr.stroke()
        # dim full track
        cr.arc(c, c, R - s*0.09, 0, 6.2832)
        cr.set_source_rgba(*col("#5A5648", .55)); cr.set_line_width(max(1.2, s*0.075)); cr.stroke()
        if progress > 0:
            frac = 1.0 - progress
            cr.arc(c, c, R - s*0.09, -1.5708, -1.5708 + frac*6.2832)
            cr.set_source_rgba(*col(color)); cr.set_line_width(max(1.2, s*0.075)); cr.stroke()
        else:
            # stopped: a quiet breathing dot so it's never fully invisible
            cr.arc(c, c, s*0.16, 0, 6.2832)
            cr.set_source_rgba(*col("#8E8468", .8)); cr.fill()
        # phase hub
        cr.arc(c, c, s*0.10, 0, 6.2832)
        cr.set_source_rgba(*col(color if progress > 0 else "#6E6858"))
        cr.fill()
        return Gdk.pixbuf_get_from_surface(surf, 0, 0, s, s)

    def _set_taskbar_icon(self, progress, color):
        if self.window is None:
            return
        key = (self.phase, round(progress, 3), color, bool(self.paused_left))
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
        edge = self._rgba(TEXT, .2)
        sheen = self._rgba("#ffffff", .16)
        self.css.load_from_data(f"""
          window.vagabond {{ background-color: transparent; color: {TEXT}; }}
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
        self.window.set_app_paintable(True)
        self.window.set_default_size(380, 360)
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
        self.window.get_style_context().add_class("vagabond")
        self.window.connect("delete-event", self._close_window)
        self.dial = DialArea()
        self.dial.set_tooltip_text(
            "Vagabond · left-click start/pause · right-click settings · Alt+drag moves the watch · the face opens when a block begins")
        self.dial.connect("button-press-event", self._face_click)
        accessible = self.dial.get_accessible()
        accessible.set_name("Vagabond mechanical timer")
        accessible.set_description(
            "A round mechanical clock with hour, minute and second hands. "
            "Left click starts or pauses the focus and rest timer. Right click opens settings. "
            "When a block begins, the face opens to reveal the phase and remaining time.")
        self.window.add(self.dial)
        self.face_image = None
        self.window.show_all()
        self.window.present()
        GLib.idle_add(self._apply_round_shape)

    def _apply_round_shape(self):
        w = self.window.get_allocated_width() or 380
        h = self.window.get_allocated_height() or 360
        r = min(w, h) / 2.0 + 14
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surf)
        cr.arc(w / 2.0, h / 2.0, r, 0, 6.2832)
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
            self._open_settings()
        return True

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
            if self.phase == "stopped":
                self.window.set_title(APP_NAME)
            else:
                self.window.set_title(f"Vagabond · {phase_text.title()} · {time_text}")
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
