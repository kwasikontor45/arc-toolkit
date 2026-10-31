"""Tests for arc-confirm — the single-action human confirmation gate."""
import io
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
import importlib.util
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_loader(
    "arc_confirm", SourceFileLoader("arc_confirm", str(ROOT / "bin/arc-confirm"))
)
arc_confirm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(arc_confirm)
arc_sop = arc_confirm.arc_sop

AGENT_VARS = ("CODEX_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_BRIDGE_SESSION_ID",
              "KIMI_SESSION_ID", "ARC_SESSION_ID", "AGENT_SESSION_ID", "AGENT_ID")


class ConfirmTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        sop_dir = Path(self.tmp.name) / "sop"
        self.db_patch = mock.patch.object(arc_sop, "DB_PATH", sop_dir / "arc-sop.db")
        self.dir_patch = mock.patch.object(arc_sop, "SOP_DIR", sop_dir)
        self.db_patch.start()
        self.dir_patch.start()
        self.env = mock.patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.exec_patch = mock.patch.object(arc_confirm.os, "execvp")
        self.mock_exec = self.exec_patch.start()

    def tearDown(self):
        self.exec_patch.stop()
        self.env.stop()
        self.dir_patch.stop()
        self.db_patch.stop()
        self.tmp.cleanup()

    def events(self):
        return arc_sop.db_query("SELECT * FROM confirm_events ORDER BY id")

    class FakeTty:
        """Test double with separate input and output buffers (a real tty's
        screen does not consume its keyboard)."""

        def __init__(self, keys: bytes):
            self._in = io.BytesIO(keys)
            self.out = io.BytesIO()

        def fileno(self):
            raise io.UnsupportedOperation

        def isatty(self):
            return True

        def read(self, n):
            return self._in.read(n)

        def readline(self):
            return self._in.readline()

        def tell(self):
            return self.out.tell()

        def seek(self, pos):
            return self.out.seek(pos)

        def write(self, data):
            return self.out.write(data)

        def close(self):
            pass

    def run_confirm(self, args, keys=b"1", tty_available=True):
        fake = self.FakeTty(keys)
        with mock.patch.object(arc_confirm, "open_tty",
                               return_value=fake if tty_available else None):
            rc = arc_confirm.main(args)
        return rc, fake

    def test_approve_once_execs_exact_command(self):
        rc, _ = self.run_confirm(["sync vault", "--", "rsync", "-a", "src/", "/mnt/storage/"], keys=b"1")
        self.assertEqual(rc, 0)
        self.mock_exec.assert_called_once_with("rsync", ["rsync", "-a", "src/", "/mnt/storage/"])
        self.assertEqual(self.events()[-1]["choice"], "once")

    def test_session_choice_binds_and_skips_prompt_later(self):
        rc, _ = self.run_confirm(["sync vault", "--", "rsync", "a", "b"], keys=b"2")
        self.assertEqual(rc, 0)
        self.assertEqual(self.events()[-1]["choice"], "session")

        def boom():
            raise AssertionError("prompt should not open for a session-approved action")

        with mock.patch.object(arc_confirm, "open_tty", side_effect=boom):
            rc = arc_confirm.main(["sync vault", "--", "rsync", "a", "b"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.events()[-1]["choice"], "pre-approved")

    def test_session_approval_does_not_cover_other_actions(self):
        rc, _ = self.run_confirm(["sync vault", "--", "rsync", "a", "b"], keys=b"2")
        self.assertEqual(rc, 0)
        rc, _ = self.run_confirm(["wipe vault", "--", "rm", "-rf", "x"], keys=b"n")
        self.assertEqual(rc, 1)
        self.assertEqual(self.events()[-1]["choice"], "reject")

    def test_reject_keys_and_unknown_key_fail_closed(self):
        for keys in (b"n", b"3", b"\x1b", b"x", b""):
            rc, _ = self.run_confirm(["act", "--", "true"], keys=keys)
            self.assertEqual(rc, 1, f"keys={keys!r}")
            self.assertFalse(self.mock_exec.called)
            self.mock_exec.reset_mock()

    def test_no_tty_refuses_and_logs(self):
        rc, _ = self.run_confirm(["act", "--", "true"], tty_available=False)
        self.assertEqual(rc, 2)
        self.assertFalse(self.mock_exec.called)
        self.assertEqual(self.events()[-1]["choice"], "refused-no-tty")

    def test_agent_is_refused_interactive_approval(self):
        with mock.patch.dict(os.environ, {"CODEX_SESSION_ID": "codex-123"}, clear=True):
            rc, _ = self.run_confirm(["act", "--", "true"])
        self.assertEqual(rc, 2)
        self.assertFalse(self.mock_exec.called)
        self.assertEqual(self.events()[-1]["choice"], "refused-agent")

    def test_reject_with_note_sanitizes_and_logs(self):
        rc, _ = self.run_confirm(["act", "--", "true"], keys=b"4" + b"not tonight \x01\x02ok\n")
        self.assertEqual(rc, 1)
        row = self.events()[-1]
        self.assertEqual(row["choice"], "reject-feedback")
        self.assertEqual(row["note"], "not tonight ok")

    def test_clear_drops_only_this_sessions_approvals(self):
        self.run_confirm(["act", "--", "true"], keys=b"2")
        self.assertTrue(arc_confirm.approval_exists(arc_sop.session_id(), arc_confirm._caller_script(), "act"))
        rc = arc_confirm.main(["--clear"])
        self.assertEqual(rc, 0)
        self.assertFalse(arc_confirm.approval_exists(arc_sop.session_id(), arc_confirm._caller_script(), "act"))

    def test_malformed_invocation_fails(self):
        self.assertEqual(arc_confirm.main([]), 2)
        self.assertEqual(arc_confirm.main(["no separator here"]), 2)
        self.assertEqual(arc_confirm.main(["act", "--"]), 2)

    def test_sanitize_strips_escapes_and_caps(self):
        self.assertEqual(arc_confirm._sanitize("rm \x1b[1m~/x", 80), "rm 1m~/x")
        self.assertEqual(arc_confirm._sanitize("a" * 200, 80), "a" * 80)


if __name__ == "__main__":
    unittest.main()
