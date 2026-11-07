"""Sicherung über echten Git-Remote; Schutz vor Verlust, Rennen und fremden Änderungen."""
import copy
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
        real_run = cb.run
        calls = []
        def fake(*args, **kwargs):
            if args[0] != 'gh':
                return real_run(*args, **kwargs)
            calls.append(args)
            if args[1] == 'api':
                return self.base
            if args[2] == 'list':
                return json.dumps([{'number': 1}])
            if args[2] == 'merge':
                return ''
            if 'state,mergeCommit,url' in args:
                return json.dumps({'state': 'MERGED', 'mergeCommit': {'oid': 'a' * 40}, 'url': 'pr/1'})
            return json.dumps({'headRefOid': first['head'], 'baseRefOid': self.base,
                               'baseRefName': 'main', 'headRefName': first['branch'],
                               'mergeable': 'MERGEABLE', 'mergeStateStatus': 'CLEAN',
                               'isCrossRepository': False, 'statusCheckRollup': []})
        with patch.object(cb, 'run', side_effect=fake):
            with self.assertRaises(ValueError):
                cb.accept(str(self.remote), 'test/repo', 'test-session', first['head'], self.base)
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', first['head'], self.base, confirmed=True)
        self.assertEqual(result['status'], 'merged')
        self.assertTrue(any('--match-head-commit' in call for call in calls))
        # Fremde Manuskriptänderung im Sitzungsbranch darf nicht mit übernommen werden.
        self.git('fetch', '-q', 'origin', first['branch'])
        self.git('checkout', '-q', '-B', 'unsafe', 'FETCH_HEAD')
        (self.work / 'manuscript.md').write_text('Fremdänderung')
        self.git('commit', '-qam', 'Fremde Änderung')
        self.git('push', '-q', 'origin', f'HEAD:refs/heads/{first["branch"]}')
        first['head'] = self.git('rev-parse', 'HEAD')
        with patch.object(cb, 'run', side_effect=fake):
            with self.assertRaisesRegex(ValueError, 'andere Änderungen'):
                cb.accept_once(str(self.remote), 'test/repo', 'test-session', first['head'], self.base, confirmed=True)


    def test_recovery_reports_failed_check_without_merging(self):
        pr = {'state': 'OPEN', 'headRefOid': self.base, 'baseRefOid': self.base,
              'mergeable': 'MERGEABLE', 'mergeStateStatus': 'BLOCKED', 'url': 'pr/1',
              'statusCheckRollup': [{'name': 'validate', 'conclusion': 'FAILURE', 'detailsUrl': 'run/1'}]}
        with patch.object(cb, 'accept_once', side_effect=ValueError('Check fehlgeschlagen')) as attempt, \
             patch.object(cb, 'run', side_effect=[json.dumps([{'number': 1}]), json.dumps(pr), pr['baseRefOid']]):
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', self.base, self.base, confirmed=True)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['checks'][0]['name'], 'validate')
        self.assertEqual(attempt.call_count, 1)

    def test_recovery_confirms_merge_after_connection_failure(self):
        pr = {'state': 'MERGED', 'headRefOid': self.base, 'baseRefOid': self.base,
              'mergeCommit': {'oid': 'b' * 40}, 'url': 'pr/1'}
        with patch.object(cb, 'accept_once', side_effect=ValueError('Verbindung')) as attempt, \
             patch.object(cb, 'run', side_effect=[json.dumps([{'number': 1}]), json.dumps(pr), pr['baseRefOid']]):
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', self.base, self.base, confirmed=True)
        self.assertEqual(result['status'], 'merged')
        self.assertEqual(attempt.call_count, 1)

    def test_recovery_retries_only_same_confirmed_head_and_base(self):
        pr = {'state': 'OPEN', 'headRefOid': self.base, 'baseRefOid': self.base,
              'mergeable': 'MERGEABLE', 'mergeStateStatus': 'CLEAN', 'url': 'pr/1'}
        with patch.object(cb, 'accept_once', side_effect=[ValueError('Transport'), {'status': 'merged'}]) as attempt, \
             patch.object(cb, 'run', side_effect=[json.dumps([{'number': 1}]), json.dumps(pr), pr['baseRefOid']]):
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', self.base, self.base, confirmed=True)
        self.assertEqual(result['status'], 'merged')
        self.assertEqual(attempt.call_count, 2)
        pr['baseRefOid'] = 'c' * 40
        with patch.object(cb, 'accept_once', side_effect=ValueError('Neu')) as attempt, \
             patch.object(cb, 'run', side_effect=[json.dumps([{'number': 1}]), json.dumps(pr), pr['baseRefOid']]):
            result = cb.accept(str(self.remote), 'test/repo', 'test-session', self.base, self.base, confirmed=True)
        self.assertEqual(result['diagnosis'], 'Zielstand geändert')
        self.assertEqual(attempt.call_count, 1)


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


if __name__ == '__main__':
    unittest.main()
