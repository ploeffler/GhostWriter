#!/usr/bin/env python3
"""KI-Angabe im Buch: wie bei diesem Buch KI genutzt wurde (#78).

Aufruf:
  python scripts/ai_disclosure.py <projektordner> suggest [--mode short|detailed] [--name-services|--no-name-services]
  python scripts/ai_disclosure.py <projektordner> set [--mode M] [--placement P] [--name-services|--no-name-services]
                                                    [--text TEXT | --text-from-suggestion | --clear-text]

Einstellung in ghostwriter.yml (fehlt = keine Angabe):

  ai_disclosure:
    mode: short            # none | short (ein Satz) | detailed (je Aufgabe) | custom (eigener Text)
    placement: imprint     # imprint (Impressum) | foreword (Vorwort) | afterword (Nachwort) | page (eigene Seite am Ende)
    name_services: true    # Dienste namentlich nennen
    text: "…"              # bestätigter Wortlaut; nur dieser kommt ins Buch

suggest schlägt einen Wortlaut aus den tatsächlichen Läufen vor (Recherche,
Ideensammlung, Kapitelrecherche, Ghostwriting, auch in Vor- und Nachspann) mit
den Diensten aus deren Kopf (`provider`). Ins Buch kommt nichts ungefragt: erst
`set --text …` bzw. `--text-from-suggestion` nach der Bestätigung des Benutzers
schreibt den Wortlaut. Ändern sich Modus oder Dienste-Nennung, gilt der Text als
nicht mehr bestätigt und wird geleert.

Der Hinweis auf die Entwicklung von GhostWriter („Entwickelt mit Unterstützung
von Claude …“, templates/branding.yml) ist etwas anderes und kommt nie ins Buch.

set ändert nur den Block `ai_disclosure` in ghostwriter.yml; der Rest der Datei
bleibt Zeichen für Zeichen erhalten. Den Commit schreibt der Assistent
(START.md, „KI-Angabe im Buch“).
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)

MODES = {'none': 'keine Angabe', 'short': 'ein Satz', 'detailed': 'je Aufgabe', 'custom': 'eigener Text'}
PLACEMENTS = {'imprint': 'im Impressum', 'foreword': 'am Ende des Vorworts', 'afterword': 'am Ende des Nachworts',
              'page': 'auf einer eigenen Seite am Ende'}
DEFAULT = {'mode': 'none', 'placement': 'imprint', 'name_services': False, 'text': ''}
# Lauf-Art → Aufgabe im Satz (Reihenfolge = Reihenfolge im Text)
TASKS = {'research': 'Recherche', 'chapter_research': 'Recherche', 'brainstorming': 'Ideensammlung',
         'writing': 'Textentwürfe', 'fact_check': 'Faktenprüfung'}
PAGE_TITLE = 'Hinweis zur KI-Nutzung'
GENERIC = {'App', 'lokal', 'offene Modelle', 'App / Website'}
LEGAL_HINT = ('Kennzeichnungspflichten (z. B. Art. 50 Abs. 4 der EU-KI-Verordnung seit 2. August 2026 für '
              'KI-erzeugte Texte zu Themen von öffentlichem Interesse, mit Ausnahme bei menschlicher Prüfung und '
              'redaktioneller Verantwortung) und Vorgaben von Verlagen und Plattformen (etwa die Angabe bei Amazon KDP) '
              'bitte selbst prüfen. Das ist keine Rechtsberatung.')


def settings(config):
    s = dict(DEFAULT)
    s.update((config or {}).get('ai_disclosure') or {})
    return s


def provider_names():
    try:
        data = yaml.safe_load((ROOT / 'providers.yml').read_text(encoding='utf-8')) or {}
    except OSError:
        return {}
    out = {}
    for section in ('special', 'providers', 'search_tools', 'queue_agents'):
        for s in data.get(section) or []:
            # „Anthropic (Claude / Claude API)“ → „Anthropic Claude“, „Perplexity (App / …)“ → „Perplexity“
            m = re.match(r'([^(]+?)\s*\(([^/)]+)', s.get('name', ''))
            product = m.group(2).strip() if m else ''
            out[s['id']] = (f'{m.group(1)} {product}' if product not in GENERIC else m.group(1)) if m else s.get('name', s['id'])
    return out


def run_files(base):
    pats = ['chapters/*/research/*/run-*.md', 'chapters/*/brainstorming/*/run-*.md', 'chapters/*/writing/*/run-*.md',
            'chapters/*/fact-check/*/run-*.md', 'matter/research/*/run-*.md', 'matter/writing/*/run-*.md',
            'matter/brainstorming/*/run-*.md']
    seen = []
    for p in pats:
        seen += sorted(base.glob(p))
    return seen


def usage(base):
    """{Aufgabe: {Dienst-ID}} aus den Köpfen der Lauf-Dateien; nur abgeschlossene Läufe."""
    out = {}
    for path in run_files(base):
        m = FRONTMATTER.match(path.read_text(encoding='utf-8'))
        head = (yaml.safe_load(m.group(1)) if m else None) or {}
        if head.get('status', 'completed') != 'completed':
            continue
        kind = head.get('type') or ('chapter_research' if '/research/kapitel/' in str(path) else path.parent.parent.name)
        task = TASKS.get(kind)
        provider = str(head.get('provider') or '').strip()
        if not task or not provider or provider.startswith('<'):
            continue
        out.setdefault(task, set()).add(provider)
    return out


def join_de(items):
    items = list(items)
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' und ' + items[-1]


def service_text(ids, names, dative=False):
    named = sorted({names.get(i, i) for i in ids if i != 'chat'})
    if 'chat' in ids:   # welcher Chat-Assistent, steht nicht im Lauf
        named.append('einem Chat-Assistenten' if dative else 'ein Chat-Assistent')
    return join_de(named) if named else ''


def suggest(base, config, mode=None, name_services=None):
    """Vorgeschlagener Wortlaut (str) oder '' wenn keine KI-Läufe protokolliert sind."""
    s = settings(config)
    mode = mode or (s['mode'] if s['mode'] in ('short', 'detailed') else 'short')
    name_services = s['name_services'] if name_services is None else name_services
    used = usage(base)
    if not used:
        return ''
    author = (((config or {}).get('project') or {}).get('author') or '').strip()
    tasks = [t for t in dict.fromkeys(TASKS.values()) if t in used]
    names = provider_names()
    end = (f'{author} hat alle Inhalte geprüft, überarbeitet und freigegeben und trägt die Verantwortung für den Text.'
           if author else 'Alle Inhalte wurden geprüft, überarbeitet und freigegeben; die Verantwortung für den Text '
                          'trägt der Autor bzw. die Autorin.')
    if mode == 'detailed':
        lines = ['Bei der Entstehung dieses Buchs wurden KI-Werkzeuge eingesetzt:', '']
        for t in tasks:
            who = service_text(used[t], names, dative=True) if name_services else ''
            lines.append(f'- {t}' + (f' (mit {who})' if who else ''))
        return '\n'.join(lines + ['', end])
    who = service_text(set().union(*used.values()), names) if name_services else ''
    first = (f'Bei der Entstehung dieses Buchs wurden KI-Werkzeuge für {join_de(tasks)} eingesetzt'
             + (f' ({who})' if who else '') + '.')
    return f'{first} {end}'


def block(s):
    out = ['ai_disclosure:', f'  mode: {s["mode"]}', f'  placement: {s["placement"]}',
           f'  name_services: {"true" if s["name_services"] else "false"}']
    if s.get('text'):
        out.append('  text: ' + yaml.safe_dump(s['text'], allow_unicode=True, width=10**6, default_style='"').rstrip('\n'))
    return '\n'.join(out) + '\n'


def write_settings(base, s):
    path = base / 'ghostwriter.yml'
    text = path.read_text(encoding='utf-8')
    new_block = block(s)
    m = re.search(r'(?m)^ai_disclosure:.*\n(?:(?:[ \t].*|)\n)*', text)
    if m:
        new = text[:m.start()] + new_block + text[m.end():]
    else:
        new = text.rstrip('\n') + '\n' + new_block
    check = (yaml.safe_load(new) or {}).get('ai_disclosure') or {}
    if {k: check.get(k, DEFAULT[k]) for k in DEFAULT} != {k: s.get(k, DEFAULT[k]) for k in DEFAULT}:
        raise SystemExit('ghostwriter.yml ließ sich nicht sicher ändern; bitte von Hand eintragen.')
    path.write_text(new, encoding='utf-8')


def apply(base, mode=None, placement=None, name_services=None, text=None, from_suggestion=False, clear=False):
    config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
    s = settings(config)
    before = (s['mode'], s['name_services'])
    if mode:
        if mode not in MODES:
            raise SystemExit(f'Modus {mode} unbekannt; möglich: {", ".join(MODES)}')
        s['mode'] = mode
    if placement:
        if placement not in PLACEMENTS:
            raise SystemExit(f'Ort {placement} unbekannt; möglich: {", ".join(PLACEMENTS)}')
        s['placement'] = placement
    if name_services is not None:
        s['name_services'] = name_services
    if (s['mode'], s['name_services']) != before:
        s['text'] = ''   # Wortlaut bei jeder Änderung neu bestätigen
    if s['mode'] == 'none' or clear:
        s['text'] = ''
    if from_suggestion:
        s['text'] = suggest(base, config, s['mode'] if s['mode'] in ('short', 'detailed') else 'short', s['name_services'])
        if not s['text']:
            raise SystemExit('Keine KI-Läufe protokolliert; es gibt nichts vorzuschlagen.')
    if text is not None:
        s['text'] = text.strip()
    write_settings(base, s)
    return s


def problems(config, has_part):
    """Hinderungsgründe für eine Auflage. has_part(kind) -> bool: freigegebener Teil vorhanden."""
    s = settings(config)
    if s['mode'] == 'none':
        return []
    out = []
    if not s.get('text'):
        out.append('KI-Angabe: Der Wortlaut ist noch nicht bestätigt (Befehl „KI-Angabe“).')
    if s['placement'] == 'imprint' and not ((config.get('typesetting') or {}).get('imprint', True)):
        out.append('KI-Angabe: Ort ist das Impressum, das Impressum ist aber ausgeschaltet (Projekteinstellungen).')
    if s['placement'] in ('foreword', 'afterword') and not has_part(s['placement']):
        name = 'Vorwort' if s['placement'] == 'foreword' else 'Nachwort'
        out.append(f'KI-Angabe: Ort ist das {name}, es gibt aber kein freigegebenes {name}.')
    return out


def for_book(config):
    """(Ort, Wortlaut) für den Satz oder None."""
    s = settings(config)
    if s['mode'] == 'none' or not s.get('text'):
        return None
    return s['placement'], s['text']


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['suggest', 'set'])
    ap.add_argument('--mode')
    ap.add_argument('--placement')
    ap.add_argument('--name-services', dest='name_services', action='store_true', default=None)
    ap.add_argument('--no-name-services', dest='name_services', action='store_false')
    ap.add_argument('--text')
    ap.add_argument('--text-from-suggestion', action='store_true')
    ap.add_argument('--clear-text', action='store_true')
    a = ap.parse_args(argv[1:])
    base = Path(a.project)
    config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
    if a.cmd == 'suggest':
        text = suggest(base, config, a.mode, a.name_services)
        print(text or 'Keine KI-Läufe protokolliert; Vorschlag: keine Angabe.')
        return 0
    s = apply(base, a.mode, a.placement, a.name_services, a.text, a.text_from_suggestion, a.clear_text)
    print(f'✓ KI-Angabe: {MODES[s["mode"]]}' + ('' if s['mode'] == 'none' else f', {PLACEMENTS[s["placement"]]}')
          + ('' if s['mode'] == 'none' else (', Wortlaut bestätigt' if s['text'] else ', Wortlaut noch nicht bestätigt')))
    print('Commit-Nachricht: KI-Angabe geändert')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
