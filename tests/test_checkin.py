"""Rückgabe einchecken (#573)."""
import re
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


BLANK_PNG = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8ffff3f0005fe02fea7d6c3f00000000049454e44ae426082')


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
        other = self.edit(self.sample_word(), 'Ersatzwort')
        folder2, r2 = checkin.checkin(self.base, self.config, [other], date='2026-11-25')
        self.assertNotEqual(folder1, folder2)
        self.assertEqual(r1['befunde'], 0)
        self.assertNotIn('befunddatei', r1)
        self.assertGreaterEqual(r2['befunde'], 1)

    def test_same_file_twice_is_refused_without_duplicates(self):
        checkin.checkin(self.base, self.config, [self.docx], date='2026-11-25')
        with self.assertRaisesRegex(ValueError, 'schon eingecheckt'):
            checkin.checkin(self.base, self.config, [self.docx], date='2026-11-25')
        self.assertEqual(len(list((self.base / 'checkouts' / self.entry['id']).glob('rueckgabe-*'))), 1)
        self.assertEqual(len(checkout.load(self.base)['checkouts'][0]['rueckgaben']), 1)

    def test_footnotes_tables_and_images_are_reported_as_not_taken_over(self):
        _, report = checkin.checkin(self.base, self.config, [self.docx], date='2026-11-25')
        self.assertTrue(any('Tabellen' in x for x in report.get('nicht_uebernommen', [])))      # das Testbuch hat eine Tabelle
        self.assertIn('Nicht übernommen: ', checkin.summary(report))

    def test_return_view_for_the_widget_and_text(self):
        folder, report = checkin.checkin(self.base, self.config, [self.restructure()], date='2026-11-25')
        rel = folder.relative_to(self.base).as_posix()
        values, blocks = checkin.view_values(self.base, self.config, rel)
        self.assertEqual(values['RET_ID'], self.entry['id'])
        self.assertEqual(len(blocks['AUFBAU']), 4)
        self.assertTrue(all(a['A_STATE'] == 'offen' for a in blocks['AUFBAU']))
        self.assertEqual(values['RET_CAN_APPLY'], '')
        self.assertIn('erst beenden', values['RET_APPLY_HINT'])
        self.assertIn(self.entry['id'], values['RET_END_ARGS'])
        self.assertIn('25.11.2026', values['RET_DATE_TEXT'])
        text = checkin.text_view(self.base, self.config, rel)
        self.assertIn('Aufbau-Änderungen', text)
        self.assertIn('Rückgabe eingecheckt', text)
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'checkin', rel], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('GW.render("rueckgabe"', out.stdout)
        checkout.end(self.base, self.config, self.entry['id'], 'zurück', by='x')
        values, _ = checkin.view_values(self.base, self.config, rel, 'en')
        self.assertEqual((values['RET_CAN_APPLY'], values['RET_END_ARGS'], values['RET_APPLY_HINT']), ('1', '', ''))
        self.assertIn('findings', values['RET_STATS_TEXT'])

    def test_changed_structure_since_return_blocks_apply(self):
        folder, report = checkin.checkin(self.base, self.config, [self.restructure()], date='2026-11-25')
        checkout.end(self.base, self.config, self.entry['id'], 'zurück', by='x')
        import sections
        sections.cmd_rename(self.base, 'sec-01-02-die-etiketten-die-wir-kennen', 'Zwischendurch geändert')
        with self.assertRaisesRegex(ValueError, 'Gliederung hat sich'):
            checkin.aufbau_apply(self.base, self.config, folder, [report['aufbau'][0]['id']], confirm=True)

    # --- Aufbau (#209) ---

    def restructure(self):
        """Gegenleser: 1.5 gelöscht, 1.4 umbenannt, 1.3 hinter 1.6 geschoben, neuer Abschnitt nach 1.9."""
        from docx import Document
        d = Document(str(self.docx))
        body = d.element.body
        kids = list(body)
        groups, cur = {}, None
        for el in kids:
            if el.tag.endswith('}p'):
                text = ''.join(t.text or '' for t in el.iter(checkin.q('t'))).strip()
                style = el.find(f'{checkin.q("pPr")}/{checkin.q("pStyle")}')
                val = (style.get(checkin.q('val')) if style is not None else '') or ''
                if val in ('Heading1', 'Heading2'):
                    cur = text[:3] if val == 'Heading2' and text[:1].isdigit() else None
                    if val == 'Heading2' and not text[:1].isdigit():
                        cur = text           # „Quellen“
            if cur and not el.tag.endswith('}sectPr'):    # Tabellen gehören zu ihrem Abschnitt
                groups.setdefault(cur, []).append(el)
        for el in groups['1.5']:
            body.remove(el)
        rename = groups['1.4'][0]
        for t in rename.iter(checkin.q('t')):
            t.text = (t.text or '').replace('Die Uhr, die bei mir anders tickt', 'Meine innere Uhr')
        anchor = groups['1.6'][-1]
        for el in reversed(groups['1.3']):
            anchor.addnext(el)
        last = groups['1.9'][-1]
        import copy
        head = copy.deepcopy(groups['1.9'][0])
        for el in list(head):
            if el.tag.endswith('}bookmarkStart') or el.tag.endswith('}bookmarkEnd'):
                head.remove(el)
        texts = list(head.iter(checkin.q('t')))
        texts[0].text = 'Neuer Gedanke'
        for t in texts[1:]:
            t.text = ''
        paras = []
        for line in ('Ein ganz neuer Absatz.', 'Und noch einer.'):
            para = copy.deepcopy(groups['1.9'][1])
            ts = list(para.iter(checkin.q('t')))
            ts[0].text = line
            for t in ts[1:]:
                t.text = ''
            paras.append(para)
        for el in reversed([head] + paras):
            last.addnext(el)
        out = self.tmp / 'umgebaut.docx'
        d.save(str(out))
        return out

    def test_structure_changes_are_listed_and_applied_only_after_confirmation(self):
        back = self.restructure()
        folder, report = checkin.checkin(self.base, self.config, [back], date='2026-11-25')
        kinds = sorted(a['art'] for a in report['aufbau'])
        self.assertEqual(kinds, ['geloescht', 'neu', 'umbenannt', 'verschoben'], report['aufbau'])
        self.assertEqual(report['befunde'], 0)                         # reine Aufbau-Änderungen, kein Text geändert
        by = {a['art']: a for a in report['aufbau']}
        self.assertEqual(by['neu']['text'], ['Ein ganz neuer Absatz.', 'Und noch einer.'])
        self.assertTrue(by['verschoben']['abschnitt'].startswith('sec-01-03'))
        self.assertEqual(by['verschoben']['hinter'][:10], 'sec-01-06-')
        rows = checkin.aufbau_list(self.base, self.config, folder.relative_to(self.base))
        self.assertEqual(len(rows), 4)
        ids = [a['id'] for a in report['aufbau']]
        with self.assertRaisesRegex(ValueError, 'Bestätigung'):
            checkin.aufbau_apply(self.base, self.config, folder, ids, confirm=False)
        with self.assertRaisesRegex(ValueError, 'läuft noch'):
            checkin.aufbau_apply(self.base, self.config, folder, ids, confirm=True)
        checkout.end(self.base, self.config, self.entry['id'], 'zurück', by='x')
        before = (self.base / 'chapters/01-endlich-eine-erklaerung/sections/03-was-hinter-den-etiketten-steckt.md').read_text(encoding='utf-8')
        results = dict(checkin.aufbau_apply(self.base, self.config, folder, [by['umbenannt']['id'], by['neu']['id']], confirm=True))
        self.assertEqual(len(results), 2, results)
        _, config = load(self.base)
        titles = [x['title'] for x in config['structure']['chapters'][0]['sections']]
        self.assertIn('Meine innere Uhr', titles)
        self.assertEqual(titles[-1], 'Neuer Gedanke')
        new = config['structure']['chapters'][0]['sections'][-1]
        self.assertIn('Ein ganz neuer Absatz.', (self.base / new['path']).read_text(encoding='utf-8'))
        rest = dict(checkin.aufbau_apply(self.base, self.config, folder, [by['verschoben']['id'], by['geloescht']['id']], confirm=True))
        _, config = load(self.base)
        numbers = {x['id']: f'1.{i}' for i, x in enumerate(config['structure']['chapters'][0]['sections'], start=1)}
        self.assertNotIn(by['geloescht']['abschnitt'], numbers)
        self.assertEqual(numbers[by['verschoben']['abschnitt']], '1.5')       # nach 1.6 (alt), 1.5 ist entfernt
        text3 = (self.base / [x for x in config['structure']['chapters'][0]['sections'] if x['id'] == by['verschoben']['abschnitt']][0]['path']).read_text(encoding='utf-8')
        self.assertEqual(text3.split('## Manuskript')[1], before.split('## Manuskript')[1])   # Text unverändert
        rep = yaml.safe_load((folder / 'rueckgabe.yml').read_text(encoding='utf-8'))
        self.assertTrue(all(a['status'] == 'uebernommen' for a in rep['aufbau']), rest)
        import validate_project
        self.assertFalse(validate_project.check_project(self.base))

    def test_missing_sections_in_unrecognized_file_delete_nothing(self):
        out = self.tmp / 'leer.docx'
        from docx import Document
        d = Document(str(self.docx))
        for el in list(d.element.body):
            if el.tag.endswith('}p') and not any('GW-' in (t.text or '') or 'Kennung' in (t.text or '') for t in el.iter(checkin.q('t'))):
                d.element.body.remove(el)
        d.save(str(out))
        _, report = checkin.checkin(self.base, self.config, [out], date='2026-11-25')
        self.assertFalse([a for a in report['aufbau'] if a['art'] == 'geloescht'])

    def test_unchanged_return_has_no_structure_changes(self):
        _, report = checkin.checkin(self.base, self.config, [self.docx], date='2026-11-25')
        self.assertEqual(report['aufbau'], [])

    @unittest.skipUnless(cv2 is not None and shutil.which('soffice') and shutil.which('pdftotext'), 'OpenCV, LibreOffice, pdftotext nötig')
    # --- Programme (#209): Word, LibreOffice, Google Docs, Pages ---

    def variant(self, program, change=None, comment=None):
        """Rückgabe-DOCX so, wie das Programm sie typischerweise schreibt (Eigenschaften, Textmarken, Kommentare, Bilder)."""
        src = self.edit(change[0], change[1], comment) if change else self.docx
        out = self.tmp / f'{program}.docx'
        if program == 'libreoffice':
            conv = self.tmp / 'lo'
            subprocess.run(['soffice', '--headless', '--convert-to', 'docx:MS Word 2007 XML', '--outdir', str(conv), str(src)],
                           check=True, capture_output=True)
            shutil.copyfile(conv / src.name, out)
            return out
        import zipfile
        app = {'word': 'Microsoft Office Word', 'google': 'Google Docs', 'pages': 'Pages'}[program]
        lose = {'word': (), 'google': ('props', 'marks'), 'pages': ('props', 'marks', 'comments', 'media')}[program]
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == 'docProps/custom.xml' and 'props' in lose:
                    continue
                if item.filename == 'word/comments.xml' and 'comments' in lose:
                    continue
                if item.filename.startswith('word/media/') and 'media' in lose:
                    data = BLANK_PNG       # Pages rendert Bilder neu: der QR-Code ist nicht mehr lesbar
                if item.filename == 'docProps/app.xml':
                    data = f'<Properties><Application>{app}</Application></Properties>'.encode()
                if item.filename == 'word/document.xml':
                    text = data.decode('utf-8')
                    if 'marks' in lose:
                        text = re.sub(r'<w:bookmark(?:Start|End)\b[^>]*/>', '', text)
                    if 'comments' in lose:
                        text = re.sub(r'<w:comment(?:RangeStart|RangeEnd|Reference)\b[^>]*/?>(?:</w:commentReference>)?', '', text)
                        text = re.sub(r'<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr></w:r>', '', text)
                    data = text.encode('utf-8')
                if item.filename in ('_rels/.rels', '[Content_Types].xml') and 'props' in lose:
                    data = re.sub(r'<(?:Relationship|Override) [^>]*custom\.xml[^>]*/>', '', data.decode('utf-8')).encode('utf-8')
                if item.filename in ('word/_rels/document.xml.rels', '[Content_Types].xml') and ('comments' in lose or 'media' in lose):
                    text = data.decode('utf-8')
                    if 'comments' in lose:
                        text = re.sub(r'<Relationship [^>]*comments[^>]*/>', '', text)
                        text = re.sub(r'<Override [^>]*comments[^>]*/>', '', text)
                    data = text.encode('utf-8')
                zout.writestr(item, data)
        return out

    def check_program(self, program, expect_comment=True):
        word = self.sample_word()
        back = self.variant(program, (word, 'Ersatzwort'), comment='Bitte prüfen' if expect_comment else None)
        folder, report = checkin.checkin(self.base, self.config, [back], date='2026-11-25')
        findings = yaml.safe_load((self.base / report['befunddatei']).read_text(encoding='utf-8'))['befunde']
        change = next(f for f in findings if f.get('alt'))
        self.assertEqual((change['alt'], change['neu']), (word, 'Ersatzwort'), program)
        return report, findings

    def test_word_return_with_tracked_changes_is_not_accepted_silently(self):
        report, _ = self.check_program('word')
        self.assertEqual(report['programm'], 'Word')
        self.assertEqual(report['kennung_aus'], 'eigenschaft')

    @unittest.skipUnless(shutil.which('soffice'), 'LibreOffice nötig')
    def test_libreoffice_roundtrip(self):
        report, findings = self.check_program('libreoffice')
        self.assertEqual(report['programm'], 'LibreOffice Writer')
        self.assertTrue(any('Bitte prüfen' in f.get('frage', '') for f in findings))

    def test_google_docs_without_properties_and_textmarks(self):
        report, findings = self.check_program('google')
        self.assertEqual(report['programm'], 'Google Docs')
        self.assertEqual(report['kennung_aus'], 'titelblatt')
        self.assertIn('Überschriften', report['zuordnung_abschnitte'])
        self.assertTrue(any('Bitte prüfen' in f.get('frage', '') for f in findings))

    def test_pages_loses_comments_and_images_comparison_over_text(self):
        report, findings = self.check_program('pages', expect_comment=False)
        self.assertEqual(report['programm'], 'Pages')
        self.assertEqual(report['kennung_aus'], 'titelblatt')
        self.assertIn('Vergleich über den Text', report['vergleich'])
        self.assertIn('Pages', report['vergleich'])
        self.assertEqual(report['kommentare'], 0)

    def test_unchanged_pages_copy_has_no_findings(self):
        back = self.variant('pages')
        _, report = checkin.checkin(self.base, self.config, [back], date='2026-11-25')
        self.assertEqual(report['befunde'], 0)

    def test_pdf_comment_is_assigned_to_section_and_note_makes_findings(self):
        from pypdf import PdfReader, PdfWriter
        try:
            from pypdf.annotations import Text as TextNote
            note_of = lambda text, rect: TextNote(text=text, rect=rect)   # noqa: E731
        except ImportError:
            from pypdf.generic import AnnotationBuilder
            note_of = lambda text, rect: AnnotationBuilder.text(text=text, rect=rect)   # noqa: E731
        files = self.cf.build(self.base, self.config, self.entry, self.out, 'o/r', 'buch/x', self.commit, '2026-11-24')
        pdf = self.out / next(f for f in files if f.endswith('.pdf'))
        pages = checkin.pdf_words(pdf)
        heads = checkin.pdf_headings(pages, {'1.1', '1.2', '1.3'})
        self.assertTrue(any(h[2] == '1.2' for h in heads), heads)
        page, y, _ = next(h for h in heads if h[2] == '1.2')
        height = pages[page - 1][1]
        w = PdfWriter(clone_from=str(pdf))
        w.add_annotation(page_number=page - 1, annotation=note_of('Hier fehlt ein Beleg', (80, height - y - 60, 100, height - y - 40)))
        marked = self.tmp / 'kommentiert.pdf'
        with open(marked, 'wb') as fh:
            w.write(fh)
        folder, report = checkin.checkin(self.base, self.config, [marked], date='2026-11-25')
        sec2 = self.config['structure']['chapters'][0]['sections'][1]['id']
        note = next(a for a in report['anmerkungen'] if a['text'] == 'Hier fehlt ein Beleg')
        self.assertEqual((note['abschnitt'], note['nummer']), (sec2, '1.2'))
        findings = yaml.safe_load((self.base / report['befunddatei']).read_text(encoding='utf-8'))['befunde']
        self.assertTrue(any(f['abschnitt'] == sec2 and 'Beleg' in f['frage'] for f in findings))
        # abgeschriebene Randnotiz eines Scans: eindeutig, unleserlich, ohne Abschnitt
        word = self.sample_word()
        sid1 = self.config['structure']['chapters'][0]['sections'][0]['id']
        item = checkin.note(self.base, self.config, folder, 1, f'{word} → Ersatzwort', abschnitt='1.1', alt=word, neu='Ersatzwort')
        self.assertTrue(item['befund'])
        with self.assertRaisesRegex(ValueError, 'nicht wörtlich'):
            checkin.note(self.base, self.config, folder, 1, 'x', abschnitt='1.1', alt='gibt es nicht im Text', neu='y')
        checkin.note(self.base, self.config, folder, 1, '(unleserlich)', abschnitt='1.1', unleserlich=True)
        checkin.note(self.base, self.config, folder, 1, 'Randnotiz ohne Zuordnung')
        rep = yaml.safe_load((folder / 'rueckgabe.yml').read_text(encoding='utf-8'))
        self.assertEqual(len(rep['anmerkungen']), 4)
        self.assertEqual(len(rep['offene_fragen']), 2)
        findings = yaml.safe_load((self.base / rep['befunddatei']).read_text(encoding='utf-8'))['befunde']
        self.assertTrue(any(f.get('alt') == word and f['abschnitt'] == sid1 for f in findings))
        import validate_project
        self.assertFalse(validate_project.check_project(self.base))

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
