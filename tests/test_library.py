"""Bibliothek (#36): Erkennungsregel, Namen, Eindeutigkeit der Kurztitel, Git-Auflistung."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import library  # noqa: E402

MANIFEST = yaml.safe_load((ROOT / 'ghostwriter-manifest.yml').read_text(encoding='utf-8'))
STARTER = {'project': {'title': '', 'title_short': ''}, 'structure': {'chapters': []}}


def book(short, chapters=True):
    return {'project': {'title': short + ' – das Buch', 'title_short': short},
            'structure': {'chapters': [{'id': 'ch-01'}] if chapters else []}}


class RuleTest(unittest.TestCase):
    def test_rule(self):
        cases = {
            ('buch/adhs', 'starter'): True,           # neu angelegt, Wizard läuft
            ('buch/adhs', 'book'): True,
            ('buch/ohne-datei', None): False,         # keine ghostwriter.yml
            ('test/test-book', 'book'): True,         # Altbestand mit Kapiteln
            ('feature/x', 'starter'): False,          # anderer Branch ohne Kapitel
            ('main', 'book'): False,                  # skip_branches (Hauptrepository)
            ('ghostwriter/buch/adhs', 'book'): False, # Arbeits-Branch
            ('v0.5', 'book'): False,
        }
        cfgs = {'starter': STARTER, 'book': book('ADHS'), None: None}
        for (name, kind), want in cases.items():
            with self.subTest(name=name, kind=kind):
                self.assertEqual(library.is_book(name, cfgs[kind], MANIFEST), want)

    def test_single_book_default_branch(self):
        # Im eigenen Buch-Repository (Fork) ist der Standard-Branch selbst ein Buch, wenn er nicht in skip steht
        m = dict(MANIFEST, update={'skip_branches': ['ghostwriter/*']})
        self.assertTrue(library.is_book('main', book('X'), m))
        self.assertFalse(library.is_book('main', STARTER, m))   # Bibliotheksmodus: main nur Programm

    def test_names(self):
        self.assertEqual(library.slug('Über Mut & Größe'), 'ueber-mut-groesse')
        self.assertEqual(library.book_branch('ADHS im Alltag', MANIFEST), 'buch/adhs-im-alltag')
        self.assertEqual(library.work_branch('buch/adhs', MANIFEST), 'ghostwriter/buch/adhs')

    def test_name_check_and_duplicates(self):
        found = library.books({'buch/adhs': book('ADHS'), 'test/test-book': book('Mut'), 'main': book('Z')}, MANIFEST)
        self.assertEqual([b['branch'] for b in found], ['buch/adhs', 'test/test-book'])
        self.assertEqual(library.name_check('Neu', found, MANIFEST)['taken'], [])
        self.assertTrue(library.name_check('ADHS', found, MANIFEST)['taken'])          # Branch vergeben
        self.assertTrue(library.name_check('mut', found, MANIFEST)['taken'])           # Tag-Slug vergeben
        self.assertTrue(library.name_check('!!!', found, MANIFEST)['taken'])
        self.assertEqual(library.duplicates(found), {})
        found.append(library.describe('buch/mut', book('MUT'), MANIFEST))
        self.assertEqual(library.duplicates(found), {'mut': ['test/test-book', 'buch/mut']})

    def test_status(self):
        self.assertEqual(library.describe('buch/a', STARTER, MANIFEST)['status'], 'setup')
        self.assertEqual(library.describe('buch/a', book('A'), MANIFEST)['status'], 'ready')


class GitTest(unittest.TestCase):
    def test_list_and_check_in_repo(self):
        with tempfile.TemporaryDirectory() as d:
            def g(*a):
                subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=d, check=True, capture_output=True)

            def commit(branch, cfg):
                g('checkout', '-q', '-B', branch, 'main') if branch != 'main' else None
                Path(d, 'ghostwriter.yml').write_text(yaml.safe_dump(cfg), encoding='utf-8')
                g('add', '.')
                g('commit', '-q', '--allow-empty', '-m', branch)
            g('init', '-q', '-b', 'main')
            commit('main', STARTER)
            commit('buch/adhs', book('ADHS'))
            commit('buch/neu', STARTER)
            commit('buch/zweit', book('adhs'))
            run = lambda *a: subprocess.run([sys.executable, str(ROOT / 'scripts/library.py'), *a,
                                             '--namespace', 'refs/heads', '--repo', d], capture_output=True, text=True)
            r = run('list', '--json')
            self.assertEqual([b['branch'] for b in json.loads(r.stdout)], ['buch/adhs', 'buch/neu', 'buch/zweit'])
            c = run('check')
            self.assertEqual(c.returncode, 1)
            self.assertIn('adhs', c.stdout)
            self.assertEqual(run('name', 'Ganz neu').returncode, 0)
            self.assertEqual(run('name', 'ADHS').returncode, 1)


if __name__ == '__main__':
    unittest.main()
