"""Tests für die Übergabe zwischen Gespräch und Manuskriptarbeit (#315) und work_modes im Profil."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import assistant  # noqa: E402
import handover  # noqa: E402


def git(base, *args):
    return subprocess.run(['git', '-C', str(base), '-c', 'user.name=t', '-c', 'user.email=t@example.org', *args],
                          capture_output=True, text=True, check=True).stdout.strip()


class HandoverTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        shutil.copy(ROOT / 'ghostwriter-manifest.yml', self.base)
        (self.base / 'conversations/s1/decisions').mkdir(parents=True)
        (self.base / 'conversations/s1/decisions/latest.json').write_text('{}', encoding='utf-8')
        git(self.base, 'init', '-q', '-b', 'buch/adhs')
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-qm', 'Buch')
        config = yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        self.path = config['structure']['chapters'][0]['sections'][1]['path']   # Abschnitt 1.2
        git(self.base, 'switch', '-q', '-c', 'ghostwriter/arbeit')
        self.edit(self.path, 'Arbeitsfassung')
        git(self.base, 'switch', '-q', 'buch/adhs')
        git(self.base, 'update-ref', 'refs/remotes/origin/ghostwriter/chat/s2', 'HEAD')   # offene Gesprächssicherung

    def edit(self, path, text):
        with open(self.base / path, 'a', encoding='utf-8') as f:
            f.write('\n' + text + '\n')
        git(self.base, 'commit', '-qam', text)

    def state(self, **kw):
        return handover.collect(self.base, 'buch/adhs', 'ghostwriter/arbeit', 12, '1.2', repo='owner/buch', **kw)

    def test_origin_references_and_explicit_local_refs_remain_distinct(self):
        git(self.base, 'remote', 'add', 'origin', 'https://example.invalid/test.git')
        local = git(self.base, 'rev-parse', 'ghostwriter/arbeit')
        remote = git(self.base, 'rev-parse', 'buch/adhs')
        git(self.base, 'update-ref', 'refs/remotes/origin/ghostwriter/arbeit', remote)
        self.assertEqual(handover.resolve(self.base, 'ghostwriter/arbeit'), remote)
        self.assertEqual(handover.resolve(self.base, 'origin/ghostwriter/arbeit'), remote)
        self.assertEqual(handover.resolve(self.base, 'refs/heads/ghostwriter/arbeit'), local)
        git(self.base, 'tag', 'lokaler-test', local)
        self.assertEqual(handover.resolve(self.base, 'refs/tags/lokaler-test'), local)
        self.assertEqual(handover.resolve(self.base, local), local)
        git(self.base, 'update-ref', '-d', 'refs/remotes/origin/ghostwriter/arbeit')
        self.assertIsNone(handover.resolve(self.base, 'ghostwriter/arbeit'))
        self.assertIsNone(handover.resolve(self.base, 'origin/ghostwriter/arbeit'))

    def test_cli_fetch_prunes_removed_work_branch(self):
        remote = self.base.parent / 'remote.git'
        subprocess.run(['git', 'clone', '--quiet', '--bare', str(self.base), str(remote)], check=True)
        git(self.base, 'remote', 'add', 'origin', str(remote))
        git(self.base, 'fetch', '-q', 'origin')
        path = self.base.parent / 'handover.json'
        path.write_text(json.dumps(self.state()))
        git(remote, 'branch', '-qD', 'ghostwriter/arbeit')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/handover.py'),
                                 str(self.base), 'check', str(path), '--fetch', '--json'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIsNone(handover.resolve(self.base, 'ghostwriter/arbeit'))

    def test_removed_merged_work_can_be_refreshed_from_book(self):
        state = self.state()
        git(self.base, 'merge', '-q', '--no-ff', '-m', 'Übernahme', 'ghostwriter/arbeit')
        git(self.base, 'branch', '-qD', 'ghostwriter/arbeit')
        result = handover.check(self.base, state)
        self.assertEqual(result['state'], 'refresh')
        self.assertEqual(result['exit'], 1)
        self.assertTrue(any('übernommen' in reason for reason in result['reasons']))

    def test_collect_and_markdown(self):
        st = self.state()
        self.assertEqual(st['book']['branch'], 'buch/adhs')
        self.assertEqual(st['work']['pr'], 12)
        self.assertEqual(st['section']['path'], self.path)
        self.assertEqual(st['section']['status'], 'writing')
        work_text = git(self.base, 'show', f'ghostwriter/arbeit:{self.path}') + '\n'
        import hashlib
        self.assertEqual(st['section']['sha256'], hashlib.sha256(work_text.encode()).hexdigest())   # Stand des Arbeitsbranches
        self.assertEqual(st['open_count'], 9)   # offene Abschnitte desselben Kapitels
        self.assertEqual(st['sessions']['accepted'], [{'path': 'conversations/s1', 'topics': ['decisions']}])
        self.assertEqual(st['sessions']['open'], [{'branch': 'ghostwriter/chat/s2'}])
        md = handover.markdown(st)
        for text in ('## Übergabe: Manuskriptarbeit an Abschnitt 1.2', '**Starttext:**', '`owner/buch`',
                     'Pull Request #12', '**Nicht gespeichert**', 'gibt nichts frei', '`ghostwriter/chat/s2`'):
            self.assertIn(text, md)
        self.assertEqual(handover.parse(md), json.loads(json.dumps(st)))
        self.assertIn('Gespräch an das Buch', handover.markdown(handover.collect(self.base, 'buch/adhs', mode='gespraech')))

    def test_decisions_and_tasks_from_backups(self):
        """Teil 2 von #315: Entscheidungen und offene Aufgaben aus übernommenen und offenen Sicherungen."""
        folder = self.base / 'conversations/s1'
        (folder / 'decisions/latest.json').write_text(json.dumps('Mara bleibt   Ich-Erzählerin.') + '\n', encoding='utf-8')
        (folder / 'planning').mkdir()
        (folder / 'planning/latest.json').write_text(json.dumps('Szene am Hafen ' * 80) + '\n', encoding='utf-8')
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-qm', 'Sicherung übernommen')
        git(self.base, 'switch', '-q', '-c', 'chat-s2')
        (self.base / 'conversations/s2/decisions').mkdir(parents=True)
        (self.base / 'conversations/s2/decisions/latest.json').write_text(json.dumps('Schluss offen lassen'), encoding='utf-8')
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-qm', 'Sicherung offen')
        git(self.base, 'update-ref', 'refs/remotes/origin/ghostwriter/chat/s2', 'HEAD')
        git(self.base, 'switch', '-q', 'buch/adhs')
        st = self.state()
        acc = st['sessions']['accepted'][0]
        self.assertEqual(acc['decisions'], 'Mara bleibt Ich-Erzählerin.')
        self.assertTrue(acc['planning'].endswith(' …'))
        self.assertLessEqual(len(acc['planning']), handover.MAX_TOPIC + 2)
        self.assertEqual(st['sessions']['open'], [{'branch': 'ghostwriter/chat/s2', 'decisions': 'Schluss offen lassen'}])
        md = handover.markdown(st)
        for text in ('**Entscheidungen aus den Sicherungen**', '- `conversations/s1`: Mara bleibt Ich-Erzählerin.',
                     '- `ghostwriter/chat/s2` (nicht übernommen): Schluss offen lassen', '**Offene Aufgaben aus den Sicherungen**'):
            self.assertIn(text, md)
        self.assertEqual(handover.parse(md), json.loads(json.dumps(st)))

    def test_check_states(self):
        md = handover.markdown(self.state())
        self.assertEqual(handover.check(self.base, handover.parse(md))['state'], 'ok')
        # Fremde Datei im Buch geändert: weiter, mit Hinweis
        self.edit('chapters/01-endlich-eine-erklaerung/README.md', 'Kapiteltext')
        result = handover.check(self.base, handover.parse(md))
        self.assertEqual(result['state'], 'ok')
        self.assertIn('nicht in den betroffenen Dateien', result['reasons'][0])
        # Neuere Fassung im Arbeitsbranch
        git(self.base, 'switch', '-q', 'ghostwriter/arbeit')
        self.edit(self.path, 'weiter')
        result = handover.check(self.base, handover.parse(md))
        self.assertEqual((result['state'], result['exit']), ('refresh', 1))
        self.assertTrue(any('neuere Commits' in r for r in result['reasons']))
        # Auseinandergelaufen: nicht schreiben
        git(self.base, 'reset', '-q', '--hard', 'HEAD~2')
        self.edit(self.path, 'anders')
        result = handover.check(self.base, handover.parse(md))
        self.assertEqual((result['state'], result['exit']), ('conflict', 2))
        git(self.base, 'switch', '-q', 'buch/adhs')

    def test_book_only_and_unknown_commit(self):
        st = handover.collect(self.base, 'buch/adhs', section='1.2')
        self.edit(self.path, 'im Buch geändert')
        result = handover.check(self.base, st)
        self.assertEqual(result['state'], 'refresh')
        self.assertTrue(any(self.path in r for r in result['reasons']))
        st['book']['head'] = '0' * 40
        self.assertEqual(handover.check(self.base, st)['state'], 'conflict')
        with self.assertRaises(ValueError):
            handover.parse('kein Block')
        with self.assertRaises(ValueError):
            handover.collect(self.base, 'buch/adhs', section='99.1')

    def test_cli(self):
        script = str(ROOT / 'scripts/handover.py')
        out = subprocess.run([sys.executable, script, str(self.base), '--work-branch', 'ghostwriter/arbeit',
                              '--section', '1.2'], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        file = self.base.parent / 'uebergabe.md'
        file.write_text(out.stdout, encoding='utf-8')
        r = subprocess.run([sys.executable, script, str(self.base), 'check', str(file)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('✓ Übergabe aktuell', r.stdout)
        git(self.base, 'switch', '-q', 'ghostwriter/arbeit')
        self.edit(self.path, 'weiter')
        r = subprocess.run([sys.executable, script, str(self.base), 'check', '-'], input=out.stdout,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('Neuere Fassung', r.stdout)
        # Lesend: Arbeitsverzeichnis unverändert
        self.assertEqual(git(self.base, 'status', '--porcelain'), '')


class WorkModesProfileTest(unittest.TestCase):
    def skill(self, **fields):
        with tempfile.TemporaryDirectory() as tmp:
            prof, errs, result = assistant.set_profile(Path(tmp), dict({'repo': 'owner/buch', 'author': 'A'}, **fields))
            if errs:
                return errs
            return (Path(tmp) / result['files'][1]).read_text(encoding='utf-8')

    def test_line_only_when_set(self):
        self.assertIn('automatisch nach Auftrag wechseln', self.skill(work_modes='auto'))
        self.assertIn('einmal fragen', self.skill(work_modes='ask'))
        self.assertNotIn('#315', self.skill())   # bestehende Profile: Skill bleibt unverändert gültig
        self.assertIn("'manual' is not one of", self.skill(work_modes='manual')[0])


if __name__ == '__main__':
    unittest.main()
