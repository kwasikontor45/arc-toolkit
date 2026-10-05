import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'apps/arc-break-taskbar/arc_break_taskbar.py'
spec = importlib.util.spec_from_file_location('timer_under_test', path)
timer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timer)


class TimerRecovery(unittest.TestCase):
    def test_new_boot_picks_up_remaining_instead_of_counting_offline_time(self):
        state = {'phase': 'focus', 'deadline': 900, 'remaining': 123, 'boot_id': 'old'}
        self.assertEqual(timer.restore_timer(state, 40, 18, 1000, 'new'), ('focus', 1123, 0))

    def test_explicit_stop_does_not_resume(self):
        self.assertEqual(timer.restore_timer({'phase': 'stopped'}, 40, 18, 1000, 'new'), ('stopped', 0, 0))

    def test_paused_timer_stays_paused(self):
        state = {'phase': 'break', 'paused_left': 42, 'boot_id': 'old'}
        self.assertEqual(timer.restore_timer(state, 40, 18, 1000, 'new'), ('break', 0, 42))

    def test_same_boot_restart_keeps_deadline(self):
        state = {'phase': 'focus', 'deadline': 1100, 'remaining': 130, 'boot_id': 'same'}
        self.assertEqual(timer.restore_timer(state, 40, 18, 1000, 'same'), ('focus', 1100, 0))

    def test_expired_active_state_does_not_turn_off(self):
        state = {'phase': 'focus', 'deadline': 900, 'remaining': 1, 'boot_id': 'same'}
        self.assertEqual(timer.restore_timer(state, 40, 18, 1000, 'same'), ('break', 2080, 0))

    def test_invalid_state_does_not_start_a_timer(self):
        state = {'phase': 'focus', 'deadline': float('nan')}
        self.assertEqual(timer.restore_timer(state, 40, 18, 1000, 'same'), ('stopped', 0, 0))


if __name__ == '__main__':
    unittest.main()
