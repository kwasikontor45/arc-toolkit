# Terminal architecture greeting

The local shell greeting is rendered from `config/greeting.sh` and the principles file `config/motd`. It follows the current Circadian Canonical Hours, keeps the word of the day, and shows the current public IPv4 egress beside the local radar status. The IP is cached for 30 minutes under `${XDG_CACHE_HOME:-~/.cache}/arc/`; refresh is limited to a two-second request, with a cached value shown if refresh fails. The local interface address stays in the Systems section. Cloud-profile greetings do not query an IP service.

The banner divider starts under the `E` in “E Pluribus Unum” and ends under the final character of the phase shown in `LOCAL_TIME`. Its length follows the rendered, wrapped time row at the current terminal width. Section markers and titles use the current bold Circadian accent.

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
