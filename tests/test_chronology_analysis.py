"""Analyseart „Chronologie“ (#364): Blöcke aus Unterlagen, strenge Prüfung, Zusammenführen, Übernehmen, Chatweg."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze  # noqa: E402
import chat_analysis as ca  # noqa: E402
import chronology  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402

SOURCES = 'research/sources.md'
SOURCES_TEXT = 'Standesamt Graz, Heiratsbuch 1948: Anna Berger heiratet am 12. Juni 1948 Karl Huber.\n'
CHAR_TEXT = '---\nid: char-anna\nname: "Anna Berger"\nrole: main\nshort: ""\n---\n\n# Anna Berger\n\nAnna erzählt, sie sei um 1930 in Graz geboren.\n'


class ChronologyAnalysisTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.base = self.root / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        (self.base / 'research').mkdir()
        (self.base / SOURCES).write_text(SOURCES_TEXT, encoding='utf-8')
        (self.base / 'characters').mkdir()
        (self.base / 'characters/char-anna.md').write_text(CHAR_TEXT, encoding='utf-8')
        cfg = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        cfg += '\ncharacters:\n- id: char-anna\n  name: Anna Berger\n  path: characters/char-anna.md\n' \
            if '\ncharacters:' not in cfg else ''
        (self.base / 'ghostwriter.yml').write_text(cfg, encoding='utf-8')
        conv = self.base / 'conversations/s1/conversation'
        conv.mkdir(parents=True)
        (conv / 'latest.json').write_text(json.dumps({'messages': [
            {'id': 'm001', 'role': 'user', 'content': 'Meine Oma Anna Berger hat 1949 geheiratet, glaube ich.'},
            {'id': 'm002', 'role': 'assistant', 'content': 'Anna Berger starb 1990.'}]}), encoding='utf-8')
        _, self.config = load(self.base)

    def texts(self):
        return dict(analyze.chronology_units(self.base, self.config))

    def test_units_read_material_not_manuscript_or_assistant(self):
        texts = self.texts()
        self.assertIn(SOURCES, texts)
        self.assertIn('characters/char-anna.md', texts)
        self.assertIn('conversations/s1#m001', texts)
        self.assertNotIn('conversations/s1#m002', texts)
        self.assertFalse(any('sections/' in k for k in texts))
        blocks = list(analyze.chronology_blocks(self.base, self.config))
        self.assertEqual(len(blocks), 1)
        self.assertTrue(blocks[0][0].startswith('src-'))

    def answer(self):
        return {'entries': [
            {'kind': 'event', 'what': 'Hochzeit von Anna und Karl', 'date': '1948-06-12', 'status': 'documented',
             'characters': ['Anna Berger', 'Karl Huber'],
             'evidence': [{'where': SOURCES, 'quote': 'Anna Berger heiratet am 12. Juni 1948 Karl Huber'}]},
            {'kind': 'event', 'what': 'Hochzeit von Anna und Karl', 'date': '1949', 'status': 'documented',
             'characters': ['Anna Berger'],
             'evidence': [{'where': 'conversations/s1#m001', 'quote': 'Anna Berger hat 1949 geheiratet'}]},
            {'kind': 'birth', 'what': 'Geburt von Anna', 'date': '1930', 'status': 'reported', 'age': 3,
             'characters': ['Anna Berger'], 'evidence': [{'where': 'characters/char-anna.md', 'quote': 'sie sei um 1930 in Graz geboren'}]},
            {'kind': 'event', 'what': 'Umzug', 'date': '1955', 'status': 'invented',
             'evidence': [{'where': SOURCES, 'quote': 'Standesamt Graz'}]},
            {'kind': 'event', 'what': 'Erfunden', 'date': '1960', 'evidence': [{'where': SOURCES, 'quote': 'steht nirgends'}]},
        ]}

    def verified(self):
        return analyze.verify_for(self.base, self.config, 'chronology', self.answer(), self.texts())

    def test_verify_is_strict(self):
        items, dropped = self.verified()
        self.assertEqual(len(items), 4)
        wedding, told, birth, move = items
        self.assertEqual((wedding['status'], wedding['date'], wedding['source']), ('documented', '1948-06-12', SOURCES))
        self.assertEqual(wedding['characters'], ['char-anna'])
        self.assertIn('Figur nicht angelegt: Karl Huber', wedding['note'])
        self.assertEqual(told['status'], 'reported')            # aus einer Sitzung höchstens Angabe
        self.assertEqual(birth['kind'], 'birth')
        self.assertNotIn('age', birth)                           # Zahl nicht im Zitat
        self.assertEqual(move['status'], 'uncertain')            # nie invented
        self.assertNotIn('date', move)                           # Jahr nicht im Zitat
        self.assertGreaterEqual(dropped, 2)

    def test_combine_links_two_dates_and_apply(self):
        items, _ = self.verified()
        data, body = analyze.chronology_combine(self.base, self.config, {'src-1': items}, [True], None, None)
        rows = data['items']
        self.assertEqual([r['n'] for r in rows], [1, 2, 3, 4])
        later = next(r for r in rows if r.get('date') == '1949')
        self.assertTrue(later.get('same_as_n'))
        choices = [{'index': i} for i, r in enumerate(rows)]
        changed = analyze.apply_chronology(self.base, self.config, data, choices)
        self.assertEqual(changed, ['story/chronology.yml'])
        entries = chronology.read(self.base)['entries']
        self.assertEqual([e['id'] for e in entries], ['chr-001', 'chr-002', 'chr-003', 'chr-004'])
        by_date = {e.get('date'): e for e in entries}
        self.assertEqual(by_date['1949']['same_as'], by_date['1948-06-12']['id'])
        self.assertEqual(validate_project.story_errors(self.base, load(self.base)[1]), [])
        kinds = {f['kind'] for f in chronology.findings(chronology.read(self.base))}
        self.assertIn('source', kinds)
        again, _ = analyze.chronology_combine(self.base, self.config, {'src-1': items}, [True], None, None)
        self.assertTrue(all(r.get('existing') for r in again['items']))   # „schon da“

    def test_background_run_without_manuscript(self):
        seen = []

        def fake(provider, key, model, system, user, kind, step='extract'):
            seen.append(user)
            return json.dumps(self.answer(), ensure_ascii=False), 100, 50
        with patch.object(analyze, 'call_llm', side_effect=fake), patch.object(analyze, 'pick_provider', return_value=('anthropic', 'k')):
            head = analyze.run(self.base, 'chronology')
        self.assertEqual(head['suggestions'], 4)
        self.assertNotIn('Küchentisch', seen[0])
        self.assertIn(SOURCES, seen[0])
        import render_view
        data = json.loads((self.base / 'analysis/chronology' / f'{head["id"]}.json').read_text(encoding='utf-8'))

        class A:
            text = True
        view = render_view.chronology_suggest_view(self.base, self.config, A(), data, '')
        self.assertIn('Chronologie-Vorschläge', view)
        self.assertIn('| 1 |', view)
        A.text = False
        widget = render_view.chronology_suggest_view(self.base, self.config, A(), data, '')
        self.assertEqual(widget.template, 'chronologie-vorschlag')
        self.assertEqual(widget.data['ENTRIES'][0]['C_STATUS'], 'reported')   # Geburt 1930 aus der Figurendatei
        self.assertEqual(widget.data['ENTRIES'][0]['C_DATE'], '1930')
        changed = analyze.apply(self.base, head['id'], 'chronology', [{'index': 0, 'status': 'reported'}])
        self.assertEqual(changed, ['story/chronology.yml'])
        self.assertEqual(chronology.read(self.base)['entries'][0]['status'], 'reported')
        self.assertIsNone(analyze.latest(self.base, 'chronology'))

    def test_chat_path_common_and_chapter(self):
        request = ca.prepare(self.base, 'chronology', 0, 'a' * 40, self.root / 'req.json')
        self.assertIn(SOURCES, request['snapshot']['texts'])
        response = self.root / 'resp.json'
        response.write_text(ca.canonical({'request_id': request['request_id'], 'kind': 'chronology', 'answer': self.answer()}))
        path, result = ca.accept(self.base, self.root / 'req.json', response)
        self.assertEqual(len(result['verified']), 4)
        self.assertTrue(analyze.chat_run_of(self.base, result))
        with self.assertRaises(ValueError):
            ca.prepare(self.base, 'chronology', 1, 'a' * 40, self.root / 'req2.json')   # Kapitel 1 ohne Rechercheläufe
        with self.assertRaises(ValueError):
            ca.prepare(self.base, 'summaries', 0, 'a' * 40, self.root / 'req3.json')


    def test_chat_path_in_parts(self):   # #450: zu umfangreich → in Teilen statt Abbruch
        with patch.object(ca, 'CHRONOLOGY_CHAT_CHARS', 120):
            with self.assertRaisesRegex(ValueError, r'in (\d+) Teilen vorbereiten \(--part 1'):
                ca.prepare(self.base, 'chronology', 0, 'a' * 40, self.root / 'big.json')
            parts = ca.chronology_parts(dict(analyze.chronology_units(self.base, self.config, 'common')))
            self.assertGreater(len(parts), 1)
            seen = {}
            for n in range(1, len(parts) + 1):
                req = ca.prepare(self.base, 'chronology', 0, 'a' * 40, self.root / f'part-{n}.json', part=n)
                self.assertEqual(req['part'], n)
                self.assertIn(f'Teil {n} von {len(parts)}', req['snapshot']['title'])
                seen.update(req['snapshot']['texts'])
            self.assertEqual(seen, dict(analyze.chronology_units(self.base, self.config, 'common')))
            with self.assertRaisesRegex(ValueError, 'gibt es nicht'):
                ca.prepare(self.base, 'chronology', 0, 'a' * 40, self.root / 'x.json', part=len(parts) + 1)
            req = json.loads((self.root / 'part-1.json').read_text(encoding='utf-8'))
            response = self.root / 'resp-1.json'
            response.write_text(ca.canonical({'request_id': req['request_id'], 'kind': 'chronology', 'answer': {'items': []}}))
            ca.accept(self.base, self.root / 'part-1.json', response)   # Teil wird beim Annehmen gleich wieder gelesen
        with self.assertRaisesRegex(ValueError, '--part nur'):
            ca.prepare(self.base, 'summaries', 1, 'a' * 40, self.root / 'y.json', part=1)

if __name__ == '__main__':
    unittest.main()
