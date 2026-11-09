#!/usr/bin/env python3
"""Prepare an offline Pages bundle; never publishes. Existing example files stay byte-identical."""
import argparse
import json
import shutil
from pathlib import Path

from build_docs_site import ROOT, build


def package(output):
    output = Path(output).resolve()
    if output == ROOT or output.is_relative_to(ROOT/'website') or output.is_relative_to(ROOT/'docs'):
        raise ValueError('Paket muss außerhalb der Quellen liegen')
    if output.exists() and any(output.iterdir()) and not (output/'.ghostwriter-pages-bundle').is_file():
        raise ValueError('Fremder Ausgabeordner wird nicht ersetzt')
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(ROOT/'website', output)
    (output/'.ghostwriter-pages-bundle').write_text('generated\n')
    build(output/'documentation')
    # The public entry pages are changed only in this generated, explicitly chosen bundle.
    for lang, name in [('de','index.html'), ('en','index.en.html')]:
        path = output/name
        text = path.read_text()
        label = 'Dokumentation' if lang == 'de' else 'Documentation'
        link = f'<a href="documentation/{lang}/index.html">{label}</a> · '
        text = text.replace('<p class="links">', '<p class="links">'+link)
        if link not in text:
            raise ValueError('Einstiegsnavigation nicht gefunden')
        path.write_text(text)
    for source in (ROOT/'website').rglob('*'):
        if source.is_file() and source.name not in ('index.html','index.en.html'):
            assert source.read_bytes() == (output/source.relative_to(ROOT/'website')).read_bytes()
    print(f'Offline-Paket vorbereitet: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/pages')
    args = parser.parse_args()
    package(args.output)
