import ast
import math
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'apps/arc-break-taskbar/arc_break_taskbar.py'
source = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
restore_node = next(node for node in source.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'restore_timer')
test_module = ast.Module(body=[restore_node], type_ignores=[])
namespace = {'math': math}
exec(compile(test_module, str(path), 'exec'), namespace)
restore_timer = namespace['restore_timer']


class TimerRecovery(unittest.TestCase):
    def test_new_boot_picks_up_remaining_instead_of_counting_offline_time(self):
        state = {'phase': 'focus', 'deadline': 900, 'remaining': 123, 'boot_id': 'old'}
        self.assertEqual(restore_timer(state, 40, 18, 1000, 'new'), ('focus', 1123, 0))

    def test_explicit_stop_does_not_resume(self):
        self.assertEqual(restore_timer({'phase': 'stopped'}, 40, 18, 1000, 'new'), ('stopped', 0, 0))

    def test_paused_timer_stays_paused(self):
        state = {'phase': 'break', 'paused_left': 42, 'boot_id': 'old'}
        self.assertEqual(restore_timer(state, 40, 18, 1000, 'new'), ('break', 0, 42))

    def test_same_boot_restart_keeps_deadline(self):
        state = {'phase': 'focus', 'deadline': 1100, 'remaining': 130, 'boot_id': 'same'}
        self.assertEqual(restore_timer(state, 40, 18, 1000, 'same'), ('focus', 1100, 0))

    def test_expired_active_state_does_not_turn_off(self):
        state = {'phase': 'focus', 'deadline': 900, 'remaining': 1, 'boot_id': 'same'}
        self.assertEqual(restore_timer(state, 40, 18, 1000, 'same'), ('break', 2080, 0))

    def test_invalid_state_does_not_start_a_timer(self):
        state = {'phase': 'focus', 'deadline': float('nan')}
        self.assertEqual(restore_timer(state, 40, 18, 1000, 'same'), ('stopped', 0, 0))


if __name__ == '__main__':
    unittest.main()
