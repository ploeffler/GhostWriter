"""Rückgabe einchecken (#573)."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import checkin  # noqa: E402
import checkout  # noqa: E402
from render_view import load  # noqa: E402

try:
    import docx
    import segno  # noqa: F401
    HAVE = bool(shutil.which('pandoc'))
except ImportError:
    HAVE = False
try:
    import cv2
except ImportError:
    cv2 = None


def git(base, *args):
    return subprocess.run(['git', '-C', str(base), *args], check=True, capture_output=True, text=True,
                          env={'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't',
                               'GIT_COMMITTER_EMAIL': 't@t', 'PATH': '/usr/bin:/bin:/usr/local/bin'}).stdout.strip()


class PureTest(unittest.TestCase):
    def test_payload(self):
        p = checkin.parse_payload('GW1|o/r|buch/x|GW-ABCD|ch-01')
        self.assertEqual((p['repo'], p['id'], p['chapter']), ('o/r', 'GW-ABCD', 'ch-01'))
        self.assertIsNone(checkin.parse_payload('GW1|o/r|buch/x|GW-0000'))        # 0 gibt es im Alphabet nicht
        self.assertIsNone(checkin.parse_payload('http://example.org'))

    def test_norm_ignores_markup_and_smart_quotes(self):
        self.assertEqual(checkin.norm('Er sagte *leise* „ja“ …'), checkin.norm('Er sagte leise "ja" ...'))

    def test_compare_section_gives_unique_alt_neu(self):
        ours = 'Der Hund lief schnell über die Straße. Dann kam er heim.\n\nEin zweiter Absatz bleibt gleich.'
        theirs = ['Der Hund lief langsam über die Straße. Dann kam er heim.', 'Ein zweiter Absatz bleibt gleich.']
        out = checkin.compare_section('s', ours, theirs, ours)
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]['art'], out[0]['alt'], out[0]['neu']), ('sprache', 'schnell', 'langsam'))

    def test_changed_since_checkout_becomes_a_question(self):
        ours = 'Der Hund lief schnell über die Straße.'
        today = 'Der Hund rannte über die Straße.'
        out = checkin.compare_section('s', ours, ['Der Hund lief langsam über die Straße.'], today)
        self.assertNotIn('alt', out[0])
        self.assertIn('seit dem Checkout geändert', out[0]['frage'])
        self.assertIn('Gegenleser', out[0]['frage'])

    def test_deleted_and_inserted_paragraphs(self):
        ours = 'Erster Absatz.\n\nZweiter Absatz.'
        out = checkin.compare_section('s', ours, ['Erster Absatz.'], ours)
        self.assertIn('gestrichen', out[0]['befund'])
        out = checkin.compare_section('s', ours, ['Erster Absatz.', 'Zweiter Absatz.', 'Neuer Absatz.'], ours)
        self.assertIn('eingefügt', out[0]['befund'])


@unittest.skipUnless(HAVE, 'pandoc, python-docx und segno nötig')
class CheckinFlowTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.base = self.tmp / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        git(self.base, 'init', '-q')
        git(self.base, 'add', '-A')
        git(self.base, 'commit', '-qm', 'start')
        _, self.config = load(self.base)
        import checkout_files
        self.cf = checkout_files
        self.commit = git(self.base, 'rev-parse', 'HEAD')
        self.entry = checkout.start(self.base, self.config, 'Anna', '1', by='x', commit=self.commit)
        self.out = self.tmp / 'out'
        files = self.cf.build(self.base, self.config, self.entry, self.out, 'o/r', 'buch/x', self.commit, '2026-11-24', pdf=False)
        self.docx = self.out / files[0]

    def edit(self, old, new, comment=None):
        d = docx.Document(str(self.docx))
        hit = None
        for p in d.paragraphs:
            if old in p.text:
                hit = p
                for r in p.runs:
                    if old in r.text:
                        r.text = r.text.replace(old, new)
                        break
                else:
                    p.text = p.text.replace(old, new)
                break
        self.assertIsNotNone(hit, old)
        if comment:
            d.add_comment(hit.runs, text=comment, author='Anna')
        out = self.tmp / 'zurueck.docx'
        d.save(str(out))
        return out

    def sample_word(self):
        sid = self.config['structure']['chapters'][0]['sections'][0]
        text = checkin.manuscript_of((self.base / sid['path']).read_text(encoding='utf-8'))
        words = [w for w in text.split() if w.isalpha() and len(w) > 6 and text.count(w) == 1]
        return words[0]

    def test_docx_return_makes_findings_and_keeps_checkout(self):
        word = self.sample_word()
        back = self.edit(word, 'Ersatzwort', comment='Bitte prüfen')
        folder, report = checkin.checkin(self.base, self.config, [back], date='2026-11-25')
        self.assertTrue((folder / 'original.docx').is_file())
        self.assertEqual(report['kennung'], self.entry['id'])
        self.assertGreaterEqual(report['befunde'], 2)                       # Textänderung + Kommentar
        self.assertEqual(report['kommentare'], 1)
        findings = yaml.safe_load((self.base / report['befunddatei']).read_text(encoding='utf-8'))
        change = next(f for f in findings['befunde'] if f.get('alt'))
        self.assertEqual((change['alt'], change['neu']), (word, 'Ersatzwort'))
        self.assertEqual(change['art'], 'sprache')
        import validate_project
        self.assertFalse(validate_project.check_project(self.base))          # Befunddatei, Checkout und Ablage sind gültig
        self.assertTrue(any('Bitte prüfen' in f.get('frage', '') for f in findings['befunde']))
        data = checkout.load(self.base)['checkouts'][0]
        self.assertEqual(data['status'], 'ausgecheckt')                     # nie automatisch beendet
        self.assertEqual(len(data['rueckgaben']), 1)
        import hinweise
        path, dialog = hinweise.collect(self.base, self.config, date='2026-11-25')    # Kette läuft weiter
        self.assertTrue(any(word in (e.get('alt') or '') for _, e in hinweise.entries(dialog)))

    def test_second_return_gets_own_folder_and_unchanged_docx_has_no_findings(self):
        folder1, r1 = checkin.checkin(self.base, self.config, [self.docx], date='2026-11-25')
        folder2, _ = checkin.checkin(self.base, self.config, [self.docx], date='2026-11-25')
        self.assertNotEqual(folder1, folder2)
        self.assertEqual(r1['befunde'], 0)
        self.assertNotIn('befunddatei', r1)

    def test_wrong_checkout_and_unknown_file_leave_nothing(self):
        with self.assertRaisesRegex(ValueError, 'gehört zu'):
            checkin.checkin(self.base, self.config, [self.docx], checkout_id='GW-2222')
        with self.assertRaisesRegex(ValueError, 'nicht eingecheckt'):
            checkin.checkin(self.base, self.config, [self.tmp / 'x.txt'])
        self.assertFalse((self.base / 'checkouts' / 'GW-2222').exists())
        self.assertEqual(checkout.load(self.base)['checkouts'][0].get('rueckgaben'), None)

    def test_late_return_after_end_is_allowed(self):
        checkout.end(self.base, self.config, self.entry['id'], 'Leser meldet sich nicht', abort=True)
        _, report = checkin.checkin(self.base, self.config, [self.docx], date='2026-11-25')
        self.assertTrue(report['spaet'])
        self.assertEqual(checkout.load(self.base)['checkouts'][0]['status'], 'abgebrochen')

    @unittest.skipUnless(cv2 is not None and shutil.which('soffice') and shutil.which('pdftoppm'), 'OpenCV, LibreOffice, pdftoppm nötig')
    def test_photo_of_printed_pages_is_assigned_by_qr(self):
        files = self.cf.build(self.base, self.config, self.entry, self.out, 'o/r', 'buch/x', self.commit, '2026-11-24')
        pdf = self.out / next(f for f in files if f.endswith('.pdf'))
        subprocess.run(['pdftoppm', '-r', '300', '-f', '1', '-l', '2', '-jpeg', str(pdf), str(self.tmp / 'foto')], check=True)
        pics = sorted(self.tmp.glob('foto-*.jpg'))
        folder, report = checkin.checkin(self.base, self.config, pics, date='2026-11-25')
        self.assertEqual(report['art'], 'scan')
        self.assertEqual([p['zuordnung'] for p in report['seiten']], ['qr', 'qr'])
        self.assertEqual(report['seiten'][1]['kapitel'], self.config['structure']['chapters'][0]['id'])
        self.assertTrue((folder / 'seite-01.jpg').is_file())
        self.assertTrue((folder / 'original-1.jpg').is_file())
        blank = self.tmp / 'leer.jpg'
        cv2.imwrite(str(blank), (255 * __import__('numpy').ones((600, 400, 3))).astype('uint8'))
        with self.assertRaisesRegex(ValueError, 'Keine Kennung'):
            checkin.checkin(self.base, self.config, [blank])


if __name__ == '__main__':
    unittest.main()
