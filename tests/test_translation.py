"""#75, Grundlagen: Sprachfassung als eigenes Buch, Begriffsliste, Trennstriche, Stand je Abschnitt, Modelle bei expliziten Inhalten."""
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import translation  # noqa: E402
import validate_project  # noqa: E402


class TranslationTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.source = self.tmp / 'original'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.source)
        self.base = self.tmp / 'en'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        cfg = yaml.safe_load((self.source / 'ghostwriter.yml').read_text(encoding='utf-8'))
        self.sid = cfg['structure']['chapters'][0]['sections'][0]['id']

    def run_cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = translation.main([str(self.base), *args])
        return code, out.getvalue()

    def init(self):
        return self.run_cli('init', '--language', 'en', '--source-branch', 'buch/adhs', '--source-edition', '1')

    def test_init_valid_schema_and_not_twice(self):
        self.assertEqual(self.init()[0], 0)
        self.assertEqual(validate_project.check_project(self.base), [])
        t = yaml.safe_load((self.base / 'ghostwriter.yml').read_text())['translation']
        self.assertEqual((t['language'], t['source_branch'], t['source_edition'], t['style']), ('en', 'buch/adhs', 1, 'close'))
        self.assertEqual(self.init()[0], 2)
        self.assertEqual(self.run_cli('init', '--language', 'english', '--source-branch', 'b', '--source-edition', '1')[0], 2)

    def test_not_a_translation_without_init(self):
        self.assertEqual(self.run_cli('terms', 'list')[0], 2)

    def test_terms_are_mandatory_before_prepare(self):
        self.init()
        code, out = self.run_cli('prepare', self.sid, '--source', str(self.source))
        self.assertEqual(code, 2)
        self.assertIn('Begriffsliste', out)
        self.assertEqual(self.run_cli('terms', 'check')[0], 1)
        self.assertEqual(self.run_cli('terms', 'add', 'Dorffunk', 'village grapevine', '--kind', 'term', '--note', 'beim ersten Vorkommen erklären')[0], 0)
        self.assertEqual(self.run_cli('terms', 'add', 'Dorffunk', 'village gossip')[0], 0)           # gleicher Begriff ersetzt den alten
        self.assertEqual(self.run_cli('terms', 'check')[0], 0)
        terms = translation.load_terms(self.base)
        self.assertEqual([(x['source'], x['target']) for x in terms], [('Dorffunk', 'village gossip')])
        self.assertEqual(self.run_cli('terms', 'add', 'x', 'y', '--kind', 'unsinn')[0], 2)

    def test_dehyphenate_only_before_lowercase(self):
        self.assertEqual(translation.dehyphenate('der Weg kam uns ent-\ngegen und ei-\nnen Hund'), 'der Weg kam uns entgegen und einen Hund')
        self.assertEqual(translation.dehyphenate('Süd-\nTirol bleibt'), 'Süd-\nTirol bleibt')       # Eigenname: nicht zusammenfügen
        self.assertEqual(translation.dehyphenate('Liste:\n- Punkt\n- Punkt'), 'Liste:\n- Punkt\n- Punkt')
        self.assertEqual(translation.dehyphenate('Absatz eins.\n\nAbsatz zwei.'), 'Absatz eins.\n\nAbsatz zwei.')

    def test_prepare_prompt_has_terms_style_and_fingerprint(self):
        self.init()
        self.run_cli('terms', 'add', 'Dorffunk', 'village grapevine', '--kind', 'term')
        code, out = self.run_cli('prepare', self.sid, '--source', str(self.source), '--json')
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual((data['language'], data['source_edition'], data['status']), ('en', 1, 'open'))
        self.assertIn('„Dorffunk“ → „village grapevine“', data['prompt'])
        self.assertIn('Absatzschlüsse', data['prompt'])
        self.assertIn('[ÜBERSETZUNG PRÜFEN', data['prompt'])
        self.assertEqual(len(data['fingerprint']), 16)

    def test_status_and_stale_when_original_changes(self):
        self.init()
        self.assertEqual(self.run_cli('record', self.sid, '--source', str(self.source), '--model', 'chat')[0], 0)
        st = yaml.safe_load((self.base / 'translation/status.yml').read_text())['sections'][self.sid]
        self.assertEqual((st['state'], st['model'], st['source_edition']), ('translated', 'chat', 1))
        self.assertIn('Keine veralteten', self.run_cli('stale', '--source', str(self.source))[1])
        from render_view import load
        _, cfg = load(self.source)
        sec = cfg['structure']['chapters'][0]['sections'][0]
        spath = self.source / sec['path']
        spath.write_text(spath.read_text(encoding='utf-8') + '\nEin neuer Satz im Original.\n', encoding='utf-8')
        code, out = self.run_cli('stale', '--source', str(self.source), '--json')
        self.assertEqual([r['section'] for r in json.loads(out)], [self.sid])
        self.assertEqual(self.run_cli('record', self.sid, '--source', str(self.source), '--model', 'chat', '--state', 'unsinn')[0], 2)

    def test_models_and_explicit_flag(self):
        self.init()
        ids = [m['id'] for m in translation.offered_models(translation.config_of(self.base))]
        self.assertIn('translategemma', ids)
        cfg = (self.base / 'ghostwriter.yml').read_text()
        (self.base / 'ghostwriter.yml').write_text(cfg + '\ncontent:\n  explicit: true\n', encoding='utf-8')
        self.assertEqual(validate_project.check_project(self.base), [])
        ids = [m['id'] for m in translation.offered_models(translation.config_of(self.base))]
        self.assertNotIn('translategemma', ids)                                    # Gemma Terms of Use: keine expliziten Inhalte
        self.assertEqual(set(ids), {'gemma-4', 'chat', 'queue'})
        out = self.run_cli('models')[1]
        self.assertIn('Apache License 2.0', out)
        self.assertNotIn('TranslateGemma', out)

    def test_imprint_note(self):
        self.init()
        self.assertIn('Translated with AI assistance, revised by Anna Beispiel.', self.run_cli('imprint', '--reviewer', 'Anna Beispiel')[1])
        self.assertIn('noch offen', self.run_cli('imprint')[1])


if __name__ == '__main__':
    unittest.main()
