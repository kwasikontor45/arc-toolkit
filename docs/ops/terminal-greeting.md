# Terminal architecture greeting

The local shell greeting is rendered from `config/greeting.sh` and the principles file `config/motd`. The word of the day leads the banner in place of the old `SYSTEM: ARCHITECTURE_LOGS` line. Its phase label is calculated from the local clock each time the greeting renders. A compact phase rail shows Nyx, Choice, Desire, and Still-Pine in their canonical colors. The butterfly follows the active phase accent; only the circular markers use bold color for a bright bead effect. The banner is static after rendering and does not run an animation or background timer.

The local route row shows the ISP address from the private `~/.config/arc/greeting-isp-ip` baseline. If the VPN is active, its tunnel address and routed public egress are shown only when they differ from that baseline; the current resolver from `/etc/resolv.conf` is shown only when it differs too. Narrow terminals render each address on a separate labeled row. The public-IP lookup follows the existing default route and never bypasses the VPN. Direct-route results are cached for 30 minutes and VPN-route results for five minutes under `${XDG_CACHE_HOME:-~/.cache}/arc/`; each request has a two-second limit and a stale value is used only for the same route mode. Cloud-profile greetings do not read the private ISP baseline or query an IP service.

The banner divider starts under the `E` in “E Pluribus Unum” and ends under the final character of the phase shown in `LOCAL_TIME`. Its length follows the rendered, wrapped time row at the current terminal width. Section dots use the active phase bead; section titles and other text keep a regular, non-glowing weight.

Cloud greeting rollout is available for the three configured on-demand EC2 labs:

```sh
arc greeting push gvm
arc greeting push soclab
arc greeting push wazuh
```

These commands only print the selected target and files. To apply one update, run the exact target with `--apply`, for example:

```sh
arc greeting push gvm --apply
```

An apply requires the SOP gate to be open, AWS credentials, and the selected instance to already be running. It does not start or stop the instance. It copies only the greeting and a cloud-safe MOTD, then updates the remote user's `~/.config/arc/` files and the managed interactive Bash block in `~/.bashrc`. Existing files are backed up once as `.before-arc-greeting`; repeat pushes refresh the managed block without duplicating it. The cloud profile omits the workstation policy path, identifies the selected lab, and shows basic node RAM, disk, and uptime only.

The rollout is per target. Review the preview and explicitly use `--apply` for each EC2 host you want changed.
