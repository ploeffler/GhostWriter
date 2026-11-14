"""Tests für die Stufen der Grundregeln (#300): Setzen, Lockern nur mit Bestätigung, Untergrenzen, Ansichten."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import rules  # noqa: E402
import validate_project  # noqa: E402


class RulesTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        self.commit = 'a' * 40

    def config(self):
        return yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))

    def entries(self):
        p = self.base / 'approvals.yml'
        return (yaml.safe_load(p.read_text(encoding='utf-8')) or {}).get('entries') or [] if p.is_file() else []

    def test_defaults(self):
        st = rules.show(self.base)
        self.assertEqual({g: s['level'] for g, s in st.items()},
                         {'facts': 'nonfiction', 'creativity': 'balanced', 'approvals': 'strict'})
        self.assertFalse(any(s['relaxed'] for s in st.values()))
        self.assertEqual(rules.problems(self.base), [])

    def test_tighten_without_confirmation(self):
        before = len(self.entries())
        r = rules.apply(self.base, 'creativity', 'careful', commit=self.commit)
        self.assertEqual(r['files'], ['ghostwriter.yml'])
        cfg = self.config()
        self.assertEqual(cfg['ai_settings']['creativity'], 'conservative')
        self.assertEqual(cfg['ai_settings']['web_research'], 'mandatory')
        self.assertEqual(cfg['rules']['creativity'], 'careful')
        self.assertEqual(len(self.entries()), before)
        self.assertEqual(validate_project.check_project(self.base), [])

    def test_relax_needs_confirmation(self):
        p = rules.plan(self.base, 'facts', 'fiction')
        self.assertTrue(p['needs_confirmation'])
        self.assertIn('ai_settings.source_policy', p['relaxes'])
        with self.assertRaises(SystemExit):
            rules.apply(self.base, 'facts', 'fiction')
        self.assertEqual(self.config()['ai_settings']['hallucination_policy'], 'strict')

    def test_relax_confirmed_and_back(self):
        rules.apply(self.base, 'facts', 'fiction', confirmed=True, by='ploeffler', commit=self.commit)
        cfg = self.config()
        self.assertEqual(cfg['ai_settings']['hallucination_policy'], 'standard')
        last = self.entries()[-1]
        self.assertEqual((last['kind'], last['id'], last['action'], last['by']), ('rules', 'rules-facts', 'granted', 'ploeffler'))
        self.assertIn('fiction', last['note'])
        self.assertEqual(validate_project.check_project(self.base), [])
        st = rules.show(self.base)['facts']
        self.assertTrue(st['confirmed'])
        rules.apply(self.base, 'facts', 'nonfiction', commit=self.commit)
        self.assertEqual(self.entries()[-1]['action'], 'revoked')
        self.assertEqual(self.config()['ai_settings']['hallucination_policy'], 'strict')
        self.assertEqual(validate_project.check_project(self.base), [])

    def test_unconfirmed_relaxation_is_reported(self):
        path = self.base / 'ghostwriter.yml'
        path.write_text(path.read_text(encoding='utf-8').replace('source_policy: required', 'source_policy: recommended'),
                        encoding='utf-8')
        errs = validate_project.check_project(self.base)
        self.assertTrue(any('ohne Bestätigung' in e for e in errs), errs)

    def test_floor(self):
        path = self.base / 'ghostwriter.yml'
        text = path.read_text(encoding='utf-8')
        path.write_text(text.replace('require_chapter_approval: true', 'require_chapter_approval: false')
                        .replace('source_policy: required', 'source_policy: optional'), encoding='utf-8')
        errs = rules.problems(self.base)
        self.assertTrue(any('require_chapter_approval' in e and 'Untergrenze' in e for e in errs), errs)
        self.assertTrue(any('source_policy' in e and 'Untergrenze' in e for e in errs), errs)

    def test_level_mismatch(self):
        path = self.base / 'ghostwriter.yml'
        path.write_text(path.read_text(encoding='utf-8') + 'rules:\n  facts: fiction\n', encoding='utf-8')
        self.assertTrue(any('rules.facts' in e for e in rules.problems(self.base)))

    def test_quick_approvals_in_views(self):
        rules.apply(self.base, 'approvals', 'quick', confirmed=True, commit=self.commit)
        cfg = self.config()
        self.assertFalse(cfg['workflow']['require_section_writing_approval'])
        self.assertTrue(cfg['workflow']['require_section_approval'])
        self.assertEqual(validate_project.check_project(self.base), [])
        run = lambda *a: subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *a,
                                         '--repo', 'o/r', '--text'], capture_output=True, text=True)
        sec = run('section', '1.1')
        self.assertEqual(sec.returncode, 0, sec.stderr)
        self.assertNotIn('Schreiben erlauben', sec.stdout)
        self.assertNotIn('Schreiben sperren', sec.stdout)
        self.assertIn('| Schreiben erlaubt | ✅ ja |', sec.stdout)
        settings = run('project-settings')
        self.assertIn('| Stufe Freigaben | Zügig · gelockert, bestätigt |', settings.stdout)
        appr = run('approval-writing', '1.1')
        self.assertIn('keine Schreibfreigabe nötig', appr.stdout)

    def test_choice_spec_renders(self):
        spec = self.base / 'rules.json'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/rules.py'), str(self.base), 'choice'], capture_output=True, text=True)
        spec.write_text(r.stdout, encoding='utf-8')
        v = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'choice', '--spec', str(spec),
                            '--repo', 'o/r', '--text'], capture_output=True, text=True)
        self.assertEqual(v.returncode, 0, v.stderr)
        self.assertIn('Erzählung', v.stdout)
        self.assertIn('Zügig', v.stdout)

    def test_cli_refuses_unconfirmed(self):
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/rules.py'), str(self.base), 'set', 'approvals', 'quick',
                            '--commit', self.commit], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Bestätigung', r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
