#!/usr/bin/env python3
"""Focused regression checks for the local-only Arc word-of-day provider."""

import copy
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ARC = ROOT / "bin" / "arc"
CATALOG = ROOT / "config" / "word-of-day.json"
LOADER = importlib.machinery.SourceFileLoader("khaos_lab_test", str(ROOT / "bin" / "khaos-lab"))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
KHAOS_LAB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = KHAOS_LAB
SPEC.loader.exec_module(KHAOS_LAB)


class WordOfDayTests(unittest.TestCase):
    def run_arc(self, *args, data_file=CATALOG, day="2026-10-10"):
        env = os.environ.copy()
        env.update(ARC_WORD_DATA_FILE=str(data_file), ARC_WORD_DATE=day)
        return subprocess.run([str(ARC), "word", *args], env=env, cwd=ROOT,
                              text=True, capture_output=True, timeout=5)

    def test_anchor_date_is_the_requested_algid_entry(self):
        result = self.run_arc("--json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {
            "date": "2026-10-10", "word": "algid", "pronunciation": "al-jid",
            "part_of_speech": "adjective", "definition": "cold or chilly",
        })

    def test_next_day_is_deterministic_and_compact(self):
        first = self.run_arc("--json", day="2026-10-11")
        second = self.run_arc("--json", day="2026-10-11")
        compact = self.run_arc("--compact", day="2026-10-11")
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout)["word"], "lucid")
        self.assertEqual(compact.stdout.strip(), "lucid / loo-sid · adjective · clear and easy to understand")

    def test_bad_catalog_fails_silently_and_does_not_emit_markup(self):
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        poisoned = copy.deepcopy(data)
        poisoned["entries"][0]["definition"] = "safe\u001b[31munsafe"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "catalog.json"
            target.write_text(json.dumps(poisoned), encoding="utf-8")
            result = self.run_arc("--json", data_file=target)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_missing_catalog_degrades_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_arc("--compact", data_file=Path(tmp) / "missing.json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_unknown_options_are_rejected(self):
        result = self.run_arc("--execute")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_panel_payload_rejects_terminal_markup_and_unexpected_fields(self):
        safe = {"date": "2026-10-10", "word": "algid", "pronunciation": "al-jid",
                "part_of_speech": "adjective", "definition": "cold or chilly"}
        self.assertEqual(KHAOS_LAB.StatusView.parse_word_payload(json.dumps(safe)), safe)
        poisoned = {**safe, "word": "algid\u001b[31m"}
        self.assertIsNone(KHAOS_LAB.StatusView.parse_word_payload(json.dumps(poisoned)))
        extra = {**safe, "private": "must never be rendered"}
        self.assertIsNone(KHAOS_LAB.StatusView.parse_word_payload(json.dumps(extra)))
        self.assertIsNone(KHAOS_LAB.StatusView.parse_word_payload("x" * 513))


if __name__ == "__main__":
    unittest.main()
