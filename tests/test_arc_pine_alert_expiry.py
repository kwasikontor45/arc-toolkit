import importlib.machinery
import importlib.util
import pathlib
import time
import unittest


class ExpiringAlertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = pathlib.Path(__file__).resolve().parents[1] / "bin" / "arc-pine-bubbles"
        loader = importlib.machinery.SourceFileLoader("arc_pine_bubbles_expiry_test", str(path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        cls.module = importlib.util.module_from_spec(spec)
        loader.exec_module(cls.module)

    def manager(self):
        manager = object.__new__(self.module.BubbleManager)
        manager.cfg = {"bubble_max_visible": 1}
        manager.active = []
        manager.by_app = {}
        manager.pending = []
        return manager

    def test_expired_alert_is_rejected_on_arrival(self):
        manager = self.manager()
        manager.push("critical", "arc-heal", "old health check", "details", time.time() - 1)
        self.assertEqual(manager.pending, [])

    def test_expired_alert_is_discarded_when_queue_drains(self):
        manager = self.manager()
        manager.pending.append(("critical", "arc-heal", "old health check", "details", time.time() - 1))
        manager._drain()
        self.assertEqual(manager.pending, [])
        self.assertEqual(manager.active, [])


if __name__ == "__main__":
    unittest.main()
