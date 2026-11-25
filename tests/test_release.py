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

    def test_prerelease_tag_and_branch_rules(self):
        self.assertEqual(release.tag_name('1.0.0', '1'), 'v1.0-rc.1')
        self.assertEqual(release.tag_name('1.0.1', 2), 'v1.0.1-rc.2')
        for bad in ('0', 'a', '-1'):
            with self.assertRaises(ValueError):
                release.tag_name('1.0.0', bad)
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp)
            self.assertEqual(release.check('1.0.0', '1.0.0', root, prerelease='1', ref='release/1.0.0'), [])
            self.assertTrue(release.check('1.0.0', '1.0.0', root, prerelease='1', ref='main'))
            self.assertTrue(release.check('1.0.0', '1.0.0', root, ref='release/1.0.0'))
            self.assertEqual(release.check('1.0.0', '1.0.0', root, ref='main'), [])

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
        cond = wf['jobs']['release']['if']
        self.assertIn("github.ref == 'refs/heads/main'", cond)
        self.assertIn("startsWith(github.ref, 'refs/heads/release/')", cond)
        self.assertIn('prerelease', inputs)
        steps = wf['jobs']['release']['steps']
        publishing = [s for s in steps if 'gh release create' in s.get('run', '') or s.get('id') == 'deployment']
        self.assertEqual(len(publishing), 2)
        for step in publishing:
            self.assertIn('!inputs.dry_run', step['if'])
        website = [s for s in steps if s.get('id') == 'deployment' or s.get('uses', '').startswith(('actions/configure-pages', 'actions/upload-pages'))
                   or s.get('name') in ('Öffentliche Website nachprüfen', 'Dokumentationswebsite bauen und prüfen')]
        self.assertEqual(len(website), 5)
        for step in website:
            self.assertIn("inputs.prerelease == ''", step['if'])   # Vorabversion veröffentlicht keine Website
        text = (ROOT / '.github/workflows/release.yml').read_text()
        self.assertIn('--prerelease --title', text)
        self.assertIn("inputs.prerelease == '' && 'github-pages' || ''", text)   # Umgebung nur für main


    def test_merged_prs_with_empty_body(self):
        """Ein Merge-Commit ohne Rumpf darf den Entwurf nicht abbrechen (str.strip() entfernt das Trennzeichen \\x1f)."""
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            g = lambda *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *a], cwd=d, check=True,
                                          capture_output=True, text=True)
            g('init', '-q', '-b', 'main')
            g('commit', '-q', '--allow-empty', '-m', 'Start')
            g('tag', 'v1.0')
            g('switch', '-q', '-c', 'x')
            g('commit', '-q', '--allow-empty', '-m', 'Arbeit')
            g('switch', '-q', 'main')
            g('merge', '-q', '--no-ff', '-m', 'Merge pull request #7 from o/x', 'x')   # ohne Rumpf
            g('switch', '-q', '-c', 'y')
            g('commit', '-q', '--allow-empty', '-m', 'Mehr')
            g('switch', '-q', 'main')
            g('merge', '-q', '--no-ff', '-m', 'Merge pull request #8 from o/y', '-m', 'Titel des PR', 'y')
            self.assertEqual(release.merged_prs('v1.0', Path(d)), [(7, 'Merge pull request #7 from o/x'), (8, 'Titel des PR')])

    def test_prepare_sets_version_and_inserts_draft_that_blocks_publishing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(tmp, version='0.9.0', de=False, en=False)
            release.prepare('1.0.0', root, prs=[(541, 'Release veröffentlichen')])
            self.assertIn('version: 1.0.0', (root / 'ghostwriter-manifest.yml').read_text())
            de = (root / 'docs/UPDATES.md').read_text()
            self.assertTrue(de.startswith('**1.0.0:** Release veröffentlichen (#541).'))
            self.assertLess(de.index('**1.0.0:**'), de.index('**0.9.0:**'))
            self.assertIn('**1.0.0** ', (root / 'docs/UPDATES.en.md').read_text())
            self.assertTrue(any('Entwurf' in p for p in release.check('1.0.0', '1.0.0', root)))
            release.prepare('1.0.0', root, prs=[(999, 'anders')])  # zweiter Lauf: Entwurf bleibt
            self.assertNotIn('#999', (root / 'docs/UPDATES.md').read_text())

    def test_languages_reports_gaps_for_partial_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in release.CATALOGS:
                (root / folder).mkdir(parents=True)
                (root / folder / 'de.json').write_text(json.dumps({'a': 'Hallo {name}', 'b': 'x'}))
                (root / folder / 'en.json').write_text(json.dumps({'a': 'Hi {name}', 'b': 'x'}))
                (root / folder / 'fr.json').write_text(json.dumps({'a': 'Salut {nom}'}))
            (root / 'docs').mkdir()
            (root / 'docs/site.json').write_text(json.dumps({'pages': [{'id': 'index', 'source': {'de': 'a.md', 'en': 'b.md'}}]}))
            report = release.languages(root)
            self.assertEqual(report['en']['status'], 'vollständig')
            self.assertEqual(report['fr']['status'], 'Lücken')
            gaps = ' '.join(report['fr']['gaps'])
            self.assertIn('Schlüssel fehlen', gaps)
            self.assertIn('Platzhalter', gaps)
            self.assertIn('Doku-Seiten ohne Fassung: index', gaps)

    def test_repository_languages_de_en_complete(self):
        report = release.languages()
        self.assertEqual(report['de']['status'], 'vollständig')
        self.assertIn('en', report)

    def test_report_verdict(self):
        langs = {'de': {'status': 'vollständig', 'gaps': []}, 'en': {'status': 'vollständig', 'gaps': []},
                 'fr': {'status': 'Lücken', 'gaps': ['x']}}
        text, ready = release.render_report('1.0.0', langs, {'Doku': True}, [{'number': 1, 'title': 'Wunsch', 'labels': []}], 'v1.0')
        self.assertTrue(ready)
        self.assertIn('bereit zum Scharfschalten', text)
        text, ready = release.render_report('1.0.0', langs, {'Doku': False},
                                            [{'number': 476, 'title': 'Fehler', 'labels': ['bug']}], 'v1.0')
        self.assertFalse(ready)
        self.assertIn('nicht bereit', text)
        self.assertIn('#476', text)
        langs['en'] = {'status': 'Lücken', 'gaps': ['y']}
        self.assertFalse(release.render_report('1.0.0', langs, {}, [], 'v1.0')[1])

    def test_testplan_open_rows_are_reported(self):
        path, open_rows = release.testplan('1.0.0')
        self.assertEqual(path, 'docs/TESTPLAN-v1.0.md')
        self.assertGreater(open_rows, 0)
        text, ready = release.render_report('1.0.0', {'de': {'status': 'vollständig', 'gaps': []},
                                                      'en': {'status': 'vollständig', 'gaps': []}}, {}, [], 'v1.0', (path, 3))
        self.assertTrue(ready)
        self.assertIn('3 Prüfungen offen', text)
        self.assertEqual(release.testplan('9.9.0'), (None, 0))

    def test_prepare_workflow_is_manual_and_never_publishes(self):
        text = (ROOT / '.github/workflows/release-prepare.yml').read_text()
        wf = yaml.load(text, Loader=yaml.BaseLoader)
        self.assertEqual(set(wf['on']), {'workflow_dispatch'})
        self.assertNotIn('pages', wf.get('permissions', {}))
        self.assertIn('--skip tests', text)
        self.assertNotIn('-f base=main', text)  # PR legt die Sitzung an, damit validate läuft
        for forbidden in ('gh release', 'deploy-pages', 'git tag'):
            self.assertNotIn(forbidden, text)


if __name__ == '__main__':
    unittest.main()
