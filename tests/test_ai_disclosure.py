"""Tests für die KI-Angabe im Buch (#78): Vorschlag aus den Läufen, Speichern, Prüfung, Satz."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import ai_disclosure  # noqa: E402
import assemble  # noqa: E402
import matter  # noqa: E402
import validate_project  # noqa: E402
from render_view import load  # noqa: E402
from test_matter import approve_chapter_1, set_part  # noqa: E402


def write_run(base, rel, kind, provider, status='completed'):
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'---\nid: run-001\ntype: {kind}\nstatus: {status}\nprovider: {provider}\nmodel: m\n---\n\n# Lauf\n',
                    encoding='utf-8')


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        self.original = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        ch = 'chapters/01-endlich-eine-erklaerung'
        write_run(self.base, f'{ch}/research/sec-a/run-001.md', 'research', 'perplexity')
        write_run(self.base, f'{ch}/research/sec-a/run-002.md', 'research', 'openai', status='failed')
        write_run(self.base, f'{ch}/writing/sec-a/run-001.md', 'writing', 'anthropic')
        write_run(self.base, 'matter/writing/mat-vorwort/run-001.md', 'writing', 'chat')

    def config(self):
        return load(self.base)[1]


class AiDisclosureTest(Base):
    def test_no_runs_no_suggestion(self):
        base = Path(self.base.parent) / 'leer'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', base)
        self.assertEqual(ai_disclosure.suggest(base, load(base)[1]), '')

    def test_suggestion_from_runs(self):
        cfg = self.config()
        self.assertEqual(ai_disclosure.usage(self.base),
                         {'Recherche': {'perplexity'}, 'Textentwürfe': {'anthropic', 'chat'}})   # failed zählt nicht
        short = ai_disclosure.suggest(self.base, cfg, 'short', name_services=False)
        self.assertTrue(short.startswith('Bei der Entstehung dieses Buchs wurden KI-Werkzeuge für Recherche und '
                                         'Textentwürfe eingesetzt.'))
        self.assertNotIn('Perplexity', short)
        named = ai_disclosure.suggest(self.base, cfg, 'short', name_services=True)
        self.assertIn('(Anthropic Claude, Perplexity und ein Chat-Assistent)', named)
        detailed = ai_disclosure.suggest(self.base, cfg, 'detailed', name_services=True)
        self.assertIn('- Recherche (mit Perplexity)', detailed)
        self.assertIn('- Textentwürfe (mit Anthropic Claude und einem Chat-Assistenten)', detailed)
        credit = yaml.safe_load((ROOT / 'templates/branding.yml').read_text(encoding='utf-8'))['credit']['text']
        for text in (short, named, detailed):
            self.assertNotIn(credit, text)

    def test_set_keeps_file_and_resets_text(self):
        s = ai_disclosure.apply(self.base, mode='short', placement='page', name_services=True)
        self.assertEqual(s['text'], '')
        text = (self.base / 'ghostwriter.yml').read_text(encoding='utf-8')
        self.assertTrue(text.startswith(self.original.rstrip('\n')))   # nur angehängt
        ai_disclosure.apply(self.base, from_suggestion=True)
        cfg = self.config()
        self.assertIn('Perplexity', cfg['ai_disclosure']['text'])
        self.assertEqual(validate_project.check_project(self.base), [])
        ai_disclosure.apply(self.base, placement='imprint')   # Ort ändern: Wortlaut bleibt
        self.assertTrue(self.config()['ai_disclosure']['text'])
        ai_disclosure.apply(self.base, name_services=False)   # Nennung ändern: neu bestätigen
        self.assertEqual(self.config()['ai_disclosure'].get('text', ''), '')
        ai_disclosure.apply(self.base, mode='custom', text='Mit KI recherchiert: "ja".\nZweite Zeile.')
        self.assertEqual(self.config()['ai_disclosure']['text'], 'Mit KI recherchiert: "ja".\nZweite Zeile.')
        ai_disclosure.apply(self.base, mode='none')
        self.assertEqual(self.config()['ai_disclosure'], {'mode': 'none', 'placement': 'imprint', 'name_services': False})

    def test_problems_block_edition(self):
        approve_chapter_1(self.base)
        def found():
            cfg = self.config()
            return assemble.problems(assemble.book_parts(self.base, cfg), cfg, assemble.matter_parts(self.base, cfg))
        self.assertEqual(found(), [])
        ai_disclosure.apply(self.base, mode='short', placement='foreword')
        self.assertEqual(found(), ['KI-Angabe: Der Wortlaut ist noch nicht bestätigt (Befehl „KI-Angabe“).',
                                   'KI-Angabe: Ort ist das Vorwort, es gibt aber kein freigegebenes Vorwort.'])
        ai_disclosure.apply(self.base, text='Mit KI.')
        matter.add(self.base, 'foreword')
        set_part(self.base, 'foreword', 'Vorab.')
        self.assertEqual(found(), [])
        cfg_path = self.base / 'ghostwriter.yml'
        cfg_path.write_text(cfg_path.read_text(encoding='utf-8') + 'typesetting:\n  imprint: false\n', encoding='utf-8')
        ai_disclosure.apply(self.base, placement='imprint')
        self.assertEqual(found(), ['KI-Angabe: Ort ist das Impressum, das Impressum ist aber ausgeschaltet '
                                   '(Projekteinstellungen).'])

    def test_body_placement(self):
        approve_chapter_1(self.base)
        matter.add(self.base, 'afterword')
        set_part(self.base, 'afterword', 'Danach.')
        path = self.base / 'matter/nachwort.md'
        path.write_text(path.read_text(encoding='utf-8').replace('approvals:', 'byline: Max\napprovals:'), encoding='utf-8')
        cfg = self.config()
        parts, mparts = assemble.book_parts(self.base, cfg), assemble.matter_parts(self.base, cfg)
        body = assemble.book_body(parts, mparts, ('afterword', 'Mit KI.'))
        self.assertIn('Danach.\n\n::: ki-angabe\nMit KI.\n:::\n\n::: signatur\n| Max\n:::', body)
        page = assemble.book_body(parts, mparts, ('page', 'Mit KI.'))
        self.assertTrue(page.rstrip().endswith('# Hinweis zur KI-Nutzung {.unnumbered .ki-angabe-seite}\n\nMit KI.'))
        self.assertNotIn('ki-angabe', assemble.book_body(parts, mparts))

    def test_views_and_wizard(self):
        ai_disclosure.apply(self.base, mode='short', name_services=True)
        run = lambda *a: subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), *a, '--text'],
                                        capture_output=True, text=True, check=True).stdout
        form = run('ai-disclosure')
        self.assertIn('| Angabe | kurz (ein Satz) |', form)
        self.assertIn('noch nicht bestätigt', form)
        self.assertIn('**Vorschlag aus den Läufen:**', form)
        self.assertIn('keine Rechtsberatung', form)
        self.assertIn('| KI-Angabe im Buch | kurz, im Impressum (Wortlaut offen) |', run('project-settings'))
        self.assertIn('Soll im Buch stehen, wie bei diesem Buch KI genutzt wurde?', run('choice', 'wizard.14'))


@unittest.skipUnless(shutil.which('pandoc') and shutil.which('xelatex') and shutil.which('pdftotext'),
                     'pandoc, xelatex oder pdftotext fehlen')
class AiDisclosureTypesettingTest(Base):
    def test_imprint_in_all_formats(self):
        approve_chapter_1(self.base)
        ai_disclosure.apply(self.base, mode='custom', placement='imprint', text='Recherche mit KI-Unterstützung.')
        out = Path(self.base.parent) / 'out'
        r = subprocess.run([sys.executable, str(ROOT / 'scripts/build_edition.py'), str(self.base), '--edition', '1',
                            '--out', str(out)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tag = yaml.safe_load((out / 'edition.yml').read_text(encoding='utf-8'))['tag']
        pdf = subprocess.run(['pdftotext', str(out / f'{tag}.pdf'), '-'], capture_output=True, text=True).stdout
        self.assertLess(pdf.index('Recherche mit KI-Unterstützung.'), pdf.index('Inhaltsverzeichnis'))
        from docx import Document
        self.assertIn('Recherche mit KI-Unterstützung.', '\n'.join(p.text for p in Document(str(out / f'{tag}.docx')).paragraphs))
        import zipfile
        with zipfile.ZipFile(out / f'{tag}.epub') as z:
            self.assertIn('Recherche mit KI-Unterstützung.', ''.join(z.read(n).decode('utf-8') for n in z.namelist()
                                                                     if n.endswith('.xhtml')))


if __name__ == '__main__':
    unittest.main()
