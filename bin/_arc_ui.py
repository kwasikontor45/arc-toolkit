"""
_arc_ui — shared design system for the arc-* Tkinter apps (khaos-lab,
arc-pine, arc-break, arc-pine-bubbles).

Built 2026-09-11, circadian engine added same day. Before this, every one
of those apps carried its own copy-pasted Rose Pine Moon palette, its own
font setup, and its own flat tk.Button/tk.Frame styling -- three
slightly-drifted copies of the same look. This module is the single
source of truth for the palette, and provides:

  - rounded_frame(): a Canvas-drawn surface for grouped content.
  - button(): a compact, restrained control with hover feedback and
    keyboard activation.
  - circadian(): a real time-of-day color engine, modeled directly on
    Kataleya's own circadian phase system (choice/still-pine/desire/nyx)
    -- the user's own words, "my signature-design or style." Four dark
    mineral anchor palettes, continuously interpolated against
    the real clock rather than hard-cut at phase boundaries -- matching
    Kataleya's own most recent design direction (its GAMEPLAN explicitly
    moved away from the four phases as discrete buckets toward continuous
    drift). Not a pixel-exact port of Kataleya's real palette values (that
    repo isn't available on this machine) -- the user explicitly said
    exact values don't matter here, gave four palette-family anchors, and
    said "feel free, do you."

Not a framework -- just consistent building blocks. Each app still owns
its own layout/logic; this owns *what it looks like*.
"""

import tkinter as tk
from datetime import datetime
from tkinter import font as tkfont

# ── Palette -- Phosphor Noir. Mineral graphite and verdigris, with warm
# circadian accents; Rose Pine remains a color influence, not the whole UI. ──
BG       = "#0c1211"
SURFACE  = "#121d1a"
OVERLAY  = "#192723"
FG       = "#e5eee8"
FG_MUTED = "#9caaa2"
GOLD     = "#dbb77d"
ROSE     = "#d9877f"
PINE     = "#8fc4aa"
TEAL     = "#88bfb2"
IRIS     = "#ada2c9"

# Semantic aliases -- read at the call site instead of the palette. Same
# colors, names that describe *why*, not just which Rose Pine Moon hue.
# Deliberately NOT phase-interpolated even where circadian() is in use --
# an error should read as an error at 3am or 3pm alike, same reasoning
# Kataleya's own design brief uses for "useful" over "pretty."
COLOR_WORK  = GOLD
COLOR_BREAK = ROSE
COLOR_OK    = TEAL
COLOR_WARN  = GOLD
COLOR_ERROR = ROSE

# ── Circadian engine ──────────────────────────────────────────────────────
# Four anchor phases, named after Kataleya's own vocabulary, each anchored
# to a real hour of day. Only the five "ambient" roles drift (bg/surface/
# overlay/fg/fg_muted) -- functional colors above stay fixed for legibility.
PHASES = {
    "choice":     {"hour": 6,  "bg": "#111918", "surface": "#192321", "overlay": "#24322e", "fg": "#e3eee8", "fg_muted": "#9aada4"},  # cool green dawn
    "desire":     {"hour": 13, "bg": "#0c1717", "surface": "#142322", "overlay": "#1d302e", "fg": "#dcece8", "fg_muted": "#93aaa5"},  # deep mineral day
    "still-pine": {"hour": 18, "bg": "#191712", "surface": "#242018", "overlay": "#342d20", "fg": "#f0e8d9", "fg_muted": "#b6a487"},  # low amber dusk
    "nyx":        {"hour": 24, "bg": BG,        "surface": SURFACE,  "overlay": OVERLAY,   "fg": FG,        "fg_muted": FG_MUTED},   # night, deepest mineral palette
}
_PHASE_ORDER = ["choice", "desire", "still-pine", "nyx"]

# Canonical Kataleya phase table (fixed 2026-07-06 across every reimplementation;
# hours are phase START times): choice 6-11 . desire 11-17 . still-pine 17-21 .
# nyx 21-6. Until 2026-09-19 this engine had the desire/still-pine NAMES swapped
# relative to it (colors/timing were fine, only the labels were wrong). The
# anchors above stay where they are (palette drifts on its own schedule); the
# `phase` label and PHASE_ACCENT below always follow the canonical table.
PHASE_START = {"choice": 6, "desire": 11, "still-pine": 17, "nyx": 21}
PHASE_ACCENT = {  # muted toolkit accents keyed to Kataleya's canonical phases
    "choice":     "#80b9c9",
    "desire":     "#d8b375",
    "still-pine": "#a2c6a5",
    "nyx":        "#b391a0",
}


def phase_name(hour=None):
    """Canonical Kataleya phase name for an hour (float) or right now."""
    if hour is None:
        now = datetime.now()
        hour = now.hour + now.minute / 60
    if hour >= PHASE_START["nyx"] or hour < PHASE_START["choice"]:
        return "nyx"
    if hour < PHASE_START["desire"]:
        return "choice"
    if hour < PHASE_START["still-pine"]:
        return "desire"
    return "still-pine"


def phase_info(hour=None):
    """(name, accent_hex) for the canonical phase at `hour` / now."""
    name = phase_name(hour)
    return name, PHASE_ACCENT[name]


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in rgb))


def _lerp_hex(c1, c2, t):
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex((r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t))


ANIM_STEPS = 6
ANIM_DELAY_MS = 14  # ~84ms total -- felt as smooth motion, not a visible slideshow


def _animate(widget, anim_state, bg_from, bg_to, fg_from, fg_to):
    """Steps a widget's bg+fg together from one pair of hex colors to
    another over ANIM_STEPS*ANIM_DELAY_MS ms, instead of snapping
    instantly -- the single biggest reason hover/selection felt "dead"
    despite already having the right colors. `anim_state` is a shared
    dict the caller owns (holds the in-flight `after` job id and the
    color actually on screen right now) so a second call -- e.g. the
    mouse re-entering before a leave-animation finishes -- can cancel
    the old job and start smoothly from the *real current* color instead
    of jumping back to whatever the old target was."""
    old_job = anim_state.get("job")
    if old_job is not None:
        try:
            widget.after_cancel(old_job)
        except Exception:
            pass

    def step(i=0):
        t = i / ANIM_STEPS
        bg = _lerp_hex(bg_from, bg_to, t)
        fg = _lerp_hex(fg_from, fg_to, t)
        try:
            widget.configure(bg=bg, fg=fg)
        except tk.TclError:
            return  # widget destroyed mid-animation
        anim_state["bg"] = bg
        anim_state["fg"] = fg
        if i < ANIM_STEPS:
            anim_state["job"] = widget.after(ANIM_DELAY_MS, lambda: step(i + 1))
        else:
            anim_state["job"] = None

    step()


def _surrounding_phases(hour):
    """Returns (name1, name2, t) -- the two anchor phases the given hour
    falls between, and how far through that window it is (0.0-1.0).
    Circular: handles the wrap from nyx (anchored at 24) back to choice
    (anchored at 6) through real midnight correctly."""
    for i, name1 in enumerate(_PHASE_ORDER):
        name2 = _PHASE_ORDER[(i + 1) % len(_PHASE_ORDER)]
        h1 = PHASES[name1]["hour"]
        h2 = PHASES[name2]["hour"]
        h2_eff = h2 if h2 > h1 else h2 + 24
        hour_eff = hour if hour >= h1 else hour + 24
        if h1 <= hour_eff < h2_eff:
            return name1, name2, (hour_eff - h1) / (h2_eff - h1)
    return "nyx", "choice", 0.0  # unreachable given the anchors above; safe fallback


def circadian(hour=None):
    """Returns a dict of {bg, surface, overlay, fg, fg_muted, phase} for
    the given hour (float, e.g. 14.5 for 2:30pm) or right now if omitted.
    Colors are continuously interpolated between the two nearest anchor
    phases -- no hard cut at a phase boundary, by design (matches
    Kataleya's own current direction, not the earlier discrete-bucket
    version). `phase` is the canonical Kataleya phase name (phase_name()),
    for display only -- don't branch UI logic on it, use the interpolated colors."""
    if hour is None:
        now = datetime.now()
        hour = now.hour + now.minute / 60
    n1, n2, t = _surrounding_phases(hour)
    p1, p2 = PHASES[n1], PHASES[n2]
    return {
        "bg":       _lerp_hex(p1["bg"], p2["bg"], t),
        "surface":  _lerp_hex(p1["surface"], p2["surface"], t),
        "overlay":  _lerp_hex(p1["overlay"], p2["overlay"], t),
        "fg":       _lerp_hex(p1["fg"], p2["fg"], t),
        "fg_muted": _lerp_hex(p1["fg_muted"], p2["fg_muted"], t),
        "phase":    phase_name(hour),
    }

# ── Spacing scale -- a real 4px-based rhythm instead of ad hoc padx/pady
# picked per call site. Use these, not raw numbers, in new code. ────────
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 20
SPACE_XL = 32

FONT_FAMILY = "DejaVu Sans"


def fonts():
    """Font objects need a Tk root to already exist, so this is a function,
    not module-level constants -- call it after your root window is up.
    Uses a common sans family for everyday controls; reserve monospace for
    live command output and technical values."""
    try:
        return {
            "title": tkfont.Font(family=FONT_FAMILY, size=14, weight="bold"),
            "big":   tkfont.Font(family=FONT_FAMILY, size=22, weight="bold"),
            "body":  tkfont.Font(family=FONT_FAMILY, size=10),
            "small": tkfont.Font(family=FONT_FAMILY, size=9),
            "label": tkfont.Font(family=FONT_FAMILY, size=9, weight="bold"),
        }
    except Exception:
        return {
            "title": tkfont.Font(size=14, weight="bold"),
            "big":   tkfont.Font(size=22, weight="bold"),
            "body":  tkfont.Font(size=10),
            "small": tkfont.Font(size=9),
            "label": tkfont.Font(size=9, weight="bold"),
        }


def _rounded_points(x1, y1, x2, y2, r):
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    if r < 0:
        r = 0
    return [
        x1 + r, y1,       x2 - r, y1,
        x2, y1,           x2, y1 + r,
        x2, y2 - r,       x2, y2,
        x2 - r, y2,       x1 + r, y2,
        x1, y2,           x1, y2 - r,
        x1, y1 + r,       x1, y1,
        x1 + r, y1,
    ]


def rounded_frame(parent, parent_bg, bg=SURFACE, radius=8, border=None, border_width=1):
    """A restrained grouped surface. Returns (outer, inner):
    pack/grid `outer` into your real layout, then pack/grid your content
    into `inner`. `parent_bg` must match whatever's actually behind this
    card (the canvas's own corners are still square -- they show
    `parent_bg` so the rounding reads correctly against it).

    Redraws on every size change via <Configure> on the inner frame, so
    it works for dynamically-sized content (a settings row growing, a
    history card wrapping text) without needing a fixed size up front."""
    state = {"bg": bg, "parent_bg": parent_bg}
    outer = tk.Canvas(parent, bg=parent_bg, highlightthickness=0, bd=0)
    inner = tk.Frame(outer, bg=bg)
    # Real bug, found live 2026-09-11: binding <Configure> on `inner` to
    # do the *first* create_window() is circular -- a widget never mapped
    # onto anything doesn't get a <Configure> event, so the callback that
    # was supposed to map it never fires, so nothing ever appears. Map it
    # once immediately (even at its pre-content size), THEN <Configure>
    # correctly fires on every real resize from here on -- same fix shape
    # as arc-pine-bubbles' bubble-placement bug earlier this project.
    inset = 8
    outer.create_window(inset, inset, window=inner, anchor="nw", tags="win")
    # Reuse the same canvas shapes while a card is resized. Deleting and
    # recreating a polygon for every Configure used to cause visible redraw
    # shimmer on Xfce's compositor. The surface uses a quiet outline without
    # a drop shadow or faux glass highlight.
    face = outer.create_polygon(0, 0, 0, 0, smooth=True, fill=bg,
                                outline=border or _lerp_hex(bg, "#ffffff", 0.09),
                                width=max(1, border_width))

    def redraw(event=None):
        w = max(outer.winfo_width(), inner.winfo_reqwidth() + inset * 2, 1)
        h = max(inner.winfo_reqheight() + inset * 2, 1)
        wanted = (inner.winfo_reqwidth() + inset * 2, h)
        if (outer.cget("width"), outer.cget("height")) != tuple(map(str, wanted)):
            outer.config(width=wanted[0], height=wanted[1])
        pts = _rounded_points(1, 1, w - 2, h - 2, min(radius, 8))
        outer.coords(face, *pts)
        outer.itemconfigure(face, fill=state["bg"],
                            outline=border or _lerp_hex(state["bg"], "#ffffff", 0.09))
        outer.tag_lower(face, "win")

    def retheme(new_bg=None, new_parent_bg=None):
        """Live re-color for the circadian engine -- changes the card's
        surface color and/or whatever's behind it, without recreating the
        widget. Callers still need to retheme their own children's bg
        separately (this only owns the card shell itself)."""
        if new_bg is not None:
            state["bg"] = new_bg
            inner.configure(bg=new_bg)
        if new_parent_bg is not None:
            state["parent_bg"] = new_parent_bg
            outer.configure(bg=new_parent_bg)
        redraw()

    inner.bind("<Configure>", redraw)
    def resize(event):
        outer.itemconfigure('win', width=max(1, event.width - inset * 2))
        redraw()
    outer.bind('<Configure>', resize)
    redraw()
    outer.retheme = retheme
    return outer, inner


def rounded_pane(parent, parent_bg, bg=SURFACE, radius=8):
    """Resizable pane shell; its content stays inset from rounded corners."""
    outer = tk.Canvas(parent, bg=parent_bg, bd=0, highlightthickness=0)
    inner = tk.Frame(outer, bg=bg)
    window = outer.create_window(8, 8, window=inner, anchor='nw')
    face = outer.create_polygon(0, 0, 0, 0, smooth=True, fill=bg,
                                outline=_lerp_hex(bg, "#ffffff", 0.09), width=1)
    last_size = [0, 0]
    last_bg = [bg]
    def resize(event):
        width, height = max(17, outer.winfo_width()), max(17, outer.winfo_height())
        face_bg = inner.cget('bg')
        if last_size == [width, height] and last_bg[0] == face_bg:
            return
        last_size[:] = [width, height]
        last_bg[0] = face_bg
        outer.itemconfigure(window, width=width - 16, height=height - 16)
        pts = _rounded_points(1, 1, width - 2, height - 2, min(radius, 8))
        outer.coords(face, *pts)
        outer.itemconfigure(face, fill=face_bg,
                            outline=_lerp_hex(face_bg, "#ffffff", 0.09))
        outer.tag_lower(face, window)
    outer.bind('<Configure>', resize)
    outer.bind('<Expose>', resize)
    return outer, inner


class PillScrollbar(tk.Canvas):
    """Rounded thumb, drag/page/wheel/keyboard controls; Scrollbar-compatible."""
    def __init__(self, parent, orient='vertical', command=None, **options):
        self.command = command
        self.orient = orient
        self.first, self.last = 0.0, 1.0
        self.thumb = options.pop('bg', OVERLAY)
        self.track = options.pop('troughcolor', parent.cget('bg'))
        self.hover = options.pop('activebackground', TEAL)
        width = max(12, options.pop('width', 14))
        for key in ('bd', 'borderwidth', 'highlightthickness', 'relief'):
            options.pop(key, None)
        super().__init__(parent, bg=self.track, width=width, height=width,
                         bd=0, highlightthickness=0, takefocus=1, **options)
        self.active = False
        self.drag_offset = None
        self.bind('<Configure>', lambda _event: self.redraw())
        self.bind('<Enter>', lambda _event: self.set_active(True))
        self.bind('<Leave>', lambda _event: self.set_active(False))
        self.bind('<Button-1>', self.press)
        self.bind('<B1-Motion>', self.drag)
        self.bind('<ButtonRelease-1>', lambda _event: setattr(self, 'drag_offset', None))
        self.bind('<Button-4>', lambda _event: self.scroll(-1))
        self.bind('<Button-5>', lambda _event: self.scroll(1))
        self.bind('<MouseWheel>', lambda event: self.scroll(-1 if event.delta > 0 else 1))
        self.bind('<Up>', lambda _event: self.scroll(-1))
        self.bind('<Down>', lambda _event: self.scroll(1))
        self.bind('<Prior>', lambda _event: self.scroll(-1, 'pages'))
        self.bind('<Next>', lambda _event: self.scroll(1, 'pages'))
        self.bind('<Home>', lambda _event: self.command and self.command('moveto', 0))
        self.bind('<End>', lambda _event: self.command and self.command('moveto', 1))

    def configure(self, cnf=None, **kwargs):
        values = dict(cnf or {}, **kwargs)
        if 'command' in values:
            self.command = values.pop('command')
        if 'activebackground' in values:
            self.hover = values.pop('activebackground')
        if 'troughcolor' in values:
            self.track = values.pop('troughcolor')
            values['bg'] = self.track
        elif 'bg' in values:
            self.thumb = values.pop('bg')
        result = super().configure(**values)
        if hasattr(self, 'first'):
            self.redraw()
        return result
    config = configure

    def set(self, first, last):
        self.first = max(0, min(1, float(first)))
        self.last = max(self.first, min(1, float(last)))
        self.redraw()

    def geometry_values(self):
        length = self.winfo_height() if self.orient == 'vertical' else self.winfo_width()
        span = max(1, length - 6)
        size = min(span, max(28, (self.last - self.first) * span))
        travel = max(0, span - size)
        position = 3 + travel * self.first / max(0.0001, 1 - (self.last - self.first))
        return position, size, travel

    def redraw(self):
        self.delete('thumb')
        pos, size, _travel = self.geometry_values()
        color = self.hover if self.active else self.thumb
        if self.orient == 'vertical':
            bounds = (3, pos, max(4, self.winfo_width() - 3), pos + size)
        else:
            bounds = (pos, 3, pos + size, max(4, self.winfo_height() - 3))
        radius = min(6, (bounds[2] - bounds[0]) / 2, (bounds[3] - bounds[1]) / 2)
        self.create_polygon(_rounded_points(*bounds, radius), smooth=True, fill=color, outline='', tags='thumb')

    def set_active(self, active):
        self.active = active
        self.redraw()

    def scroll(self, count, units='units'):
        if self.command:
            self.command('scroll', count, units)
        return 'break'

    def press(self, event):
        self.focus_set()
        axis = event.y if self.orient == 'vertical' else event.x
        pos, size, _travel = self.geometry_values()
        if pos <= axis <= pos + size:
            self.drag_offset = axis - pos
        else:
            self.scroll(-1 if axis < pos else 1, 'pages')

    def drag(self, event):
        if self.drag_offset is None or not self.command:
            return
        axis = event.y if self.orient == 'vertical' else event.x
        _pos, _size, travel = self.geometry_values()
        fraction = max(0, min(1, (axis - self.drag_offset - 3) / max(1, travel)))
        self.command('moveto', fraction * (1 - (self.last - self.first)))


class RoundedLabel(tk.Canvas):
    """A compact, keyboard-focusable control with a quiet beveled edge."""
    def __init__(self, parent, text='', font=None, bg=SURFACE, fg=FG, padx=10, pady=6,
                 takefocus=1, **options):
        self.look = dict(text=text, font=font, bg=bg, fg=fg, padx=padx, pady=pady, anchor='center')
        super().__init__(parent, bg=parent.cget('bg'), bd=0, highlightthickness=0,
                         takefocus=takefocus, **options)
        self._shadow = self.create_polygon(0, 0, 0, 0, smooth=True, outline='', tags='shadow')
        self._face = self.create_polygon(0, 0, 0, 0, smooth=True, width=1, tags='face')
        self._sheen = self.create_line(0, 0, 0, 0, width=1, capstyle='round', tags='sheen')
        self._label_shadow = self.create_text(0, 0, tags='label-shadow')
        self._label = self.create_text(0, 0, tags='label')
        self.resize_to_text()
        self.bind('<Configure>', lambda _event: self.redraw())

    def resize_to_text(self):
        font = tkfont.Font(font=self.look['font'])
        lines = self.look['text'].split('\n')
        super().configure(width=max(font.measure(line) for line in lines) + self.look['padx'] * 2,
                          height=font.metrics('linespace') * len(lines) + self.look['pady'] * 2)

    def configure(self, cnf=None, **kwargs):
        values = dict(cnf or {}, **kwargs)
        resized = any(key in values for key in ('text', 'font', 'padx', 'pady'))
        for key in tuple(values):
            if key in self.look:
                self.look[key] = values.pop(key)
        result = super().configure(**values)
        if resized:
            self.resize_to_text()
        self.redraw()
        return result
    config = configure

    def cget(self, key):
        return self.look[key] if key in self.look else super().cget(key)

    def redraw(self):
        width, height = self.winfo_width(), self.winfo_height()
        if width < 2 or height < 2:
            return
        super().configure(bg=self.master.cget('bg'))
        radius = min(7, height / 3, width / 3)
        points = _rounded_points(1, 1, width - 2, height - 2, radius)
        bg = self.look['bg']
        edge = _lerp_hex(bg, '#ffffff', .12)
        low_edge = self.look['fg']
        self.itemconfigure(self._shadow, state='hidden')
        self.coords(self._face, *points)
        self.itemconfigure(self._face, fill=bg, outline=edge)
        self.itemconfigure(self._sheen, state='hidden')
        left = self.look['anchor'] in ('w', 'nw', 'sw')
        x = self.look['padx'] if left else width / 2
        anchor = 'w' if left else 'center'
        self.itemconfigure(self._label_shadow, state='hidden')
        self.coords(self._label, x, height / 2)
        self.itemconfigure(self._label, text=self.look['text'], font=self.look['font'],
                           fill=self.look['fg'], anchor=anchor)
        self.tag_lower(self._shadow)
        self.tag_raise(self._face)
        self.tag_raise(self._label)


def button(parent, text, command=None, font=None, bg=SURFACE, fg=TEAL,
           hover_bg=OVERLAY, hover_fg=None, disabled_fg=FG_MUTED,
           padx=10, pady=6):
    """Compact Canvas button with keyboard activation and hover feedback, replacing
    the flat tk.Button pattern every app previously copy-pasted (static
    bg, no feedback until an actual click). Returns the Label with one
    extra method, .set_enabled(bool) -- plain tk.Label has no built-in
    disabled state the way tk.Button does, and several callers (arc-break
    especially) depend on real enable/disable, not just a re-color, so
    this gates the click handler itself, not only the look."""
    hover_fg = hover_fg or fg
    state = {"enabled": True, "fg": fg, "bg": bg, "hover_bg": hover_bg, "hover_fg": hover_fg}
    anim = {"job": None, "bg": bg, "fg": fg}
    lbl = RoundedLabel(parent, text=text, font=font, bg=bg, fg=fg,
                    padx=padx, pady=pady, cursor="hand2")

    def on_enter(_e):
        if state["enabled"]:
            _animate(lbl, anim, anim["bg"], state["hover_bg"], anim["fg"], state["hover_fg"])

    def on_leave(_e):
        if state["enabled"]:
            _animate(lbl, anim, anim["bg"], state["bg"], anim["fg"], state["fg"])

    def on_click(_e):
        if state["enabled"] and command:
            command()

    def _snap(bg, fg):
        """Cancel any in-flight hover animation and set the look
        immediately -- used by the three deliberate-state-change methods
        below, none of which should race or blend with a hover fade."""
        job = anim.get("job")
        if job is not None:
            try:
                lbl.after_cancel(job)
            except Exception:
                pass
            anim["job"] = None
        anim["bg"], anim["fg"] = bg, fg
        lbl.configure(bg=bg, fg=fg)

    def set_enabled(enabled):
        state["enabled"] = enabled
        _snap(state["bg"], state["fg"] if enabled else disabled_fg)
        lbl.configure(cursor="hand2" if enabled else "arrow")

    def set_look(bg=None, fg=None):
        """Persistent look override, distinct from hover -- e.g. a
        sidebar nav button's 'currently selected' state. Changes what
        *resting* (non-hover) looks like; hover still layers hover_bg/
        hover_fg on top of whatever this sets, same as normal."""
        if bg is not None:
            state["bg"] = bg
        if fg is not None:
            state["fg"] = fg
        if state["enabled"]:
            _snap(state["bg"], state["fg"])

    def retheme(bg=None, hover_bg=None):
        """Live re-color for the circadian engine -- only the ambient
        bg/hover_bg drift with time, not the button's own semantic fg
        (start stays teal, stop stays rose, etc, regardless of hour)."""
        if bg is not None:
            state["bg"] = bg
        if hover_bg is not None:
            state["hover_bg"] = hover_bg
        _snap(state["bg"], state["fg"] if state["enabled"] else disabled_fg)

    lbl.bind("<Enter>", on_enter)
    lbl.bind("<Leave>", on_leave)
    lbl.bind("<Button-1>", on_click)
    lbl.bind('<Return>', on_click)
    lbl.bind('<space>', on_click)
    lbl.bind('<FocusIn>', on_enter)
    lbl.bind('<FocusOut>', on_leave)
    lbl.set_enabled = set_enabled
    lbl.set_look = set_look
    lbl.retheme = retheme
    return lbl


def divider(parent, bg_line=OVERLAY, **pack_kwargs):
    """A thin horizontal rule -- the one flat-rectangle pattern every app
    already used consistently, kept as-is rather than reinvented."""
    f = tk.Frame(parent, bg=bg_line, height=1)
    f.pack(fill="x", **pack_kwargs)
    return f
