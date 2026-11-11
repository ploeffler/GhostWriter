"""Sicherung über echten Git-Remote; Schutz vor Verlust, Rennen und fremden Änderungen."""
import copy
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import chat_backup as cb


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root / 'remote.git'
        self.work = self.root / 'work'
        cb.run('git', 'init', '--quiet', '--bare', str(self.remote))
        cb.run('git', 'init', '--quiet', '-b', 'main', str(self.work))
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.work / 'manuscript.md').write_text('Buch unverändert')
        self.git('add', '.')
        self.git('commit', '-qm', 'Basis')
        self.base = self.git('rev-parse', 'HEAD')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-q', 'origin', 'main')
        cb.run('git', '--git-dir', str(self.remote), 'symbolic-ref', 'HEAD', 'refs/heads/main')
        self.payload = {'context': {'project': 'Programm GhostWriter'},
                        'coverage': {'description': 'Sichtbare Beiträge 1–2', 'gaps': []},
                        'messages': [{'id': '1', 'role': 'user', 'content': 'Idee A'},
                                     {'id': '2', 'role': 'assistant', 'content': 'Variante B'}],
                        'topics': {'brainstorming': 'A und B, noch offen', 'decisions': 'Keine Freigabe'}}

    def git(self, *args):
        return cb.run('git', *args, cwd=self.work)

    def save(self, head=None, **kwargs):
        return cb.save(str(self.remote), 'main', 'test-session', self.payload, head or self.base, **kwargs)

    def test_roundtrip_topics_repeat_and_append_only(self):
        first = self.save()
        self.assertEqual(len(first['commits']), 3)
        self.assertEqual(self.git('ls-remote', 'origin', 'refs/heads/main').split()[0], self.base)
        restored = cb.resume(str(self.remote), 'test-session')
        self.assertEqual(restored['topics']['conversation']['messages'], self.payload['messages'])
        self.assertEqual(self.save(first['head'])['commits'], [])
        self.payload['topics']['brainstorming'] += '; Idee C'
        second = self.save(first['head'])
        self.assertEqual([x['topic'] for x in second['commits']], ['brainstorming'])
        self.payload['messages'][0]['content'] = 'Ausgetauscht'
        with self.assertRaisesRegex(ValueError, 'Frühere Beiträge'):
            self.save(second['head'])

    def test_stale_head_and_system_messages_rejected(self):
        first = self.save()
        with self.assertRaisesRegex(ValueError, 'Stand inzwischen'):
            self.save()
        self.payload['messages'].append({'id': '3', 'role': 'system', 'content': 'intern'})
        with self.assertRaises(ValueError):
            self.save(first['head'])
        with self.assertRaises(ValueError):
            cb.save(str(self.remote), 'main', '../escape', self.payload, self.base)

    def test_pr_failure_does_not_lose_commits_and_retry_reuses_branch(self):
        with patch.object(cb, 'open_pr', side_effect=ValueError('Netz')):
            first = self.save(github_repo='test/repo')
        self.assertEqual(first['status'], 'remote_saved_pr_pending')
        with patch.object(cb, 'session_prs', return_value=[]), \
             patch.object(cb, 'open_pr', return_value='https://example.invalid/pr/1'):
            again = self.save(first['head'], github_repo='test/repo')
        self.assertEqual(again['commits'], [])
        self.assertEqual(again['pr'], 'https://example.invalid/pr/1')

    def test_accept_checks_files_and_requires_confirmation(self):
        first = self.save()
        merged = []
        def info(repo, number, cwd=None):
            if merged:
                return {'state': 'MERGED', 'mergeCommit': {'oid': 'a' * 40}, 'url': 'pr/1'}
            return {'headRefOid': first['head'], 'baseRefOid': self.base,
                    'baseRefName': 'main', 'headRefName': first['branch'],
                    'mergeable': 'MERGEABLE', 'mergeStateStatus': 'CLEAN', 'url': 'pr/1',
                    'isCrossRepository': False, 'statusCheckRollup': []}
        def api(repo, path, *fields, method='GET', **kwargs):
            merged.append((path, fields, method))
        fake = dict(find_prs=lambda *a, **k: [{'number': 1}], pr_info=info, gh_api=api)
        with patch.multiple(cb, **fake):
            with self.assertRaises(ValueError):
                cb.accept(str(self.remote), 'test/repo', 'test-session', first['head'], self.base)
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', first['head'], self.base, confirmed=True)
        self.assertEqual(result['status'], 'merged')
        # Merge per REST mit festgelegtem Kopf (entspricht --match-head-commit).
        self.assertEqual(merged, [('pulls/1/merge', (('merge_method', 'merge'), ('sha', first['head'])), 'PUT')])
        merged.clear()
        # Fremde Manuskriptänderung im Sitzungsbranch darf nicht mit übernommen werden.
        self.git('fetch', '-q', 'origin', first['branch'])
        self.git('checkout', '-q', '-B', 'unsafe', 'FETCH_HEAD')
        (self.work / 'manuscript.md').write_text('Fremdänderung')
        self.git('commit', '-qam', 'Fremde Änderung')
        self.git('push', '-q', 'origin', f'HEAD:refs/heads/{first["branch"]}')
        first['head'] = self.git('rev-parse', 'HEAD')
        with patch.multiple(cb, **fake):
            with self.assertRaisesRegex(ValueError, 'andere Änderungen'):
                cb.accept_once(str(self.remote), 'test/repo', 'test-session', first['head'], self.base, confirmed=True)


    def test_recovery_reports_failed_check_without_merging(self):
        pr = {'state': 'OPEN', 'headRefOid': self.base, 'baseRefOid': self.base,
              'mergeable': 'MERGEABLE', 'mergeStateStatus': 'BLOCKED', 'url': 'pr/1',
              'statusCheckRollup': [{'name': 'validate', 'conclusion': 'FAILURE', 'detailsUrl': 'run/1'}]}
        with patch.object(cb, 'accept_once', side_effect=ValueError('Check fehlgeschlagen')) as attempt, \
             patch.object(cb, 'find_prs', return_value=[{'number': 1}]), \
             patch.object(cb, 'pr_info', return_value=pr):
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', self.base, self.base, confirmed=True)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['checks'][0]['name'], 'validate')
        self.assertEqual(attempt.call_count, 1)

    def test_recovery_confirms_merge_after_connection_failure(self):
        pr = {'state': 'MERGED', 'headRefOid': self.base, 'baseRefOid': self.base,
              'mergeCommit': {'oid': 'b' * 40}, 'url': 'pr/1'}
        with patch.object(cb, 'accept_once', side_effect=ValueError('Verbindung')) as attempt, \
             patch.object(cb, 'find_prs', return_value=[{'number': 1}]), \
             patch.object(cb, 'pr_info', return_value=pr):
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', self.base, self.base, confirmed=True)
        self.assertEqual(result['status'], 'merged')
        self.assertEqual(attempt.call_count, 1)

    def test_recovery_retries_only_same_confirmed_head_and_base(self):
        pr = {'state': 'OPEN', 'headRefOid': self.base, 'baseRefOid': self.base,
              'mergeable': 'MERGEABLE', 'mergeStateStatus': 'CLEAN', 'url': 'pr/1'}
        with patch.object(cb, 'accept_once', side_effect=[ValueError('Transport'), {'status': 'merged'}]) as attempt, \
             patch.object(cb, 'find_prs', return_value=[{'number': 1}]), \
             patch.object(cb, 'pr_info', return_value=pr):
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', self.base, self.base, confirmed=True)
        self.assertEqual(result['status'], 'merged')
        self.assertEqual(attempt.call_count, 2)
        pr['baseRefOid'] = 'c' * 40
        with patch.object(cb, 'accept_once', side_effect=ValueError('Neu')) as attempt, \
             patch.object(cb, 'find_prs', return_value=[{'number': 1}]), \
             patch.object(cb, 'pr_info', return_value=pr):
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', self.base, self.base, confirmed=True)
        self.assertEqual(result['diagnosis'], 'Zielstand geändert')
        self.assertEqual(attempt.call_count, 1)


    def test_recovery_waits_for_pending_checks_via_rest(self):
        pr = {'state': 'OPEN', 'headRefOid': self.base, 'baseRefOid': self.base,
              'mergeable': 'UNKNOWN', 'mergeStateStatus': 'UNKNOWN', 'url': 'pr/1', 'statusCheckRollup': []}
        with patch.object(cb, 'accept_once', side_effect=[ValueError('noch offen'), {'status': 'merged'}]), \
             patch.object(cb, 'find_prs', return_value=[{'number': 1}]), \
             patch.object(cb, 'pr_info', return_value=pr), \
             patch.object(cb, 'wait_for_pr') as wait:
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', self.base, self.base, confirmed=True)
        self.assertEqual(result['status'], 'merged')
        wait.assert_called_once_with('test/repo', '1')

    def test_no_graphql_commands(self):
        """`gh pr …` nutzt GraphQL, das in Claude-Code-Sitzungen gesperrt ist (#253)."""
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        for path in scripts.glob('*.py'):
            text = path.read_text(encoding='utf-8')
            with self.subTest(path=path.name):
                self.assertNotIn("'gh', 'pr'", text)
                self.assertNotIn('"gh", "pr"', text)

    def test_rest_pull_requests_are_normalized(self):
        calls = []
        pull = {'number': 7, 'html_url': 'https://github.com/o/r/pull/7', 'state': 'open', 'merged': False,
                'mergeable': True, 'mergeable_state': 'clean', 'merge_commit_sha': 'd' * 40,
                'head': {'sha': 'a' * 40, 'ref': 'ghostwriter/chat/s', 'repo': {'full_name': 'o/r'}},
                'base': {'sha': 'b' * 40, 'ref': 'main', 'repo': {'full_name': 'o/r'}}}
        def fake(*args, **kwargs):
            calls.append(args)
            url = args[4]
            if url.startswith('repos/o/r/pulls?'):
                return json.dumps([pull, {**pull, 'number': 8, 'state': 'closed', 'merged_at': 'x'}])
            if '/check-runs' in url:
                return json.dumps({'check_runs': [
                    {'name': 'validate', 'status': 'completed', 'conclusion': 'success', 'details_url': 'u'},
                    {'name': 'lang', 'status': 'in_progress', 'conclusion': None}]})
            if url.endswith('/status'):
                return json.dumps({'statuses': [{'context': 'ci', 'state': 'failure', 'target_url': 't'}]})
            return json.dumps(pull)
        with patch.object(cb, 'run', side_effect=fake):
            prs = cb.find_prs('o/r', 'ghostwriter/chat/s')
            info = cb.pr_info('o/r', '7')
        self.assertTrue(all(c[:2] == ('gh', 'api') for c in calls))
        self.assertIn('head=o:ghostwriter/chat/s', calls[0][4])
        self.assertEqual([(p['number'], p['state']) for p in prs], [(7, 'OPEN'), (8, 'MERGED')])
        self.assertEqual((info['mergeable'], info['mergeStateStatus'], info['isCrossRepository']),
                         ('MERGEABLE', 'CLEAN', False))
        self.assertIsNone(info['mergeCommit'])
        self.assertEqual([c.get('conclusion') or c.get('state') for c in info['statusCheckRollup']],
                         ['SUCCESS', 'IN_PROGRESS', 'FAILURE'])
        self.assertTrue(cb.pending(info))
        fork = {**pull, 'head': {**pull['head'], 'repo': None}, 'mergeable': None}
        with patch.object(cb, 'gh_api', side_effect=[fork, {}, {}]):
            other = cb.pr_info('o/r', '7')
        self.assertTrue(other['isCrossRepository'])
        self.assertEqual(other['mergeable'], 'UNKNOWN')

    def test_open_pr_uses_rest_and_finds_pr_created_despite_error(self):
        posts = []
        def api(repo, path, *fields, method='GET', **kwargs):
            if method == 'POST':
                posts.append(dict(fields))
                raise ValueError('gh: Vorgang fehlgeschlagen (Code 1, GitHub HTTP 502)')
            return [] if not posts else [{'number': 3, 'html_url': 'pr/3', 'state': 'open',
                                          'base': {'ref': 'main'}}]
        with patch.object(cb, 'gh_api', side_effect=api):
            url = cb.open_pr('o/r', 'main', 'ghostwriter/chat/s', 's', self.root)
        self.assertEqual(url, 'pr/3')
        self.assertEqual(posts[0]['head'], 'ghostwriter/chat/s')
        self.assertEqual(posts[0]['base'], 'main')

    def test_gh_error_names_http_status_but_not_details(self):
        failed = subprocess.CompletedProcess([], 1, '', 'HTTP 403: GitHub GraphQL is not available (token=geheim)')
        with patch.object(cb.subprocess, 'run', return_value=failed):
            with self.assertRaises(ValueError) as caught:
                cb.run('gh', 'api', 'repos/o/r')
        self.assertIn('HTTP 403', str(caught.exception))
        self.assertNotIn('geheim', str(caught.exception))

    def test_pr_pending_reports_cause_and_second_save_still_uploads(self):
        error = ValueError('gh: Vorgang fehlgeschlagen (Code 1, GitHub HTTP 403)')
        with patch.object(cb, 'open_pr', side_effect=error):
            first = self.save(github_repo='test/repo')
        self.assertEqual(first['status'], 'remote_saved_pr_pending')
        self.assertIn('HTTP 403', first['cause'])
        # Zweiter Aufruf: PR-Abfrage über REST, neuer Stand wird trotzdem hochgeladen.
        self.payload['topics']['research'] = 'Neue Quelle'
        with patch.object(cb, 'find_prs', return_value=[]), \
             patch.object(cb, 'open_pr', return_value='pr/1'):
            second = self.save(first['head'], github_repo='test/repo')
        self.assertEqual([c['topic'] for c in second['commits']], ['research'])
        self.assertEqual(second['status'], 'remote_saved')

    def manifest(self):
        return cb.resume(str(self.remote), 'test-session')['session']

    def test_last_saved_time_and_origin_follow_real_changes(self):
        import datetime
        t1 = datetime.datetime(2026, 11, 10, 16, 51, 47, tzinfo=datetime.timezone.utc)
        origin = {'device': 'Laptop Küche', 'os': 'Linux', 'client': 'Claude Desktop', 'client_version': '1.2'}
        first = self.save(origin=origin, now=t1)
        self.assertEqual(first['saved_at'], '2026-11-10T16:51:47Z')
        self.assertEqual(self.manifest()['last_saved'], {'at': '2026-11-10T16:51:47Z', 'origin': origin})
        # Wiederholung ohne Änderung: kein neuer Zeitpunkt, keine neue Herkunft
        later = t1 + datetime.timedelta(hours=1)
        again = self.save(first['head'], origin={'client': 'ChatGPT'}, now=later)
        self.assertEqual(again['commits'], [])
        self.assertEqual(again['saved_at'], '2026-11-10T16:51:47Z')
        # Fehlgeschlagener Push: remote bleibt beim alten Zeitpunkt
        self.payload['topics']['research'] = 'Neue Quelle'
        real_run = cb.run
        def failed_push(*args, **kwargs):
            if args[:2] == ('git', 'push'):
                raise ValueError('simulierter Uploadfehler')
            return real_run(*args, **kwargs)
        with patch.object(cb, 'run', side_effect=failed_push), self.assertRaises(ValueError):
            self.save(first['head'], origin={'client': 'ChatGPT'}, now=later)
        self.assertEqual(self.manifest()['last_saved']['at'], '2026-11-10T16:51:47Z')
        # Echte Änderung von einem anderen Gerät: neuer Zeitpunkt, Herkunft der neuen Fassung
        third = self.save(first['head'], origin={'client': 'ChatGPT'}, now=later)
        self.assertEqual(self.manifest()['last_saved'], {'at': '2026-11-10T17:51:47Z', 'origin': {'client': 'ChatGPT'}})
        self.assertEqual([c['topic'] for c in third['commits']], ['research'])

    def test_old_backup_without_origin_stays_loadable(self):
        first = self.save()
        info = self.manifest()
        self.assertEqual(info['last_saved']['origin'], {})
        # Ältere Sicherung ohne last_saved (vor #237): Laden und Weitersichern gehen weiter
        self.git('fetch', '-q', 'origin', first['branch'])
        self.git('checkout', '-q', '-B', 'old', 'FETCH_HEAD')
        path = self.work / 'conversations/test-session/session.json'
        data = json.loads(path.read_text())
        data.pop('last_saved')
        path.write_text(cb.canonical(data))
        self.git('commit', '-qam', 'alte Sicherung')
        self.git('push', '-q', 'origin', f'HEAD:refs/heads/{first["branch"]}')
        head = self.git('rev-parse', 'HEAD')
        self.assertNotIn('last_saved', self.manifest())
        unchanged = self.save(head)
        self.assertIsNone(unchanged['saved_at'])
        self.payload['topics']['research'] = 'Neu'
        self.assertTrue(self.save(head)['saved_at'])

    def test_origin_rejects_unknown_or_multiline_values(self):
        for origin in ({'hostname': 'pc-123'}, {'device': 'a\nb'}, {'client': 'x' * 81}):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                self.save(origin=origin)
        self.assertNotIn('ghostwriter/chat/', self.git('ls-remote', '--heads', 'origin'))

    def test_resume_after_merge_and_branch_cleanup(self):
        first = self.save()
        self.git('fetch', '-q', 'origin', first['branch'])
        self.git('merge', '--no-ff', '-qm', 'Session übernommen', 'FETCH_HEAD')
        self.git('push', '-q', 'origin', 'main')
        self.git('push', '-q', 'origin', '--delete', first['branch'])
        restored = cb.resume(str(self.remote), 'test-session', base='main')
        self.assertEqual(restored['topics']['brainstorming'], self.payload['topics']['brainstorming'])

    def test_symlink_in_backup_path_is_rejected(self):
        (self.work / 'conversations').symlink_to(self.root / 'outside', target_is_directory=True)
        self.git('add', 'conversations')
        self.git('commit', '-qm', 'Unsicherer Pfad')
        self.git('push', '-q', 'origin', 'main')
        head = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'symbolischer Link'):
            self.save(head)
        self.assertFalse((self.root / 'outside').exists())

    def test_concurrent_remote_writer_is_not_overwritten(self):
        first = self.save()
        self.payload['topics']['research'] = 'Neue Quelle'
        real_run = cb.run
        def concurrent(*args, **kwargs):
            if args[:3] == ('git', 'push', '--quiet'):
                self.git('fetch', '-q', 'origin', first['branch'])
                self.git('checkout', '-q', '-B', 'concurrent', 'FETCH_HEAD')
                (self.work / 'other').write_text('Parallel')
                self.git('add', 'other')
                self.git('commit', '-qm', 'Paralleler Stand')
                self.git('push', '-q', 'origin', f'HEAD:refs/heads/{first["branch"]}')
            return real_run(*args, **kwargs)
        with patch.object(cb, 'run', side_effect=concurrent):
            with self.assertRaises(ValueError):
                self.save(first['head'])
        current = self.git('ls-remote', 'origin', f'refs/heads/{first["branch"]}').split()[0]
        self.assertEqual(current, self.git('rev-parse', 'HEAD'))



    def answer_review(self):
        self.payload['messages'].append({'id': '3', 'role': 'user', 'content': 'Meine konkrete Antwort'})
        self.payload['topics']['brainstorming'] = 'Antwort ausgewertet; nächste Frage noch offen.'
        return {'section_id': 'sec-one', 'source_commit': self.base,
                'answer_message_id': '3', 'dialogue_complete': False, 'awaiting_reply': True,
                'items': [{'id': 'q1', 'question': 'Erste Frage', 'status': 'answered', 'evidence': ['3']},
                          {'id': 'q2', 'question': 'Nächste Frage', 'status': 'open', 'evidence': ['2']}]}

    def test_answer_checkpoint_uploads_one_commit_before_discussion_is_complete(self):
        review = self.answer_review()
        before = copy.deepcopy(self.payload)
        first = cb.answer_checkpoint(str(self.remote), 'main', 'test-session', self.payload, self.base, review)
        self.assertTrue(first['reply_ready'])
        self.assertEqual(first['trigger'], 'section_answer_evaluated')
        self.assertEqual(first['answer_message_id'], '3')
        self.assertEqual(len(first['commits']), 1)
        self.assertEqual(self.payload, before)
        restored = cb.resume(str(self.remote), 'test-session')
        self.assertEqual(restored['topics']['conversation']['messages'], before['messages'])
        self.assertEqual(json.loads(restored['topics']['section_answer']), review)
        self.assertEqual(restored['topics']['brainstorming'], before['topics']['brainstorming'])
        self.assertEqual(self.git('ls-remote', 'origin', 'refs/heads/main').split()[0], self.base)
        # Retry the same evaluated reply: remote proof, no new commit or push.
        real_run = cb.run
        def no_push(*args, **kwargs):
            self.assertNotEqual(args[:2], ('git', 'push'))
            return real_run(*args, **kwargs)
        with patch.object(cb, 'run', side_effect=no_push):
            again = cb.answer_checkpoint(str(self.remote), 'main', 'test-session', self.payload, first['head'], review)
        self.assertEqual(again['commits'], [])
        self.assertEqual(again['head'], first['head'])
        self.assertTrue(again['reply_ready'])
        # A later answer appends to this session rather than creating another branch.
        self.payload['messages'] += [{'id': '4', 'role': 'assistant', 'content': 'Nächste Frage?'},
                                     {'id': '5', 'role': 'user', 'content': 'Zweite Antwort'}]
        self.payload['topics']['brainstorming'] += ' Zweite Antwort ausgewertet.'
        review['answer_message_id'] = '5'
        review['items'][1].update(status='answered', evidence=['5'])
        second = cb.answer_checkpoint(str(self.remote), 'main', 'test-session', self.payload, again['head'], review)
        self.assertEqual(second['branch'], first['branch'])
        count = cb.run('git', '--git-dir', str(self.remote), 'rev-list', '--count',
                       self.base + '..refs/heads/' + second['branch'])
        self.assertEqual(count, '2')

    def test_answer_checkpoint_cli_outputs_receipt_only_after_upload(self):
        review = self.answer_review()
        payload_path, review_path = self.root/'input.json', self.root/'review.json'
        payload_path.write_text(json.dumps(self.payload))
        review_path.write_text(json.dumps(review))
        output = io.StringIO()
        real_run, pushes = cb.run, []
        def transport(*args, **kwargs):
            if args[:2] == ('git', 'push'):
                self.assertEqual(output.getvalue(), '')
                pushes.append(True)
            return real_run(*args, **kwargs)
        argv = ['chat_backup.py', 'answer-checkpoint', str(self.remote), 'test-session', str(payload_path),
                '--review', str(review_path), '--base', 'main', '--expected-head', self.base,
                '--github-repo', 'test/repo']
        with patch.object(sys, 'argv', argv), patch.object(cb, 'run', side_effect=transport), \
             patch.object(cb, 'open_pr', return_value='https://example.invalid/pr/1'), \
             contextlib.redirect_stdout(output):
            cb.main()
        receipt = json.loads(output.getvalue())
        self.assertEqual(len(pushes), 1)
        self.assertTrue(receipt['reply_ready'])
        self.assertEqual(receipt['head'], cb.resume(str(self.remote), 'test-session')['head'])

    def test_answer_checkpoint_rejects_missing_old_or_already_answered_message(self):
        review = self.answer_review()
        for modify in ('missing', 'old', 'unreferenced', 'visible_reply'):
            payload, changed = copy.deepcopy(self.payload), copy.deepcopy(review)
            if modify == 'missing':
                changed['answer_message_id'] = 'missing'
            elif modify == 'old':
                changed['answer_message_id'] = '1'
            elif modify == 'unreferenced':
                changed['items'][0]['evidence'] = ['1']
            else:
                payload['messages'].append({'id': '4', 'role': 'assistant', 'content': 'Bereits ausgegebene Zusammenfassung'})
            with self.subTest(modify=modify), patch.object(cb, 'save') as save:
                with self.assertRaises(ValueError):
                    cb.answer_checkpoint(str(self.remote), 'main', 'test-session', payload, self.base, changed)
                save.assert_not_called()

    def test_answer_checkpoint_push_error_does_not_report_ready_and_can_retry(self):
        review = self.answer_review()
        real_run = cb.run
        def failed_push(*args, **kwargs):
            if args[:2] == ('git', 'push'):
                raise ValueError('simulierter Uploadfehler')
            return real_run(*args, **kwargs)
        with patch.object(cb, 'run', side_effect=failed_push), self.assertRaises(ValueError):
            cb.answer_checkpoint(str(self.remote), 'main', 'test-session', self.payload, self.base, review)
        self.assertNotIn('ghostwriter/chat/', self.git('ls-remote', '--heads', 'origin'))
        recovered = cb.answer_checkpoint(str(self.remote), 'main', 'test-session', self.payload, self.base, review)
        self.assertTrue(recovered['reply_ready'])
        self.assertEqual(len(recovered['commits']), 1)

    def test_answer_checkpoint_reports_uploaded_content_when_pr_creation_fails(self):
        review = self.answer_review()
        with patch.object(cb, 'open_pr', side_effect=ValueError('PR nicht erreichbar')):
            result = cb.answer_checkpoint(str(self.remote), 'main', 'test-session',
                                          self.payload, self.base, review, github_repo='test/repo')
        self.assertEqual(result['status'], 'remote_saved_pr_pending')
        self.assertTrue(result['reply_ready'])  # the reply is durably uploaded even if the PR is pending
        self.assertEqual(cb.resume(str(self.remote), 'test-session')['head'], result['head'])

    def review(self):
        return {'section_id': 'sec-one', 'source_commit': self.base,
                'dialogue_complete': True, 'awaiting_reply': False,
                'items': [{'id': 'question-1', 'question': 'Welche Variante?',
                           'status': 'decided', 'evidence': ['1']}]}

    def test_section_checkpoint_saves_once_and_preserves_dialogue_evidence(self):
        before = copy.deepcopy(self.payload)
        review = self.review()
        result = cb.section_checkpoint(str(self.remote), 'main', 'test-session',
                                       self.payload, self.base, review)
        self.assertEqual(result['trigger'], 'section_dialogue_completed')
        self.assertEqual(self.payload, before)
        loaded = cb.resume(str(self.remote), 'test-session')
        self.assertEqual(json.loads(loaded['topics']['section_dialogue']), review)
        self.assertEqual(loaded['topics']['conversation']['messages'], self.payload['messages'])
        repeated = cb.section_checkpoint(str(self.remote), 'main', 'test-session',
                                         self.payload, result['head'], review)
        self.assertEqual(repeated['commits'], [])
        self.assertEqual(self.git('ls-remote', 'origin', 'refs/heads/main').split()[0], self.base)

    def test_section_checkpoint_does_not_write_while_discussion_is_open(self):
        for changes in ({'dialogue_complete': False}, {'awaiting_reply': True},
                        {'items': [{'id': 'q', 'question': 'Noch offen?', 'status': 'open', 'evidence': ['1']}] }):
            review = {**self.review(), **changes}
            with patch.object(cb, 'save') as save:
                result = cb.section_checkpoint(str(self.remote), 'main', 'test-session',
                                               self.payload, self.base, review)
            self.assertEqual(result['status'], 'not_due')
            save.assert_not_called()
        self.assertNotIn('ghostwriter/chat/', self.git('ls-remote', '--heads', 'origin'))

    def test_section_checkpoint_requires_available_evidence_and_user_deferral(self):
        for status, evidence in [('deferred', ['2']), ('decided', ['missing'])]:
            review = self.review()
            review['items'][0].update(status=status, evidence=evidence)
            with patch.object(cb, 'save') as save:
                with self.assertRaises(ValueError):
                    cb.section_checkpoint(str(self.remote), 'main', 'test-session',
                                          self.payload, self.base, review)
            save.assert_not_called()
        review = self.review()
        review['items'][0]['status'] = 'deferred'
        with patch.object(cb, 'save', return_value={'status': 'remote_saved'}) as save:
            result = cb.section_checkpoint(str(self.remote), 'main', 'test-session',
                                           self.payload, self.base, review)
        self.assertEqual(result['status'], 'remote_saved')
        save.assert_called_once()


if __name__ == '__main__':
    unittest.main()
