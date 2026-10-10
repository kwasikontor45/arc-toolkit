#!/usr/bin/env python3
"""Presentation-only checks for the SOP terminal welcome and gate hint."""

import importlib.util
from importlib.machinery import SourceFileLoader
from io import StringIO
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_loader(
    "arc_sop", SourceFileLoader("arc_sop", str(ROOT / "bin/arc-sop"))
)
arc_sop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(arc_sop)


class SopBannerTests(unittest.TestCase):
    def test_compact_locked_banner_is_plain_and_actionable(self):
        stream = StringIO()
        with patch.object(arc_sop, "_circadian_phase", return_value=("choice", "#5ec8ed")):
            arc_sop.print_gate_banner(False, compact=True, stream=stream)
        output = stream.getvalue()
        self.assertIn(")(  )(  ARC", output)
        self.assertIn("SOP GATE: LOCKED", output)
        self.assertIn("Next: read > accept > begin", output)
        self.assertIn("CHOICE", output)
        self.assertNotIn("\033[", output)
        self.assertLessEqual(len(output.splitlines()), 5)

    def test_open_banner_keeps_all_seven_principles_and_source(self):
        stream = StringIO()
        with patch.object(arc_sop, "_circadian_phase", return_value=("nyx", "#ea9a97")):
            arc_sop.print_gate_banner(True, stream=stream)
        output = stream.getvalue()
        self.assertIn("SOP GATE: READY", output)
        self.assertIn("I WWSJD", output)
        self.assertIn("VII Inevitable", output)
        self.assertIn(str(arc_sop.MO_FILE), output)

    def test_reading_guide_keeps_full_paths_without_extra_clutter(self):
        stream = StringIO()
        arc_sop.print_reading_guide(stream=stream, reader_hint=False)
        output = stream.getvalue()
        for path in (arc_sop.INTEL_OPS / "GAMEPLAN.md", arc_sop.SOT_FILE, arc_sop.MO_FILE):
            self.assertIn(str(path), output)
        self.assertEqual(len(output.splitlines()), 4)


if __name__ == "__main__":
    unittest.main()
