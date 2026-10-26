import importlib.util
import importlib.machinery
import signal
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bin'))
import _arc_pine_common as pine

_pined_path = Path(__file__).resolve().parents[1] / 'bin' / 'arc-pined'
_pined_loader = importlib.machinery.SourceFileLoader('arc_pined_test', str(_pined_path))
_pined_spec = importlib.util.spec_from_loader(_pined_loader.name, _pined_loader)
pined = importlib.util.module_from_spec(_pined_spec)
_pined_loader.exec_module(pined)


class NotificationAudio(unittest.TestCase):
    def test_reused_pid_is_treated_as_stale_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            pid_path = data_dir / 'arc-pined.pid'
            pid_path.write_text('2230')
            with patch.object(pined, 'DATA_DIR', data_dir), \
                 patch.object(pined, 'PID_PATH', pid_path), \
                 patch.object(pined.os, 'kill'), \
                 patch.object(pined, '_pid_belongs_to_arc_pined', return_value=False):
                pined._refuse_if_already_running()
            self.assertEqual(pid_path.read_text(), str(pined.os.getpid()))

    def test_live_arc_pined_pid_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            pid_path = data_dir / 'arc-pined.pid'
            pid_path.write_text('2230')
            with patch.object(pined, 'DATA_DIR', data_dir), \
                 patch.object(pined, 'PID_PATH', pid_path), \
                 patch.object(pined.os, 'kill'), \
                 patch.object(pined, '_pid_belongs_to_arc_pined', return_value=True):
                with self.assertRaises(SystemExit):
                    pined._refuse_if_already_running()
            self.assertEqual(pid_path.read_text(), '2230')

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

    def test_failed_mute_is_not_registered_for_restore(self):
        import json
        from types import SimpleNamespace
        streams = [{'index': 9, 'mute': False, 'properties': {'application.name': 'Music'}}]
        responses = [
            SimpleNamespace(stdout=json.dumps(streams), returncode=0),
            SimpleNamespace(stdout='', returncode=1),
        ]
        with patch.object(pine.subprocess, 'run', side_effect=responses):
            self.assertEqual(pine._duck_other_streams(), [])

    def test_shutdown_waits_for_audio_worker_and_retries_restore(self):
        finished = threading.Event()
        worker = threading.Thread(target=lambda: (time.sleep(0.03), finished.set()))
        worker.start()
        with patch.object(pine, '_AUDIO_THREADS', {worker}), \
             patch.object(pine, '_ACTIVE_DUCKED', {12}), \
             patch.object(pine, '_restore_ducked') as restore, \
             patch.object(pine.signal, 'signal') as set_signal, \
             patch.object(pine.os, 'kill') as kill, \
             patch.dict(pine._AUDIO_SHUTDOWN_HANDLERS, {signal.SIGTERM: signal.SIG_DFL}, clear=True):
            pine._audio_shutdown_handler(signal.SIGTERM, None)
        self.assertTrue(finished.is_set())
        restore.assert_called_once_with((12,))
        set_signal.assert_called_once_with(signal.SIGTERM, signal.SIG_DFL)
        kill.assert_called_once_with(pine.os.getpid(), signal.SIGTERM)

    def test_async_audio_installs_shutdown_guard_and_tracks_worker(self):
        with patch.object(pine, 'install_audio_shutdown_guard') as install, \
             patch.object(pine, 'emit_audio') as emit:
            worker = pine.emit_audio_async(None, 'test speech')
            worker.join(timeout=1)
            self.assertFalse(worker.is_alive())
            install.assert_called_once_with()
            emit.assert_called_once_with(None, 'test speech', 50, None, 1.10)
            self.assertNotIn(worker, pine._AUDIO_THREADS)

    def test_speech_level_and_pace_do_not_change_alert_chime(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(pine, 'DATA_DIR', Path(directory)), \
             patch.object(pine, '_wake_sink', return_value=True), \
             patch.object(pine, 'play_sound') as play, \
             patch.object(pine, '_duck_other_streams', return_value=[13]), \
             patch.object(pine, 'speak') as speak, \
             patch.object(pine, '_restore_ducked') as restore:
            pine.emit_audio('alert.oga', 'soft spoken alert', 90, 58, 1.10)
        play.assert_called_once_with('alert.oga', 90)
        speak.assert_called_once_with('soft spoken alert', 58,
                                      sink_ready=True, length_scale=1.10)
        restore.assert_called_once_with([13])

    def test_upgraded_orage_identity_inherits_but_explicit_override_wins(self):
        cfg = {'app_rules': {'orage': {'speak': True}}}
        self.assertTrue(pine.should_speak(cfg, 'Orage'))
        cfg['app_rules']['Orage'] = {'speak': False}
        self.assertFalse(pine.should_speak(cfg, 'Orage'))


if __name__ == '__main__':
    unittest.main()
