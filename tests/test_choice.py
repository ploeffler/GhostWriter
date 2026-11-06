"""Auswahlkarten (#81): templates/wizard-choices.yml ist gültig, Widget und Textfassung
enthalten alle Antworten, Vorauswahl aus ghostwriter.yml, eigene Auswahl über --spec."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'tests/fixtures/adhs'
sys.path.insert(0, str(ROOT / 'scripts'))
import render_view  # noqa: E402


def run(*args):
    r = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(FIX), 'choice', *args],
                       capture_output=True, text=True)
    return r


def payload(out):
    return json.loads(re.search(r'GW\.render\("auswahl",(.*)\)</script>', out).group(1))


class ChoiceTest(unittest.TestCase):
    def test_library_is_valid(self):
        lib = yaml.safe_load((ROOT / 'templates/wizard-choices.yml').read_text(encoding='utf-8'))
        for step, spec in lib['steps'].items():
            with self.subTest(step):
                render_view.check_choice_spec(spec)
                for q in spec['questions']:
                    self.assertEqual(len({o['value'] for o in q['options']}), len(q['options']))
                    for o in q['options']:
                        self.assertLessEqual(set(o), {'value', 'label', 'desc', 'recommended'})

    def test_widget_has_all_options(self):
        r = run('wizard.5')
        self.assertEqual(r.returncode, 0, r.stderr)
        d = payload(r.stdout)
        self.assertEqual(d['STEP'], 'wizard.5')
        self.assertEqual(d['TITLE'], 'Neues Buch · Schritt 5 von 14')
        self.assertEqual([q['Q_KEY'] for q in d['QUESTIONS']], ['book_type', 'length'])
        self.assertEqual(len(d['OPTIONS']), 8)
        self.assertEqual(sum(o['OPT_RECOMMENDED'] == '1' for o in d['OPTIONS'] if o['OPT_Q'] == '2'), 1)

    def test_preselect_from_config(self):
        d = payload(run('wizard.6').stdout)
        sel = [o['OPT_VALUE'] for o in d['OPTIONS'] if o['OPT_SELECTED']]
        self.assertEqual(sel, ['de'])

    def test_text_version(self):
        r = run('wizard.13', '--text')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('`1a` Keine geplant · *empfohlen*', r.stdout)
        self.assertIn('*(mehrere möglich)*', r.stdout)
        self.assertIn('`S` überspringt', r.stdout)
        self.assertNotIn('<', r.stdout.replace('<sub>', '').replace('</sub>', ''))

    def test_english_wizard_steps_render_and_preserve_option_values(self):
        lib = yaml.safe_load((ROOT / 'templates/wizard-choices.yml').read_text(encoding='utf-8'))
        before = (FIX / 'ghostwriter.yml').read_bytes()
        for step, spec in lib['steps'].items():
            with self.subTest(step=step):
                title = f"New book · Step {step.split('.')[-1]} of {lib['steps_total']}"
                text = run(step, '--text', '--language', 'en', '--repo', 'owner/book')
                self.assertEqual(text.returncode, 0, text.stderr)
                self.assertIn(title, text.stdout)
                self.assertNotIn('{step}', text.stdout)
                widget = run(step, '--language', 'en', '--ui-ref', 'a' * 40, '--repo', 'owner/book')
                self.assertEqual(widget.returncode, 0, widget.stderr)
                data = payload(widget.stdout)
                self.assertEqual(data['TITLE'], title)
                self.assertEqual([o['OPT_VALUE'] for o in data['OPTIONS']],
                                 [o['value'] for q in spec['questions'] for o in q['options']])
        self.assertEqual(before, (FIX / 'ghostwriter.yml').read_bytes())

    def test_custom_spec(self):
        spec = {'step': 'custom.1', 'title': 'Test', 'questions': [{'key': 'x', 'header': 'X', 'text': 'Frage?',
                'options': [{'value': 'a', 'label': 'A'}, {'value': 'b', 'label': 'B'}]}]}
        d = payload(run('--spec', json.dumps(spec)).stdout)
        self.assertEqual(d['STEP'], 'custom.1')
        self.assertEqual(d['SKIPPABLE'], '')

    def test_invalid_spec_is_refused(self):
        spec = {'questions': [{'key': 'x', 'header': 'X', 'text': '?', 'options': [{'value': 'a', 'label': 'A'}]}]}
        self.assertNotEqual(run('--spec', json.dumps(spec)).returncode, 0)
        self.assertNotEqual(run('wizard.99').returncode, 0)


if __name__ == '__main__':
    unittest.main()
