"""Versionierte Skill-Kopien ohne Netzwerk oder Änderungen persönlicher Skills."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import sync_skills as ss


class SyncSkillsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / 'source'
        self.source.mkdir()
        self.target = Path(self.tmp.name) / 'target'
        self.target.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        for name in ss.NAMES:
            path = self.source / 'skills' / name / 'SKILL.md'
            path.parent.mkdir(parents=True)
            path.write_text(f'---\nname: {name}\ndescription: Test\n---\nRegeln\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Quelle')
        self.commit = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.source), *args], text=True).strip()

    def test_shipped_copies_match_lock(self):
        self.assertEqual(ss.check(ROOT)['repository'], ss.REPOSITORY)

    def test_lock_and_only_general_skill_folders_are_program_owned(self):
        import yaml
        manifest = yaml.safe_load((ROOT / 'ghostwriter-manifest.yml').read_text())
        self.assertIn(ss.LOCK, manifest['managed'])
        self.assertNotIn('.claude/skills/', manifest['managed'])
        for name in ss.NAMES:
            self.assertIn('.claude/skills/' + name + '/', manifest['managed'])
        self.assertIn('.claude/skills/ghostwriter/', manifest['managed'])      # bleibt gelistet, damit das Update die alte Kopie entfernt (#569)
        self.assertNotIn('ghostwriter', ss.NAMES)

    def test_fixed_commit_ignores_dirty_source_and_preserves_personal_skill(self):
        personal = self.target / '.claude/skills/personal/SKILL.md'
        personal.parent.mkdir(parents=True)
        personal.write_text('Persönliche Regeln')
        (self.source / 'skills/ghostwriter-lektorat/SKILL.md').write_text('Ungeprüfter Entwurf')
        result = ss.sync(self.source, self.commit, self.target)
        self.assertEqual(result['commit'], self.commit)
        self.assertEqual(personal.read_text(), 'Persönliche Regeln')
        self.assertIn('Regeln', ss.target(self.target, 'ghostwriter-lektorat').read_text())
        self.assertFalse((self.target / '.claude/skills/ghostwriter').exists())   # entfällt (#569)
        self.assertFalse((self.target / '.claude/skills/buchteaser').exists())

    def test_drift_is_rejected(self):
        ss.sync(self.source, self.commit, self.target)
        ss.target(self.target, 'ghostwriter-lektorat').write_text('Abweichende Regeln')
        with self.assertRaises(ValueError):
            ss.check(self.target)

    def test_moving_ref_and_incomplete_source_cannot_overwrite_targets(self):
        with self.assertRaises(ValueError):
            ss.sync(self.source, 'main', self.target)
        self.git('rm', 'skills/ghostwriter-lektorat/SKILL.md')
        self.git('commit', '-qm', 'Unvollständig')
        with self.assertRaises(ValueError):
            ss.sync(self.source, self.git('rev-parse', 'HEAD'), self.target)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_symlink_target_is_rejected_before_any_write(self):
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        (self.target / '.claude').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            ss.sync(self.source, self.commit, self.target)
        self.assertEqual(list(outside.iterdir()), [])
