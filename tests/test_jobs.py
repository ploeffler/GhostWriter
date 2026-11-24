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
        self.assertEqual(pending, {'buch/b': {'research.yml': 1}})     # nur der offene zählt
        calls = []
        ok = lambda args: calls.append(args) or subprocess.CompletedProcess(args, 0, '', '')
        lines = jobs.start_pending(pending, base=self.base, run=ok)
        self.assertEqual(calls, [['gh', 'workflow', 'run', 'research.yml', '--ref', 'buch/b']])
        calls.clear()
        jobs.start_pending({'buch/b': {'import.yml': 1, 'colorize.yml': 2}}, base=self.base, run=ok)
        self.assertEqual(calls, [['gh', 'workflow', 'run', 'colorize.yml', '--ref', 'buch/b'],
                                 ['gh', 'workflow', 'run', 'import.yml', '--ref', 'buch/b', '-f', 'step=queue']])
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


class ChatTest(Base):
    """#482: drei Recherchen im Chat kurz hintereinander werden drei Aufträge, alle erledigt."""
    def test_three_chat_requests_all_done(self):
        for q in ('A', 'B', 'C'):
            jobs.main([str(self.base), 'enqueue', '--section', 'sec-01-01', '--question', q, '--requested-by', 'chat',
                       '--push-to', 'ghostwriter/buch/b'])
        git(self.base, 'fetch', '-q', 'origin')
        self.assertEqual(len(self.remote_files('request-')), 3)              # jeder Auftrag sofort gesichert
        with self.fake_run(), mock.patch.object(jobs, 'budget_low', return_value=False):
            results, remaining = jobs.process(self.base, push_to='ghostwriter/buch/b')
        self.assertEqual(([r['ok'] for r in results], remaining), ([True, True, True], 0))
        self.assertEqual([c[1] for c in self.calls], ['request-001', 'request-002', 'request-003'])

    def test_section_view_offers_queue_only_with_api_service(self):
        import render_view
        self.assertEqual(render_view.research_queue_values(self.base)['RESEARCH_QUEUE_AVAILABLE'], 'false')
        cfg = yaml.safe_load((self.base / 'ghostwriter.yml').read_text())
        cfg['ai_providers'] = {'available': ['google'], 'services': {'google': {'access': 'api', 'api_key_secret': 'GEMINI_API_KEY'}}}
        (self.base / 'ghostwriter.yml').write_text(yaml.safe_dump(cfg))
        values = render_view.research_queue_values(self.base)
        self.assertEqual(values['RESEARCH_QUEUE_AVAILABLE'], 'true')
        self.assertIn('mit Internet über', values['RESEARCH_QUEUE_TEXT'])

    def test_start_md_uses_jobs_not_dispatch(self):
        text = (ROOT / 'START.md').read_text(encoding='utf-8')
        part = text[text.index('### Recherche mit Internet in der Action'):text.index('### Vor- und Nachspann')]
        self.assertIn('scripts/jobs.py . enqueue', part)
        self.assertIn('nie `dispatches` mit `section`', part)


class ReportTest(Base):
    """#484: Meldung beim Wiedereinstieg und Zahlen im Bücherregal, nur aus Auftrags- und Laufdateien."""
    def test_status_report_and_library_numbers(self):
        git(self.base, 'push', '-q', 'origin', 'HEAD:refs/heads/buch/b')
        git(self.base, 'fetch', '-q', 'origin')
        self.assertEqual(jobs.remote_status(self.base), {})                 # ohne Neues nichts
        self.assertEqual(jobs.report({}), '')
        for sid in ('sec-01-01', 'sec-01-02', 'sec-02-01'):
            self.add(sid, '2026-11-22T20:00:00+00:00')
        with self.fake_run(fail='sec-01-02'), mock.patch.object(jobs, 'budget_low', return_value=False):
            jobs.process(self.base, limit=2, push_to='ghostwriter/buch/b')
        git(self.base, 'fetch', '-q', 'origin')
        status = jobs.remote_status(self.base)
        info = status['buch/b']
        self.assertEqual({k: info[k] for k in ('done', 'failed', 'waiting', 'waiting_budget')},
                         {'done': 1, 'failed': 1, 'waiting': 1, 'waiting_budget': 0})
        self.assertEqual(info['done_sections'], ['sec-01-01'])
        text = jobs.report(status)
        self.assertTrue(text.startswith('Seit deinem letzten Besuch: 1 fertig · 1 fehlgeschlagen · 1 wartet'))
        self.assertIn('sec-01-02: Anbieter antwortet nicht', text)
        self.assertIn('Since your last visit', jobs.report(status, 'en'))
        # Übernommen ins Buch: nicht mehr „fertig“
        git(self.base, 'push', '-q', 'origin', 'origin/ghostwriter/buch/b:refs/heads/buch/b')
        git(self.base, 'fetch', '-q', 'origin')
        self.assertEqual(jobs.remote_status(self.base)['buch/b']['done'], 0)
        import render_view
        self.assertEqual(render_view.jobs_text({'done': 2, 'failed': 0, 'waiting': 1, 'waiting_budget': 1}),
                         'Warteschlange: 2 fertig · 2 warten')
        self.assertEqual(render_view.jobs_text({'done': 0, 'failed': 0, 'waiting': 0, 'waiting_budget': 0}), '')
        self.assertEqual(render_view.jobs_text(None), '')


class OtherTypesTest(Base):
    """#479: Analyse, Colorieren und Import über dieselbe Warteschlange."""
    def fake_runner(self, fail=None):
        def runner(base, job):
            f = job['data'].get(job['type']) or {}
            self.calls.append((job['type'], dict(f)))
            if fail and f.get('folder') == fail:
                raise research.ResearchError('Bild fehlt')
            out = Path(base) / 'analysis' / f'{len(self.calls)}.txt'
            out.parent.mkdir(exist_ok=True)
            out.write_text('ergebnis')
            return {'label': f'{job["type"]} {len(self.calls)}', 'paths': ['analysis'], 'action': f'{job["type"]}.x'}
        return runner

    def test_three_per_type_each_saved_error_continues(self):
        for i in range(3):
            jobs.main([str(self.base), 'enqueue', '--type', 'colorize', '--field', f'folder=bilder/{i}', '--field', 'consent=true'])
        jobs.enqueue(self.base, 'analysis', fields={'kind': 'style', 'scope': 'book', 'unbekannt': 'x'})
        files = jobs.files(self.base)
        self.assertEqual([p.relative_to(self.base).as_posix() for p in files],
                         ['jobs/request-001.yml', 'jobs/request-002.yml', 'jobs/request-003.yml', 'jobs/request-004.yml'])
        first = yaml.safe_load(files[0].read_text())
        self.assertEqual(first['colorize'], {'folder': 'bilder/0', 'consent': True})
        self.assertNotIn('unbekannt', yaml.safe_load(files[3].read_text())['analysis'])   # nur bekannte Felder
        with mock.patch.dict(jobs.RUNNERS, {'colorize': self.fake_runner(fail='bilder/1')}), \
                mock.patch.object(jobs, 'budget_low', return_value=False):
            results, remaining = jobs.process(self.base, push_to='ghostwriter/buch/b', types=['colorize'])
        self.assertEqual([r['ok'] for r in results], [True, False, True])
        self.assertEqual(remaining, 0)                                         # die Analyse zählt hier nicht
        self.assertEqual([j['type'] for j in jobs.queue(self.base)], ['analysis'])
        git(self.base, 'fetch', '-q', 'origin')
        log = git(self.base, 'log', '--format=%s%n%b', 'origin/ghostwriter/buch/b')
        self.assertEqual(log.count('GhostWriter-Aktion: colorize.x'), 2)       # je Ergebnis ein Commit
        self.assertIn('fehlgeschlagen', log)

    def test_free_import_steps_ignore_budget_and_colorize_needs_consent(self):
        jobs.enqueue(self.base, 'import', fields={'step': 'convert', 'file': 'import/original/a.docx'})
        jobs.enqueue(self.base, 'import', fields={'step': 'outline'})
        with mock.patch.dict(jobs.RUNNERS, {'import': self.fake_runner()}), mock.patch.object(jobs, 'budget_low', return_value=True):
            results, _ = jobs.process(self.base, commit=False)
        self.assertEqual([(r['ok'], r.get('waiting', False)) for r in results], [(True, False), (False, True)])
        jobs.enqueue(self.base, 'colorize', fields={'folder': 'bilder/x'})
        job = jobs.queue(self.base, types=['colorize'])[0]
        with mock.patch.object(jobs, 'script', return_value=''):
            with self.assertRaisesRegex(research.ResearchError, 'Einverständnis'):
                jobs.run_colorize(self.base, job)

    def test_jobs_only_counted_on_their_branch(self):
        git(self.base, 'push', '-q', 'origin', 'HEAD:refs/heads/buch/b')
        jobs.enqueue(self.base, 'analysis', fields={'kind': 'style'})           # gehört auf den Buch-Branch
        jobs.enqueue(self.base, 'colorize', fields={'folder': 'f', 'consent': True})
        jobs.commit_push(self.base, 'Aufträge', 'ghostwriter/buch/b')
        git(self.base, 'fetch', '-q', 'origin')
        self.assertEqual(jobs.remote_pending(self.base), {'buch/b': {'colorize.yml': 1}})
        git(self.base, 'push', '-q', 'origin', 'HEAD:refs/heads/buch/b', '--force')
        git(self.base, 'fetch', '-q', 'origin')
        self.assertEqual(jobs.remote_pending(self.base)['buch/b'], {'analyse.yml': 1, 'colorize.yml': 1})


class WorkflowTest(unittest.TestCase):
    def test_workflow_queue(self):
        """#480/#479: alle vier Actions legen Aufträge im Job prep an (ohne Gruppe, nie verdrängt) und arbeiten
        im Job process in der gemeinsamen Gruppe je Buch ab."""
        for wf, type_ in (('research', 'research'), ('analyse', 'analysis'), ('colorize', 'colorize'), ('import', 'import')):
            with self.subTest(wf=wf):
                text = (ROOT / f'.github/workflows/{wf}.yml').read_text(encoding='utf-8')
                data = yaml.safe_load(text)
                self.assertNotIn('concurrency', data)                          # nicht auf Workflow-Ebene
                self.assertNotIn('concurrency', data['jobs']['prep'])
                job = data['jobs']['process']
                self.assertEqual(job['concurrency']['group'], 'jobs-${{ needs.prep.outputs.book }}')
                self.assertEqual(job['timeout-minutes'], 30)
                self.assertIn(f'--type {type_}', text)
                self.assertIn(f'--types {type_}', text)
                self.assertIn(f'gh workflow run {wf}.yml', text)
                self.assertEqual(data['permissions']['actions'], 'write')
                on = data.get('on', data.get(True))
                for name, spec in on['workflow_dispatch']['inputs'].items():
                    self.assertFalse(spec.get('required', False), name)       # ohne Eingaben = nur abarbeiten
        text = (ROOT / '.github/workflows/research.yml').read_text(encoding='utf-8')
        for secret in ('ANTHROPIC', 'OPENAI', 'GOOGLE'):
            self.assertIn(f'GHOSTWRITER_RESEARCH_KEY_{secret}: ${{{{ steps.provider.outputs.secret_{secret.lower()}', text)
        self.assertIn('-f step=queue', (ROOT / '.github/workflows/import.yml').read_text(encoding='utf-8'))
        for wf in ('research', 'analyse', 'colorize', 'import'):   # #62: pausiert kein Selbstneustart
            data = yaml.safe_load((ROOT / f'.github/workflows/{wf}.yml').read_text(encoding='utf-8'))
            step = next(st for st in data['jobs']['process']['steps'] if st.get('name') == 'Selbstneustart')
            self.assertIn("vars.GHOSTWRITER_ACTIONS_PAUSED != 'true'", step['if'])

if __name__ == '__main__':
    unittest.main()
