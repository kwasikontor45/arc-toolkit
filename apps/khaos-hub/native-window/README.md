# Khaos Hub native window

A GTK 3 + WebKitGTK 4.1 desktop shell for the existing local Khaos Hub at `http://127.0.0.1:8766/`. It opens as a native desktop window with a local-only private profile; it does not run Chromium or expose browser chrome. The Hub service lifecycle remains owned by its existing launcher/service.

## Security boundary

- The Hub window process tree runs in a dedicated user systemd scope with `IPAddressDeny=any` and only IPv4/IPv6 loopback allowed.
- The app profile and cache are private (`0700`). The app process is read-only except for that profile, cache, and the user's Downloads directory.
- WebKit may navigate only to the exact local Hub origin. Deliberate clicks on public HTTP(S) links open in the default browser; private, loopback, localhost, `.local`, and `.internal` destinations are rejected.
- WebKit permissions, plugins, developer extras, WebGL, automatic popups, and file-origin access are disabled. User-selected JSON imports and user-confirmed exports remain supported.
- Offline startup has a retry card. The launcher fails closed if it cannot create its sandbox scope.

## Runtime

This package bundles three GI introspection typelibs and their Debian copyright notices. It uses the host's GTK 3, PyGObject, and WebKitGTK 4.1 shared libraries; those must be installed and ABI-compatible. The type libraries came from Debian packages `gir1.2-webkit2-4.1`, `gir1.2-javascriptcoregtk-4.1`, and `gir1.2-soup-3.0` (WebKitGTK 2.52.6-1; Soup 3.6.6-1). No engine binaries or network assets are included.

## Install / rollback

Run `./install-user.sh` from this directory for a per-user install. It saves an owner-only timestamped copy of the previous launcher before replacement. Run `./uninstall-user.sh` to remove the package and restore the newest saved launcher. The existing desktop entry and Control Center action keep their established launcher path.

Press Ctrl+R/F5 to reload, Ctrl+Plus/Minus to adjust zoom, and Ctrl+0 to reset zoom. The GTK headerbar refresh button also reloads the local Hub.
