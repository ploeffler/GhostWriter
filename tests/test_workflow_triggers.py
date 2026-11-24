"""#287: Pushes auf Arbeits-Branches legen keine Workflow-Läufe an (weniger Läufe, weniger E-Mails)."""
import fnmatch
import pathlib
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = ['validate.yml', 'index.yml', 'edition.yml', 'library.yml']
WORK_BRANCHES = ['ghostwriter/buch/x', 'ghostwriter/chat/2026-11-13-a', 'codex/x', 'claude/x', 'feat/x', 'fix/x']
BOOK_BRANCHES = ['main', 'buch/x']


def push_filter(name):
    data = yaml.safe_load((ROOT / '.github' / 'workflows' / name).read_text(encoding='utf-8'))
    on = data.get('on', data.get(True))
    return on['push'].get('branches-ignore', [])


def ignored(patterns, branch):
    # GitHub-Glob: ** passt auch über „/“ hinweg; fnmatch-* tut das ebenfalls.
    return any(fnmatch.fnmatchcase(branch, p.replace('**', '*')) for p in patterns)


class WorkflowTriggerTest(unittest.TestCase):
    def test_work_branches_start_no_push_run(self):
        for name in WORKFLOWS:
            patterns = push_filter(name)
            for b in WORK_BRANCHES:
                self.assertTrue(ignored(patterns, b), f'{name}: {b} würde einen Lauf starten')

    def test_book_branches_still_run(self):
        for name in WORKFLOWS:
            patterns = push_filter(name)
            for b in BOOK_BRANCHES:
                self.assertFalse(ignored(patterns, b), f'{name}: {b} wäre ausgeschlossen')


class ValidateDoubleRunTest(unittest.TestCase):
    """#485: kein zweiter Volllauf auf dem Standard-Branch für einen schon geprüften Baum."""

    def setUp(self):
        self.text = (ROOT / '.github' / 'workflows' / 'validate.yml').read_text(encoding='utf-8')
        self.data = yaml.safe_load(self.text)

    def steps(self):
        return self.data['jobs']['validate']['steps']

    def test_newest_push_cancels_older_run(self):
        self.assertIs(self.data['concurrency']['cancel-in-progress'], True)

    def test_full_pr_run_records_tree_as_last_step(self):
        last = self.steps()[-1]
        self.assertEqual(last.get('uses'), 'actions/upload-artifact@v4')
        self.assertEqual(last['with']['name'], 'validate-full-${{ steps.scope.outputs.tree }}')
        self.assertIn("github.event_name == 'pull_request'", last['if'])
        self.assertIn("steps.scope.outputs.mode == 'full'", last['if'])

    def test_default_branch_skips_tests_for_checked_tree(self):
        scope = next(s for s in self.steps() if s.get('id') == 'scope')
        self.assertIn('actions/artifacts?name=validate-full-$tree', scope['run'])
        self.assertIn('mode=skip', scope['run'])
        tests = next(s for s in self.steps() if s.get('name', '').startswith('Tests'))
        self.assertIn('"$MODE" = "skip"', tests['run'])
        self.assertEqual(self.data['permissions'].get('actions'), 'read')


if __name__ == '__main__':
    unittest.main()
