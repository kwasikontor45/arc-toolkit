#!/usr/bin/env python3
"""Khaos Hub native desktop shell. Web content stays on the local Hub origin."""
from __future__ import annotations

import os
import ipaddress
import subprocess
import sys
import urllib.parse
from pathlib import Path

APP_ID = "studio.khaos.KhaosHub"
WM_CLASS = "KhaosHub"
APP_URL = "http://127.0.0.1:8766/"
APP_ORIGIN = ("http", "127.0.0.1", 8766)
PACKAGE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = PACKAGE_DIR / "runtime" / "girepository-1.0"
if RUNTIME_DIR.is_dir():
    existing = os.environ.get("GI_TYPELIB_PATH", "")
    os.environ["GI_TYPELIB_PATH"] = os.pathsep.join(filter(None, (str(RUNTIME_DIR), existing)))
os.umask(0o077)

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, WebKit2  # noqa: E402

DATA_ROOT = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "khaos-hub-native"
PROFILE_DIR = DATA_ROOT / "profile"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "khaos-hub-native"


def is_local_hub_uri(uri: str) -> bool:
    """Allow only the exact local Hub origin; reject credentials and malformed ports."""
    try:
        parsed = urllib.parse.urlsplit(uri)
        return (
            parsed.scheme == APP_ORIGIN[0]
            and parsed.hostname == APP_ORIGIN[1]
            and parsed.port == APP_ORIGIN[2]
            and parsed.username is None
            and parsed.password is None
            and not parsed.fragment.startswith("javascript:")
        )
    except (TypeError, ValueError):
        return False


def prepare_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


class HubWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app, title="Khaos Hub · Personal Workspace")
        self.set_wmclass(WM_CLASS, WM_CLASS)
        self.set_opacity(0.985)
        self.brand_pixbuf = self._load_brand_pixbuf()
        if self.brand_pixbuf is not None:
            self.set_icon(self.brand_pixbuf)
            self.set_icon_list([self.brand_pixbuf])
        self.set_default_size(1200, 820)
        self.set_size_request(620, 440)
        self._build_header()
        self._build_view()
        self.connect("key-press-event", self._on_key_press)
        self.show_all()
        self.webview.load_uri(APP_URL)

    @staticmethod
    def _load_brand_pixbuf():
        """Build the small icon pixbuf from raw RGBA bytes; do not spawn image loaders."""
        path = PACKAGE_DIR / "icon-kimi-64.rgba"
        try:
            pixels = path.read_bytes()
            if len(pixels) != 64 * 64 * 4:
                return None
            return GdkPixbuf.Pixbuf.new_from_bytes(
                GLib.Bytes.new(pixels), GdkPixbuf.Colorspace.RGB,
                True, 8, 64, 64, 64 * 4,
            )
        except (OSError, GLib.Error, TypeError) as error:
            print(f"Khaos Hub icon decode failed: {error}", file=sys.stderr)
            return None

    def _build_header(self) -> None:
        # Keep the window manager's native title bar; themed GTK HeaderBar icons
        # can invoke nested image-loader sandboxes under this app's systemd unit.
        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        topbar.set_margin_start(16)
        topbar.set_margin_end(16)
        topbar.set_margin_top(10)
        topbar.set_margin_bottom(10)
        topbar.get_style_context().add_class("hub-topbar")
        identity = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        if self.brand_pixbuf is not None:
            icon = Gtk.Image.new_from_pixbuf(self.brand_pixbuf.scale_simple(34, 34, GdkPixbuf.InterpType.BILINEAR))
            icon.get_style_context().add_class("hub-brand-mark")
            icon.set_tooltip_text("Kimi · Khaos Hub")
            identity.pack_start(icon, False, False, 0)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title = Gtk.Label(label="Khaos Hub", xalign=0)
        title.get_style_context().add_class("hub-title")
        subtitle = Gtk.Label(label="Personal workspace · local session", xalign=0)
        subtitle.get_style_context().add_class("hub-subtitle")
        labels.pack_start(title, False, False, 0)
        labels.pack_start(subtitle, False, False, 0)
        identity.pack_start(labels, False, False, 0)
        topbar.pack_start(identity, True, True, 0)

        self.connection_label = Gtk.Label(label="LOCAL ONLY")
        self.connection_label.get_style_context().add_class("hub-status")
        topbar.pack_start(self.connection_label, False, False, 0)
        refresh = Gtk.Button(label="Reload")
        refresh.set_tooltip_text("Reload Khaos Hub")
        refresh.set_action_name("app.reload")
        refresh.get_style_context().add_class("hub-refresh")
        topbar.pack_end(refresh, False, False, 0)
        self.root.pack_start(topbar, False, False, 0)
        self.add(self.root)

    def _build_view(self) -> None:
        prepare_private_dir(PROFILE_DIR)
        prepare_private_dir(CACHE_DIR)
        manager = WebKit2.WebsiteDataManager(
            base_data_directory=str(PROFILE_DIR),
            disk_cache_directory=str(CACHE_DIR),
        )
        context = WebKit2.WebContext(website_data_manager=manager)
        context.set_cache_model(WebKit2.CacheModel.WEB_BROWSER)
        self.webview = WebKit2.WebView.new_with_context(context)
        self.content_manager = self.webview.get_user_content_manager()
        stylesheet = WebKit2.UserStyleSheet.new(
            ".topbar { display: none !important; }",
            WebKit2.UserContentInjectedFrames.ALL_FRAMES,
            WebKit2.UserStyleLevel.USER,
            None,
            None,
        )
        self.content_manager.add_style_sheet(stylesheet)
        settings = self.webview.get_settings()
        for name, value in (
            ("enable-plugins", False),
            ("enable-developer-extras", False),
            ("javascript-can-open-windows-automatically", False),
            ("allow-file-access-from-file-urls", False),
            ("allow-universal-access-from-file-urls", False),
            ("enable-webgl", False),
            ("enable-media", False),
        ):
            try:
                settings.set_property(name, value)
            except (TypeError, AttributeError):
                pass
        self.webview.connect("decide-policy", self._decide_policy)
        self.webview.connect("create", self._deny_new_window)
        self.webview.connect("permission-request", self._deny_permission)
        self.webview.connect("run-file-chooser", self._run_file_chooser)
        self.webview.connect("load-changed", self._load_changed)
        self.webview.connect("load-failed", self._load_failed)
        context.connect("download-started", self._prepare_download)

        self.overlay = Gtk.Overlay()
        self.overlay.add(self.webview)
        self.error_card = self._make_error_card()
        self.error_card.set_halign(Gtk.Align.CENTER)
        self.error_card.set_valign(Gtk.Align.CENTER)
        self.error_card.set_no_show_all(True)
        self.overlay.add_overlay(self.error_card)
        self.root.pack_start(self.overlay, True, True, 0)

    def _make_error_card(self) -> Gtk.Widget:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.set_halign(Gtk.Align.CENTER)
        card.set_valign(Gtk.Align.CENTER)
        card.set_margin_start(28)
        card.set_margin_end(28)
        card.set_margin_top(26)
        card.set_margin_bottom(26)
        card.get_style_context().add_class("hub-error-card")
        mark = Gtk.Label(label="KH  /  LOCAL WORKSPACE")
        mark.get_style_context().add_class("hub-error-mark")
        heading = Gtk.Label(label="Your Hub is taking a moment.")
        heading.get_style_context().add_class("hub-error-heading")
        message = Gtk.Label(label="Khaos Hub is available only on this computer. Check that its local service is running, then try again.")
        message.set_line_wrap(True)
        message.set_max_width_chars(54)
        message.set_justify(Gtk.Justification.CENTER)
        message.get_style_context().add_class("hub-error-copy")
        retry = Gtk.Button(label="Retry connection")
        retry.get_style_context().add_class("hub-retry")
        retry.connect("clicked", lambda _button: self.webview.load_uri(APP_URL))
        card.pack_start(mark, False, False, 0)
        card.pack_start(heading, False, False, 0)
        card.pack_start(message, False, False, 0)
        card.pack_start(retry, False, False, 4)
        return card

    def _decide_policy(self, _view, decision, decision_type) -> bool:
        if decision_type != WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            return False
        nav = decision.get_navigation_action()
        request = decision.get_request()
        uri = request.get_uri() if request else ""
        if is_local_hub_uri(uri):
            decision.use()
            return True
        decision.ignore()
        if nav and nav.is_user_gesture() and self._is_safe_external_uri(uri):
            self._open_external(uri)
        return True

    @staticmethod
    def _is_safe_external_uri(uri: str) -> bool:
        try:
            parsed = urllib.parse.urlsplit(uri)
            host = (parsed.hostname or "").rstrip(".").lower()
            if parsed.scheme not in ("http", "https") or not host or parsed.username or parsed.password:
                return False
            if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
                return False
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                return "." in host
            return address.is_global
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _open_external(uri: str) -> None:
        # A deliberate click gets a separate, unrestricted desktop-browser scope.
        # WebKit itself remains denied all non-loopback IP traffic.
        unit = "khaos-hub-link-" + GLib.uuid_string_random().replace("-", "")[:12]
        try:
            subprocess.Popen(
                ["/usr/bin/systemd-run", "--user", "--scope", "--quiet", f"--unit={unit}", "--", "/usr/bin/xdg-open", uri],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True,
            )
        except OSError:
            pass

    @staticmethod
    def _deny_new_window(_view, _action):
        return None

    @staticmethod
    def _deny_permission(_view, request):
        request.deny()
        return True

    def _run_file_chooser(self, _view, request) -> bool:
        dialog = Gtk.FileChooserDialog(
            title="Import a Khaos Hub library backup",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Open", Gtk.ResponseType.ACCEPT)
        dialog.set_select_multiple(request.get_select_multiple())
        json_filter = Gtk.FileFilter()
        json_filter.set_name("JSON library backups")
        json_filter.add_mime_type("application/json")
        json_filter.add_pattern("*.json")
        dialog.add_filter(json_filter)
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            files = [Gio.File.new_for_path(path) for path in dialog.get_filenames()]
            if files:
                request.select_files(files)
            else:
                request.cancel()
        else:
            request.cancel()
        dialog.destroy()
        return True

    def _prepare_download(self, _context, download) -> None:
        download.connect("decide-destination", self._choose_download_destination)

    def _choose_download_destination(self, download, suggested_name: str) -> bool:
        downloads = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) or str(Path.home() / "Downloads")
        downloads_path = Path(downloads).expanduser()
        dialog = Gtk.FileChooserDialog(
            title="Save Khaos Hub library export",
            transient_for=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Save", Gtk.ResponseType.ACCEPT)
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name(Path(suggested_name).name or "khaos-hub-library.json")
        if downloads_path.is_dir():
            dialog.set_current_folder(str(downloads_path))
        json_filter = Gtk.FileFilter()
        json_filter.set_name("JSON library backups")
        json_filter.add_mime_type("application/json")
        json_filter.add_pattern("*.json")
        dialog.add_filter(json_filter)
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            destination = Path(dialog.get_filename()).expanduser().resolve()
            try:
                destination.relative_to(downloads_path.resolve())
            except ValueError:
                dialog.destroy()
                download.cancel()
                self._show_notice("For safety, save exports in Downloads, then move them if needed.")
                return True
            download.set_allow_overwrite(True)
            download.set_destination(Gio.File.new_for_path(str(destination)).get_uri())
            dialog.destroy()
            return True
        dialog.destroy()
        download.cancel()
        return True

    def _show_notice(self, message: str) -> None:
        notice = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Export not saved",
        )
        notice.format_secondary_text(message)
        notice.run()
        notice.destroy()

    def _load_changed(self, _view, event) -> None:
        if event == WebKit2.LoadEvent.STARTED:
            self.error_card.hide()
            self.connection_label.set_text("CONNECTING")
        elif event == WebKit2.LoadEvent.FINISHED:
            self.error_card.hide()
            self.connection_label.set_text("LOCAL SESSION")

    def _load_failed(self, _view, _event, failing_uri, _error) -> bool:
        if is_local_hub_uri(failing_uri):
            self.connection_label.set_text("OFFLINE")
            self.error_card.show_all()
            return True
        return False

    def _on_key_press(self, _window, event) -> bool:
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        key = event.keyval
        if ctrl and key in (Gdk.KEY_r, Gdk.KEY_R, Gdk.KEY_F5):
            self.webview.reload()
            return True
        if key == Gdk.KEY_F5:
            self.webview.reload()
            return True
        if ctrl and key in (Gdk.KEY_plus, Gdk.KEY_equal):
            self.webview.set_zoom_level(min(1.5, self.webview.get_zoom_level() + 0.1))
            return True
        if ctrl and key == Gdk.KEY_minus:
            self.webview.set_zoom_level(max(0.8, self.webview.get_zoom_level() - 0.1))
            return True
        if ctrl and key == Gdk.KEY_0:
            self.webview.set_zoom_level(1.0)
            return True
        return False


class KhaosHubApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.add_action(self._make_reload_action())

    def _make_reload_action(self):
        action = Gio.SimpleAction.new("reload", None)
        action.connect("activate", self._reload)
        return action

    def _reload(self, *_args) -> None:
        if self.window is not None:
            self.window.webview.reload()

    def do_activate(self) -> None:
        if self.window is None:
            self.window = HubWindow(self)
            provider = Gtk.CssProvider()
            provider.load_from_data(b"""
                .hub-topbar { background: linear-gradient(112deg, rgba(28,42,46,.96), rgba(13,20,24,.94)); color: #e2e9e5; border-bottom: 1px solid rgba(196,220,220,.18); box-shadow: inset 0 1px rgba(255,255,255,.08); }
                .hub-brand-mark { border-radius: 50%; padding: 1px; background: linear-gradient(145deg, rgba(196,220,220,.2), rgba(13,20,24,.82)); border: 1px solid rgba(196,220,220,.2); }
                .hub-title { color: #e7eee9; font-size: 13px; font-weight: 700; }
                .hub-subtitle { color: #9aa9a4; font-size: 10px; }
                .hub-status { color: #83d6b4; background: rgba(77,170,134,.12); border: 1px solid rgba(131,214,180,.24); border-radius: 12px; padding: 4px 9px; font-size: 9px; font-weight: 700; letter-spacing: .06em; }
                .hub-refresh { color: #dce5df; border-radius: 9px; }
                .hub-error-card { background: #171f24; border: 1px solid #405258; border-radius: 18px; padding: 28px; box-shadow: 0 18px 48px rgba(0,0,0,.38); }
                .hub-error-mark { color: #8dd7b6; font-size: 10px; font-weight: 700; letter-spacing: .14em; }
                .hub-error-heading { color: #e6ede8; font-size: 20px; font-weight: 700; }
                .hub-error-copy { color: #aebbb5; font-size: 12px; }
                .hub-retry { color: #e4eee7; background: #28433e; border: 1px solid #477064; border-radius: 12px; padding: 9px 16px; }
            """)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        self.window.present()


def main() -> int:
    for directory in (PROFILE_DIR, CACHE_DIR):
        prepare_private_dir(directory)
    application = KhaosHubApplication()
    return application.run(sys.argv[:1])


if __name__ == "__main__":
    raise SystemExit(main())
