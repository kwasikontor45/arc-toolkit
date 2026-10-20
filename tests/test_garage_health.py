import importlib.machinery
import importlib.util
import json
import shlex
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "apps/surgery-workshop/garage-health.py"
loader = importlib.machinery.SourceFileLoader("garage_health_under_test", str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
garage_health = importlib.util.module_from_spec(spec)
loader.exec_module(garage_health)

PANEL_SOURCE = SOURCE.parents[2] / "bin/khaos-lab"
panel_loader = importlib.machinery.SourceFileLoader("khaos_lab_under_test", str(PANEL_SOURCE))
panel_spec = importlib.util.spec_from_loader(panel_loader.name, panel_loader)
khaos_panel = importlib.util.module_from_spec(panel_spec)
panel_loader.exec_module(khaos_panel)


class GarageHealthReportChecks(unittest.TestCase):
    def test_circadian_boundaries_use_project_canonical_phases(self):
        self.assertEqual(garage_health.circadian_phase(5), ("Nyx", "#ea9a97"))
        self.assertEqual(garage_health.circadian_phase(6), ("Choice", "#5ec8ed"))
        self.assertEqual(garage_health.circadian_phase(11), ("Desire", "#f6c177"))
        self.assertEqual(garage_health.circadian_phase(17), ("Still-Pine", "#c4a7e7"))
        self.assertEqual(garage_health.circadian_phase(21), ("Nyx", "#ea9a97"))

    def write_report(self, path, generated_at=None, findings=None, extra=None):
        report = {
            "schema_version": 1,
            "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
            "counts": {"ok": 1, "healed": 1, "flag": 1},
            "findings": findings or [
                {"component": "watcher:arc-pined", "state": "flag"},
                {"component": "vpn", "state": "healed"},
                {"component": "fail2ban", "state": "ok"},
            ],
        }
        if extra:
            report.update(extra)
        path.write_text(json.dumps(report), encoding="utf-8")
        path.chmod(0o600)

    def test_reads_only_normalized_sanitized_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            self.write_report(path, extra={"raw_message": "secret detail must not reach the UI"})
            result = garage_health.read_report(path)
        self.assertEqual(result["counts"], {"ok": 1, "healed": 1, "flag": 1})
        self.assertEqual(result["findings"][0], {"component": "watcher:arc-pined", "state": "flag"})
        self.assertNotIn("raw_message", result)
        self.assertNotIn("generated_at", result["findings"][0])

    def test_marks_old_snapshot_stale(self):
        then = datetime.now(timezone.utc) - timedelta(hours=7)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            self.write_report(path, generated_at=then.isoformat())
            result = garage_health.read_report(path)
        self.assertTrue(result["stale"])

    def test_legacy_arc_heal_report_is_reduced_to_state_and_component(self):
        sample = (
            "# arc-heal — 20261020T120000Z\n"
            "Run took 12s · 1 ok · 0 healed · 1 flagged\n"
            "- 🚩 **vpn** — desired state is connected; sensitive detail omitted\n"
            "- ✅ **fail2ban** — active\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latest-status.md"
            path.write_text(sample, encoding="utf-8")
            result = garage_health.read_legacy_report(path)
        self.assertEqual(result["counts"], {"ok": 1, "healed": 0, "flag": 1})
        self.assertEqual(result["findings"], [
            {"component": "vpn", "state": "flag"},
            {"component": "fail2ban", "state": "ok"},
        ])

    def test_rejects_unsafe_mode_bad_state_and_oversized_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            self.write_report(path)
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "permissions"):
                garage_health.read_report(path)

            self.write_report(path, findings=[{"component": "vpn", "state": "run-command"}])
            with self.assertRaisesRegex(ValueError, "state"):
                garage_health.read_report(path)

            self.write_report(path, findings=[{"component": "x", "state": "ok"}] * 101)
            with self.assertRaisesRegex(ValueError, "finding list"):
                garage_health.read_report(path)

    def test_rejects_symlink_and_malformed_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.json"
            link = root / "link.json"
            self.write_report(target)
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "regular file"):
                garage_health.read_report(link)

            self.write_report(target, generated_at="not-a-time")
            with self.assertRaises(ValueError):
                garage_health.read_report(target)

    def test_arc_heal_writer_emits_private_sanitized_contract(self):
        source = (SOURCE.parents[2] / "bin/arc-heal").read_text(encoding="utf-8")
        start = source.index("_write_garage_report() {")
        end = source.index("\n}\n", start) + 3
        writer = source[start:end]
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "garage-health.json"
            prefix = (
                "FINDINGS=('FLAG::vpn::private IP 203.0.113.8 and token-value' "
                "'OK::fail2ban::active')\n"
                "OK=1\nHEALED=0\nFLAGGED=1\n"
                f"GARAGE_REPORT={shlex.quote(str(report_path))}\n"
            )
            subprocess.run(["bash"], input=prefix + writer + "\n_write_garage_report\n",
                           text=True, capture_output=True, check=True)
            payload_text = report_path.read_text(encoding="utf-8")
            payload = json.loads(payload_text)
            self.assertEqual(stat_mode(report_path), 0o600)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual([x["component"] for x in payload["findings"]], ["vpn", "fail2ban"])
        self.assertNotIn("203.0.113.8", payload_text)
        self.assertNotIn("token-value", payload_text)


class GarageWorkspaceChecks(unittest.TestCase):
    def test_catalog_sanitizes_labels_and_excludes_unregistered_paths(self):
        view = object.__new__(khaos_panel.GarageView)
        rows = view._catalog([
            {"id": "repo.kontor-studio", "kind": "repo", "name": "Kontor\nStudio",
             "status": "active", "observed": "up", "health": "ok", "detail": "private"},
            {"id": "../outside", "kind": "repo", "name": "escape", "observed": "up"},
            {"id": "random.service", "kind": "service", "name": "unexpected", "observed": "up"},
            {"id": "svc.khaos-hub", "kind": "service", "name": "Hub", "observed": "up"},
        ])
        self.assertEqual({row["id"] for row in rows}, {"repo.kontor-studio", "svc.khaos-hub"})
        project = next(row for row in rows if row["id"] == "repo.kontor-studio")
        self.assertEqual(project["name"], "Kontor Studio")
        self.assertNotIn("detail", project)

    def test_local_home_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "khaos-lab"
            inside = root / "project"
            outside = Path(directory) / "outside"
            inside.mkdir(parents=True)
            outside.mkdir()
            escape = root / "escape"
            escape.symlink_to(outside, target_is_directory=True)
            with mock.patch.object(khaos_panel, "KHAOS_ROOT", root), mock.patch.object(
                    khaos_panel, "GARAGE_LOCAL_HOMES",
                    {"safe": inside, "escape": escape}):
                view = object.__new__(khaos_panel.GarageView)
                self.assertEqual(view._localHome("safe"), inside.resolve())
                self.assertIsNone(view._localHome("escape"))
                self.assertIsNone(view._localHome("not-allowlisted"))

    def test_bad_json_report_does_not_fall_back_to_older_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "garage-health.json"
            legacy_path = root / "latest-status.md"
            json_path.write_text("{invalid", encoding="utf-8")
            json_path.chmod(0o600)
            legacy_path.write_text(
                "# arc-heal — 20261020T120000Z\n- 🚩 **vpn** — stale prior state\n",
                encoding="utf-8")
            with mock.patch.object(khaos_panel, "GARAGE_HEALTH_REPORT_PATH", json_path), mock.patch.object(
                    khaos_panel, "HEAL_LOG_PATH", legacy_path):
                result = khaos_panel.garageHealthSummary()
        self.assertFalse(result["available"])
        self.assertEqual(result["summary"], "report unavailable")

    def test_missing_json_report_uses_sanitized_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_path = root / "latest-status.md"
            legacy_path.write_text(
                "# arc-heal — 20261020T120000Z\n- 🚩 **vpn** — sensitive details omitted\n",
                encoding="utf-8")
            with mock.patch.object(khaos_panel, "GARAGE_HEALTH_REPORT_PATH", root / "missing.json"), mock.patch.object(
                    khaos_panel, "HEAL_LOG_PATH", legacy_path):
                result = khaos_panel.garageHealthSummary()
        self.assertTrue(result["available"])
        self.assertIn("1 attention", result["summary"])
        self.assertNotIn("sensitive", result["summary"])

    def test_catalog_paginates_in_bounded_batches(self):
        view = object.__new__(khaos_panel.GarageView)
        view.visibleLimit = view.MAX_INITIAL
        with mock.patch.object(view, "renderItems") as render_items:
            view._showMore()
        self.assertEqual(view.visibleLimit, view.MAX_INITIAL + view.PAGE_SIZE)
        render_items.assert_called_once_with()

    def test_resource_summary_calls_out_stale_scan_without_using_color_as_only_cue(self):
        stale, color, freshness = khaos_panel.GarageView.resourceStatus(0, 0, 0, 120)
        self.assertIn("stale", stale)
        self.assertIn("0 drift", stale)
        self.assertEqual(color, khaos_panel.GOLD)
        self.assertIn("last scan", freshness)

        current, color, _freshness = khaos_panel.GarageView.resourceStatus(1, 0, 0, 30)
        self.assertIn("1 drift", current)
        self.assertEqual(color, khaos_panel.ROSE)

        unknown, color, freshness = khaos_panel.GarageView.resourceStatus(0, 0, 0, None)
        self.assertIn("stale", unknown)
        self.assertEqual(freshness, "scan age unavailable")
        self.assertEqual(color, khaos_panel.GOLD)


def stat_mode(path):
    return path.stat().st_mode & 0o777


if __name__ == "__main__":
    unittest.main()
