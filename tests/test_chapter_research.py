"""Formular „Kapitelrecherche“: Werte aus Kapitel-README und letztem Kapitel-Lauf."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(base, *extra):
    out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(base), 'chapter-research', '1', *extra],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(re.search(r'GW\.render\("kapitelrecherche",(.*)\)</script>', out).group(1))


class ChapterResearchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / 'p'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        import yaml
        cfg = yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        self.chapter = self.base / cfg['structure']['chapters'][0]['path']
        self.first_section = cfg['structure']['chapters'][0]['sections'][0]['title']

    def tearDown(self):
        self.tmp.cleanup()

    def test_without_run(self):
        d = render(self.base)
        self.assertEqual(d['LAST_RUN'], '')
        self.assertEqual(d['PREV_CHAPTER'], '')          # Kapitel 1 hat kein vorheriges
        self.assertEqual(d['NEXT_CHAPTER'], 'true')
        self.assertTrue(d['NEXT_CHAPTER_LABEL'].startswith('Kapitel 2 · '))
        self.assertEqual((d['NEXT_WEIGHT'], d['RESEARCH_TASK']), (2, 'goal'))
        self.assertEqual(d['SUGGESTED_SECTIONS'], [])
        self.assertEqual(d['SUGGESTED_GOAL'], '')
        self.assertIn('noch keine Kapitelrecherche', d['RUN_COUNT_TEXT'])

    def test_last_run_suggestions_and_draft(self):
        run = (ROOT / 'templates/chapter-research-run.md').read_text(encoding='utf-8')
        run = run.replace('Ein bis zwei Sätze: Was soll der Leser nach dem Kapitel verstanden haben?', 'Ziel-Vorschlag')
        run = run.replace('## Vorschlag: Kurzbeschreibung\n\nEin bis drei Sätze.', '## Vorschlag: Kurzbeschreibung\n\nKurz-Vorschlag')
        run = run.replace('Nur bei der Aufgabe „Abschnitte erstellen“: je Zeile `- Titel: Kurzbeschreibung in einem Satz`, in der vorgeschlagenen Reihenfolge. Nur neue Abschnitte; vorhandene stehen unter „Hinweise für die Abschnitte“.',
                          '- Neuer Abschnitt: Ein Satz.\n- ' + self.first_section + ': schon vorhanden')
        run = run.replace('<goal|sections|summary|leer>', 'sections')
        run = run.replace('<FRAGESTELLUNG>', 'Alte Frage').replace('YYYY-MM-DD', '2026-11-01')
        folder = self.chapter / 'research/kapitel'
        folder.mkdir(parents=True)
        (folder / 'run-001.md').write_text(run, encoding='utf-8')
        d = render(self.base)
        self.assertEqual((d['LAST_RUN'], d['SUGGESTED_GOAL'], d['SUGGESTED_SUMMARY']), ('true', 'Ziel-Vorschlag', 'Kurz-Vorschlag'))
        self.assertEqual(d['RESEARCH_QUESTION'], 'Alte Frage')
        self.assertEqual(d['RESEARCH_TASK'], 'sections')
        self.assertEqual(d['SUGGESTED_SECTIONS'], [{'SUG_TITLE': 'Neuer Abschnitt', 'SUG_SUMMARY': 'Ein Satz.'}])  # vorhandener Titel fällt weg
        self.assertIn('bleiben unverändert', d['SECTIONS_NOTE'])
        self.assertIn('01.11.2026', d['RUN_COUNT_TEXT'])
        draft = Path(self.tmp.name) / 'draft.json'
        draft.write_text(json.dumps({'goal': 'Entwurf', 'question': 'Neue Frage', 'task': '', 'weight_next': 3}),
                         encoding='utf-8')
        d = render(self.base, '--draft', str(draft))
        self.assertEqual((d['CHAPTER_GOAL'], d['RESEARCH_QUESTION']), ('Entwurf', 'Neue Frage'))
        self.assertEqual((d['RESEARCH_TASK'], d['NEXT_WEIGHT']), ('', 3))


if __name__ == '__main__':
    unittest.main()
