#!/usr/bin/env python3
"""Regression checks for the compact interactive SOP acceptance flow."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from importlib.machinery import SourceFileLoader
import importlib.util
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_loader(
    "arc_sop", SourceFileLoader("arc_sop", str(ROOT / "bin/arc-sop"))
)
arc_sop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(arc_sop)


class TtyStringIO(StringIO):
    def isatty(self):
        return True


class SopInteractiveAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sop_dir = self.root / "sop"
        self.intel = self.root / "intel-ops"
        self.intel.mkdir()
        self.gameplan = self.intel / "GAMEPLAN.md"
        self.sot = self.intel / "SOT.md"
        self.mo = self.intel / "MO.md"
        self.gameplan.write_text("# history\n", encoding="utf-8")
        self.sot.write_text("# current SOT\n", encoding="utf-8")
        self.mo.write_text("\n".join(
            f"**{roman}. Principle {index}**\nBody {index}."
            for index, roman in enumerate(("I", "II", "III", "IV", "V", "VI", "VII"), 1)
        ), encoding="utf-8")
        self.patches = [
            patch.object(arc_sop, "SOP_DIR", self.sop_dir),
            patch.object(arc_sop, "DB_PATH", self.sop_dir / "test.db"),
            patch.object(arc_sop, "INTEL_OPS", self.intel),
            patch.object(arc_sop, "SOT_FILE", self.sot),
            patch.object(arc_sop, "MO_FILE", self.mo),
            patch.object(arc_sop, "agent_id", return_value="codex"),
            patch.object(arc_sop, "session_id", return_value="test-session"),
            patch.object(arc_sop, "_notify"),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def rows(self, query):
        conn = sqlite3.connect(self.sop_dir / "test.db")
        try:
            return conn.execute(query).fetchall()
        finally:
            conn.close()

    def run_start(self, inputs, tty=True, digest=""):
        output = TtyStringIO() if tty else StringIO()
        stdin = TtyStringIO() if tty else StringIO()
        with patch("sys.stdin", stdin), redirect_stdout(output), \
             patch("builtins.input", side_effect=inputs), \
             patch.object(arc_sop.shutil, "which", return_value=None):
            result = arc_sop.cmd_start("test task", digest)
        return result, output.getvalue()

    def test_y_without_review_does_not_unlock(self):
        result, output = self.run_start(["y", "n"])
        self.assertEqual(result, 2)
        self.assertIn("Read the current packet first", output)
        self.assertEqual(self.rows("SELECT * FROM acks"), [])
        self.assertFalse("[STARTING]" in self.gameplan.read_text())

    def test_n_denies_without_logging(self):
        result, output = self.run_start(["n"])
        self.assertEqual(result, 2)
        self.assertIn("declined", output)
        self.assertEqual(self.rows("SELECT * FROM acks"), [])
        events = self.rows("SELECT event FROM policy_events")
        self.assertEqual(events, [("denied",)])

    def test_read_then_y_accepts_and_logs_exact_sources(self):
        result, output = self.run_start(["r", "", "", "", "y"])
        self.assertEqual(result, 0)
        self.assertEqual(len(self.rows("SELECT * FROM acks")), 1)
        reads = self.rows("SELECT source_path, source_sha256, event FROM policy_events WHERE event='read'")
        self.assertEqual(len(reads), 3)
        self.assertEqual({row[0] for row in reads}, {str(self.gameplan), str(self.sot), str(self.mo)})
        self.assertTrue(all(row[2] == "read" for row in reads))
        self.assertEqual(self.rows("SELECT event FROM policy_events WHERE event='accepted'"), [("accepted",)])
        self.assertIn("ready for today's work", output)
        self.assertIn("[STARTING] test task", self.gameplan.read_text())

    def test_policy_change_during_read_fails_closed(self):
        first_choice = iter(["r"])

        def answer(prompt=""):
            if prompt.startswith("[enter]"):
                self.sot.write_text("# changed while review was open\n", encoding="utf-8")
                return ""
            return next(first_choice)

        result, output = self.run_start(answer)
        self.assertEqual(result, 2)
        self.assertIn("Policy changed during review", output)
        self.assertEqual(self.rows("SELECT * FROM acks"), [])
        self.assertEqual(self.rows("SELECT * FROM policy_events"), [])
        self.assertNotIn("[STARTING]", self.gameplan.read_text())

    def test_non_tty_shows_live_fingerprint_and_exact_fingerprint_is_not_claimed_as_read(self):
        result, output = self.run_start([], tty=False)
        self.assertEqual(result, 2)
        self.assertIn(f"SOP_FINGERPRINT={arc_sop._policy_digest()}", output)
        result, output = self.run_start([], tty=False, digest=arc_sop._policy_digest())
        self.assertEqual(result, 0)
        self.assertIn("accepted current policy fingerprint", output)
        self.assertEqual(self.rows("SELECT event FROM policy_events"), [("accepted",)])

    def test_interactive_tty_does_not_accept_pasted_fingerprint(self):
        digest = arc_sop._policy_digest()
        result, output = self.run_start(["r", "", "", "", "y"], tty=True, digest=digest)
        self.assertEqual(result, 0)
        self.assertIn("reviewed and accepted", output)
        self.assertEqual(len(self.rows("SELECT * FROM policy_events WHERE event='read'")), 3)


if __name__ == "__main__":
    unittest.main()
