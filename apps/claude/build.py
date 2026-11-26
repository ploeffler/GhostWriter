#!/usr/bin/env python3
"""Baut apps/claude/index.html aus index.src.html und den Teilen in apps/shared/ und apps/claude/ (#662, Schritt 2).

Das Artefakt in Claude braucht eine einzige Datei. Die Quellen sind in Teile zerlegt: apps/shared/ (Ansichten und Abläufe, für beide Apps
gleich) und apps/claude/ (Anschluss an den Konnektor und Start). Eine Zeile `@@include <Pfad>@@` in index.src.html wird durch den Inhalt
der Datei ersetzt (Pfad relativ zu apps/claude/). index.html nie von Hand ändern.

  python3 apps/claude/build.py           baut index.html
  python3 apps/claude/build.py --check   prüft, dass index.html zu den Quellen passt (Exit 1 sonst)
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INCLUDE = re.compile(r'^@@include (\S+)@@$')


def build():
    lines = (HERE / 'index.src.html').read_text(encoding='utf-8').split('\n')
    out = []
    for line in lines:
        m = INCLUDE.match(line)
        if not m:
            out.append(line)
            continue
        text = (HERE / m.group(1)).read_text(encoding='utf-8')
        out.append(text[:-1] if text.endswith('\n') else text)
    return '\n'.join(out)


def main():
    html = build()
    target = HERE / 'index.html'
    if '--check' in sys.argv:
        if not target.is_file() or target.read_text(encoding='utf-8') != html:
            print('✗ apps/claude/index.html passt nicht zu den Quellen: python3 apps/claude/build.py')
            return 1
        print('✓ index.html passt zu den Quellen')
        return 0
    target.write_text(html, encoding='utf-8')
    print(f'index.html: {len(html.encode("utf-8"))} Bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
