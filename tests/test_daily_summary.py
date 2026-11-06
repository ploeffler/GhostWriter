import unittest

from scripts.daily_summary import content_paths, is_content_file


class DailySummaryTests(unittest.TestCase):
    def test_only_book_content_roots_are_counted(self):
        manifest = {"book": ["chapters/", "matter/", "research/", "ghostwriter.yml", "costs/"]}
        self.assertEqual(content_paths(manifest), ["chapters/", "matter/", "research/"])

    def test_program_and_status_files_are_excluded(self):
        paths = content_paths({"book": ["chapters/", "matter/", "research/"]})
        self.assertTrue(is_content_file("chapters/01/section.md", paths))
        self.assertTrue(is_content_file("matter/prologue.md", paths))
        self.assertFalse(is_content_file("scripts/update_from_upstream.py", paths))
        self.assertFalse(is_content_file(".ghostwriter/update.yml", paths))
        self.assertFalse(is_content_file("ghostwriter.yml", paths))




from pathlib import Path
import os
import subprocess
import tempfile
from unittest.mock import patch
from scripts import daily_summary as ds


class ReportTests(unittest.TestCase):
    def test_pagination_does_not_drop_recent_prs(self):
        batch = [{'updated_at': '2026-11-06'}] * 100
        with patch.object(ds, '_api', side_effect=[batch, [{'updated_at': '2026-11-05'}]]) as api:
            self.assertEqual(len(ds._pages('o/r', 'pulls?state=all')), 101)
            self.assertIn('&page=2', api.call_args.args[1])

    def test_main_repo_and_local_update_status_are_separate(self):
        with patch.object(ds, '_pulls') as pulls, patch.object(ds, '_updates') as updates:
            lines = []
            ds.append_daily_summary(lines, 'author/book', [], {'upstream': {'repo': 'o/program'}})
            self.assertEqual(pulls.call_args.args[1], 'o/program')
            self.assertEqual(updates.call_args.args[1], 'author/book')
            self.assertIn('Keine Buchinhaltsänderungen', '\n'.join(lines))

    def test_unavailable_data_is_not_reported_as_zero(self):
        with patch.object(ds, '_content_activity', side_effect=RuntimeError), \
                patch.object(ds, '_pulls', side_effect=OSError), patch.object(ds, '_api', side_effect=OSError):
            lines = []
            ds.append_daily_summary(lines, 'o/r', ['buch/a'], {})
            text = '\n'.join(lines)
            self.assertIn('unbekannt | unbekannt', text)
            self.assertIn('Entscheidungen unbekannt', text)
            self.assertIn('Update-/Pausenmeldungen nicht verfügbar', text)

    def test_failed_fetch_does_not_claim_no_activity(self):
        with patch.dict(os.environ, {'SUMMARY_BRANCHES_AVAILABLE': 'false'}), \
                patch.object(ds, '_pulls'), patch.object(ds, '_updates'):
            lines = []
            ds.append_daily_summary(lines, 'o/r', ['buch/a'], {})
            self.assertIn('Buchaktivität unbekannt', '\n'.join(lines))
            self.assertNotIn('Keine Buchinhaltsänderungen', '\n'.join(lines))

    def test_old_open_prs_show_decisions_and_review_blocks(self):
        recent = {'number': 1, 'title': 'Neu | <script>', 'updated_at': '2026-11-06', 'state': 'closed', 'merged_at': 'now'}
        old = {'number': 2, 'title': 'Alt', 'updated_at': '2020-01-01', 'state': 'open'}
        with patch.object(ds, '_pages', side_effect=[[recent], [old], [
                {'user': {'login': 'a'}, 'state': 'CHANGES_REQUESTED'}]]), \
                patch.object(ds, '_api', return_value={'mergeable_state': 'clean'}):
            lines = []
            ds._pulls(lines, 'o/r', '2026-11-05')
            text = '\n'.join(lines)
            self.assertIn('gemergt', text)
            self.assertIn('Änderungen angefordert', text)
            self.assertIn('#2 Alt', text)
            self.assertNotIn('<script>', text)
            self.assertIn('&#124;', text)

    def test_unknown_merge_status_does_not_offer_approval(self):
        pr = {'number': 3, 'title': 'Offen', 'state': 'open'}
        with patch.object(ds, '_pages', side_effect=[[], [pr], []]), patch.object(ds, '_api', return_value={}):
            lines = []
            ds._pulls(lines, 'o/r', '2026-11-05')
            self.assertIn('Status noch unbekannt', '\n'.join(lines))

    def test_pause_and_failed_history_remain_visible(self):
        with patch.dict(os.environ, {'UPDATE_PAUSED': 'true', 'GITHUB_EVENT_NAME': 'schedule'}, clear=True), \
                patch.object(ds, '_pages', side_effect=[
                    [{'number': 4, 'title': 'GhostWriter-Automatik pausiert'}],
                    [{'id': 55, 'conclusion': 'failure'}]]):
            lines = []
            ds._updates(lines, 'author/book', '2026-11-05')
            text = '\n'.join(lines)
            self.assertIn('Update übersprungen', text)
            self.assertIn('/issues/4', text)
            self.assertIn('/actions/runs/55', text)

    def test_manual_run_reports_pause_as_warning(self):
        with patch.dict(os.environ, {'UPDATE_PAUSED': 'true', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
                                     'UPDATE_OUTCOME': 'success'}, clear=True), \
                patch.object(ds, '_pages', return_value=[]):
            lines = []
            ds._updates(lines, 'o/r', '2026-11-05')
            text = '\n'.join(lines)
            self.assertIn('Update-Schritt erfolgreich', text)
            self.assertIn('manuelle Lauf', text)
            self.assertNotIn('Update übersprungen', text)

    def test_workflow_preserves_single_schedule_and_failure_isolation(self):
        import yaml
        workflow = yaml.safe_load(Path('.github/workflows/update.yml').read_text())
        trigger = workflow.get('on', workflow.get(True))
        self.assertEqual(trigger['schedule'], [{'cron': '23 3 * * *'}])
        step = workflow['jobs']['update']['steps'][-1]
        self.assertTrue(step['continue-on-error'])
        self.assertEqual(step['if'], 'always()')
        self.assertEqual(step['env']['UPDATE_OUTCOME'], '${{ steps.apply.outcome }}')


class ContentActivityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.patcher = patch.object(ds, '_git', side_effect=self.git)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def git(self, *args):
        r = subprocess.run(['git', *args], cwd=self.root, text=True, capture_output=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        return r.stdout

    def commit(self, path, content):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        self.git('add', '.')
        self.git('commit', '-qm', 'Test')
        self.git('update-ref', 'refs/remotes/origin/buch/test', 'HEAD')

    def activity(self):
        return ds._content_activity('buch/test', ['chapters/'], '2000-01-01T00:00:00Z')

    def test_root_status_and_program_changes(self):
        self.commit('chapters/a.md', 'status: writing\n\nText\n')
        self.assertEqual(self.activity(), (1, 1))
        self.commit('chapters/a.md', 'status: approved\n\nText\n')
        self.commit('scripts/x.py', 'print(1)\n')
        self.assertEqual(self.activity(), (1, 1))
        self.commit('chapters/a.md', 'status: approved\n\nNeuer Text\n')
        self.assertEqual(self.activity(), (2, 1))

    def test_deletion_and_rename_count_changed_paths(self):
        self.commit('chapters/a.md', 'Text\n')
        self.git('mv', 'chapters/a.md', 'chapters/b.md')
        self.git('commit', '-qm', 'Verschieben')
        self.git('update-ref', 'refs/remotes/origin/buch/test', 'HEAD')
        self.assertEqual(self.activity(), (2, 2))
        self.git('rm', 'chapters/b.md')
        self.git('commit', '-qm', 'Entfernen')
        self.git('update-ref', 'refs/remotes/origin/buch/test', 'HEAD')
        self.assertEqual(self.activity(), (3, 2))

    def test_merge_counts_real_content_and_unique_files(self):
        self.commit('chapters/a.md', 'A\n')
        base = self.git('rev-parse', 'HEAD').strip()
        self.git('checkout', '-qb', 'side')
        self.commit('chapters/b.md', 'B\n')
        self.git('checkout', '-qb', 'other', base)
        self.commit('scripts/x.py', 'x\n')
        self.git('merge', '--no-ff', '-m', 'Merge', 'side')
        self.git('update-ref', 'refs/remotes/origin/buch/test', 'HEAD')
        self.assertEqual(self.activity(), (3, 2))

    def test_missing_ref_is_unknown_and_empty_paths_are_zero(self):
        self.assertEqual(ds._content_activity('missing', [], '2000-01-01'), (0, 0))
        with self.assertRaises(RuntimeError):
            ds._content_activity('missing', ['chapters/'], '2000-01-01')


if __name__ == "__main__":
    unittest.main()
