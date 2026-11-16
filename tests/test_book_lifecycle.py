"""A01/A02: lokaler Buchlebenszyklus mit fiktiven Daten, ohne GitHub-Zugriff.

Die Dateien für bestätigte Schritte werden wie im Chatworkflow geschrieben.
Dies prüft die vorhandenen Validatoren/Assembler und echte lokale Git-Stände,
nicht die Identität eines Benutzers oder eine serverseitige Rollenprüfung.
"""
import hashlib
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import assemble
import library
import validate_project
from render_view import load
from workflow_support import assess_write, compare_book_work


class BookLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'library'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Fiktiver Testautor')
        self.git('config', 'user.email', 'test@example.invalid')
        shutil.copy(ROOT / 'templates/ghostwriter-starter.yml', self.repo / 'ghostwriter.yml')
        shutil.copy(ROOT / 'ghostwriter-manifest.yml', self.repo / 'ghostwriter-manifest.yml')
        self.write_yaml('approvals.yml', {'entries': []})
        self.git('add', '.')
        self.git('commit', '-qm', 'Leere Testbibliothek')
        self.main = self.git('rev-parse', 'main')
        # Zweites Buch als unabhängigen Stand erhalten.
        other = library.create_book('Zweites Testbuch', 'Zweites', cwd=self.repo, namespace='refs/heads', base='main')
        self.assertEqual(other['taken'], [])
        self.other = other['branch']
        self.other_head = self.git('rev-parse', self.other)
        self.git('switch', '-q', 'main')
        new = library.create_book('Der rote Kiesel', 'Kiesel', 'Testautor', cwd=self.repo, namespace='refs/heads', base='main')
        self.assertEqual(new['taken'], [])
        self.book = new['branch']
        self.work = 'ghostwriter/' + self.book
        self.book_start = self.git('rev-parse', 'HEAD')
        self.assertEqual(self.git('rev-list', '--count', 'main..HEAD'), '1')
        self.git('switch', '-q', '-c', self.work)
        self.cfg = yaml.safe_load((self.repo / 'ghostwriter.yml').read_text())
        self.cfg['project']['title'] = 'Der rote Kiesel'
        self.cfg['structure']['chapters'] = [{
            'id': 'ch-kiesel', 'title': 'Am Bach', 'path': 'chapters/01-am-bach',
            'status': 'in_progress', 'sections': [{
                'id': 'sec-kiesel', 'title': 'Der Fund', 'path': 'chapters/01-am-bach/sections/01-fund.md'}]}]
        self.section = self.cfg['structure']['chapters'][0]['sections'][0]['path']
        self.head = {'id': 'sec-kiesel', 'number': '1.1', 'title': 'Der Fund',
                     'status': 'planned', 'fact_check': 'optional',
                     'approvals': {'writing': False, 'section': False}}
        self.manuscript = 'Noch nicht begonnen.'
        self.ledger = {'entries': []}
        self.save_state()
        (self.repo / 'chapters/01-am-bach/README.md').write_text(
            '# Kapitel 1 – Am Bach\n\n## Ziel des Kapitels\n\nEin Fund.\n\n## Kurzbeschreibung\n\nEine fiktive Szene.\n')
        self.commit('Fiktive Struktur angelegt')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def write_yaml(self, path, value):
        (self.repo / path).write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False))

    def save_state(self):
        self.write_yaml('ghostwriter.yml', self.cfg)
        self.write_yaml('approvals.yml', self.ledger)
        p = self.repo / self.section
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('---\n' + yaml.safe_dump(self.head, allow_unicode=True, sort_keys=False) +
                     '---\n\n# 1.1 Der Fund\n\n## Ziel des Abschnitts\n\nEin Fund.\n\n'
                     '## Kurzbeschreibung\n\nEine fiktive Szene.\n\n## Manuskript\n\n' + self.manuscript + '\n')

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-qm', message)
        return self.git('rev-parse', 'HEAD')

    def record(self, kind, action, note=None):
        entry = {'kind': kind, 'id': 'ch-kiesel' if kind == 'chapter' else 'sec-kiesel',
                 'action': action, 'at': '2026-11-16T12:00:00Z', 'by': 'fiktiver-testautor',
                 'commit': self.git('rev-parse', 'HEAD')}
        if note:
            entry['note'] = note
        self.ledger['entries'].append(entry)

    def problems(self):
        _, cfg = load(self.repo)
        return assemble.problems(assemble.book_parts(self.repo, cfg), cfg)

    def complete_local_lifecycle(self):
        self.assertTrue(self.problems())
        self.assertEqual(validate_project.check_project(self.repo), [])
        # Simulierte ausdrückliche Schreibfreigabe, dann Text und Überarbeitung.
        self.record('writing', 'granted')
        self.head.update(status='writing', approvals={'writing': True, 'section': False})
        self.manuscript = 'Mira fand am Bach einen roten Kiesel.'
        self.save_state()
        first = self.commit('Schreibfreigabe und erster Testentwurf')
        self.manuscript = 'Mira hob den roten Kiesel aus dem flachen Wasser.'
        self.save_state()
        current = self.commit('Fiktiven Abschnitt überarbeitet')
        self.assertFalse(assess_write(self.repo, first, current, [self.section])['safe_to_prepare'])
        # Ein noch nicht übernommener Entwurf ist kein Buchstand.
        self.assertNotIn('chapters/', self.git('ls-tree', '-r', '--name-only', self.book))
        self.assertTrue(self.problems())
        self.head.update(status='approved', approvals={'writing': True, 'section': True})
        digest = hashlib.sha256(self.manuscript.encode()).hexdigest()
        self.record('section', 'granted', 'content_sha256=' + digest)
        self.cfg['structure']['chapters'][0]['status'] = 'approved'
        self.record('chapter', 'granted')
        self.save_state()
        self.commit('Abschnitt und Kapitel im Test bestätigt')
        self.assertEqual(validate_project.check_project(self.repo), [])
        self.assertEqual(self.problems(), [])
        # Manipulation nach Abschluss muss den Export blockieren.
        path = self.repo / self.section
        saved = path.read_text()
        path.write_text(saved.replace(self.manuscript, self.manuscript + ' Unbestätigter Nachtrag.'))
        self.assertTrue(self.problems())
        self.assertTrue(validate_project.check_project(self.repo))
        path.write_text(saved)
        # Ausdrückliches Wiederöffnen: alte Einträge bleiben erhalten.
        old_entries = list(self.ledger['entries'])
        self.record('section', 'revoked')
        self.record('chapter', 'revoked')
        self.record('writing', 'revoked')
        self.head.update(status='revision', approvals={'writing': False, 'section': False})
        self.cfg['structure']['chapters'][0]['status'] = 'in_progress'
        self.save_state()
        self.commit('Im Test wieder geöffnet')
        self.assertEqual(validate_project.check_project(self.repo), [])
        self.assertTrue(self.problems())
        self.assertEqual(self.ledger['entries'][:len(old_entries)], old_entries)
        self.record('writing', 'granted')
        self.manuscript = 'Mira legte den roten Kiesel auf das trockene Ufer.'
        self.head.update(status='writing', approvals={'writing': True, 'section': False})
        self.save_state()
        self.commit('Nach erneuter Schreibfreigabe geändert')
        self.head.update(status='approved', approvals={'writing': True, 'section': True})
        self.record('section', 'granted', 'content_sha256=' + hashlib.sha256(self.manuscript.encode()).hexdigest())
        self.cfg['structure']['chapters'][0]['status'] = 'approved'
        self.record('chapter', 'granted')
        self.save_state()
        final = self.commit('Erneuten Abschluss im Test protokolliert')
        self.assertEqual(validate_project.check_project(self.repo), [])
        self.assertEqual(self.problems(), [])
        changes = compare_book_work(self.repo, self.book, self.work)
        self.assertTrue(changes['files'])
        self.assertTrue(all(f['state'] == 'nur_arbeitsfassung' for f in changes['files']))
        self.git('switch', '-q', self.book)
        self.git('merge', '--no-ff', '-qm', 'Teständerungen ausdrücklich übernommen', self.work)
        self.assertEqual(self.git('rev-parse', 'HEAD^{tree}'), self.git('rev-parse', final + '^{tree}'))
        self.assertEqual(self.git('rev-parse', 'main'), self.main)
        self.assertEqual(self.git('rev-parse', self.other), self.other_head)
        self.assertEqual(self.problems(), [])
        # Lokaler Auflagen-Tag bleibt bei nachfolgenden Arbeitsänderungen unverändert.
        self.git('tag', 'kiesel-auflage-1')
        edition = self.git('rev-parse', 'kiesel-auflage-1')
        self.git('switch', '-q', self.work)
        self.git('commit', '--allow-empty', '-qm', 'Spätere Testarbeit')
        self.assertEqual(self.git('rev-parse', 'kiesel-auflage-1'), edition)
        self.assertNotEqual(self.git('rev-parse', self.work), final)
        self.git('switch', '-q', self.book)
        return edition

    def test_new_book_edit_reopen_merge_and_preserved_edition(self):
        self.complete_local_lifecycle()

    @unittest.skipUnless(shutil.which('pandoc') and importlib.util.find_spec('docx'),
                         'pandoc und python-docx für EPUB/DOCX-Export nötig')
    def test_local_lifecycle_exports_proof_and_edition(self):
        self.complete_local_lifecycle()
        before = self.git('status', '--porcelain')
        for proof in (True, False):
            out = Path(self.temp.name) / ('proof' if proof else 'edition')
            args = ['--proof'] if proof else ['--edition', '1', '--date', '2026-11-16']
            run = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.repo),
                                  *args, '--formats', 'docx,epub', '--out', str(out)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual({p.suffix for p in out.iterdir()}, {'.yml', '.epub', '.docx'})
        self.assertEqual(self.git('status', '--porcelain'), before)
