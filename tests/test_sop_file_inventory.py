"""Regression tests for SOP baseline file selection."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import importlib.util
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_loader(
    "arc_sop", SourceFileLoader("arc_sop", str(ROOT / "bin/arc-sop"))
)
arc_sop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(arc_sop)


class SopFileInventoryTests(unittest.TestCase):
    def test_excludes_volatile_state_but_keeps_policy_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "GAMEPLAN.md").write_text("plan", encoding="utf-8")
            (root / ".source-workbench").mkdir()
            (root / ".source-workbench" / "workbench.sqlite3").write_bytes(b"db")
            (root / "inventory").mkdir()
            (root / "inventory" / "ledger.jsonl").write_text("entry", encoding="utf-8")
            (root / "notes").mkdir()
            (root / "notes" / "review.md").write_text("review", encoding="utf-8")
            with patch.object(arc_sop, "INTEL_OPS", root):
                found = {str(rel) for rel, _path in arc_sop.sop_files()}
        self.assertEqual(found, {"GAMEPLAN.md", "notes/review.md"})

    def test_exclude_is_subtree_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes").mkdir()
            (root / "notes" / ".source-workbench.md").write_text("policy", encoding="utf-8")
            with patch.object(arc_sop, "INTEL_OPS", root):
                found = {str(rel) for rel, _path in arc_sop.sop_files()}
        self.assertEqual(found, {"notes/.source-workbench.md"})


if __name__ == "__main__":
    unittest.main()
