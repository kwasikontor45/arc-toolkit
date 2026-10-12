# Real-time LAN reconnaissance alerts

Suricata's EVE ARP events are enabled so the watcher can see local-layer
discovery such as Nmap `-sn` on the directly connected LAN. The watcher raises
one immediate Arc Pine critical notification after one source queries 20
distinct IPv4 targets within five seconds. It does not notify on ordinary
single-host ARP requests.

`system/suricata/arc-local.rules` adds alert-only TCP SYN, UDP, and ICMP
thresholds for higher-volume reconnaissance against `$HOME_NET`. Matching
Suricata scan alerts bypass the normal notification batch and are sent
immediately, with a 30-second per-signature/source/target repeat cooldown.
ARP sweeps have a 60-second per-source cooldown. Normal Suricata severity 1/2
alerts retain their existing batching and flood cap.

This is detection and notification only: it does not drop packets, change
firewall rules, or change VPN/DNS state. Thresholds are intentionally
conservative heuristics; a busy legitimate client can resemble a scan, and
traffic not visible to this host's Suricata interface cannot trigger these
alerts. Review events with `arc sec suricata` or `arc logs suricata`.

To roll back, remove the `arc-local.rules` entry from the Suricata
`rule-files:` list, set the EVE `arp` output back to `enabled: no`, remove
`/var/lib/suricata/rules/arc-local.rules`, restore the previous watcher from
the repository if needed, then validate and restart Suricata and its watcher.
The deployment backup is recorded in the session GAMEPLAN entry.
