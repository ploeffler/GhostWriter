"""#675: Antwort oder Anweisung im Feld `neu` landet nie wörtlich im Manuskript; eigenes Feld `antwort`, Sperre der Datei."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import hinweise  # noqa: E402
import checks  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402


class AntwortTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        _, self.config = load(self.base)
        self.s11 = self.config['structure']['chapters'][0]['sections'][0]
        self.text = checks.manuscript(self.base, self.config, self.s11['id'])
        sentences = [m.group().strip() for m in hinweise.SENTENCE.finditer(self.text)]
        self.sentence = next(x for x in sentences if len(x.split()) >= 8 and self.text.count(x) == 1
                             and '\n' not in x and not hinweise._INSTRUCTION.search(x))
        (self.base / 'editorial').mkdir(exist_ok=True)
        findings = {'bericht': 'editorial/rundum-kap-01.md', 'befunde': [
            {'id': 'b-001', 'abschnitt': self.s11['id'], 'art': 'aufbau', 'schweregrad': 'blockierend',
             'befund': 'Ort unklar', 'frage': 'Hafen oder See?', 'alt': self.sentence, 'status': 'offen'},
            {'id': 'b-002', 'abschnitt': self.s11['id'], 'art': 'kontinuitaet', 'befund': 'Taufe',
             'alt': self.sentence, 'status': 'offen'}]}
        (self.base / 'editorial/rundum-kap-01.yml').write_text(yaml.safe_dump(findings, allow_unicode=True), encoding='utf-8')
        self.path, _ = hinweise.collect(self.base, self.config, date='2026-11-25', commit='abcdef1')

    def body(self):
        return checks.manuscript(self.base, self.config, self.s11['id'])

    def force(self, entry_id, **fields):
        """Eintrag wie in YAWA von Hand bzw. mit älterem Programm beschrieben (ohne die neuen Prüfungen in decide)."""
        data = hinweise.read_yaml(self.path)
        for _, e in hinweise.entries(data):
            if e['id'] == entry_id:
                e.update(fields)
        hinweise.write_yaml(self.path, data)

    def test_answer_in_neu_is_not_applied(self):
        """e-008-Fall: `neu` = „Hafen“ für einen ganzen Satz → plan ⚠️, apply ändert nichts."""
        self.force('e-001', entscheidung='geändert', neu='Hafen')
        data = hinweise.read_yaml(self.path)
        marks = {e['id']: (m, why) for m, e, why in hinweise.plan(self.base, self.config, data)}
        self.assertEqual(marks['e-001'][0], '⚠️')
        self.assertIn('kürzer', marks['e-001'][1])
        before = self.body()
        result = hinweise.apply(self.base, self.config, self.path)
        self.assertEqual(result['applied'], [])
        self.assertEqual(self.body(), before)

    def test_instruction_and_timeline_are_not_applied(self):
        """e-010/e-011-Fall: mehrzeilige Anweisung bzw. Zeitleiste mit Pfeilen."""
        self.force('e-001', entscheidung='geändert',
                   neu='Barawitzka hört den Namen in der Taufe zum ersten Mal.\nDie Szene entsprechend ändern.')
        self.force('e-002', entscheidung='geändert', neu='- 1923: Taufe\n- 1925: Umzug → in 3.3 angleichen')
        data = hinweise.read_yaml(self.path)
        marks = {e['id']: (m, why) for m, e, why in hinweise.plan(self.base, self.config, data)}
        self.assertEqual(marks['e-001'][0], '⚠️')
        self.assertIn('Anweisung', marks['e-001'][1])
        self.assertEqual(marks['e-002'][0], '⚠️')
        before = self.body()
        hinweise.apply(self.base, self.config, self.path)
        self.assertEqual(self.body(), before)

    def test_decide_rejects_answer_as_new_and_stores_answer_apart(self):
        with self.assertRaisesRegex(ValueError, '--answer'):
            hinweise.decide(self.path, 'e-001', 'geändert', 'Hafen')
        e = hinweise.decide(self.path, 'e-001', 'geändert', answer='Hafen')
        self.assertEqual((e['antwort'], e['neu'], e['entscheidung']), ('Hafen', '', 'geändert'))
        data = hinweise.read_yaml(self.path)
        marks = {e['id']: (m, why) for m, e, why in hinweise.plan(self.base, self.config, data)}
        self.assertEqual(marks['e-001'], ('⚠️', 'Antwort des Autors ohne neuen Wortlaut: von Hand umsetzen'))
        self.assertIn('> Antwort: Hafen', hinweise.show_single(data, 'e-001'))
        self.assertFalse(validate_project.check_project(self.base))
        # danach der echte Ersatzsatz: wird umgesetzt, die Antwort bleibt getrennt stehen
        new = self.sentence.replace(self.sentence.split()[0], 'Im Hafen ' + self.sentence.split()[0].lower(), 1)
        e = hinweise.decide(self.path, 'e-001', 'geändert', new, answer='Hafen')
        self.assertEqual((e['antwort'], e['neu']), ('Hafen', new))
        result = hinweise.apply(self.base, self.config, self.path)
        self.assertEqual([x['id'] for x in result['applied']], ['e-001'])
        self.assertIn(new, self.body())
        self.assertNotIn('Hafen\n', self.body())

    def test_as_text_confirms_short_replacement(self):
        e = hinweise.decide(self.path, 'e-001', 'geändert', 'Hafen.', as_text=True)
        self.assertTrue(e['ersatz_bestaetigt'])
        data = hinweise.read_yaml(self.path)
        self.assertEqual([m for m, x, _ in hinweise.plan(self.base, self.config, data) if x['id'] == 'e-001'], ['✅'])
        # ohne Bestätigung hält plan denselben Text zurück
        self.force('e-001', ersatz_bestaetigt=False)
        data = hinweise.read_yaml(self.path)
        self.assertEqual([m for m, x, _ in hinweise.plan(self.base, self.config, data) if x['id'] == 'e-001'], ['⚠️'])

    def test_accept_skips_suspicious_proposal(self):
        data = hinweise.read_yaml(self.path)
        for _, e in hinweise.entries(data):
            e['schweregrad'] = 'mittel'
        hinweise.write_yaml(self.path, data)
        self.force('e-002', neu='Hafen')
        self.assertFalse(hinweise.proposal(hinweise.read_yaml(self.path)['autorenentscheidung'][1]))
        self.assertEqual(hinweise.accept(self.path), [])

    def test_ordinary_replacement_still_applies(self):
        neu = self.sentence[:-1] + ', sagte sie' + self.sentence[-1] if self.sentence[-1] in '.!?' else self.sentence + ' Gut.'
        self.assertEqual(hinweise.not_replacement({'alt': self.sentence, 'neu': neu}), '')
        self.assertEqual(hinweise.not_replacement({'alt': 'sehr schnell', 'neu': 'schnell'}), '')
        self.assertEqual(hinweise.not_replacement({'alt': self.sentence, 'neu': ''}), '')

    def test_lock_blocks_apply_and_accept_not_decide(self):
        self.force('e-001', entscheidung='geändert', neu='Hafen')
        hinweise.lock(self.path, 'kein apply bis #675')
        data = hinweise.read_yaml(self.path)
        self.assertEqual(data['gesperrt'], 'kein apply bis #675')
        with self.assertRaisesRegex(ValueError, 'gesperrt: kein apply bis #675'):
            hinweise.apply(self.base, self.config, self.path)
        with self.assertRaisesRegex(ValueError, 'gesperrt'):
            hinweise.accept(self.path)
        hinweise.decide(self.path, 'e-002', 'nein')
        self.assertEqual(hinweise.read_yaml(self.path)['gesperrt'], 'kein apply bis #675')   # bleibt beim Neuschreiben
        self.assertIn('Gesperrt', hinweise.show(hinweise.read_yaml(self.path)))
        self.assertIn('gesperrt', hinweise.plan_text([], hinweise.read_yaml(self.path)))
        values, _ = hinweise.widget_values(self.base, self.path)
        self.assertTrue(values['REVIEW_COUNT_TEXT'].startswith('⛔ Gesperrt'))
        self.assertFalse(validate_project.check_project(self.base))
        hinweise.lock(self.path, None)
        self.assertNotIn('gesperrt', hinweise.read_yaml(self.path))

    def test_cli_answer_lock_and_merge_warning(self):
        def run(*a):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/hinweise.py'), *a], capture_output=True, text=True)
        out = run('decide', str(self.base), 'e-001', '--answer', 'Hafen')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(hinweise.read_yaml(self.path)['autorenentscheidung'][0]['antwort'], 'Hafen')
        self.force('e-002', entscheidung='geändert', neu='See')
        out = run('collect', str(self.base), '--date', '2026-11-25', '--merge')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('⚠️ e-002', out.stdout)
        out = run('lock', str(self.base), '--reason', 'Prüfung läuft')
        self.assertEqual(out.returncode, 0, out.stderr)
        out = run('apply', str(self.base))
        self.assertEqual(out.returncode, 1)
        self.assertIn('Prüfung läuft', out.stderr)
        self.assertEqual(run('unlock', str(self.base)).returncode, 0)
        widget = hinweise.widget_values(self.base, self.path)[1]['AUTHOR']
        self.assertIn('Antwort: Hafen', widget[0]['E_QUESTION'])
        self.assertIn('⚠️', widget[1]['E_QUESTION'])


if __name__ == '__main__':
    unittest.main()
