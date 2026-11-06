#!/usr/bin/env python3
"""Compact, read-only Garage view for Arc Heal's sanitized local report."""

from __future__ import annotations

import json
import os
import re
import shutil
import queue
import stat
import subprocess
import threading
import time
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk


REPORT_PATH = Path.home() / "khaos-lab/arc-heal-log/garage-health.json"
LEGACY_REPORT_PATH = Path.home() / "khaos-lab/arc-heal-log/latest-status.md"
INVENTORY_PATH = (Path.home() / "khaos-lab/local-cloud-hub/operations/current/"
                  "inventory/inventory.json")
MAX_REPORT_BYTES = 64 * 1024
MAX_FINDINGS = 100
MAX_INVENTORY_BYTES = 2 * 1024 * 1024
MAX_INVENTORY_ASSETS = 500
COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
RESOURCE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
ENDPOINT_RE = re.compile(r"^(?:\[[0-9A-Fa-f:.%_-]{1,80}\]|[0-9A-Fa-f:.%_-]{1,80}):\d{1,5}$")
STALE_AFTER_SECONDS = 6 * 60 * 60
INVENTORY_STALE_AFTER_SECONDS = 45 * 60
DOCKER_REFRESH_SECONDS = 30
CONNECTION_REFRESH_SECONDS = 15

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


def read_fleet_inventory(path: Path = INVENTORY_PATH, now: float | None = None) -> dict:
    """Read a bounded inventory snapshot protected by the user's private home directory."""
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError("inventory is not a regular file owned by this user")
    home = Path.home()
    home_info = home.stat()
    if home_info.st_uid != os.getuid() or home_info.st_mode & 0o077:
        raise ValueError("user home is not private enough for inventory data")
    if not path.resolve(strict=True).is_relative_to(home.resolve()):
        raise ValueError("inventory is outside the user's private home")
    if info.st_size > MAX_INVENTORY_BYTES:
        raise ValueError("inventory is too large")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("assets"), list):
        raise ValueError("unsupported inventory format")
    if len(raw["assets"]) > MAX_INVENTORY_ASSETS:
        raise ValueError("inventory asset list is too large")
    generated = _parse_time(raw.get("generated"))
    age = max(0.0, (now if now is not None else time.time()) - generated.timestamp())
    resources = []
    for item in raw["assets"]:
        if not isinstance(item, dict) or item.get("kind") not in {
                "cloud-instance", "container", "virtual-machine", "vm"}:
            continue
        identifier, name = item.get("id"), item.get("name")
        status, observed = item.get("status"), item.get("observed")
        health = item.get("health")
        if (not isinstance(identifier, str) or not COMPONENT_RE.fullmatch(identifier)
                or not isinstance(name, str) or not RESOURCE_NAME_RE.fullmatch(name)
                or not isinstance(status, str) or not RESOURCE_NAME_RE.fullmatch(status)
                or not isinstance(observed, str) or not RESOURCE_NAME_RE.fullmatch(observed)
                or not isinstance(health, str) or not RESOURCE_NAME_RE.fullmatch(health)):
            continue
        if status == "retired" or (item["kind"] == "cloud-instance" and identifier.startswith("cloud.old")):
            continue
        resources.append({"id": identifier, "kind": item["kind"], "name": name,
                          "status": status, "observed": observed, "health": health})
    return {"generated_at": generated, "age_seconds": age,
            "stale": age > INVENTORY_STALE_AFTER_SECONDS, "resources": resources}


def read_docker_snapshot() -> dict:
    """Read local Docker state only; pin the endpoint to the local Unix socket."""
    executable = shutil.which("docker")
    if not executable:
        return {"available": False, "containers": [], "note": "Docker CLI unavailable"}
    try:
        result = subprocess.run(
            [executable, "--host", "unix:///var/run/docker.sock", "ps", "--all",
             "--format", "{{.Names}}\t{{.State}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=4, check=False)
    except subprocess.TimeoutExpired:
        return {"available": False, "containers": [], "note": "local Docker query timed out"}
    except OSError:
        return {"available": False, "containers": [], "note": "local Docker query unavailable"}
    if result.returncode != 0 or len(result.stdout) > 16_384:
        return {"available": False, "containers": [], "note": "local Docker state unavailable"}
    containers = []
    for line in result.stdout.splitlines()[:50]:
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        name, state, status = parts
        if not RESOURCE_NAME_RE.fullmatch(name) or state not in {
                "running", "exited", "created", "paused", "restarting", "removing", "dead"}:
            continue
        healthy = "healthy" if re.search(r"\(healthy\)\s*$", status) else ""
        containers.append({"name": name, "state": state, "health": healthy})
    return {"available": True, "containers": containers,
            "note": "local Docker socket · read-only"}


def read_established_tcp() -> dict:
    """Read bounded TCP peer metadata; never capture payloads or resolve addresses."""
    executable = shutil.which("ss")
    if not executable:
        return {"available": False, "flows": [], "note": "ss utility unavailable"}
    try:
        result = subprocess.run([executable, "-Htnp", "state", "established"],
                                capture_output=True, text=True, timeout=4, check=False)
    except subprocess.TimeoutExpired:
        return {"available": False, "flows": [], "note": "socket query timed out"}
    except OSError:
        return {"available": False, "flows": [], "note": "socket query unavailable"}
    if result.returncode != 0 or len(result.stdout) > 32_768:
        return {"available": False, "flows": [], "note": "socket state unavailable"}
    flows = []
    for line in result.stdout.splitlines()[:100]:
        fields = line.split(None, 4)
        if len(fields) < 4:
            continue
        local, peer = fields[2], fields[3]
        if not ENDPOINT_RE.fullmatch(local) or not ENDPOINT_RE.fullmatch(peer):
            continue
        process, pid = "process unavailable", ""
        if len(fields) == 5:
            match = re.search(r'users:\(\("([A-Za-z0-9_.+-]{1,64})",pid=(\d{1,10})', fields[4])
            if match:
                process, pid = match.groups()
        flows.append({"protocol": "TCP", "state": "ESTABLISHED", "process": process,
                      "pid": pid, "local": local, "peer": peer})
    return {"available": True, "flows": flows[:60], "note": "TCP established · metadata only"}


def collect_fleet_snapshot() -> dict:
    try:
        inventory = read_fleet_inventory()
    except (OSError, ValueError, json.JSONDecodeError):
        inventory = None
    return {"inventory": inventory, "docker": read_docker_snapshot()}


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
        self.root.title("Garage · Emergency Room")
        self.root.geometry("760x620")
        self.root.minsize(520, 420)
        self.root.configure(bg=COLORS["bg"])
        self.show_all = tk.BooleanVar(value=False)
        self.collector_queue = queue.Queue()
        self.collector_pending = set()
        self.collector_requested = {"fleet": 0.0, "network": 0.0}
        self._build()
        self.refresh()
        self._request_collectors(force=True)
        self.root.after(250, self._poll_collectors)
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
        style.configure("Garage.TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("Garage.TNotebook.Tab", background=COLORS["raised"],
                        foreground=COLORS["muted"], padding=(14, 8))
        style.map("Garage.TNotebook.Tab", background=[("selected", COLORS["surface"])],
                  foreground=[("selected", COLORS["ink"])])

        shell = ttk.Frame(self.root, style="Garage.TFrame", padding=16)
        shell.pack(fill="both", expand=True)
        title_row = ttk.Frame(shell, style="Garage.TFrame")
        title_row.pack(fill="x")
        self.title_label = ttk.Label(title_row, text="GARAGE  /  EMERGENCY ROOM", style="Title.TLabel")
        self.title_label.pack(side="left")
        self.phase_label = ttk.Label(title_row, text="", style="Muted.TLabel")
        self.phase_label.pack(side="left", padx=(8, 0), pady=(5, 0))
        self.refresh_button = ttk.Button(title_row, text="Refresh", style="Garage.TButton",
                                         command=self.refresh_all)
        self.refresh_button.pack(side="right")

        self.notebook = ttk.Notebook(shell, style="Garage.TNotebook")
        self.notebook.pack(fill="both", expand=True, pady=(12, 0))
        self.health_tab = ttk.Frame(self.notebook, style="Garage.TFrame", padding=10)
        self.fleet_tab = ttk.Frame(self.notebook, style="Garage.TFrame", padding=10)
        self.network_tab = ttk.Frame(self.notebook, style="Garage.TFrame", padding=10)
        self.notebook.add(self.health_tab, text="Health")
        self.notebook.add(self.fleet_tab, text="Lab fleet")
        self.notebook.add(self.network_tab, text="Connections")

        self.summary = ttk.Label(self.health_tab, text="Reading report…", style="Ink.TLabel",
                                 wraplength=680)
        self.summary.pack(anchor="w", pady=(4, 2))
        self.timestamp = ttk.Label(self.health_tab, text="", style="Muted.TLabel")
        self.timestamp.pack(anchor="w", pady=(0, 12))
        self.root.bind("<Configure>", self._resize_text)

        self.list_frame = ttk.Frame(self.health_tab, style="Surface.TFrame", padding=12)
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

        self.all_button = ttk.Button(self.health_tab, text="Show all checks", style="Garage.TButton",
                                     command=self._toggle_all)
        self.all_button.pack(anchor="w", pady=(10, 2))
        ttk.Label(self.health_tab,
                  text="Arc Heal performs its approved repairs. Garage reports only.",
                  style="Muted.TLabel", wraplength=680).pack(anchor="w", pady=(7, 0))

        ttk.Label(self.fleet_tab, text="LAB FLEET  ·  LOCAL + CLOUD", style="Title.TLabel").pack(anchor="w")
        self.fleet_summary = ttk.Label(self.fleet_tab, text="Waiting for inventory and Docker…",
                                       style="Ink.TLabel", wraplength=680)
        self.fleet_summary.pack(anchor="w", pady=(10, 2))
        self.fleet_timestamp = ttk.Label(self.fleet_tab, text="", style="Muted.TLabel")
        self.fleet_timestamp.pack(anchor="w", pady=(0, 8))
        self.fleet_chart = tk.Canvas(self.fleet_tab, height=106, bg=COLORS["bg"],
                                     highlightthickness=0, borderwidth=0, takefocus=False)
        self.fleet_chart.pack(fill="x", pady=(0, 4))
        self.fleet_chart.bind("<Configure>", lambda _event: self._draw_fleet_chart())
        self.fleet_chart_summary = ttk.Label(self.fleet_tab, text="", style="Muted.TLabel",
                                             wraplength=680)
        self.fleet_chart_summary.pack(anchor="w", pady=(0, 8))
        self.fleet_frame = ttk.Frame(self.fleet_tab, style="Surface.TFrame", padding=10)
        self.fleet_frame.pack(fill="both", expand=True)
        self.fleet_canvas = tk.Canvas(self.fleet_frame, bg=COLORS["surface"],
                                      highlightthickness=0, borderwidth=0, takefocus=True)
        self.fleet_scroll = ttk.Scrollbar(self.fleet_frame, orient="vertical",
                                          command=self.fleet_canvas.yview)
        self.fleet_rows = ttk.Frame(self.fleet_canvas, style="Surface.TFrame")
        self.fleet_rows.bind("<Configure>", lambda _event: self.fleet_canvas.configure(
            scrollregion=self.fleet_canvas.bbox("all")))
        self.fleet_window = self.fleet_canvas.create_window(
            (0, 0), window=self.fleet_rows, anchor="nw")
        self.fleet_canvas.configure(yscrollcommand=self.fleet_scroll.set)
        self.fleet_canvas.bind("<Configure>", lambda event: self.fleet_canvas.itemconfigure(
            self.fleet_window, width=event.width))
        self.fleet_canvas.bind("<MouseWheel>", lambda event: self.fleet_canvas.yview_scroll(
            int(-event.delta / 120), "units"))
        self.fleet_canvas.bind("<Button-4>", lambda _event: self.fleet_canvas.yview_scroll(-1, "units"))
        self.fleet_canvas.bind("<Button-5>", lambda _event: self.fleet_canvas.yview_scroll(1, "units"))
        self.fleet_canvas.pack(side="left", fill="both", expand=True)
        self.fleet_scroll.pack(side="right", fill="y")
        ttk.Label(self.fleet_tab,
                  text="Cloud states come from the timestamped Arc inventory snapshot. "
                       "Docker is queried locally; no VM or container is started or stopped.",
                  style="Muted.TLabel", wraplength=680).pack(anchor="w", pady=(8, 0))

        ttk.Label(self.network_tab, text="NETWORK  ·  OBSERVED TCP", style="Title.TLabel").pack(anchor="w")
        self.network_summary = ttk.Label(self.network_tab, text="Reading current connections…",
                                         style="Ink.TLabel", wraplength=680)
        self.network_summary.pack(anchor="w", pady=(10, 2))
        self.network_timestamp = ttk.Label(self.network_tab, text="", style="Muted.TLabel")
        self.network_timestamp.pack(anchor="w", pady=(0, 8))
        self.network_frame = ttk.Frame(self.network_tab, style="Surface.TFrame", padding=10)
        self.network_frame.pack(fill="both", expand=True)
        self.network_canvas = tk.Canvas(self.network_frame, bg=COLORS["surface"],
                                        highlightthickness=0, borderwidth=0, takefocus=True)
        self.network_scroll = ttk.Scrollbar(self.network_frame, orient="vertical",
                                            command=self.network_canvas.yview)
        self.network_rows = ttk.Frame(self.network_canvas, style="Surface.TFrame")
        self.network_rows.bind("<Configure>", lambda _event: self.network_canvas.configure(
            scrollregion=self.network_canvas.bbox("all")))
        self.network_window = self.network_canvas.create_window(
            (0, 0), window=self.network_rows, anchor="nw")
        self.network_canvas.configure(yscrollcommand=self.network_scroll.set)
        self.network_canvas.bind("<Configure>", lambda event: self.network_canvas.itemconfigure(
            self.network_window, width=event.width))
        for sequence, amount in (("<MouseWheel>", -1), ("<Button-4>", -1), ("<Button-5>", 1),
                                 ("<Up>", -1), ("<Down>", 1)):
            self.network_canvas.bind(sequence, lambda event, step=amount: self.network_canvas.yview_scroll(
                step if not hasattr(event, "delta") or not event.delta
                else int(-event.delta / 120), "units"))
        self.network_canvas.pack(side="left", fill="both", expand=True)
        self.network_scroll.pack(side="right", fill="y")
        ttk.Label(self.network_tab,
                  text="Local host TCP metadata only. No payloads, DNS queries, listeners, UDP, "
                       "container network namespaces, or cloud flow logs are collected. "
                       "Those sources need a separate, approved read-only integration.",
                  style="Muted.TLabel", wraplength=680).pack(anchor="w", pady=(8, 0))

        self.root.bind("<Control-r>", lambda _event: self.refresh_all())
        self._update_phase()

    def _clear_rows(self):
        for child in self.rows.winfo_children():
            child.destroy()

    def _resize_text(self, event):
        if event.widget is self.root:
            width = max(240, event.width - 80)
            self.summary.configure(wraplength=width)
            self.timestamp.configure(wraplength=width)
            self.fleet_summary.configure(wraplength=width)
            self.fleet_timestamp.configure(wraplength=width)
            self.fleet_chart_summary.configure(wraplength=width)
            self.network_summary.configure(wraplength=width)
            self.network_timestamp.configure(wraplength=width)
            self._fit_nested_labels(self.fleet_rows, width)
            self._fit_nested_labels(self.network_rows, width)
            self._draw_fleet_chart()

    @staticmethod
    def _fit_nested_labels(container, width):
        for child in container.winfo_children():
            if isinstance(child, (tk.Label, ttk.Label)):
                child.configure(wraplength=width)
            GarageHealth._fit_nested_labels(child, width)

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

    def refresh_all(self):
        self.refresh()
        self._request_collectors(force=True)

    def _request_collectors(self, force: bool = False):
        now = time.monotonic()
        collectors = (
            ("fleet", collect_fleet_snapshot, DOCKER_REFRESH_SECONDS),
            ("network", read_established_tcp, CONNECTION_REFRESH_SECONDS),
        )
        for name, collector, interval in collectors:
            if name in self.collector_pending:
                continue
            if not force and now - self.collector_requested[name] < interval:
                continue
            self.collector_requested[name] = now
            self.collector_pending.add(name)
            threading.Thread(target=self._collect_in_background,
                             args=(name, collector), daemon=True).start()

    def _collect_in_background(self, name, collector):
        try:
            snapshot = collector()
        except Exception:
            snapshot = {"available": False, "note": "local read failed"}
        collected = datetime.now().astimezone().strftime("%a %b %d · %I:%M:%S %p %Z")
        self.collector_queue.put((name, snapshot, collected))

    def _poll_collectors(self):
        try:
            while True:
                name, snapshot, collected = self.collector_queue.get_nowait()
                self.collector_pending.discard(name)
                if name == "fleet":
                    self._render_fleet(snapshot, collected)
                elif name == "network":
                    self._render_network(snapshot, collected)
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(250, self._poll_collectors)

    def _fleet_row(self, title: str, status: str, detail: str, color: str):
        row = ttk.Frame(self.fleet_rows, style="Garage.TFrame")
        row.pack(fill="x", pady=4)
        copy = ttk.Frame(row, style="Garage.TFrame")
        copy.pack(side="left", fill="x", expand=True)
        ttk.Label(copy, text=title, style="Ink.TLabel").pack(anchor="w")
        ttk.Label(copy, text=detail, style="Muted.TLabel", wraplength=600).pack(anchor="w")
        badge = tk.Label(row, text=status, bg=COLORS["raised"], fg=color,
                         font=("DejaVu Sans", 8, "bold"), padx=8, pady=5)
        badge.pack(side="right", padx=(8, 0))

    def _draw_fleet_chart(self, cloud=None, docker=None):
        if cloud is not None:
            self._chart_data = (cloud, docker or {"running": 0, "stopped": 0, "unknown": 0})
        if not hasattr(self, "_chart_data"):
            return
        cloud, docker = self._chart_data
        self.fleet_chart.delete("all")
        width = max(300, self.fleet_chart.winfo_width())
        bar_x, bar_w = 104, max(100, width - 224)
        for index, (label, counts) in enumerate((("CLOUD VMS", cloud), ("DOCKER", docker))):
            y = 14 + index * 43
            self.fleet_chart.create_text(0, y + 7, text=label, anchor="w",
                                         fill=COLORS["muted"], font=("DejaVu Sans", 8, "bold"))
            self.fleet_chart.create_rectangle(bar_x, y, bar_x + bar_w, y + 16,
                                              fill=COLORS["raised"], outline="")
            total = sum(counts.values())
            position = bar_x
            if total:
                for key, color in (("running", COLORS["ok"]), ("stopped", COLORS["muted"]),
                                   ("unknown", COLORS["attention"])):
                    amount = counts.get(key, 0)
                    if amount:
                        segment = bar_w * amount / total
                        self.fleet_chart.create_rectangle(position, y, position + segment, y + 16,
                                                          fill=color, outline="")
                        position += segment
            else:
                self.fleet_chart.create_text(bar_x + 7, y + 8, text="no data", anchor="w",
                                             fill=COLORS["ink"], font=("DejaVu Sans", 8))
            self.fleet_chart.create_text(bar_x + bar_w + 9, y + 8,
                                         text=f"{counts.get('running', 0)}/{total} up",
                                         anchor="w", fill=COLORS["ink"],
                                         font=("DejaVu Sans", 8, "bold"))

    def _render_fleet(self, data: dict, collected: str):
        for child in self.fleet_rows.winfo_children():
            child.destroy()
        inventory = data.get("inventory")
        docker = data.get("docker", {"available": False, "containers": [],
                                       "note": "local Docker state unavailable"})
        clouds = [] if inventory is None else [
            item for item in inventory["resources"] if item["kind"] == "cloud-instance"]
        registered = [] if inventory is None else [
            item for item in inventory["resources"] if item["kind"] == "container"]
        local_vms = [] if inventory is None else [
            item for item in inventory["resources"] if item["kind"] in {"vm", "virtual-machine"}]
        cloud_counts = {key: 0 for key in ("running", "stopped", "unknown")}
        for item in clouds:
            state = item["observed"] if item["observed"] in {"running", "stopped"} else "unknown"
            cloud_counts[state] += 1
        docker_containers = docker.get("containers", [])
        docker_counts = {key: 0 for key in ("running", "stopped", "unknown")}
        if docker.get("available"):
            present = {item["name"]: item for item in docker_containers}
            shown = set()
            for item in registered:
                current = present.get(item["name"])
                if current:
                    shown.add(item["name"])
                    state = current["state"]
                    category = ("running" if state == "running" else
                                "stopped" if state in {"exited", "created", "dead"} else "unknown")
                    docker_counts[category] += 1
                    status = state.upper()
                    color = COLORS["ok"] if category == "running" else (
                        COLORS["muted"] if category == "stopped" else COLORS["stale"])
                    health = f" · {current['health']}" if current["health"] else ""
                    self._fleet_row(f"SOC CONTAINER  ·  {item['name']}", status,
                                    f"Live local Docker state{health} · registry {item['status']}", color)
                else:
                    docker_counts["unknown"] += 1
                    self._fleet_row(f"SOC CONTAINER  ·  {item['name']}", "NOT FOUND",
                                    "Registered in inventory, absent from the local Docker list.",
                                    COLORS["attention"])
            for current in docker_containers:
                if current["name"] in shown or any(x["name"] == current["name"] for x in registered):
                    continue
                category = ("running" if current["state"] == "running" else
                            "stopped" if current["state"] in {"exited", "created", "dead"} else "unknown")
                docker_counts[category] += 1
                color = COLORS["ok"] if category == "running" else COLORS["muted"]
                self._fleet_row(f"DOCKER CONTAINER  ·  {current['name']}", current["state"].upper(),
                                "Present in local Docker; not matched to a registered SOC container.", color)
        else:
            docker_counts["unknown"] = len(registered)
            self._fleet_row("LOCAL DOCKER", "UNKNOWN", docker.get("note", "State unavailable"),
                            COLORS["stale"])
            for item in registered:
                self._fleet_row(f"SOC CONTAINER  ·  {item['name']}", "UNKNOWN",
                                f"Last registry observation: {item['observed']} · not a live check.",
                                COLORS["stale"])

        inventory_age = "inventory unavailable"
        if inventory is not None:
            age = int(inventory["age_seconds"])
            inventory_age = f"inventory {'STALE · ' if inventory['stale'] else ''}"
            inventory_age += f"{age // 60} min old · generated " + inventory["generated_at"].astimezone().strftime(
                "%H:%M %Z")
        else:
            self._fleet_row("INVENTORY", "UNAVAILABLE",
                            "Owner-only Arc inventory could not be validated.", COLORS["attention"])
        if not local_vms:
            self._fleet_row("LOCAL VMS", "NOT REGISTERED",
                            "No local VM asset is registered in Arc inventory.", COLORS["stale"])
        else:
            for item in local_vms:
                self._fleet_row(f"LOCAL VM  ·  {item['name']}", item["observed"].upper(),
                                f"Arc inventory · {item['status']}", COLORS["muted"])
        for item in clouds:
            state = item["observed"] if item["observed"] in {"running", "stopped"} else "unknown"
            label = item["observed"].upper() + (" · ON-DEMAND" if item["status"] == "on-demand" else "")
            color = COLORS["ok"] if state == "running" else (
                COLORS["muted"] if state == "stopped" else COLORS["stale"])
            if inventory and inventory["stale"]:
                label += " · STALE"
                color = COLORS["stale"]
            self._fleet_row(f"CLOUD LAB VM  ·  {item['name']}", label,
                            f"Arc inventory snapshot · health {item['health']}", color)

        cloud_text = ((f"Cloud labs: {len(clouds)} · {cloud_counts['running']} running · "
                       f"{cloud_counts['stopped']} stopped · {cloud_counts['unknown']} unknown")
                      if inventory is not None else "Cloud labs: snapshot unavailable")
        if docker.get("available"):
            docker_text = (f"Docker: {sum(docker_counts.values())} local containers · "
                           f"{docker_counts['running']} running · {docker_counts['stopped']} stopped · "
                           f"{docker_counts['unknown']} unknown")
        else:
            docker_text = "Docker: live state unknown"
        self.fleet_summary.configure(text=f"{cloud_text}     ·     {docker_text}")
        self.fleet_timestamp.configure(text=f"Collected {collected} · {inventory_age} · {docker.get('note', '')}")
        cloud_chart = (f"Cloud VM bar · {cloud_counts['running']} running / {cloud_counts['stopped']} stopped / "
                       f"{cloud_counts['unknown']} unknown" if inventory is not None
                       else "Cloud VM bar · no inventory snapshot")
        self.fleet_chart_summary.configure(
            text=f"{cloud_chart}     |     Docker bar · {docker_counts['running']} running / "
                 f"{docker_counts['stopped']} stopped / {docker_counts['unknown']} unknown")
        self._draw_fleet_chart(cloud_counts, docker_counts)

    def _render_network(self, data: dict, collected: str):
        for child in self.network_rows.winfo_children():
            child.destroy()
        if not data.get("available"):
            self.network_summary.configure(text="Connection metadata unavailable",
                                           foreground=COLORS["stale"])
            self.network_timestamp.configure(text=data.get("note", "No socket snapshot available"))
            return
        flows = data.get("flows", [])
        self.network_summary.configure(
            text=f"{len(flows)} established TCP conversation(s) observed · process attribution shown when available",
            foreground=COLORS["ink"])
        self.network_timestamp.configure(text=f"Sampled {collected} · {data.get('note', '')}")
        if not flows:
            ttk.Label(self.network_rows, text="No established TCP conversations observed.",
                      style="ReportMuted.TLabel").pack(anchor="w", pady=5)
            return
        for flow in flows:
            row = ttk.Frame(self.network_rows, style="Surface.TFrame")
            row.pack(fill="x", pady=4)
            process = flow["process"] + (f" · PID {flow['pid']}" if flow["pid"] else "")
            tk.Label(row, text=process, anchor="w", bg=COLORS["surface"], fg=COLORS["ink"],
                     font=("DejaVu Sans", 9, "bold")).pack(fill="x")
            tk.Label(row, text=f"{flow['local']}  →  {flow['peer']}   ·   {flow['state']}",
                     anchor="w", justify="left", wraplength=650, bg=COLORS["surface"],
                     fg=COLORS["muted"], font=("DejaVu Sans Mono", 9)).pack(fill="x", pady=(2, 4))

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
            self._request_collectors()
            self.root.after(15_000, self._tick)


def main():
    root = tk.Tk()
    GarageHealth(root)
    root.mainloop()


if __name__ == "__main__":
    main()
