"""#480: Hintergrund-Warteschlange – Reihenfolge, Speichern je Auftrag, Budget, Fehler, Startwege."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import jobs  # noqa: E402
import research  # noqa: E402

SECTION = '---\nid: {id}\nnumber: "{n}"\ntitle: T\nstatus: planned\napprovals:\n  writing: false\n  section: false\n---\n\n# {n}\n'


def git(cwd, *args):
    return subprocess.run(['git', '-c', 'user.name=T', '-c', 'user.email=t@t', *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.origin = root / 'origin.git'
        self.base = root / 'buch'
        git(root, 'init', '-q', '--bare', '-b', 'main', str(self.origin))
        git(root, 'clone', '-q', str(self.origin), str(self.base))
        chapters = []
        for c in (1, 2):
            secs = []
            for s in (1, 2):
                sid = f'sec-0{c}-0{s}'
                path = f'chapters/ch-0{c}/sections/{sid}.md'
                (self.base / path).parent.mkdir(parents=True, exist_ok=True)
                (self.base / path).write_text(SECTION.format(id=sid, n=f'{c}.{s}'), encoding='utf-8')
                secs.append({'id': sid, 'title': 'T', 'path': path})
            chapters.append({'id': f'ch-0{c}', 'title': 'K', 'path': f'chapters/ch-0{c}', 'sections': secs})
        (self.base / 'ghostwriter.yml').write_text(yaml.safe_dump({'project': {'title': 'B'}, 'structure': {'chapters': chapters}}),
                                                   encoding='utf-8')
        git(self.base, 'add', '.')
        git(self.base, 'commit', '-qm', 'Buch')
        git(self.base, 'push', '-q', 'origin', 'HEAD:refs/heads/ghostwriter/buch/b')
        git(self.base, 'config', 'user.name', 'T')
        git(self.base, 'config', 'user.email', 't@t')
        self.calls = []

    def add(self, sid, at, **extra):
        return jobs.enqueue(self.base, section=sid, now=__import__('datetime').datetime.fromisoformat(at), **extra)

    def fake_run(self, fail=None, crash=None):
        def run(base, sid, question, provider, model, defaults, now, request=None):
            self.calls.append((sid, request, provider))
            if fail and sid == fail:
                raise research.ResearchError('Anbieter antwortet nicht')
            if crash and sid == crash:
                raise KeyboardInterrupt   # Abbruch mitten im Lauf
            folder = next(Path(base).glob(f'chapters/*/research/{sid}'))
            n = len(list(folder.glob('run-*.md'))) + 1
            (folder / f'run-{n:03d}.md').write_text(f'---\nrequest: {request}\n---\n', encoding='utf-8')
            return {'path': str((folder / f'run-{n:03d}.md').relative_to(base)), 'number': sid, 'searches': 1,
                    'sources': 1, 'cost': None}
        return mock.patch.object(research, 'run', side_effect=run)

    def remote_files(self, pattern):
        out = git(self.base, 'ls-tree', '-r', '--name-only', 'origin/ghostwriter/buch/b')
        return sorted(p for p in out.splitlines() if pattern in p)



class QueueTest(Base):
    def test_order_book_then_time(self):
        self.add('sec-02-01', '2026-11-22T20:00:00+00:00')
        self.add('sec-01-02', '2026-11-22T21:00:00+00:00')
        self.add('sec-01-02', '2026-11-22T20:30:00+00:00')
        self.add('sec-01-01', '2026-11-22T22:00:00+00:00')
        order = [(j['section_id'], j['data']['requested_at'][11:16]) for j in jobs.queue(self.base)]
        self.assertEqual(order, [('sec-01-01', '22:00'), ('sec-01-02', '20:30'), ('sec-01-02', '21:00'), ('sec-02-01', '20:00')])

    def test_each_job_saved_and_pushed_abort_keeps_first(self):
        """Abnahme #480: drei Aufträge, Abbruch im zweiten erhält den ersten; der nächste Lauf erledigt den Rest."""
        for sid, at in (('sec-01-01', '20:00'), ('sec-01-02', '20:01'), ('sec-02-01', '20:02')):
            self.add(sid, f'2026-11-22T{at}:00+00:00', provider='google')
        with self.fake_run(crash='sec-01-02'), mock.patch.object(jobs, 'budget_low', return_value=False):
            with self.assertRaises(KeyboardInterrupt):
                jobs.process(self.base, push_to='ghostwriter/buch/b')
        git(self.base, 'fetch', '-q', 'origin')
        self.assertEqual(self.remote_files('run-'), ['chapters/ch-01/research/sec-01-01/run-001.md'])
        self.assertEqual(self.calls[0], ('sec-01-01', 'request-001', 'google'))   # Anbieter aus dem Auftrag
        git(self.base, 'checkout', '-q', '--', '.')
        with self.fake_run(), mock.patch.object(jobs, 'budget_low', return_value=False):
            results, remaining = jobs.process(self.base, push_to='ghostwriter/buch/b')
        git(self.base, 'fetch', '-q', 'origin')
        self.assertEqual([r['ok'] for r in results], [True, True])
        self.assertEqual(remaining, 0)
        self.assertEqual(len(self.remote_files('run-')), 3)
        self.assertEqual(self.remote_files('request-'), [])
        self.assertGreaterEqual(int(git(self.base, 'rev-list', '--count', 'origin/ghostwriter/buch/b')), 4)   # je Auftrag ein Commit

    def test_error_does_not_stop_and_limit_leaves_rest(self):
        for sid in ('sec-01-01', 'sec-01-02', 'sec-02-01', 'sec-02-02'):
            self.add(sid, '2026-11-22T20:00:00+00:00')
        with self.fake_run(fail='sec-01-02'), mock.patch.object(jobs, 'budget_low', return_value=False):
            results, remaining = jobs.process(self.base, limit=3, commit=False)
        self.assertEqual([r['ok'] for r in results], [True, False, True])
        self.assertEqual(remaining, 1)
        failed = [j for j in jobs.jobs(self.base) if j['state'] == 'failed']
        self.assertIn('antwortet nicht', failed[0]['data']['error'])
        self.assertIn('failed_at', failed[0]['data'])

    def test_budget_waits_for_confirmation(self):
        path = self.add('sec-01-01', '2026-11-22T20:00:00+00:00')
        self.add('sec-01-02', '2026-11-22T20:00:00+00:00', confirm_low_budget=True)
        with self.fake_run(), mock.patch.object(jobs, 'budget_low', return_value=True):
            results, remaining = jobs.process(self.base, commit=False)
        self.assertEqual([(r['ok'], r.get('waiting', False)) for r in results], [(False, True), (True, False)])
        self.assertEqual(remaining, 0)                                # wartende laufen nicht im Kreis
        self.assertEqual(yaml.safe_load(path.read_text())['waiting'], 'budget')
        self.assertEqual([j['state'] for j in jobs.jobs(self.base)], ['waiting_budget'])
        data = yaml.safe_load(path.read_text())
        data['confirm_low_budget'] = True                              # „Trotzdem starten“
        path.write_text(yaml.safe_dump(data))
        self.assertEqual(len(jobs.queue(self.base)), 1)

    def test_three_dispatches_lose_nothing_and_schema(self):
        import json
        from jsonschema import Draft202012Validator
        schema = Draft202012Validator(json.loads((ROOT / 'schemas/job.schema.json').read_text()))
        for _ in range(3):
            jobs.main([str(self.base), 'enqueue', '--section', 'sec-01-01', '--question', 'Q', '--requested-by', 'workflow_dispatch'])
        files = jobs.files(self.base)
        self.assertEqual([p.name for p in files], ['request-001.yml', 'request-002.yml', 'request-003.yml'])
        for p in files:
            data = yaml.safe_load(p.read_text())
            self.assertEqual(list(schema.iter_errors(data)), [])
            self.assertEqual((data['type'], data['requested_by']), ('research', 'workflow_dispatch'))
        self.assertTrue(list(schema.iter_errors({'type': 'research'})))   # Recherche braucht den Abschnitt
        self.assertEqual(list(schema.iter_errors({'section_id': 's', 'provider': 'google'})), [])   # Aufträge der App ohne type

    def test_key_per_provider(self):
        with mock.patch.dict(os.environ, {'GHOSTWRITER_RESEARCH_KEY_GOOGLE': 'g', 'GHOSTWRITER_RESEARCH_KEY_OPENAI': ''}, clear=False):
            self.assertEqual(research.api_key('google'), 'g')
            self.assertEqual(research.api_key('anthropic'), '')
        env = {k: v for k, v in os.environ.items() if not k.startswith(research.KEY_ENV)}
        with mock.patch.dict(os.environ, dict(env, GHOSTWRITER_RESEARCH_KEY='x'), clear=True):
            self.assertEqual(research.api_key('google'), 'x')   # alter Weg: ein Schlüssel


class RemoteTest(Base):
    """#481: Kontrolllauf im Update-Lauf findet liegengebliebene Aufträge und startet die Abarbeitung."""
    def test_remote_pending_and_start(self):
        git(self.base, 'push', '-q', 'origin', 'HEAD:refs/heads/buch/b')
        self.add('sec-01-01', '2026-11-22T20:00:00+00:00')
        failed = self.add('sec-01-02', '2026-11-22T20:00:00+00:00')
        failed.write_text(yaml.safe_dump({'section_id': 'sec-01-02', 'error': 'x'}))
        waiting = self.add('sec-02-01', '2026-11-22T20:00:00+00:00')
        waiting.write_text(yaml.safe_dump({'section_id': 'sec-02-01', 'waiting': 'budget'}))
        jobs.commit_push(self.base, 'Aufträge', 'ghostwriter/buch/b')
        git(self.base, 'fetch', '-q', 'origin')
        pending = jobs.remote_pending(self.base)
        self.assertEqual(pending, {'buch/b': 1})                       # nur der offene zählt
        calls = []
        ok = lambda args: calls.append(args) or subprocess.CompletedProcess(args, 0, '', '')
        lines = jobs.start_pending(pending, base=self.base, run=ok)
        self.assertEqual(calls, [['gh', 'workflow', 'run', 'research.yml', '--ref', 'buch/b']])
        self.assertIn('gestartet', lines[-1])
        calls.clear()
        lines = jobs.start_pending(pending, paused=True, base=self.base, run=ok)
        self.assertEqual(calls, [])
        self.assertIn('1 Aufträge warten; Automatik pausiert', lines[0])
        self.assertIn('Probelauf', jobs.start_pending(pending, dry_run=True, base=self.base, run=ok)[-1])
        self.assertEqual(calls, [])
        lines = jobs.start_pending({'buch/fehlt': 2}, base=self.base, run=ok)
        self.assertIn('kein Buch-Branch', lines[-1])
        self.assertIn('keine liegengebliebenen', jobs.start_pending({}, base=self.base)[0])

    def test_update_workflow_step(self):
        data = yaml.safe_load((ROOT / '.github/workflows/update.yml').read_text(encoding='utf-8'))
        self.assertEqual(data['permissions']['actions'], 'write')
        step = next(s for s in data['jobs']['update']['steps'] if s.get('name') == 'Hintergrund-Warteschlange prüfen')
        self.assertIn('scripts/jobs.py . remote', step['run'])
        self.assertIn('--paused', step['run'])
        self.assertTrue(step['continue-on-error'])


class WorkflowTest(unittest.TestCase):
    def test_workflow_queue(self):
        text = (ROOT / '.github/workflows/research.yml').read_text(encoding='utf-8')
        data = yaml.safe_load(text)
        job = data['jobs']['research']
        self.assertEqual(job['concurrency']['group'], 'research-${{ needs.book.outputs.book }}')
        self.assertEqual(job['timeout-minutes'], 30)
        self.assertIn('scripts/jobs.py . process', text)
        self.assertIn('scripts/jobs.py . enqueue', text)
        self.assertIn('gh workflow run research.yml', text)
        self.assertEqual(data['permissions']['actions'], 'write')
        on = data.get('on', data.get(True))
        self.assertFalse(on['workflow_dispatch']['inputs']['section'].get('required', False))
        for secret in ('ANTHROPIC', 'OPENAI', 'GOOGLE'):
            self.assertIn(f'GHOSTWRITER_RESEARCH_KEY_{secret}: ${{{{ steps.provider.outputs.secret_{secret.lower()}', text)


if __name__ == '__main__':
    unittest.main()
