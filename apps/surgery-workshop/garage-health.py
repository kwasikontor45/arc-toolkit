#!/usr/bin/env python3
"""Compact, read-only Garage view for Arc Heal's sanitized local report."""

from __future__ import annotations

import json
import os
import re
import stat
import time
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk


REPORT_PATH = Path.home() / "khaos-lab/arc-heal-log/garage-health.json"
LEGACY_REPORT_PATH = Path.home() / "khaos-lab/arc-heal-log/latest-status.md"
MAX_REPORT_BYTES = 64 * 1024
MAX_FINDINGS = 100
COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
STALE_AFTER_SECONDS = 6 * 60 * 60

COLORS = {
    "bg": "#141a18",
    "surface": "#1c2420",
    "raised": "#242e29",
    "ink": "#edf2ed",
    "muted": "#b2beb6",
    "line": "#435249",
    "ok": "#9ac7a6",
    "healed": "#80c8c1",
    "attention": "#ea9a97",
    "stale": "#f6c177",
}
def circadian_phase(hour: int) -> tuple[str, str]:
    if hour < 6 or hour >= 21:
        return "Nyx", "#ea9a97"
    if hour < 11:
        return "Choice", "#5ec8ed"
    if hour < 17:
        return "Desire", "#f6c177"
    return "Still-Pine", "#c4a7e7"


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 32:
        raise ValueError("invalid report time")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("report time must include a timezone")
    return parsed.astimezone(timezone.utc)


def read_report(path: Path = REPORT_PATH, now: float | None = None) -> dict:
    """Load only the bounded, owner-only schema; discard all unrecognized fields."""
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("report is not a regular file owned by this user")
    if info.st_mode & 0o077:
        raise ValueError("report permissions are broader than owner-only")
    if info.st_size > MAX_REPORT_BYTES:
        raise ValueError("report is too large")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise ValueError("unsupported report format")
    generated = _parse_time(raw.get("generated_at"))
    findings_in = raw.get("findings")
    if not isinstance(findings_in, list) or len(findings_in) > MAX_FINDINGS:
        raise ValueError("invalid finding list")

    findings = []
    for item in findings_in:
        if not isinstance(item, dict):
            raise ValueError("invalid finding")
        component = item.get("component")
        state = item.get("state")
        if not isinstance(component, str) or not COMPONENT_RE.fullmatch(component):
            raise ValueError("invalid component identifier")
        if not isinstance(state, str) or state not in {"ok", "healed", "flag"}:
            raise ValueError("invalid finding state")
        # Deliberately do not surface arbitrary messages from host checks.
        findings.append({"component": component, "state": state})

    counts = {state: sum(item["state"] == state for item in findings)
              for state in ("ok", "healed", "flag")}
    age = max(0.0, (now if now is not None else time.time()) - generated.timestamp())
    return {
        "generated_at": generated,
        "age_seconds": age,
        "stale": age > STALE_AFTER_SECONDS,
        "counts": counts,
        "findings": findings,
    }


def read_legacy_report(path: Path = LEGACY_REPORT_PATH, now: float | None = None) -> dict:
    """Sanitize an existing Arc Heal Markdown result while the JSON feed is new."""
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("legacy report is not a regular file owned by this user")
    if info.st_size > MAX_REPORT_BYTES:
        raise ValueError("legacy report is too large")
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^# arc-heal — (\d{8}T\d{6}Z)$", text, re.M)
    if not match:
        raise ValueError("unrecognized Arc Heal report")
    generated = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    findings = []
    state_markers = {"✅": "ok", "🩹": "healed", "🚩": "flag"}
    for line in text.splitlines():
        match = re.match(r"^-\s+(✅|🩹|🚩)\s+\*\*([^*]{1,120})\*\*\s+—", line)
        if not match:
            continue
        component = match.group(2)
        if COMPONENT_RE.fullmatch(component):
            findings.append({"component": component, "state": state_markers[match.group(1)]})
            if len(findings) > MAX_FINDINGS:
                raise ValueError("legacy finding list is too large")
    counts = {state: sum(item["state"] == state for item in findings)
              for state in ("ok", "healed", "flag")}
    age = max(0.0, (now if now is not None else time.time()) - generated.timestamp())
    return {"generated_at": generated, "age_seconds": age, "stale": age > STALE_AFTER_SECONDS,
            "counts": counts, "findings": findings}


def load_latest_report() -> dict:
    """Prefer the new contract; use sanitized Markdown only before its first run."""
    if REPORT_PATH.exists():
        return read_report()
    return read_legacy_report()


def _component_label(component: str) -> str:
    return component.replace(":", "  ·  ").replace("-", " ").replace("_", " ")


class GarageHealth:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Garage · Health")
        self.root.geometry("520x440")
        self.root.minsize(340, 300)
        self.root.configure(bg=COLORS["bg"])
        self.show_all = tk.BooleanVar(value=False)
        self._build()
        self.refresh()
        self.root.after(15_000, self._tick)

    def _build(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Garage.TFrame", background=COLORS["bg"])
        style.configure("Surface.TFrame", background=COLORS["surface"])
        style.configure("Ink.TLabel", background=COLORS["bg"], foreground=COLORS["ink"],
                        font=("DejaVu Sans", 10))
        style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"],
                        font=("DejaVu Sans", 9))
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["ink"],
                        font=("DejaVu Sans", 17, "bold"))
        style.configure("Report.TLabel", background=COLORS["surface"], foreground=COLORS["ink"],
                        font=("DejaVu Sans", 11, "bold"))
        style.configure("ReportMuted.TLabel", background=COLORS["surface"],
                        foreground=COLORS["muted"], font=("DejaVu Sans", 9))
        style.configure("Garage.TButton", padding=(12, 7), font=("DejaVu Sans", 9))

        shell = ttk.Frame(self.root, style="Garage.TFrame", padding=16)
        shell.pack(fill="both", expand=True)
        title_row = ttk.Frame(shell, style="Garage.TFrame")
        title_row.pack(fill="x")
        self.title_label = ttk.Label(title_row, text="GARAGE  /  HEALTH", style="Title.TLabel")
        self.title_label.pack(side="left")
        self.phase_label = ttk.Label(title_row, text="", style="Muted.TLabel")
        self.phase_label.pack(side="left", padx=(8, 0), pady=(5, 0))
        self.refresh_button = ttk.Button(title_row, text="Refresh", style="Garage.TButton",
                                         command=self.refresh)
        self.refresh_button.pack(side="right")

        self.summary = ttk.Label(shell, text="Reading report…", style="Ink.TLabel", wraplength=470)
        self.summary.pack(anchor="w", pady=(16, 2))
        self.timestamp = ttk.Label(shell, text="", style="Muted.TLabel")
        self.timestamp.pack(anchor="w", pady=(0, 12))
        self.root.bind("<Configure>", self._resize_text)

        self.list_frame = ttk.Frame(shell, style="Surface.TFrame", padding=12)
        self.list_frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(self.list_frame, bg=COLORS["surface"], highlightthickness=0,
                                borderwidth=0, takefocus=True)
        self.scroll = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.canvas.yview)
        self.rows = ttk.Frame(self.canvas, style="Surface.TFrame")
        self.rows.bind("<Configure>", lambda _event: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.rows, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.bind("<MouseWheel>", lambda event: self.canvas.yview_scroll(
            int(-event.delta / 120), "units"))
        self.canvas.bind("<Button-4>", lambda _event: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda _event: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<Up>", lambda _event: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Down>", lambda _event: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<Prior>", lambda _event: self.canvas.yview_scroll(-1, "pages"))
        self.canvas.bind("<Next>", lambda _event: self.canvas.yview_scroll(1, "pages"))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(
            self.canvas_window, width=event.width))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")

        self.all_button = ttk.Button(shell, text="Show all checks", style="Garage.TButton",
                                     command=self._toggle_all)
        self.all_button.pack(anchor="w", pady=(10, 2))
        ttk.Label(shell, text="Arc Heal checks and applies its approved safe repairs. Garage only reports.",
                  style="Muted.TLabel", wraplength=470).pack(anchor="w", pady=(7, 0))
        self.root.bind("<Control-r>", lambda _event: self.refresh())
        self._update_phase()

    def _clear_rows(self):
        for child in self.rows.winfo_children():
            child.destroy()

    def _resize_text(self, event):
        if event.widget is self.root:
            width = max(240, event.width - 40)
            self.summary.configure(wraplength=width)
            self.timestamp.configure(wraplength=width)

    def _update_phase(self):
        name, accent = circadian_phase(datetime.now().hour)
        self.title_label.configure(foreground=accent)
        self.phase_label.configure(text=f"· {name}", foreground=accent)

    def _row(self, finding: dict):
        state = finding["state"]
        labels = {"flag": ("ATTENTION", COLORS["attention"]),
                  "healed": ("AUTO-FIXED", COLORS["healed"]),
                  "ok": ("HEALTHY", COLORS["ok"])}
        state_text, color = labels[state]
        row = ttk.Frame(self.rows, style="Surface.TFrame")
        row.pack(fill="x", pady=4)
        name = tk.Label(row, text=_component_label(finding["component"]), anchor="w",
                        bg=COLORS["surface"], fg=COLORS["ink"],
                        font=("DejaVu Sans", 10), wraplength=300)
        name.pack(side="left", fill="x", expand=True)
        badge = tk.Label(row, text=state_text, bg=COLORS["raised"], fg=color,
                         font=("DejaVu Sans", 8, "bold"), padx=8, pady=4)
        badge.pack(side="right", padx=(8, 0))

    def refresh(self):
        self._update_phase()
        self._clear_rows()
        try:
            report = load_latest_report()
        except FileNotFoundError:
            self.summary.configure(text="No health report yet", foreground=COLORS["muted"])
            self.timestamp.configure(text="Arc Heal will publish one after its next check.")
            self.all_button.configure(state="disabled")
            return
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.summary.configure(text="Health report unavailable", foreground=COLORS["attention"])
            self.timestamp.configure(text=f"The local report failed validation: {error}")
            self.all_button.configure(state="disabled")
            return

        counts = report["counts"]
        status = ("Needs attention" if counts["flag"] else
                  "Auto-repair completed" if counts["healed"] else "All checks healthy")
        color = COLORS["attention"] if counts["flag"] else COLORS["ok"]
        if report["stale"]:
            status = "Report is stale · " + status
            color = COLORS["stale"]
        self.summary.configure(text=(f"{status}  ·  {counts['flag']} attention  ·  "
                                     f"{counts['healed']} auto-fixed  ·  {counts['ok']} healthy"),
                                foreground=color)
        when = report["generated_at"].astimezone().strftime("%a %b %d · %I:%M %p %Z")
        self.timestamp.configure(text=f"Last scan {when}  ·  updated automatically every 15 sec")
        findings = report["findings"]
        chosen = findings if self.show_all.get() else [x for x in findings if x["state"] != "ok"]
        if not chosen:
            ttk.Label(self.rows, text="No current issues or recent repairs.",
                      style="ReportMuted.TLabel").pack(anchor="w", pady=5)
        else:
            for finding in chosen:
                self._row(finding)
        self.all_button.configure(state="normal",
                                  text="Show attention only" if self.show_all.get()
                                  else "Show all checks")

    def _toggle_all(self):
        self.show_all.set(not self.show_all.get())
        self.refresh()

    def _tick(self):
        if self.root.winfo_exists():
            self.refresh()
            self.root.after(15_000, self._tick)


def main():
    root = tk.Tk()
    GarageHealth(root)
    root.mainloop()


if __name__ == "__main__":
    main()
