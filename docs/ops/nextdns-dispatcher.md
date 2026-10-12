# NextDNS network recovery

The proposed dispatcher source is
`system/networkmanager/dispatcher.d/90-nextdns-heal`. Its workstation copy
would be `/etc/NetworkManager/dispatcher.d/90-nextdns-heal`, owned by
`root:root` with mode `0755`. It is hardened but remains uninstalled; this
change does not install it or alter the live resolver.

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

## Install later

Preserve any installed copy under `/var/backups`, install the source with root
ownership and mode `0755`, and validate with `bash -n`. Confirm the resolver is
still a regular file managed with NetworkManager `dns=none`; exercise a
virtual-link event and verify it exits without restarting NextDNS. Installation
alone remains inert until the owner explicitly opts in with `arc dns on`.
Do not change VPN routing, the NextDNS profile, or leak-protection policy as
part of a dispatcher update.
