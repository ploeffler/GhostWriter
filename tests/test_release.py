import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import release  # noqa: E402


def make_root(tmp, version='1.0.0', de=True, en=True):
    root = Path(tmp)
    (root / 'docs').mkdir()
    (root / 'ghostwriter-manifest.yml').write_text(f'version: {version}\n')
    (root / 'docs/UPDATES.md').write_text(('**1.0.0:** Neu.\n\n' if de else '') + '**0.9.0:** Alt.\n')
    (root / 'docs/UPDATES.en.md').write_text(('**1.0.0** adds new.\n\n' if en else '') + '**0.9.0:** Old.\n')
    return root


class ReleaseTest(unittest.TestCase):
    def test_tag_name_follows_existing_tags(self):
        self.assertEqual(release.tag_name('0.9.0'), 'v0.9')
        self.assertEqual(release.tag_name('1.0.0'), 'v1.0')
        self.assertEqual(release.tag_name('1.0.1'), 'v1.0.1')
        with self.assertRaises(ValueError):
            release.tag_name('1.0')

    def test_check_passes_with_matching_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(release.check('1.0.0', '1.0.0', make_root(tmp)), [])

    def test_check_refuses_wrong_confirmation_version_or_missing_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp, version='0.9.0', en=False)
            problems = ' '.join(release.check('1.0.0', 'ok', root))
            self.assertIn('Manifest', problems)
            self.assertIn('Bestätigung', problems)
            self.assertIn('UPDATES.en.md', problems)

    def test_notes_extracts_only_version_paragraph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            self.assertEqual(release.notes('1.0.0', root), '**1.0.0:** Neu.')
            self.assertIsNone(release.notes('2.0.0', root))

    def test_site_check(self):
        good = {'/build-info.json': json.dumps({'version': '1.0.0'}),
                '/de/index.html': '<strong>1.0.0</strong>', '/en/index.html': '<strong>1.0.0</strong>'}
        get = lambda url: good[url.removeprefix('https://x')]
        self.assertEqual(release.check_site('https://x/', '1.0.0', get), [])
        stale = dict(good, **{'/build-info.json': json.dumps({'version': '0.6.0'})})
        problems = release.check_site('https://x', '1.0.0', lambda url: stale[url.removeprefix('https://x')])
        self.assertTrue(any('0.6.0' in p for p in problems))

    def test_workflow_is_manual_main_only_and_has_dry_run(self):
        wf = yaml.load((ROOT / '.github/workflows/release.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(set(wf['on']), {'workflow_dispatch'})
        inputs = wf['on']['workflow_dispatch']['inputs']
        self.assertEqual(inputs['dry_run']['default'], 'false')
        self.assertIn('confirm', inputs)
        self.assertIn("github.ref == 'refs/heads/main'", wf['jobs']['release']['if'])
        steps = wf['jobs']['release']['steps']
        publishing = [s for s in steps if 'gh release create' in s.get('run', '') or s.get('id') == 'deployment']
        self.assertEqual(len(publishing), 2)
        for step in publishing:
            self.assertIn('!inputs.dry_run', step['if'])


if __name__ == '__main__':
    unittest.main()
