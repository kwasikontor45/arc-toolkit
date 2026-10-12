# NextDNS network recovery

The dispatcher source is `system/networkmanager/dispatcher.d/90-nextdns-heal`;
the workstation copy is `/etc/NetworkManager/dispatcher.d/90-nextdns-heal`.
On 2026-10-12 the previously installed, unguarded hook was preserved as
`/var/backups/90-nextdns-heal-20261012-103236` and replaced with this guarded
version. The installed file is mode `0755` and its SHA-256 matches the source.
The backup hash is `70652ac5c36d7d031d72c2de1d6e7c7457f51817e821c86c08a9e17b9bd21ba9`.
The current desired-state file is absent, so the replacement exits before
service or resolver operations unless the owner explicitly opts in.

## Fail-closed opt-in

`~/.config/arc/nextdns-autoheal-state` is the single desired-state file.
`arc dns on` atomically writes `on` with owner-only permissions before it
activates NextDNS. `arc dns off` writes `off` before deactivating NextDNS, so a
concurrent network event cannot undo the opt-out. Missing, malformed,
symlinked, or incorrectly permissioned state disables automatic DNS repair.
`arc dns status` reports the auto-heal state. The periodic NextDNS health check
and `arc-heal` DNS-leak repair also honor this state. `arc-dns` is the sole
writer; repair scripts only read it.

The dispatcher responds only to interface `up` and global
`connectivity-change` events. Disconnects and interface churn do not trigger a
restart. It skips loopback and container-only links (`docker0`, `lxcbr0`,
`br-*`, `veth*`, `virbr*`, `podman*`, and `cni*`). Events use a lock and
five-second debounce. It restarts NextDNS only when auto-heal is opted in and
the service is already active. It refuses to replace a symlink or non-file at
`/etc/resolv.conf`; if the explicitly enabled local-stub config needs repair,
it uses an atomic same-directory replacement. Dispatcher messages go to
journald under `arc-nextdns-heal`.

## Deployment and verification

The current process verified `bash -n`, matching source/installed hashes, and
that invoking the hook with the desired-state file absent leaves
`/etc/resolv.conf` unchanged. A system-bus restriction prevented querying the
NextDNS unit state from this session. Verify service status on the host with
`systemctl is-active nextdns.service`; inspect the desired-state choice with
`arc dns status`. Installation alone remains inert until the owner explicitly
opts in with `arc dns on`. Do not change VPN routing, the NextDNS profile, or
leak-protection policy as part of a dispatcher update.
