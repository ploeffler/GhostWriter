#!/usr/bin/env python3
"""Baut apps/web/index.html und sw.js und kopiert die mitgelieferte UI-Laufzeit (#662, Schritt 3).

Wie bei der Claude-Web-App (apps/claude/build.py) setzt die Zeile `@@include <Pfad>@@` in index.src.html die Teile aus apps/shared/ und den
Anschluss dieser App (ports-web.js, boot-web.js) zusammen. Die Widget-Laufzeit und die Symbole kommen aus apps/claude/vendor/ (gleicher Auszug,
gebaut mit apps/claude/build_vendor.py) und werden nach apps/web/vendor/ kopiert, damit die App aus einem einzigen Ordner läuft, auch offline.
js-yaml (MIT, vendor/js-yaml.LICENSE) liegt fest in vendor/.

  python3 apps/web/build.py           baut
  python3 apps/web/build.py --check   prüft, dass alles zu den Quellen passt (Exit 1 sonst)
"""
import hashlib
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLAUDE = HERE.parent / 'claude'
COPIES = ['gw-lite.js', 'icons.css']

_spec = importlib.util.spec_from_file_location('claude_build', CLAUDE / 'build.py')
_claude = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_claude)


def expected():
    manifest = (HERE.parent.parent / 'ghostwriter-manifest.yml').read_text(encoding='utf-8')
    version = re.search(r'^version:\s*([0-9][0-9.]*)', manifest, re.M).group(1)
    files = {HERE / 'index.html': _claude.build(HERE).replace('@@APP_VERSION@@', version)}
    for name in COPIES:
        files[HERE / 'vendor' / name] = (CLAUDE / 'vendor' / name).read_text(encoding='utf-8')
    # Service Worker: die Fassung im Namen des Speichers ist ein Hash über alles, was er zwischenspeichert (neuer Stand = neuer Speicher)
    h = hashlib.sha256()
    sw_src = (HERE / 'sw.src.js').read_text(encoding='utf-8')
    for part in [sw_src, files[HERE / 'index.html'], (HERE / 'manifest.webmanifest').read_text(encoding='utf-8'),
                 (HERE / 'vendor' / 'js-yaml.min.js').read_text(encoding='utf-8'), (HERE / 'faehigkeiten.json').read_text(encoding='utf-8'), (HERE / 'modelle.json').read_text(encoding='utf-8')] + [files[HERE / 'vendor' / n] for n in COPIES]:
        h.update(part.encode('utf-8'))
    for asset in ('easymde.min.js', 'easymde.min.css', 'purify.min.js'):
        h.update((HERE / 'vendor' / asset).read_bytes())
    for icon in sorted((HERE / 'icons').iterdir()):
        h.update(icon.read_bytes())
    files[HERE / 'sw.js'] = sw_src.replace('@@VERSION@@', h.hexdigest()[:12])
    return files


def main():
    files = expected()
    if '--check' in sys.argv:
        bad = [str(p.relative_to(HERE)) for p, text in files.items() if not p.is_file() or p.read_text(encoding='utf-8') != text]
        if bad:
            print('✗ passt nicht zu den Quellen: ' + ', '.join(bad) + ' – python3 apps/web/build.py')
            return 1
        print('✓ apps/web passt zu den Quellen')
        return 0
    for p, text in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        print(f'{p.relative_to(HERE)}: {len(text.encode("utf-8"))} Bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
