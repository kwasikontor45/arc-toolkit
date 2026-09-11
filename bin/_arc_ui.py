"""
_arc_ui — shared design system for the arc-* Tkinter apps (khaos-lab,
arc-pine, arc-break, arc-pine-bubbles).

Built 2026-09-11, circadian engine added same day. Before this, every one
of those apps carried its own copy-pasted Rose Pine Moon palette, its own
font setup, and its own flat tk.Button/tk.Frame styling -- three
slightly-drifted copies of the same look. This module is the single
source of truth for the palette, and provides:

  - rounded_frame(): a genuinely rounded-corner card (Canvas-drawn, not a
    padding illusion), for anything that should read as a "card" rather
    than a flat rectangle.
  - button(): a label-based button with a real hover-state color
    transition (Tkinter has no CSS :hover, but <Enter>/<Leave> binding
    gets you the same felt effect) instead of a static flat rectangle.
  - circadian(): a real time-of-day color engine, modeled directly on
    Kataleya's own circadian phase system (choice/still-pine/desire/nyx)
    -- the user's own words, "my signature-design or style." Four anchor
    palettes (dawn-iris, midnight-ocean day, golden-hour gold, and the
    existing Rose Pine Moon for night), continuously interpolated against
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

# ── Palette -- Rose Pine Moon, canonical fallback/default -- every app
# should import these, not redefine them. Equivalent to circadian()'s
# "nyx" (night) anchor -- kept as plain constants too since not every call
# site needs live time-of-day drift (a one-shot popup, a status icon). ──
BG       = "#232136"
SURFACE  = "#2a273f"
OVERLAY  = "#393552"
FG       = "#e0def4"
FG_MUTED = "#6e6a86"
GOLD     = "#f6c177"
ROSE     = "#eb6f92"
PINE     = "#3e8fb0"
TEAL     = "#9ccfd8"
IRIS     = "#c4a7e7"

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
    "choice":     {"hour": 6,  "bg": "#201f30", "surface": "#26243c", "overlay": "#352f4d", "fg": "#e3e0f2", "fg_muted": "#726d8f"},  # dawn, iris-leaning
    "still-pine": {"hour": 13, "bg": "#0f1c24", "surface": "#15252f", "overlay": "#1e3542", "fg": "#dbe8ec", "fg_muted": "#5c7681"},  # day, midnight ocean
    "desire":     {"hour": 18, "bg": "#2b2035", "surface": "#342942", "overlay": "#493655", "fg": "#f1e7da", "fg_muted": "#8d7968"},  # golden hour, gold-leaning
    "nyx":        {"hour": 24, "bg": BG,        "surface": SURFACE,  "overlay": OVERLAY,   "fg": FG,        "fg_muted": FG_MUTED},   # night, Rose Pine Moon as-is
}
_PHASE_ORDER = ["choice", "still-pine", "desire", "nyx"]


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in rgb))


def _lerp_hex(c1, c2, t):
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex((r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t))


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
    version). `phase` is the nearer anchor's name, for display/debugging
    only -- don't branch UI logic on it, use the interpolated colors."""
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
        "phase":    n1 if t < 0.5 else n2,
    }

# ── Spacing scale -- a real 4px-based rhythm instead of ad hoc padx/pady
# picked per call site. Use these, not raw numbers, in new code. ────────
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 20
SPACE_XL = 32

FONT_FAMILY = "JetBrains Mono"


def fonts():
    """Font objects need a Tk root to already exist, so this is a function,
    not module-level constants -- call it after your root window is up.
    Falls back to the platform default family if JetBrains Mono isn't
    installed, same defensive pattern arc-break already used."""
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


def rounded_frame(parent, parent_bg, bg=SURFACE, radius=10, border=None, border_width=1):
    """A real rounded-corner card, Canvas-drawn. Returns (outer, inner):
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
    outer.create_window(0, 0, window=inner, anchor="nw", tags="win")

    def redraw(event=None):
        outer.delete("shape")
        w = max(inner.winfo_reqwidth(), 1)
        h = max(inner.winfo_reqheight(), 1)
        outer.config(width=w, height=h)
        pts = _rounded_points(1, 1, w - 1, h - 1, radius)
        if border:
            outer.create_polygon(pts, smooth=True, fill=state["bg"], outline=border,
                                  width=border_width, tags="shape")
        else:
            outer.create_polygon(pts, smooth=True, fill=state["bg"], outline=state["bg"], tags="shape")
        outer.tag_lower("shape")

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
    redraw()
    outer.retheme = retheme
    return outer, inner


def button(parent, text, command=None, font=None, bg=SURFACE, fg=TEAL,
           hover_bg=OVERLAY, hover_fg=None, disabled_fg=FG_MUTED,
           padx=10, pady=6):
    """Label-based button with a real hover-state transition, replacing
    the flat tk.Button pattern every app previously copy-pasted (static
    bg, no feedback until an actual click). Returns the Label with one
    extra method, .set_enabled(bool) -- plain tk.Label has no built-in
    disabled state the way tk.Button does, and several callers (arc-break
    especially) depend on real enable/disable, not just a re-color, so
    this gates the click handler itself, not only the look."""
    hover_fg = hover_fg or fg
    state = {"enabled": True, "fg": fg, "bg": bg, "hover_bg": hover_bg, "hover_fg": hover_fg}
    lbl = tk.Label(parent, text=text, font=font, bg=bg, fg=fg,
                    padx=padx, pady=pady, cursor="hand2")

    def on_enter(_e):
        if state["enabled"]:
            lbl.configure(bg=state["hover_bg"], fg=state["hover_fg"])

    def on_leave(_e):
        if state["enabled"]:
            lbl.configure(bg=state["bg"], fg=state["fg"])

    def on_click(_e):
        if state["enabled"] and command:
            command()

    def set_enabled(enabled):
        state["enabled"] = enabled
        lbl.configure(
            cursor="hand2" if enabled else "arrow",
            fg=state["fg"] if enabled else disabled_fg,
            bg=state["bg"],
        )

    def retheme(bg=None, hover_bg=None):
        """Live re-color for the circadian engine -- only the ambient
        bg/hover_bg drift with time, not the button's own semantic fg
        (start stays teal, stop stays rose, etc, regardless of hour)."""
        if bg is not None:
            state["bg"] = bg
        if hover_bg is not None:
            state["hover_bg"] = hover_bg
        lbl.configure(bg=state["bg"], fg=state["fg"] if state["enabled"] else disabled_fg)

    lbl.bind("<Enter>", on_enter)
    lbl.bind("<Leave>", on_leave)
    lbl.bind("<Button-1>", on_click)
    lbl.set_enabled = set_enabled
    lbl.retheme = retheme
    return lbl


def divider(parent, bg_line=OVERLAY, **pack_kwargs):
    """A thin horizontal rule -- the one flat-rectangle pattern every app
    already used consistently, kept as-is rather than reinvented."""
    f = tk.Frame(parent, bg=bg_line, height=1)
    f.pack(fill="x", **pack_kwargs)
    return f
