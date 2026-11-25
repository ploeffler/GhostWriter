#!/usr/bin/env python3
"""Baut vendor/gw-lite.js und vendor/icons.css für die Claude-Web-App.

Die Web-App lädt keine Schrift- oder Skriptdateien aus dem Netz nach (die
Artefakt-Umgebung von Claude lässt nur wenige Quellen zu). Deshalb liegt hier
ein Auszug der Widget-Laufzeit aus ghostwriter-ui: nur die Vorlagen, die die
App zeigt, und nur die deutschen Texte. Die Symbole kommen als CSS-Masken aus
dem Paket @tabler/icons statt als Schrift.

  python3 apps/claude/build_vendor.py \
      --gw ../ghostwriter-ui/dist/gw.js \
      --tabler <ordner von @tabler/icons>/icons/outline

Vorlagen, die die App braucht, stehen in TEMPLATES. Kommt eine Ansicht dazu,
hier eintragen und neu bauen. Die Dateien in vendor/ nie von Hand ändern.
"""
import argparse
import json
import re
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = ['buecherregal', 'projektuebersicht', 'kapitelansicht', 'abschnitt-bearbeiten', 'aenderungen-uebernehmen',
             'freigabe-bestaetigen', 'kapitel-anlegen', 'kapitel-bearbeiten', 'abschnitt-anlegen', 'reihenfolge',
             'projektdaten-bearbeiten', 'daten', 'figuren', 'figur-bearbeiten', 'figuren-vorschlag', 'hinweisdurchsicht', 'warteschlange', 'rueckgabe']
KEY_RE = re.compile(r'(?:ui|status|runtime)\.[a-z0-9_]+')


def split_runtime(text):
    """Zerlegt gw.js in Kopf, LOCALIZED-Zeile, I18N, Vorlagenblöcke und restliche Laufzeit."""
    lines = text.split('\n')
    i_loc = next(i for i, l in enumerate(lines) if l.startswith('  var LOCALIZED='))
    i_i18n = next(i for i, l in enumerate(lines) if l.startswith('  var I18N='))
    head = lines[:i_loc]
    i18n = json.JSONDecoder().raw_decode(lines[i_i18n][len('  var I18N='):])[0]
    blocks, k = {}, i_i18n + 1
    while k < len(lines) and lines[k].startswith('  T["'):
        name = re.match(r'  T\["([^"]+)"\]=', lines[k]).group(1)
        end = k
        while lines[end] != '}};':
            end += 1
        blocks[name] = '\n'.join(lines[k:end + 1])
        k = end + 1
    return head, i18n, blocks, '\n'.join(lines[k:])


def build_runtime(gw_text):
    head, i18n, blocks, rest = split_runtime(gw_text)
    missing = [t for t in TEMPLATES if t not in blocks]
    if missing:
        raise SystemExit('Vorlagen fehlen in gw.js: ' + ', '.join(missing))
    body = '\n'.join(blocks[t] for t in TEMPLATES)
    used = set(KEY_RE.findall(body + rest))
    de = {k: v for k, v in i18n['de'].items() if k in used or k.startswith(('status.', 'runtime.'))}
    version = re.search(r'var VERSION="([^"]+)"', '\n'.join(head)).group(1)
    out = [f'/* Auszug für „GhostWriter für Claude“: nur die benutzten Vorlagen und deutschen Texte aus ghostwriter-ui {version}, '
           'unverändert übernommen (apps/claude/build_vendor.py) */']
    out += head
    out.append('  var LOCALIZED=' + json.dumps(TEMPLATES, ensure_ascii=False) + ';')
    out.append('  var I18N=' + json.dumps({'de': de}, ensure_ascii=False, sort_keys=True) + ';')
    out.append(body)
    out.append(rest)
    return '\n'.join(out), version


def build_icons(texts, tabler_dir):
    names = sorted(set(re.findall(r'\bti-[a-z0-9]+(?:-[a-z0-9]+)*', '\n'.join(texts))) - {'ti-'})
    out = ['/* Tabler Icons (MIT, https://tabler.io) – nur die in dieser App benutzten Symbole, als Masken statt Schrift */',
           '.ti{display:inline-block;width:1em;height:1em;vertical-align:-.14em;background-color:currentColor;'
           '-webkit-mask:var(--ti) center/contain no-repeat;mask:var(--ti) center/contain no-repeat;flex:none}']
    missing = []
    for n in names:
        p = Path(tabler_dir, n[3:] + '.svg')
        if not p.is_file():
            missing.append(n)
            continue
        svg = re.sub(r'<!--.*?-->', '', p.read_text(encoding='utf-8'), flags=re.S)
        svg = re.sub(r'\s+', ' ', svg).replace('> <', '><').strip()
        svg = re.sub(r' class="[^"]*"', '', svg).replace('currentColor', '#000')
        # einfache Anführungszeichen um url(...), weil das SVG doppelte enthält
        out.append(".%s{--ti:url('data:image/svg+xml,%s')}" % (n, urllib.parse.quote(svg, safe=' =:/"')))
    return '\n'.join(out) + '\n', missing


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--gw', required=True, help='dist/gw.js aus ghostwriter-ui')
    ap.add_argument('--tabler', required=True, help='Ordner icons/outline aus dem npm-Paket @tabler/icons')
    args = ap.parse_args()
    runtime, version = build_runtime(Path(args.gw).read_text(encoding='utf-8'))
    (HERE / 'vendor' / 'gw-lite.js').write_text(runtime, encoding='utf-8')
    css, missing = build_icons([runtime, (HERE / 'index.html').read_text(encoding='utf-8')], args.tabler)
    (HERE / 'vendor' / 'icons.css').write_text(css, encoding='utf-8')
    print(f'gw-lite.js aus ghostwriter-ui {version}: {len(TEMPLATES)} Vorlagen; icons.css: {css.count(".ti-")} Symbole')
    if missing:
        raise SystemExit('Symbole nicht gefunden: ' + ', '.join(missing))


if __name__ == '__main__':
    main()
