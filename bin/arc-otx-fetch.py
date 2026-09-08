#!/usr/bin/env python3
"""arc-otx-fetch — pull subscribed OTX pulses, extract IOCs, print as
Wazuh CDB list lines (key: or key:value). One list per invocation.

Usage: arc-otx-fetch.py <ip|domain|hash> [max_pulses]

Deliberately bounded (default 300 pulses, ~5-10 API pages) rather than
pulling the full subscribed history on every run -- this account has
9000+ pulses total; a full historical pull isn't needed to get real,
current threat-intel value, and keeps both the API load and the
resulting list size sane for a personal lab, not a production SOC feed
pipeline.
"""
import json
import os
import sys
import urllib.request

CONF = os.path.expanduser("~/.config/arc/otx.conf")
API_BASE = "https://otx.alienvault.com/api/v1"


def load_key():
    with open(CONF) as f:
        for line in f:
            line = line.strip()
            if line.startswith("OTX_API_KEY="):
                return line.split("=", 1)[1]
    raise SystemExit("OTX_API_KEY not found in " + CONF)


def fetch_pulses(api_key, max_pulses):
    url = f"{API_BASE}/pulses/subscribed?limit=50"
    pulses = []
    while url and len(pulses) < max_pulses:
        req = urllib.request.Request(url, headers={"X-OTX-API-KEY": api_key})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        pulses.extend(data.get("results", []))
        url = data.get("next")
    return pulses[:max_pulses]


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("ip", "domain", "hash"):
        print("usage: arc-otx-fetch.py <ip|domain|hash> [max_pulses]", file=sys.stderr)
        sys.exit(1)
    kind = sys.argv[1]
    max_pulses = int(sys.argv[2]) if len(sys.argv) > 2 else 300

    type_map = {
        "ip": {"IPv4"},
        "domain": {"domain", "hostname"},
        "hash": {"FileHash-SHA256"},
    }
    wanted = type_map[kind]

    api_key = load_key()
    pulses = fetch_pulses(api_key, max_pulses)

    seen = set()
    for pulse in pulses:
        pulse_name = pulse.get("name", "")
        for ind in pulse.get("indicators", []):
            if ind.get("type") not in wanted:
                continue
            value = (ind.get("indicator") or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            if kind == "hash":
                # match malware-hashes' own key:family format -- pulse
                # name is the closest thing OTX gives us to a family/
                # campaign label per indicator.
                label = pulse_name[:40].replace(":", "-") or "OTX"
                print(f"{value}:{label}")
            else:
                print(f"{value}:")


if __name__ == "__main__":
    main()
