# Home network and IP guard

Khaos Lab → Network exposes the Eero summary and interactive router controls,
plus the latest guarded home-IP check and a confirmed one-shot sync action.
The summary labels the address as **host egress** and shows its route device;
when the route is `proton0`, that is the VPN exit, not the ISP/router WAN IP.

`arc-home-ip-heal.timer` checks every 30 minutes while the user's systemd
session is running. It runs only `arc-heal --ip-only`; it does not run the
broader system healer. The guard requires a Wi-Fi default route matching the
owner-only home SSID and gateway in `~/.config/arc/home-ip-sync.conf`, with
VPN/tunnel/proxy routing and NextDNS/custom loopback DNS inactive. Any
unknown or incomplete condition defers without querying AWS. It never turns
VPN or DNS settings on or off.

The existing repair path uses the tracked `~/khaos-lab/aws-infra` Terraform
source and never changes security groups through raw AWS calls. That checkout
is currently absent, so the timer cannot repair a changed SSH allowlist until
the Terraform source is restored and validated. Current VPN and NextDNS are
both active, so the live check correctly defers. Use `arc heal ip-status` to
read the latest result, `arc heal ip` for a guarded one-shot, and
`systemctl --user disable --now arc-home-ip-heal.timer` to stop the schedule.

Eero's device, node, speed-test, diagnostics, password, and forwarding controls
remain in `arc eero`; Khaos Lab opens that manager in a terminal. The periodic
Eero client watcher remains opt-in from the panel.
