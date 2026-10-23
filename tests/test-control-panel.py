"""Local control-panel regressions. No live service or cloud actions."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

ROOT = Path(os.environ.get('PANEL_ROOT', str(Path(__file__).resolve().parents[1])))
sys.path.insert(0, str(ROOT / 'bin'))
source = os.environ.get('PANEL_SOURCE', str(ROOT / 'bin/khaos-lab'))
loader = importlib.machinery.SourceFileLoader('panel_audit', source)
spec = importlib.util.spec_from_loader(loader.name, loader)
panel = importlib.util.module_from_spec(spec)
loader.exec_module(panel)

class Controls(unittest.TestCase):
    def test_sudo_packet_auth_ignores_cache_without_invalidating_it(self):
        with patch.object(panel.subprocess, 'run', return_value=NS(returncode=0)) as run:
            self.assertTrue(panel.verify_sudo_password('fixture-only-secret'))
        argv = run.call_args.args[0]
        options = run.call_args.kwargs
        self.assertEqual(argv, ['sudo', '-S', '-k', '-v', '-p', ''])
        self.assertEqual(options['input'], 'fixture-only-secret\n')
        self.assertIs(options['stdout'], panel.subprocess.DEVNULL)
        self.assertIs(options['stderr'], panel.subprocess.DEVNULL)
        self.assertEqual(options['timeout'], 30)
        self.assertFalse(options['check'])

    def test_policy_packet_is_not_opened_until_sudo_auth_succeeds(self):
        for answer, accepted, expected in ((None, False, False),
                                           ('wrong-fixture', False, False),
                                           ('right-fixture', True, True)):
            with self.subTest(accepted=accepted, cancelled=answer is None):
                displayed, logs = [], []
                view = NS(
                    accept_var=NS(set=Mock()),
                    docs_read=set(),
                    doc_hashes={'stale': 'hash'},
                    app=NS(root=object(), console=NS(log=lambda *args: logs.append(args))),
                )
                view._authenticate_policy_read = lambda: panel.SopView._authenticate_policy_read(view)
                view._display_policy_packet = lambda paths: displayed.append(paths)
                with patch.object(panel.simpledialog, 'askstring', return_value=answer), \
                     patch.object(panel, 'verify_sudo_password', return_value=accepted) as verify:
                    panel.SopView._read_policy_packet(view)
                self.assertEqual(bool(displayed), expected)
                self.assertEqual(verify.called, answer is not None)
                self.assertFalse(view.docs_read)
                self.assertFalse(view.doc_hashes)

    def test_sudo_packet_auth_fails_closed_on_timeout_or_denial(self):
        with patch.object(panel.subprocess, 'run', return_value=NS(returncode=1)):
            self.assertFalse(panel.verify_sudo_password('fixture-only-secret'))
        with patch.object(panel.subprocess, 'run', side_effect=subprocess.TimeoutExpired('sudo', 30)):
            self.assertFalse(panel.verify_sudo_password('fixture-only-secret'))

    def test_policy_packet_stays_closed_if_password_prompt_is_unavailable(self):
        logs = []
        view = NS(app=NS(root=object(), console=NS(log=lambda *args: logs.append(args))))
        with patch.object(panel.simpledialog, 'askstring', side_effect=panel.tk.TclError):
            self.assertFalse(panel.SopView._authenticate_policy_read(view))
        self.assertEqual(len(logs), 1)

    def test_legacy_policy_reader_also_requires_auth_before_dialog(self):
        view = NS(_authenticate_policy_read=lambda: False)
        with patch.object(panel, 'Dialog') as dialog:
            panel.SopView._read_doc(view, 'SOT', Path('/unused'))
        dialog.assert_not_called()

    def test_explicit_detached_confirmation_and_recheck(self):
        launched, dialogs, checks = [], [], []
        class Dialog:
            def __init__(self, *args):
                self.win = NS(bind=lambda *args: None); dialogs.append(self)
            def label(self, *args, **kwargs): pass
            def buttons(self, specs): self.specs = specs
            def close(self): pass
        allowed = [True]
        fake = NS(require_ops_gate=lambda cmd: checks.append(cmd) or allowed[0],
                  ensure_console_room=lambda: None,
                  console=NS(log=lambda *args: None), f=NS(small=None),
                  runner=NS(detach=lambda cmd: (launched.append(cmd) or True, 'launched')))
        fake._launch_action = lambda a: panel.App._launch_action(fake, a)
        action = panel.Action('sensitive launcher', 'true', confirm=True, detach=True)
        with patch.object(panel, 'Dialog', Dialog):
            panel.App.run_action(fake, action)
            self.assertEqual(launched, [])
            self.assertEqual(len(dialogs), 1)
            allowed[0] = False
            dialogs[0].specs[0][2]()
            self.assertEqual(launched, [])
            allowed[0] = True
            dialogs[0].specs[0][2]()
            self.assertEqual(launched, ['true'])
            self.assertEqual(len(checks), 3)

    def test_calendar_locked_does_not_save(self):
        calls = []
        fake = NS(app=NS(require_ops_gate=lambda cmd: False), busy=False,
                  message=NS(configure=lambda **kw: None), _set_checks_enabled=lambda value: None)
        value = NS(set=lambda v: calls.append(v), get=lambda: True)
        with patch.object(panel.threading, 'Thread') as worker:
            panel.CalendarView.toggle(fake, {'done': False}, value)
            worker.assert_not_called()
        self.assertEqual(calls, [False])
        self.assertFalse(fake.busy)

    def test_mobile_status_handles_independent_failures(self):
        class Label:
            def configure(self, **kwargs): pass
        for tailnet_ok, waydroid in [(False, 'Container service: stopped'),
                                      (True, 'unexpected status output')]:
            states = {}
            fake = NS(alive=lambda: True, refresh_button=Label(),
                      _peer_map=panel.MobileAccessView._peer_map,
                      _set=lambda key, text, color: states.update({key: text}))
            panel.MobileAccessView._apply_status(fake,
                (tailnet_ok, '{"Self":{"Online":true},"Peer":{}}', True,
                 waydroid, False, '', False, '', False, ''))
            self.assertIn('Waydroid', states)
            self.assertEqual(fake._busy, False)

    def test_preflight_is_literal_argv(self):
        class Process:
            pid = 123
            def wait(self, **kwargs): return 0
        with patch.object(panel.subprocess, 'Popen', return_value=Process()) as launch:
            ok, _ = panel.Runner().run('arc sop start "$(untrusted-input)"')
        self.assertTrue(ok)
        self.assertFalse(launch.call_args.kwargs['shell'])
        self.assertEqual(launch.call_args.args[0], ['arc','sop','start','$(untrusted-input)'])

    def test_timeout_kills_term_resistant_descendant(self):
        with tempfile.TemporaryDirectory(prefix='panel-timeout-') as td:
            pidfile = Path(td)/'child.pid'
            child = ('import os,signal,time; from pathlib import Path; '
                     'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                     f'Path({str(pidfile)!r}).write_text(str(os.getpid())); time.sleep(30)')
            parent = ('import subprocess,sys,time; '
                      f'subprocess.Popen([sys.executable,"-c",{child!r}]); time.sleep(30)')
            pid = None
            try:
                ok, output = panel.Runner().run('exec '+shlex.join([sys.executable,'-c',parent]), timeout=.5)
                self.assertFalse(ok)
                self.assertIn('timed out', output)
                pid = int(pidfile.read_text())
                for _ in range(40):
                    status = Path(f'/proc/{pid}/stat')
                    if not status.exists() or status.read_text().split()[2] == 'Z': break
                    time.sleep(.025)
                else: self.fail('descendant survived timed-out parent')
            finally:
                if pid is None and pidfile.exists(): pid = int(pidfile.read_text())
                if pid:
                    try: os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError: pass

    def test_logs_are_scrollable_and_sqlite_reads_are_readonly(self):
        self.assertTrue(panel.LogsView.scrollable)
        commands = []
        fake = NS(app=NS(runner=NS(run=lambda cmd, **kw: (commands.append(cmd) or True, ''))))
        panel.LogsView._tail(fake, {'path':Path('/nonexistent/history.db'),'kind':'sqlite'})
        self.assertIn('-readonly', shlex.split(commands[0]))

    def test_missing_status_is_never_reported_healthy(self):
        fake = NS(app=NS(runner=NS(run=lambda *args, **kw: (False, ''))))
        services = panel.StatusView.checks(fake)['services']
        self.assertIn('unavailable', services())
        with patch.object(panel.CalendarView, 'request', return_value={'error':'offline'}):
            self.assertIn('unavailable', panel.StatusView.calendar_status(fake))

    def test_mobile_rejects_malformed_peer_shapes(self):
        for data in [{'Self':[]}, {'Self':{},'Peer':{'a':[]}}, [], 'offline']:
            with self.subTest(data=data):
                import json
                self.assertEqual(panel.MobileAccessView._peer_map(json.dumps(data)), (None,None))

    def test_confirmation_policy_matches_launcher_semantics(self):
        self.assertTrue(panel.ConfirmPolicy.required(panel.Action('change', 'arc vpn disconnect')))
        self.assertTrue(panel.ConfirmPolicy.required(panel.Action('console', 'terminal', confirm=True, detach=True)))
        self.assertFalse(panel.ConfirmPolicy.required(panel.Action('guide', 'xdg-open build-guide.md', detach=True)))
        self.assertFalse(panel.ConfirmPolicy.required(panel.Action('status', 'arc vpn status')))

def runGuiSelftest():
    """Build every view offline; never invoke a real operational command."""
    import json
    panel.STUDIO_DOC_DIR = ROOT / 'docs/studio'
    def fixture(self, cmd, timeout=30):
        if cmd == 'arc word --json':
            return True, json.dumps(dict(date='2026-10-18', word='austere',
                pronunciation='aw steer', part_of_speech='adjective',
                definition='Plain and restrained.'))
        return False, 'unavailable (isolated audit fixture)'
    def denyLaunch(*args):
        raise AssertionError('GUI selftest must never launch actions')
    unraisable = []
    originalHook = sys.unraisablehook
    def captureCleanupError(args):
        unraisable.append(str(args.exc_value))
        originalHook(args)
    with patch.object(sys, 'unraisablehook', captureCleanupError), \
         patch.object(panel.Runner, 'run', fixture), \
         patch.object(panel.Runner, 'detach', denyLaunch), \
         patch.object(panel, 'check_sop_gate', lambda timeout=5: (True, 'isolated policy fixture')), \
         patch.object(panel.CalendarView, 'request', return_value={'error': 'offline audit fixture'}):
        app = panel.App()
        # Keep a retired variable alive on a worker, with a real Tcl trace.
        # Owner destruction must remove both Tcl resources on the UI thread.
        import gc
        import threading
        owner = panel.tk.Frame(app.root)
        variable = panel.owned_variable(owner, value='dialog value')
        trace = variable.trace_add('write', lambda *args: None)
        name = str(variable)
        manager = app.root._panelVariables
        count = len(manager.variables)
        owner.destroy()
        assert variable.get() == 'dialog value', 'dialog callback lost its value before returning'
        app.root.update_idletasks()
        assert not app.root.tk.getboolean(app.root.tk.call('info', 'exists', name))
        assert not app.root.tk.call('info', 'commands', trace)
        assert len(manager.variables) == count - 1
        references = [variable]
        del variable, owner
        worker = threading.Thread(target=lambda: (references.clear(), gc.collect()))
        worker.start(); worker.join(timeout=3)
        assert not worker.is_alive(), 'cleanup worker blocked in Tk'
        assert not unraisable, unraisable
        print('  widget-owned variable and trace cleanup: ok', flush=True)
        # Root destruction must also release variables whose idle cleanup has
        # not run, rather than abandoning them in a dead event queue.
        closingOwner = panel.tk.Frame(app.root)
        closingVariable = panel.owned_variable(closingOwner, value='closing')
        closingOwner.destroy()
        app.root.geometry('650x480')
        app.select('Logs')
        app._pump(.3)
        app.content.yview_moveto(1)
        app._pump(.2)
        assert app.content.yview()[1] >= .99, 'bottom log row is unreachable'
        assert app.content.yview()[0] > 0, 'small-window logs did not scroll'
        print('  650x480 Logs scroll reaches bottom: ok', flush=True)
        if os.environ.get('PANEL_SCREENSHOT'):
            from PIL import ImageGrab
            ImageGrab.grab(xdisplay=os.environ['DISPLAY']).save(os.environ['PANEL_SCREENSHOT'])
        result = app.selftest()
        assert closingVariable._tk is None, 'root shutdown left pending Tcl state'
        assert not manager.variables and not manager.pending, 'variable cleanup leaked'
        gc.collect()
        assert not unraisable, unraisable
        print('  Tk shutdown cleanup warnings: none', flush=True)
        return result

if __name__ == '__main__':
    if '--gui' in sys.argv:
        raise SystemExit(runGuiSelftest())
    unittest.main()
