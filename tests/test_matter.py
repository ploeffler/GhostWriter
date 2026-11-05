"""Tests für Vor- und Nachspann (#57, #58): Anlegen, Prüfung, Zusammenführen, Übersicht, Satz.

Ein Buch mit allen vier Teilen (Widmung, Prolog, Epilog, Danksagung) und eines ohne
(tests/fixtures/adhs unverändert). Der Satz (PDF, DOCX, EPUB) läuft nur, wenn pandoc
und xelatex installiert sind; in validate.yml fehlen sie, dort entfällt dieser Teil.
"""
import hashlib
import json
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
import assemble  # noqa: E402
import build_index  # noqa: E402
import matter  # noqa: E402
import validate_project  # noqa: E402
from render_view import MATTER, german_key, load  # noqa: E402

TEXTS = {'dedication': 'Für Anna,\n\ndie immer an mich geglaubt hat.',
         'prologue': 'Es war ein Dienstag, als alles begann.\n\n# Rückblick\n\nDamals wusste ich nichts.',
         'epilogue': 'Heute sehe ich vieles anders.',
         'acknowledgments': 'Ich danke allen, die mitgelesen haben.'}


def set_part(base, kind, text=None, approved=True):
    """Text und Freigabe eines Teils setzen."""
    path = base / 'matter' / MATTER[kind][2]
    t = path.read_text(encoding='utf-8')
    if text is not None:
        t = t.split('## Manuskript\n', 1)[0] + '## Manuskript\n\n' + text + '\n'
    t = re.sub(r'(?m)^status: \w+', f'status: {"approved" if approved else "writing"}', t, count=1)
    t = re.sub(r'(?m)^  writing: \w+', '  writing: true', t, count=1)
    t = re.sub(r'(?m)^  section: \w+', f'  section: {"true" if approved else "false"}', t, count=1)
    path.write_text(t, encoding='utf-8')
    head = yaml.safe_load(t.split('---', 2)[1])
    manuscript = t.split('## Manuskript\n', 1)[1].strip()
    digest = hashlib.sha256(manuscript.encode('utf-8')).hexdigest()
    ledger_path = base / 'approvals.yml'
    ledger = yaml.safe_load(ledger_path.read_text(encoding='utf-8')) if ledger_path.is_file() else {'entries': []}
    entry = {'kind': 'matter', 'id': head['id'], 'action': 'granted' if approved else 'revoked',
             'at': '2026-11-05T12:00:00Z', 'by': 'test', 'commit': '1234567'}
    if approved:
        entry['note'] = 'content_sha256=' + digest
    ledger['entries'].append(entry)
    ledger_path.write_text(yaml.safe_dump(ledger, allow_unicode=True, sort_keys=False), encoding='utf-8')

def approve_chapter_1(base):
    cfg_path = base / 'ghostwriter.yml'
    text = cfg_path.read_text(encoding='utf-8')
    cfg = yaml.safe_load(text)
    ch = cfg['structure']['chapters'][0]
    text = re.sub(rf'(?ms)(- id: {ch["id"]}\n.*?status: )\w+', r'\1approved', text, count=1)
    cfg_path.write_text(text, encoding='utf-8')
    ledger_path = base / 'approvals.yml'
    ledger = yaml.safe_load(ledger_path.read_text(encoding='utf-8')) if ledger_path.is_file() else {'entries': []}
    for section in ch['sections']:
        p = base / section['path']
        t = re.sub(r'(?m)^status: \w+', 'status: approved', p.read_text(encoding='utf-8'), count=1)
        t = re.sub(r'\*?\[(PLATZHALTER-ANEKDOTE|QUELLE PRÜFEN|MEDIZIN PRÜFEN|RECHT PRÜFEN)[^\]]*\]\*?', '', t)
        manuscript = t.split('## Manuskript\n', 1)[1].strip()
        digest = hashlib.sha256(manuscript.encode('utf-8')).hexdigest()
        t = re.sub(r'(?m)^  section: \w+', '  section: true', t, count=1)
        p.write_text(t, encoding='utf-8')
        ledger['entries'].append({'kind': 'section', 'id': section['id'], 'action': 'granted',
            'at': '2026-11-05T12:00:00Z', 'by': 'test', 'commit': '1234567', 'note': 'content_sha256=' + digest})
    ledger['entries'].append({'kind': 'chapter', 'id': ch['id'], 'action': 'granted',
        'at': '2026-11-05T12:00:00Z', 'by': 'test', 'commit': '1234567'})
    ledger_path.write_text(yaml.safe_dump(ledger, allow_unicode=True, sort_keys=False), encoding='utf-8')
    readme = base / ch['path'] / 'README.md'
    readme.write_text(re.sub(r'\[(QUELLE PRÜFEN|MEDIZIN PRÜFEN)[^\]]*\]', '', readme.read_text(encoding='utf-8')),
                      encoding='utf-8')


class MatterBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        self.original = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')

    def add_all(self):
        # absichtlich durcheinander: die Reihenfolge im Buch bestimmt das Skript
        for kind in ('acknowledgments', 'prologue', 'epilogue', 'dedication'):
            matter.add(self.base, kind)
        for kind, text in TEXTS.items():
            set_part(self.base, kind, text)


class MatterTest(MatterBase):
    # ---------- Anlegen und Prüfen ----------

    def test_add_keeps_file_and_orders_parts(self):
        self.add_all()
        text = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        cfg = yaml.safe_load(text)
        self.assertEqual([i['kind'] for i in cfg['structure']['front_matter']], ['dedication', 'prologue'])
        self.assertEqual([i['kind'] for i in cfg['structure']['back_matter']], ['epilogue', 'acknowledgments'])
        # Alles außer den neuen Blöcken bleibt Zeichen für Zeichen gleich
        stripped = re.sub(r'(?ms)^  (front|back)_matter:\n.*?(?=^  [a-z])', '', text)
        self.assertEqual(stripped, self.original)
        self.assertEqual(validate_project.check_project(self.base), [])
        with self.assertRaises(SystemExit):
            matter.add(self.base, 'prologue')
        self.assertEqual(matter.kind_of('Widmung'), 'dedication')

    def test_validation_finds_problems(self):
        matter.add(self.base, 'dedication')
        path = self.base / 'matter/widmung.md'
        path.write_text(path.read_text(encoding='utf-8').replace('kind: dedication', 'kind: prologue'), encoding='utf-8')
        errors = validate_project.check_project(self.base)
        self.assertTrue(any('Art prologue statt dedication' in e for e in errors), errors)
        path.unlink()
        self.assertTrue(any(e.endswith('widmung.md: fehlt') for e in validate_project.check_project(self.base)))

    def test_approvals_log_knows_matter(self):
        matter.add(self.base, 'epilogue')
        (self.base / 'approvals.yml').write_text(yaml.safe_dump({'entries': [
            {'kind': 'matter', 'id': 'mat-epilog', 'action': 'revoked', 'at': '2026-11-03T10:00:00+01:00',
             'by': 'ploeffler', 'commit': 'abc1234'},
            {'kind': 'writing', 'id': 'mat-epilog', 'action': 'revoked', 'at': '2026-11-03T10:00:00+01:00',
             'by': 'ploeffler', 'commit': 'abc1234'},
            {'kind': 'matter', 'id': 'mat-prolog', 'action': 'revoked', 'at': '2026-11-03T10:00:00+01:00',
             'by': 'ploeffler', 'commit': 'abc1234'}]}), encoding='utf-8')
        errors = validate_project.check_project(self.base)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('mat-prolog unbekannt', errors[0])

    # ---------- Zusammenführen ----------

    def test_book_order_and_headings(self):
        self.add_all()
        approve_chapter_1(self.base)
        _, config = load(self.base)
        parts, mparts = assemble.book_parts(self.base, config), assemble.matter_parts(self.base, config)
        self.assertEqual(assemble.problems(parts, config, mparts), [])
        body = assemble.book_body(parts, mparts)
        heads = re.findall(r'(?m)^# (.+)$', body)
        self.assertEqual(heads[0], 'Widmung {.unnumbered .unlisted .dedication epub:type=dedication}')
        self.assertEqual(heads[1], 'Prolog {.unnumbered .prologue epub:type=prologue}')
        self.assertEqual(heads[2], config['structure']['chapters'][0]['title'])
        self.assertEqual(heads[-2:], ['Epilog {.unnumbered .epilogue epub:type=epilogue}',
                                      'Danksagung {.unnumbered .acknowledgments epub:type=acknowledgments}'])
        self.assertIn('::: widmung\nFür Anna,', body)
        self.assertIn('## Rückblick', body)   # Überschriften im Text eine Ebene unter dem Teil
        self.assertNotIn('## Manuskript', body)

    def test_unapproved_part_is_left_out_with_note(self):
        self.add_all()
        approve_chapter_1(self.base)
        set_part(self.base, 'epilogue', approved=False)
        _, config = load(self.base)
        mparts = assemble.matter_parts(self.base, config)
        self.assertEqual(assemble.problems(assemble.book_parts(self.base, config), config, mparts), [])
        self.assertNotIn('# Epilog', assemble.book_body(assemble.book_parts(self.base, config), mparts))
        self.assertEqual(assemble.matter_notes(mparts), ['Epilog ist nicht freigegeben und fehlt in der Auflage.'])
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/assemble.py'), str(self.base), 'check'],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn('ⓘ Epilog ist nicht freigegeben', out.stdout)
        self.assertIn('3 Teile Vor-/Nachspann', out.stdout)
        # Probedruck: auch der nicht freigegebene Teil, mit Vermerk
        proof = assemble.book_body(assemble.book_parts(self.base, config, proof=True),
                                   assemble.matter_parts(self.base, config, proof=True))
        self.assertIn('# Epilog', proof)
        self.assertRegex(proof, r'Stand: \w+, nicht freigegeben')

    def test_marker_in_approved_part_blocks(self):
        self.add_all()
        approve_chapter_1(self.base)
        set_part(self.base, 'prologue', 'Es war 1998 [QUELLE PRÜFEN: Jahr].')
        _, config = load(self.base)
        found = assemble.problems(assemble.book_parts(self.base, config), config, assemble.matter_parts(self.base, config))
        self.assertEqual(found, ['Offener Marker in Prolog: [QUELLE PRÜFEN: Jahr]'])

    # ---------- Übersichtsdatei und Ansichten ----------

    def test_index_only_lists_matter_when_present(self):
        _, config = load(self.base)
        self.assertNotIn('matter', build_index.build(self.base, config))   # Buch ohne Vor-/Nachspann: unverändert
        self.add_all()
        _, config = load(self.base)
        data = build_index.build(self.base, config)
        self.assertEqual([(m['id'], m['area'], m['status']) for m in data['matter']],
                         [('mat-widmung', 'front', 'approved'), ('mat-prolog', 'front', 'approved'),
                          ('mat-epilog', 'back', 'approved'), ('mat-danksagung', 'back', 'approved')])
        self.assertEqual(json.loads(build_index.render(data)), data)

    def view(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *args, '--text'],
                              capture_output=True, text=True, check=True).stdout

    def test_text_views(self):
        self.assertNotIn('Vorspann:', self.view('project'))
        self.add_all()
        set_part(self.base, 'epilogue', approved=False)
        overview = self.view('project')
        self.assertIn('**Vorspann:** Widmung', overview)
        self.assertIn('**Nachspann:** Epilog', overview)
        self.assertIn('`V` Vor- und Nachspann', overview)
        part = self.view('matter', 'epilog')
        self.assertIn('### 📜 Epilog', part)
        self.assertIn('Heute sehe ich vieles anders.', part)
        self.assertIn('`GS` Ghostwriting sofort', part)
        self.assertNotIn('Ghostwriting', self.view('matter', 'Widmung'))
        listing = self.view('matter')
        self.assertIn('| Danksagung | Nachspann |', listing)
        confirm = self.view('approval-matter', 'epilog')
        self.assertIn('Epilog freigeben', confirm)
        self.assertIn('`OK` bestätigt', confirm)
        self.assertIn('⛔', self.view('approval-matter', 'widmung'))   # schon freigegeben


class MatterEmptyTest(unittest.TestCase):
    def test_listing_offers_all_parts(self):
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(ROOT / 'tests/fixtures/adhs'),
                              'matter', '--text'], capture_output=True, text=True, check=True).stdout
        for title in ('Widmung', 'Prolog', 'Epilog', 'Danksagung'):
            self.assertIn(f'`+ {title}` anlegen', out)


class ForewordGlossaryTest(MatterBase):
    """#58: Vorwort, Nachwort, Glossar."""

    def add_seven(self):
        for kind in ('glossary', 'afterword', 'foreword'):
            matter.add(self.base, kind)
        self.add_all()
        set_part(self.base, 'foreword', 'Ein Wort vorab.')
        set_part(self.base, 'afterword', 'Ein Wort danach.')
        path = self.base / 'matter/vorwort.md'
        path.write_text(path.read_text(encoding='utf-8').replace(
            'approvals:', 'byline: Dr. Maria Muster\nplace_date: Graz, im Oktober 2026\napprovals:'), encoding='utf-8')
        for term, expl in (('Zeitblindheit', 'Zeit schlecht schätzen'), ('Ärger', 'ein Gefühl'), ('ADHS', 'Störung'),
                           ('Ödem', 'Schwellung'), ('Ober', 'Kellner'), ('Apfel', 'Obst')):
            matter.glossary_set(self.base, term, expl)
        set_part(self.base, 'glossary')

    def test_order_of_all_seven(self):
        self.add_seven()
        cfg = yaml.safe_load((self.base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        self.assertEqual([i['kind'] for i in cfg['structure']['front_matter']], ['dedication', 'foreword', 'prologue'])
        self.assertEqual([i['kind'] for i in cfg['structure']['back_matter']],
                         ['epilogue', 'afterword', 'glossary', 'acknowledgments'])
        self.assertEqual(validate_project.check_project(self.base), [])
        approve_chapter_1(self.base)
        _, config = load(self.base)
        mparts = assemble.matter_parts(self.base, config)
        body = assemble.book_body(assemble.book_parts(self.base, config), mparts)
        heads = [h.split(' {')[0] for h in re.findall(r'(?m)^# (.+)$', body)]
        self.assertEqual(heads[:3], ['Widmung', 'Vorwort', 'Prolog'])
        self.assertEqual(heads[-4:], ['Epilog', 'Nachwort', 'Glossar', 'Danksagung'])
        self.assertIn('epub:type=foreword', body)
        self.assertIn('epub:type=glossary', body)
        self.assertIn('::: signatur\n| Dr. Maria Muster\n| Graz, im Oktober 2026\n:::', body)

    def test_glossary_sorted_with_umlauts(self):
        self.add_seven()
        _, config = load(self.base)
        md = next(m[2] for m in assemble.matter_parts(self.base, config) if m[1]['kind'] == 'glossary')
        terms = re.findall(r'(?m)^\[(.+?)\]\{#gl-[^}]*\}\n:   ', md)
        self.assertEqual(terms, ['ADHS', 'Apfel', 'Ärger', 'Ober', 'Ödem', 'Zeitblindheit'])
        # in der Datei ebenfalls sortiert, als Liste
        text = (self.base / 'matter/glossar.md').read_text(encoding='utf-8')
        self.assertIn('- ADHS: Störung\n- Apfel: Obst\n- Ärger: ein Gefühl\n', text)
        self.assertEqual(sorted(['Zebra', 'äußerst', 'Affe', 'Straße', 'Stall'], key=german_key),
                         ['Affe', 'äußerst', 'Stall', 'Straße', 'Zebra'])

    def test_glossary_edit_and_duplicates(self):
        self.add_seven()
        with self.assertRaises(SystemExit):
            matter.glossary_set(self.base, 'adhs', 'nochmal', new=True)
        matter.glossary_set(self.base, 'adhs', 'Aufmerksamkeitsdefizit')   # ändert, legt nicht doppelt an
        matter.glossary_remove(self.base, 'ödem')
        _, entries = __import__('render_view').glossary_entries(
            (self.base / 'matter/glossar.md').read_text(encoding='utf-8').split('## Manuskript\n')[1])
        self.assertEqual(len(entries), 5)
        self.assertIn(('adhs', 'Aufmerksamkeitsdefizit'), entries)
        # von Hand doppelt eingetragen: Prüfung, Auflage und Freigabe schlagen an
        path = self.base / 'matter/glossar.md'
        path.write_text(path.read_text(encoding='utf-8') + '- Apfel: nochmal\n', encoding='utf-8')
        self.assertTrue(any('Begriff mehrfach eingetragen: Apfel' in e for e in validate_project.check_project(self.base)))
        approve_chapter_1(self.base)
        _, config = load(self.base)
        found = assemble.problems(assemble.book_parts(self.base, config), config, assemble.matter_parts(self.base, config))
        self.assertEqual(found, ['Glossar: Begriff mehrfach eingetragen: Apfel / Apfel'])
        set_part(self.base, 'glossary', approved=False)
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'approval-matter',
                              'glossar', '--text'], capture_output=True, text=True, check=True).stdout
        self.assertIn('⛔ Begriffe mehrfach eingetragen: Apfel', out)

    def test_signature_only_for_foreword_and_afterword(self):
        matter.add(self.base, 'dedication')
        path = self.base / 'matter/widmung.md'
        path.write_text(path.read_text(encoding='utf-8').replace('approvals:', 'byline: X\napprovals:'), encoding='utf-8')
        self.assertTrue(any('byline gibt es nur bei Vorwort und Nachwort' in e
                            for e in validate_project.check_project(self.base)))

    def test_glossary_view(self):
        self.add_seven()
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'matter', 'Glossar',
                              '--text'], capture_output=True, text=True, check=True).stdout
        self.assertIn('**6 Begriffe**', out)
        self.assertIn('| Ärger | ein Gefühl |', out)
        self.assertIn('`+ Begriff: Erklärung` aufnehmen', out)
        self.assertNotIn('Ghostwriting', out)
        vorwort = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'matter',
                                  'vorwort', '--text'], capture_output=True, text=True, check=True).stdout
        self.assertIn('| Verfasser | Dr. Maria Muster |', vorwort)


@unittest.skipUnless(shutil.which('pandoc') and shutil.which('xelatex') and shutil.which('pdftotext'),
                     'pandoc, xelatex oder pdftotext fehlen')
class MatterTypesettingTest(MatterBase):
    """Satz in allen drei Formaten mit allen sieben Teilen."""

    def test_edition_formats(self):
        ForewordGlossaryTest.add_seven(self)
        approve_chapter_1(self.base)
        out = Path(self.base.parent) / 'out'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--edition', '1',
                            '--out', str(out), '--date', '2026-11-03'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ed = yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))
        self.assertEqual(ed['matter'], ['mat-widmung', 'mat-vorwort', 'mat-prolog', 'mat-epilog', 'mat-nachwort',
                                        'mat-glossar', 'mat-danksagung'])
        pdf = subprocess.run(['pdftotext', str(out / f'{ed["tag"]}.pdf'), '-'], capture_output=True, text=True).stdout
        # Widmung vor dem Inhaltsverzeichnis, ohne Überschrift und ohne Eintrag darin
        self.assertLess(pdf.index('Für Anna'), pdf.index('Inhaltsverzeichnis'))
        toc = pdf[pdf.index('Inhaltsverzeichnis'):pdf.index('Ein Wort vorab')]
        self.assertNotIn('Widmung', pdf)
        self.assertEqual(re.findall(r'(?m)^(Vorwort|Prolog|Epilog|Nachwort|Glossar|Danksagung)\s', toc),
                         ['Vorwort', 'Prolog', 'Epilog', 'Nachwort', 'Glossar', 'Danksagung'])
        self.assertLess(pdf.index('Dr. Maria Muster'), pdf.index('Es war ein Dienstag'))
        from docx import Document
        styles = [p.style.name for p in Document(str(out / f'{ed["tag"]}.docx')).paragraphs]
        self.assertIn('Widmung', styles)
        self.assertIn('Widmung Text', styles)
        self.assertIn('Signatur', styles)
        self.assertIn('Definition Term', styles)
        import zipfile
        with zipfile.ZipFile(out / f'{ed["tag"]}.epub') as z:
            xhtml = ''.join(z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('.xhtml'))
            nav = z.read('EPUB/nav.xhtml').decode('utf-8')
        for role in ('dedication', 'foreword', 'prologue', 'epilogue', 'afterword', 'glossary', 'acknowledgments'):
            self.assertIn(f'epub:type="{role}"', xhtml)
        self.assertNotIn('Widmung', nav)


if __name__ == '__main__':
    unittest.main()


class MatterWidgetTest(MatterBase):
    """Widget-Ausgabe (ghostwriter-ui ab 0.25.0): Vorlagen und Daten."""

    def widget(self, *args):
        out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *args],
                             capture_output=True, text=True, check=True).stdout
        m = re.search(r'GW\.render\("([^"]+)",(.*)\)</script>', out)
        return m.group(1), json.loads(m.group(2).replace('<\/', '</'))

    def test_overview_list_and_part(self):
        matter.add(self.base, 'glossary')
        matter.add(self.base, 'foreword')
        matter.glossary_set(self.base, 'Zeit', 'Dauer')
        matter.glossary_set(self.base, 'Ärger', 'Gefühl')
        name, data = self.widget('project')
        self.assertEqual(name, 'projektuebersicht')
        self.assertEqual([m['MATTER_ID'] for m in data['MATTER_FRONT']], ['mat-vorwort'])
        self.assertEqual([m['MATTER_ID'] for m in data['MATTER_BACK']], ['mat-glossar'])
        name, data = self.widget('matter')
        self.assertEqual(name, 'vor-nachspann')
        self.assertEqual(len(data['PARTS']), 7)
        self.assertEqual({p['PART_KIND']: p['PART_ID'] for p in data['PARTS']}['dedication'], '')
        name, data = self.widget('matter', 'glossar')
        self.assertEqual(name, 'teil-bearbeiten')
        self.assertEqual((data['GLOSSARY'], data['GHOSTWRITING'], data['RESEARCH']), ('1', '', '1'))
        self.assertEqual([e['G_TERM'] for e in data['GLOSSARY_ENTRIES']], ['Ärger', 'Zeit'])
        _, data = self.widget('matter', 'vorwort')
        self.assertEqual((data['SIGNED'], data['GHOSTWRITING'], data['MATTER_MANUSCRIPT']), ('1', '1', ''))

    def test_no_matter_blocks_without_parts(self):
        _, data = self.widget('project')
        self.assertNotIn('MATTER_FRONT', data)
        self.assertNotIn('MATTER_BACK', data)


class GlossaryReferenceTest(MatterBase):
    """#107: Verweise aus dem Text aufs Glossar."""

    def setUp(self):
        super().setUp()
        _, config = load(self.base)
        self.section = self.base / config['structure']['chapters'][0]['sections'][0]['path']
        t = self.section.read_text(encoding='utf-8')
        head, _, ms = t.partition('## Manuskript\n')
        self.section.write_text(head + '## Manuskript\n\nWer [ADHS]{.glossar} hat, kennt [Ärgernisse]{.glossar term="Ärger"}.\n'
                                + ms, encoding='utf-8')
        approve_chapter_1(self.base)

    def body(self):
        _, config = load(self.base)
        parts, mparts = assemble.book_parts(self.base, config), assemble.matter_parts(self.base, config)
        return assemble.problems(parts, config, mparts), assemble.book_body(parts, mparts)

    def test_without_glossary_plain_text(self):
        found, body = self.body()
        self.assertEqual(found, [])
        self.assertIn('Wer ADHS hat, kennt Ärgernisse.', body)

    def test_links_and_missing_term(self):
        matter.add(self.base, 'glossary')
        matter.glossary_set(self.base, 'ADHS', 'Störung')
        set_part(self.base, 'glossary')
        found, body = self.body()
        self.assertEqual(found, ['Glossar-Verweis ohne Eintrag in Kapitel 1: „Ärger“'])
        matter.glossary_set(self.base, 'Ärger', 'Gefühl')
        found, body = self.body()
        self.assertEqual(found, [])
        self.assertIn('Wer [ADHS](#gl-adhs){.glossar} hat, kennt [Ärgernisse](#gl-aerger){.glossar}.', body)
        self.assertIn('[Ärger]{#gl-aerger}\n:   Gefühl', body)
        # Glossar nicht freigegeben: kein Link, kein Hindernis
        set_part(self.base, 'glossary', approved=False)
        found, body = self.body()
        self.assertEqual(found, [])
        self.assertIn('Wer ADHS hat', body)

    @unittest.skipUnless(shutil.which('pandoc') and shutil.which('xelatex') and shutil.which('pdftotext'),
                         'pandoc, xelatex oder pdftotext fehlen')
    def test_marks_in_formats(self):
        matter.add(self.base, 'glossary')
        matter.glossary_set(self.base, 'ADHS', 'Störung')
        matter.glossary_set(self.base, 'Ärger', 'Gefühl')
        set_part(self.base, 'glossary')
        cfg = self.base / 'ghostwriter.yml'
        cfg.write_text(cfg.read_text(encoding='utf-8') + 'typesetting:\n  glossary_marks: italic\n', encoding='utf-8')
        out = Path(self.base.parent) / 'out'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--edition', '1',
                            '--out', str(out), '--formats', 'pdf,pdf_print,epub'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tag = yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))['tag']
        import zipfile
        with zipfile.ZipFile(out / f'{tag}.epub') as z:
            xhtml = ''.join(z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('.xhtml'))
        self.assertRegex(xhtml, r'<a href="[^"]*#gl-adhs" class="glossar"><em>ADHS</em></a>')
        self.assertNotIn('→', xhtml)
        dests = lambda f: subprocess.run(['pdfinfo', '-dests', str(out / f)], capture_output=True, text=True).stdout
        self.assertIn('gl-adhs', dests(f'{tag}.pdf'))
        raw = (out / f'{tag}-druck.pdf').read_bytes()
        import zlib
        links = 0
        for m in re.finditer(rb'stream\r?\n(.*?)\r?\nendstream', raw, re.S):
            try:
                links += zlib.decompress(m.group(1)).count(b'/D(gl-adhs)')
            except zlib.error:
                pass
        self.assertEqual(links + raw.count(b'/D(gl-adhs)'), 0)   # Druck-PDF: Anker ja, Link nein
