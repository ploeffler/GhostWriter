"""#540: Figurenbild-Assistent – Bildstil, Prompt aus Profil und Stil, Varianten mit Prompt und Prüfsumme."""
import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze  # noqa: E402
import characters  # noqa: E402
import figurenbild  # noqa: E402
import validate_project  # noqa: E402

PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?'
       b'\x00\x05\xfe\x02\xfe\xa7\x9a\x9d\xd1\x00\x00\x00\x00IEND\xaeB`\x82')


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.base = self.tmp / 'buch'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.base)
        characters.add(self.base, 'Strolchi', 'main', 'Ein neugieriger kleiner Hund')
        characters.add(self.base, 'Opi', 'supporting')
        characters.update(self.base, 'opi', {'age': '78', 'appearance': 'groß, weißer Bart', 'visual': 'grüner Filzhut'})
        (self.tmp / 'bild.png').write_bytes(PNG)
        (self.tmp / 'prompt.txt').write_text('Porträt von Opi, grüner Filzhut. Keine Beschriftung.', encoding='utf-8')

    def run_cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = figurenbild.main([str(self.base), *args])
        return code, out.getvalue()

    def add_image(self, figure='opi', **kw):
        args = ['variante', figure, str(self.tmp / 'bild.png'), '--prompt-datei', str(self.tmp / 'prompt.txt')]
        for k, v in kw.items():
            args += [f'--{k.replace("_", "-")}', v] if not isinstance(v, list) else [x for i in v for x in (f'--{k}', i)]
        return self.run_cli(*args)


class FigurenbildTest(Base):
    def test_style_set_show_and_series_inheritance(self):
        self.assertIn('Noch kein Bildstil', self.run_cli('stil')[1])
        code, _ = self.run_cli('stil', 'set', json.dumps({'medium': 'foto', 'licht': 'weiches Licht', 'ausschluesse': 'Glamour, Retusche'}))
        self.assertEqual(code, 0)
        stored = yaml.safe_load((self.base / 'images/stil.yml').read_text())
        self.assertEqual(stored['ausschluesse'], ['Glamour', 'Retusche'])
        series = self.tmp / 'stil.yml'
        series.write_text(yaml.safe_dump({'medium': 'comic', 'farbigkeit': 'gedämpft'}), encoding='utf-8')
        style, origin = figurenbild.merged_style(self.base, series)
        self.assertEqual((style['medium'], style['farbigkeit']), ('foto', 'gedämpft'))   # Band überschreibt, erbt den Rest
        self.assertEqual((origin['medium'], origin['farbigkeit']), ('buch', 'serie'))
        self.assertEqual(self.run_cli('stil', 'set', json.dumps({'medium': 'ölgemälde'}))[0], 2)        # unbekanntes Medium
        self.assertEqual(self.run_cli('stil', 'set', json.dumps({'erzaehlstimme': 'ich'}))[0], 2)        # kein Platz für Erzählstimme
        code, _ = self.run_cli('stil', 'set', json.dumps({'farbigkeit': 'warm'}))
        self.assertEqual(yaml.safe_load((self.base / 'images/stil.yml').read_text())['medium'], 'foto')  # ergänzt, nicht ersetzt

    def test_prompt_separates_profile_author_and_design(self):
        self.run_cli('stil', 'set', json.dumps({'medium': 'foto', 'licht': 'weiches Licht'}))
        code, out = self.run_cli('prompt', 'opi', '--kleidung', 'Strickjacke, Rostrot', '--json')
        data = json.loads(out)
        self.assertEqual((data['herkunft']['aussehen'], data['herkunft']['merkmale'], data['herkunft']['kleidung'], data['herkunft']['stil']),
                         ('profil', 'profil', 'autor', 'bildgestaltung'))
        self.assertIn('weißer Bart', data['prompt'])
        self.assertIn('fotorealistisch', data['prompt'])
        self.assertIn('Keine Beschriftung', data['prompt'])
        self.assertEqual(data['offen'], ['ausdruck', 'ort'])                         # nicht im Profil: Vorschlag, kein Manuskriptfakt
        self.assertIn('Noch offen', self.run_cli('prompt', 'Opi')[1])
        self.assertEqual(self.run_cli('prompt', 'gibtsnicht')[0], 2)
        # das Profil bleibt unberührt
        self.assertNotIn('Rostrot', (self.base / 'characters/char-opi.md').read_text())

    def test_variante_keeps_original_prompt_checksum_and_change_links_input(self):
        code, out = self.add_image(kleidung='Strickjacke', werkzeug='Chat-Bilddienst')
        self.assertEqual(code, 0, out)
        data = yaml.safe_load((self.base / 'characters/char-opi/bilder.yml').read_text())
        first = data['bilder'][0]
        self.assertEqual((first['id'], first['art'], first['status'], first['modell']), ('bild-001', 'erzeugung', 'idee', 'unbekannt'))
        self.assertEqual(first['werkzeug'], 'Chat-Bilddienst')
        self.assertIn('grüner Filzhut', first['prompt'])
        self.assertTrue((self.base / 'characters/char-opi' / first['datei']).is_file())
        # Änderung ohne Eingabebild ist nicht erlaubt, mit Eingabebild entsteht eine neue Variante, das Original bleibt
        self.assertEqual(self.add_image(art='aenderung')[0], 2)
        self.assertEqual(self.add_image(art='aenderung', eingabe=['bild-009'])[0], 2)
        self.assertEqual(self.add_image(art='aenderung', eingabe=['bild-001'])[0], 0)
        data = yaml.safe_load((self.base / 'characters/char-opi/bilder.yml').read_text())
        self.assertEqual([(i['id'], i['eingabe']) for i in data['bilder']], [('bild-001', []), ('bild-002', ['bild-001'])])
        self.assertEqual(data['bilder'][0]['sha256'], figurenbild.sha256(self.base / 'characters/char-opi' / data['bilder'][0]['datei']))
        # ohne Prompt kein Bild
        self.assertEqual(self.run_cli('variante', 'opi', str(self.tmp / 'bild.png'))[0], 2)
        # Neue Bilder können nicht gleich „referenz“ sein
        self.assertEqual(self.add_image(status='referenz')[0], 2)

    def test_reference_needs_approval_and_check_finds_changes_and_same_clothing(self):
        self.add_image('opi', kleidung='Strickjacke Rostrot')
        self.add_image('strolchi', kleidung='strickjacke rostrot')
        self.assertEqual(self.run_cli('waehlen', 'opi', 'bild-001', '--status', 'gewaehlt')[0], 0)
        self.assertEqual(self.run_cli('waehlen', 'strolchi', 'bild-001', '--status', 'gewaehlt')[0], 0)
        self.assertEqual(self.run_cli('waehlen', 'opi', 'bild-001', '--status', 'referenz')[0], 2)                   # keine Freigabe
        self.assertEqual(self.run_cli('waehlen', 'opi', 'bild-001', '--status', 'referenz', '--referenz', 'ref-img-001')[0], 2)
        code, out = self.run_cli('pruefen')
        self.assertEqual(code, 1)
        self.assertIn('gleiche Kleidung', out)
        # verändertes Original fällt über die Prüfsumme auf
        (self.base / 'characters/char-opi/bilder/bild-001.png').write_bytes(PNG + b'x')
        self.assertIn('Prüfsumme weicht ab', self.run_cli('pruefen')[1])

    def test_project_validation_covers_style_and_images(self):
        self.run_cli('stil', 'set', json.dumps({'medium': 'comic'}))
        self.add_image()
        self.assertEqual(validate_project.check_project(self.base), [])
        (self.base / 'images/stil.yml').write_text('medium: ölgemälde\n')
        self.assertTrue(any('stil.yml' in e for e in validate_project.check_project(self.base)))
        (self.base / 'images/stil.yml').write_text('medium: foto\n')
        (self.base / 'characters/char-opi/bilder/bild-001.png').unlink()
        self.assertTrue(any('Bilddatei fehlt' in e for e in validate_project.check_project(self.base)))


class PortraitsAnalysisTest(Base):
    """Analyseart `portraits` (#540): werkweite Personenübersicht ohne KI."""
    def groups(self):
        head = analyze.run(self.base, 'portraits')
        data = yaml.safe_load(json.dumps(json.loads((self.base / 'analysis/portraits' / head['result']).read_text())))
        return head, {i['id']: i['group'] for i in data['items']}, data

    def test_groups_and_no_changes_and_no_cost(self):
        before = (self.base / 'characters/char-opi.md').read_text()
        head, groups, data = self.groups()
        self.assertEqual(groups, {'char-strolchi': 'braucht_hilfe', 'char-opi': 'vorbereitbar'})
        self.assertEqual((head['provider'], head['cost'], head['input_tokens']), (None, 0, 0))   # ohne KI, ohne Kosten
        strolchi = next(i for i in data['items'] if i['id'] == 'char-strolchi')
        self.assertIn('Wie sieht Strolchi aus', strolchi['question'])
        self.assertEqual((self.base / 'characters/char-opi.md').read_text(), before)            # nichts angelegt oder geändert
        self.assertFalse((self.base / 'characters/char-opi/bilder.yml').exists())

    def test_existing_image_and_changed_profile_and_untracked_person(self):
        self.add_image('opi')
        self.run_cli('waehlen', 'opi', 'bild-001', '--status', 'gewaehlt')
        self.assertEqual(self.groups()[1]['char-opi'], 'vorhanden')
        characters.update(self.base, 'opi', {'appearance': 'groß, weißer Bart, Glatze'})        # Profil seit dem Bild geändert
        self.assertEqual(self.groups()[1]['char-opi'], 'aktualisieren')
        # Name aus der Figuren-Analyse, zu dem es kein Profil gibt
        (self.base / 'analysis/characters').mkdir(parents=True)
        (self.base / 'analysis/characters/run-001.json').write_text(json.dumps({'items': [
            {'name': 'Opi', 'aliases': [], 'sections': []}, {'name': 'Frau Meier', 'aliases': ['Meiers'], 'sections': ['1.1']}]}))
        _, groups, data = self.groups()
        extra = [i for i in data['items'] if i['group'] == 'ohne_profil']
        self.assertEqual([i['name'] for i in extra], ['Frau Meier'])

    def test_text_view_for_any_client(self):
        import subprocess
        head = analyze.run(self.base, 'portraits')
        for lang, word in (('de', 'Autorenhilfe'), ('en', 'Needs the author')):
            out = subprocess.run([sys.executable, str(ROOT / 'scripts/render_view.py'), str(self.base), 'analysis-suggest', '--draft',
                                  f'analysis/portraits/{head["result"]}', '--repo', 'o/r', '--language', lang],
                                 capture_output=True, text=True).stdout
            self.assertIn(word, out)
            self.assertNotIn('{{', out)


if __name__ == '__main__':
    unittest.main()
