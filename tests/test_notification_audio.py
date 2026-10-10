import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bin'))
import _arc_pine_common as pine


class NotificationAudio(unittest.TestCase):
    def test_restore_runs_even_when_speech_fails(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(pine, 'DATA_DIR', Path(directory)), \
             patch.object(pine, '_wake_sink', return_value=True), \
             patch.object(pine, '_duck_other_streams', return_value=[10, 11]), \
             patch.object(pine, 'speak', side_effect=RuntimeError('test failure')), \
             patch.object(pine, '_restore_ducked') as restore:
            with self.assertRaises(RuntimeError):
                pine.emit_audio(None, 'test')
            restore.assert_called_once_with([10, 11])

    def test_processor_and_previously_muted_streams_are_left_alone(self):
        import json
        streams = [
            {'index': 1, 'mute': False, 'properties': {'application.name': 'Music'}},
            {'index': 2, 'mute': True, 'properties': {'application.name': 'Muted app'}},
            {'index': 3, 'mute': False, 'properties': {'application.id': 'com.github.wwmm.easyeffects'}},
            {'index': 4, 'mute': False, 'properties': {'application.name': 'ArcPine'}},
            {'index': 5, 'mute': False, 'properties': {'node.name': 'effect_output.speaker_studio_eq'}},
        ]
        from types import SimpleNamespace
        with patch.object(pine.subprocess, 'run', return_value=SimpleNamespace(stdout=json.dumps(streams), returncode=0)) as run:
            self.assertEqual(pine._duck_other_streams(), [1])
            self.assertEqual(run.call_args_list[-1].args[0], ['pactl', 'set-sink-input-mute', '1', '1'])
            self.assertEqual(run.call_count, 2)

    def test_upgraded_orage_identity_inherits_but_explicit_override_wins(self):
        cfg = {'app_rules': {'orage': {'speak': True}}}
        self.assertTrue(pine.should_speak(cfg, 'Orage'))
        cfg['app_rules']['Orage'] = {'speak': False}
        self.assertFalse(pine.should_speak(cfg, 'Orage'))


if __name__ == '__main__':
    unittest.main()
