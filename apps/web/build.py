#!/usr/bin/env python3
"""Baut apps/web/index.html und kopiert die mitgelieferte UI-Laufzeit (#662, Schritt 3).

Wie bei der Claude-Web-App (apps/claude/build.py) setzt die Zeile `@@include <Pfad>@@` in index.src.html die Teile aus apps/shared/ und den
Anschluss dieser App (ports-web.js, boot-web.js) zusammen. Die Widget-Laufzeit und die Symbole kommen aus apps/claude/vendor/ (gleicher Auszug,
gebaut mit apps/claude/build_vendor.py) und werden nach apps/web/vendor/ kopiert, damit die App aus einem einzigen Ordner läuft, auch offline.
js-yaml (MIT, vendor/js-yaml.LICENSE) liegt fest in vendor/.

  python3 apps/web/build.py           baut
  python3 apps/web/build.py --check   prüft, dass alles zu den Quellen passt (Exit 1 sonst)
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLAUDE = HERE.parent / 'claude'
COPIES = ['gw-lite.js', 'icons.css']

_spec = importlib.util.spec_from_file_location('claude_build', CLAUDE / 'build.py')
_claude = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_claude)


def expected():
    files = {HERE / 'index.html': _claude.build(HERE)}
    for name in COPIES:
        files[HERE / 'vendor' / name] = (CLAUDE / 'vendor' / name).read_text(encoding='utf-8')
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
