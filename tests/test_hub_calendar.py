import importlib.machinery
import importlib.util
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


def load_script(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class CalendarChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.hub = load_script('hub_under_test', Path(__file__).resolve().parents[1] / 'bin/khaos-hub')
        self.hub.SOURCE = self.root / 'calendar.ics'
        self.hub.STATE = self.root / 'state'
        self.hub.SOURCE.write_text('''BEGIN:VCALENDAR
BEGIN:VTODO
UID:undated-task
SUMMARY:An undated task
END:VTODO
END:VCALENDAR
''')

    def test_check_uncheck_persistence_conflict_and_source_preservation(self):
        original = self.hub.SOURCE.read_bytes()
        item = self.hub.snapshot()['items'][0]
        saved = self.hub.set_checked({'id': item['id'], 'done': True, 'revision': 0})['items'][0]
        self.assertTrue(saved['done'])
        self.assertEqual(self.hub.snapshot()['items'][0]['revision'], 1)
        with self.assertRaises(RuntimeError):
            self.hub.set_checked({'id': item['id'], 'done': False, 'revision': 0})
        saved = self.hub.set_checked({'id': item['id'], 'done': False, 'revision': 1})['items'][0]
        self.assertFalse(saved['done'])
        self.assertEqual(original, self.hub.SOURCE.read_bytes())

    def test_unknown_entry_and_nonboolean_check_rejected(self):
        with self.assertRaises(ValueError):
            self.hub.set_checked({'id': 'not-an-appointment', 'done': True, 'revision': 0})
        with self.assertRaises(ValueError):
            self.hub.set_checked({'id': 'x', 'done': 'false', 'revision': 0})

    def test_recurrence_exception_and_override_have_independent_marks(self):
        self.hub.SOURCE.write_text('''BEGIN:VCALENDAR
BEGIN:VEVENT
UID:series
SUMMARY:Daily event
DTSTART:20261005T090000Z
RRULE:FREQ=DAILY;COUNT=4
EXDATE:20261006T090000Z
END:VEVENT
BEGIN:VEVENT
UID:series
RECURRENCE-ID:20261007T090000Z
DTSTART:20261007T100000Z
SUMMARY:Moved event
END:VEVENT
END:VCALENDAR
''')
        items = self.hub.calendar_items(self.hub.SOURCE, datetime(2026, 10, 5, tzinfo=timezone.utc))
        self.assertEqual(len(items), 3)
        self.assertEqual(len({i['id'] for i in items}), 3)
        self.assertEqual(sum(i['title'] == 'Moved event' for i in items), 1)
        self.assertFalse(any('2026-10-06' in i['date'] for i in items))


if __name__ == '__main__':
    unittest.main()
