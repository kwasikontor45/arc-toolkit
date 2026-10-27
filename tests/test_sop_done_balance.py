#!/usr/bin/env python3
"""Regression tests for GAMEPLAN STARTING/DONE heading recognition."""

from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
import importlib.util
from importlib.machinery import SourceFileLoader
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_loader(
    "arc_sop", SourceFileLoader("arc_sop", str(ROOT / "bin/arc-sop"))
)
arc_sop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(arc_sop)


class SopDoneBalanceTests(unittest.TestCase):
    def run_balance(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            intel_ops = Path(tmp)
            (intel_ops / "GAMEPLAN.md").write_text(text, encoding="utf-8")
            output = StringIO()
            with patch.object(arc_sop, "INTEL_OPS", intel_ops), redirect_stdout(output):
                result = arc_sop.cmd_done_balance()
            return result, output.getvalue()

    def test_accepts_legacy_and_descriptive_done_headers(self):
        today = datetime.now().strftime("%Y-%m-%d")
        text = (
            f"## {today} · codex · [STARTING] One\n"
            f"## {today} · codex · [DONE] One\n"
            f"## {today} · codex · [STARTING] Two\n"
            f"## {today} · codex · [DONE · Two]\n"
        )
        result, output = self.run_balance(text)
        self.assertTrue(result)
        self.assertIn("(2/2)", output)

    def test_body_mentions_do_not_count_as_done_entries(self):
        today = datetime.now().strftime("%Y-%m-%d")
        text = (
            f"## {today} · codex · [STARTING] One\n"
            "- Example expected heading: [DONE · One]\n"
        )
        result, output = self.run_balance(text)
        self.assertFalse(result)
        self.assertIn("1 more STARTING than DONE records", output)
        self.assertIn("context only; counts are not paired by task ID", output)

    def test_ignores_other_days(self):
        result, output = self.run_balance(
            "## 2026-01-01 · codex · [STARTING] Old\n"
            "## 2026-01-01 · codex · [DONE · Old]\n"
        )
        self.assertTrue(result)
        self.assertIn("(0/0)", output)


if __name__ == "__main__":
    unittest.main()
