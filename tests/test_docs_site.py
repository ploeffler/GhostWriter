"""Public content boundary, language pairing, build and release safeguards."""
import importlib.util
import json
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('docs_site', ROOT/'scripts/build_docs_site.py')
site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site)


class DocumentationSiteTests(unittest.TestCase):
    def test_complete_build_and_local_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'documentation'
            site.build(out)
            cfg = site.config()
            self.assertEqual(len(list(out.rglob('*.html'))), 2*len(cfg['pages'])+1)
            self.assertEqual(json.loads((out/'build-info.json').read_text())['version'],
                             str(site.yaml.safe_load((ROOT/'ghostwriter-manifest.yml').read_text())['version']))
            # Removing a target must make the checker fail.
            (out/'de/guide.html').unlink()
            with self.assertRaises(ValueError):
                site.check(out)

    def test_only_explicit_public_sources_and_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'documentation'
            site.build(out)
            self.assertFalse(list(out.rglob('*.md')))
            self.assertFalse(list(out.rglob('*.yml')))
            for path in out.rglob('*'):
                if path.is_file():
                    self.assertNotIn('conversations', path.parts)
                    self.assertNotIn('tests', path.parts)
                    self.assertNotIn('beispielmaterial', path.parts)
            info=json.loads((out/'build-info.json').read_text())
            selected={f'docs/{s}' for p in site.config()['pages'] for s in p['source'].values()}
            self.assertEqual(set(info['sources']), selected)
            soup=site.parse_page('[Intern](../ENTSCHEIDUNGSAUFTRAG-v1.0.md)')
            site.rewrite(soup, ROOT/'docs/ANLEITUNG.md','de',site.config(),out,ROOT)
            self.assertFalse(soup.find('a'))

    def test_unknown_files_and_paths_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            for link in ['../conversations/private.md','../../private.png','javascript:alert(1)']:
                soup=site.parse_page(f'[Link]({link})')
                with self.assertRaises(ValueError):
                    site.rewrite(soup,ROOT/'docs/ANLEITUNG.md','de',site.config(),Path(tmp),ROOT)

    def test_rebuild_removes_stale_public_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'documentation'; site.build(out)
            (out/'old-private.html').write_text('obsolete')
            site.build(out)
            self.assertFalse((out/'old-private.html').exists())

    def test_checker_rejects_stale_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'documentation'; site.build(out)
            original=Path.read_bytes
            def read(path):
                data=original(path)
                return data+b'\nChanged' if path.name=='WEBSITE-START.md' else data
            with patch.object(Path,'read_bytes',read):
                with self.assertRaisesRegex(ValueError,'veraltet'):
                    site.check(out)

    def test_refuses_foreign_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'keep').write_text('keep')
            with self.assertRaises(ValueError): site.build(Path(tmp))
            self.assertEqual((Path(tmp)/'keep').read_text(),'keep')

    def test_language_pair_required(self):
        cfg=site.config(); del cfg['pages'][0]['source']['en']
        original=Path.read_text
        def read(path,*args,**kwargs):
            return json.dumps(cfg) if path.name=='site.json' else original(path,*args,**kwargs)
        with patch.object(Path,'read_text',read):
            with self.assertRaisesRegex(ValueError,'Sprachpaar'): site.config()

    def test_pages_remains_manual_and_opt_in(self):
        workflow=site.yaml.load((ROOT/'.github/workflows/pages.yml').read_text(),Loader=site.yaml.BaseLoader)
        self.assertEqual(set(workflow['on']),{'workflow_dispatch'})
        self.assertEqual(workflow['on']['workflow_dispatch']['inputs']['documentation']['default'],'false')
        self.assertNotIn('workflow_run',workflow['on'])
        self.assertIn("github.ref == 'refs/heads/main'",workflow['jobs']['deploy']['if'])

    @unittest.skipUnless(shutil.which('node'), 'Node lokal nicht vorhanden; Suchlogik separat mit Node-REPL geprüft')
    def test_search_matching_and_empty_query(self):
        # This tests the actual browser search algorithm without starting a browser.
        script=ROOT/'scripts/docsite/search.js'
        js=f'''const {{search}}=require({json.dumps(str(script))});
const entries=[{{title:'Überarbeiten',text:'Texte prüfen',url:'writing.html'}},{{title:'Bilder',text:'überarbeiten',url:'images.html'}}];
if(search(entries,'uberarbeiten')[0].url!=='writing.html') process.exit(1);
if(search(entries,'Texte prüfen').length!==1) process.exit(2);
if(search(entries,'zzzzz').length!==0||search(entries,' ').length!==0) process.exit(3);
'''
        subprocess.run(['node','-e',js],check=True,capture_output=True)


if __name__=='__main__': unittest.main()
