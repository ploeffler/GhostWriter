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


if __name__ == '__main__':
    unittest.main()
