"""Uhrzeiten offener Änderungen in Ortszeit statt UTC (#252)."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_view  # noqa: E402


class ChangeDateTest(unittest.TestCase):
    def show(self, value, language='de', timezone=None):
        with patch.dict(render_view.UI, {'language': language, 'timezone': timezone}):
            return render_view.change_date(value)

    def test_github_utc_is_shown_in_local_time_for_german(self):
        # Gemeldeter Fall: 17:51 Ortszeit Wien erschien als 16:51.
        self.assertEqual(self.show('2026-11-10T16:51:47Z'), '10.11.2026, 17:51')
        self.assertEqual(self.show('2026-07-10T16:51:47Z'), '10.07.2026, 18:51')  # Sommerzeit

    def test_offset_input_and_explicit_timezone(self):
        self.assertEqual(self.show('2026-10-31T23:12:00+01:00'), '31.10.2026, 23:12')
        self.assertEqual(self.show('2026-11-10T16:51:47Z', timezone='America/New_York'), '10.11.2026, 11:51')
        self.assertEqual(self.show('2026-11-10T23:30:00Z', timezone='Europe/Vienna'), '11.11.2026, 00:30')

    def test_utc_is_labelled_and_unknown_zone_falls_back_to_utc(self):
        self.assertEqual(self.show('2026-11-06T10:20:00Z', language='en'), '2026-11-06, 10:20 UTC')
        self.assertEqual(self.show('2026-11-06T10:20:00Z', language='en', timezone='Europe/London'), '2026-11-06, 10:20')
        self.assertEqual(self.show('2026-11-06T10:20:00Z', timezone='Mars/Olympus'), '06.11.2026, 10:20 UTC')

    def test_naive_and_invalid_values_unchanged(self):
        self.assertEqual(self.show('2026-11-06T10:20:00'), '06.11.2026, 10:20')
        self.assertEqual(self.show('gestern'), 'gestern')
        self.assertEqual(self.show(None), '')


if __name__ == '__main__':
    unittest.main()
