import base64
import hashlib
import importlib.machinery
import importlib.util
import io
import re
import unittest
from pathlib import Path


def load_script(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class GarageRouteChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.hub = load_script("garage_hub_under_test", cls.root / "bin/khaos-hub")
        cls.app = cls.root / "apps/surgery-workshop/garage.html"
        cls.body = cls.app.read_text()

    def test_garage_is_one_offline_file_with_a_narrow_route(self):
        assets = self.hub.static_assets()
        expected = {"/garage", "/garage/", "/garage/index.html"}
        self.assertEqual(assets.keys() & expected, expected)
        self.assertEqual({p for p in assets if p.startswith("/garage")}, expected)
        self.assertTrue(all(assets[p][0] / assets[p][1] == self.app for p in expected))
        self.assertTrue(all(assets[p][2] == "text/html; charset=utf-8" for p in expected))

        for tag in ("style", "script"):
            inline = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", self.body, re.S).group(1)
            digest = base64.b64encode(hashlib.sha256(inline.encode()).digest()).decode()
            self.assertIn(f"sha256-{digest}", self.body)

        for unsafe in ("fetch(", "XMLHttpRequest", "WebSocket(", "localStorage", "sessionStorage", "eval("):
            self.assertNotIn(unsafe, self.body)
        for remote in ("http://", "https://", "<iframe", "<link"):
            self.assertNotIn(remote, self.body)
        self.assertIn("img-src data:", self.body)
        self.assertEqual(self.body.count("<img "), 3)
        self.assertIn("data:image/png;base64,", self.body)
        self.assertIn("data:image/jpeg;base64,", self.body)
        wallpaper = self.root / "apps/khaos-hub/web/kimi-wallpaper.jpg"
        self.assertIn(base64.b64encode(wallpaper.read_bytes()).decode(), self.body)
        self.assertIn("connect-src 'none'", self.body)
        self.assertIn("default-src 'none'", self.body)
        # Browsers ignore frame-ancestors in a CSP meta element; enforce it on the response.
        self.assertNotIn("frame-ancestors", self.body)
        self.assertIn("no host access", self.body)
        for context in ("Calendar looks stale", "A task was checked", "A status tile looks wrong"):
            self.assertIn(context, self.body)

    def test_horizon_asset_is_shared_by_explicit_routes(self):
        assets = self.hub.static_assets()
        expected = self.root / "apps/surgery-workshop/horizon-dusk.jpg"
        self.assertEqual(assets["/horizon-dusk.jpg"][0] / assets["/horizon-dusk.jpg"][1], expected)
        self.assertTrue(expected.is_file())
        encoded = base64.b64encode(expected.read_bytes()).decode()
        self.assertIn("data:image/jpeg;base64," + encoded, self.body)

    def test_hub_response_policy_is_hash_scoped_and_sources_are_not_served(self):
        handler = object.__new__(self.hub.Handler)
        handler.path = "/garage/"
        handler.wfile = io.BytesIO()
        headers = {}
        handler.send_response = lambda status: headers.setdefault("status", status)
        handler.send_header = lambda name, value: headers.__setitem__(name, value)
        handler.end_headers = lambda: None
        handler.reply(200, self.app.read_bytes(), "text/html; charset=utf-8")

        self.assertEqual(headers["status"], 200)
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertIn("img-src data:", headers["Content-Security-Policy"])
        self.assertIn("connect-src 'none'", headers["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        for tag in ("style", "script"):
            inline = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", self.body, re.S).group(1)
            digest = base64.b64encode(hashlib.sha256(inline.encode()).digest()).decode()
            self.assertIn(f"sha256-{digest}", headers["Content-Security-Policy"])

        assets = self.hub.static_assets()
        for private_or_old in ("/garage/source/hub-html", "/garage/app.js", "/garage/app.css", "/garage/icon.svg"):
            self.assertNotIn(private_or_old, assets)


if __name__ == "__main__":
    unittest.main()
