"""
_arc_ui — shared design system for the arc-* Tkinter apps (khaos-lab,
arc-pine, arc-break, arc-pine-bubbles).

Built 2026-09-11. Before this, every one of those apps carried its own
copy-pasted Rose Pine Moon palette, its own font setup, and its own flat
tk.Button/tk.Frame styling -- three slightly-drifted copies of the same
look, which is a real part of why the whole toolkit reads as "rigid" /
"prototype" despite each app individually working fine. This module is
the single source of truth for the palette, and provides two real visual
upgrades plain Tkinter doesn't give you for free:

  - rounded_frame(): a genuinely rounded-corner card (Canvas-drawn, not a
    padding illusion), for anything that should read as a "card" rather
    than a flat rectangle.
  - button(): a label-based button with a real hover-state color
    transition (Tkinter has no CSS :hover, but <Enter>/<Leave> binding
    gets you the same felt effect) instead of a static flat rectangle.

Not a framework -- just consistent building blocks. Each app still owns
its own layout/logic; this owns *what it looks like*.
"""

import tkinter as tk
from tkinter import font as tkfont

# ── Palette -- Rose Pine Moon, canonical -- every app should import these,
# not redefine them. ─────────────────────────────────────────────────────
BG       = "#232136"
SURFACE  = "#2a273f"
OVERLAY  = "#393552"
FG       = "#e0def4"
FG_MUTED = "#6e6a86"
GOLD     = "#f6c177"
ROSE     = "#eb6f92"
PINE     = "#3e8fb0"
TEAL     = "#9ccfd8"

# Semantic aliases -- read at the call site instead of the palette. Same
# colors, names that describe *why*, not just which Rose Pine Moon hue.
COLOR_WORK  = GOLD
COLOR_BREAK = ROSE
COLOR_OK    = TEAL
COLOR_WARN  = GOLD
COLOR_ERROR = ROSE

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
            outer.create_polygon(pts, smooth=True, fill=bg, outline=border,
                                  width=border_width, tags="shape")
        else:
            outer.create_polygon(pts, smooth=True, fill=bg, outline=bg, tags="shape")
        outer.tag_lower("shape")

    inner.bind("<Configure>", redraw)
    redraw()
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
    state = {"enabled": True, "fg": fg}
    lbl = tk.Label(parent, text=text, font=font, bg=bg, fg=fg,
                    padx=padx, pady=pady, cursor="hand2")

    def on_enter(_e):
        if state["enabled"]:
            lbl.configure(bg=hover_bg, fg=hover_fg)

    def on_leave(_e):
        if state["enabled"]:
            lbl.configure(bg=bg, fg=state["fg"])

    def on_click(_e):
        if state["enabled"] and command:
            command()

    def set_enabled(enabled):
        state["enabled"] = enabled
        lbl.configure(
            cursor="hand2" if enabled else "arrow",
            fg=state["fg"] if enabled else disabled_fg,
            bg=bg,
        )

    lbl.bind("<Enter>", on_enter)
    lbl.bind("<Leave>", on_leave)
    lbl.bind("<Button-1>", on_click)
    lbl.set_enabled = set_enabled
    return lbl


def divider(parent, bg_line=OVERLAY, **pack_kwargs):
    """A thin horizontal rule -- the one flat-rectangle pattern every app
    already used consistently, kept as-is rather than reinvented."""
    f = tk.Frame(parent, bg=bg_line, height=1)
    f.pack(fill="x", **pack_kwargs)
    return f
