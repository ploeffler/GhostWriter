#!/usr/bin/env python3
"""KI-Angabe im Buch: wie bei diesem Buch KI genutzt wurde (#78, #356).

Aufruf:
  python scripts/ai_disclosure.py <projektordner> suggest [--mode short|detailed] [--name-services|--no-name-services]
  python scripts/ai_disclosure.py <projektordner> set [--mode M] [--placement P] [--name-services|--no-name-services]
                                                    [--functions "A, B und C"]
                                                    [--text TEXT | --text-from-suggestion | --clear-text]

Mindestangabe (#356): In jedem Buch steht der Mustersatz

  Bei der Entstehung dieses Buchs wurden Funktionen einer KI genutzt, etwa für
  Rechtschreibung, Grammatik, Zeichensetzung und Quellenrecherche. {Autor} hat
  alle Inhalte geprüft und trägt die Verantwortung für den Text.

mit dem Autor aus `project.author` (ohne Autor: „Alle Inhalte wurden geprüft;
die Verantwortung für den Text trägt der Autor bzw. die Autorin.“). Er ist die
Vorgabe für alle Bücher, braucht keine Bestätigung und keine Läufe und lässt
sich nicht abwählen; nur die Aufzählung ist je Buch änderbar (`functions`).
Englische Bücher (`project.language: en…`) erhalten ihn auf Englisch.

Einstellung in ghostwriter.yml (fehlt = nur die Mindestangabe im Impressum):

  ai_disclosure:
    mode: functions        # functions (nur Mindestangabe) | short (+ ein Satz) | detailed (+ je Aufgabe) | custom (+ eigener Text)
    placement: imprint     # imprint (Impressum) | foreword (Vorwort) | afterword (Nachwort) | page (eigene Seite am Ende)
    name_services: true    # Dienste im Zusatz namentlich nennen (short, detailed)
    functions: [Rechtschreibung, Grammatik]   # Aufzählung im Mustersatz; fehlt = FUNCTIONS
    text: "…"              # bestätigter Zusatz; kommt nach der Mindestangabe ins Buch

`none` (früher „keine Angabe“) gilt wie `functions`.

suggest schlägt den Zusatz aus den tatsächlichen Läufen vor (Recherche,
Ideensammlung, Kapitelrecherche, Ghostwriting, auch in Vor- und Nachspann) mit
den Diensten aus deren Kopf (`provider`). Der Zusatz kommt nicht ungefragt ins
Buch: erst `set --text …` bzw. `--text-from-suggestion` nach der Bestätigung des
Benutzers schreibt ihn. Ändern sich Modus oder Dienste-Nennung, gilt er als
nicht mehr bestätigt und wird geleert. Enthält ein eigener Text den Mustersatz
schon, steht er nur einmal im Buch.

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

MODES = {'functions': 'nur Mindestangabe', 'short': 'Mindestangabe und ein Satz',
         'detailed': 'Mindestangabe und je Aufgabe', 'custom': 'Mindestangabe und eigener Text'}
PLACEMENTS = {'imprint': 'im Impressum', 'foreword': 'am Ende des Vorworts', 'afterword': 'am Ende des Nachworts',
              'page': 'auf einer eigenen Seite am Ende'}
SUGGESTED = ('short', 'detailed')   # Zusätze mit Vorschlag aus den Läufen
# Aufzählung im Mustersatz „Funktionen einer KI“ (#356); je Buch änderbar über ai_disclosure.functions
FUNCTIONS = ['Rechtschreibung', 'Grammatik', 'Zeichensetzung', 'Quellenrecherche']
FUNCTIONS_EN = ['spelling', 'grammar', 'punctuation', 'source research']
DEFAULT = {'mode': 'functions', 'placement': 'imprint', 'name_services': False, 'text': ''}
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
    if s['mode'] == 'none':   # „keine Angabe“ gibt es nicht mehr (#356)
        s['mode'] = 'functions'
    return s


def english(config):
    return str(((config or {}).get('project') or {}).get('language') or 'de').lower().startswith('en')


def placement(config):
    """Ort der Angabe; ohne eigene Wahl bei ausgeschaltetem Impressum die eigene Seite am Ende."""
    s = settings(config)
    explicit = 'placement' in ((config or {}).get('ai_disclosure') or {})
    if s['placement'] == 'imprint' and not explicit and not ((config or {}).get('typesetting') or {}).get('imprint', True):
        return 'page'
    return s['placement']


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


def functions(config):
    """Aufzählung für den Mustersatz: ai_disclosure.functions, sonst die Vorgabe."""
    items = [str(x).strip() for x in (settings(config).get('functions') or []) if str(x).strip()]
    return items or list(FUNCTIONS_EN if english(config) else FUNCTIONS)


def join_en(items):
    items = list(items)
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def minimum_sentence(config):
    """Erster Satz der Mindestangabe (daran wird erkannt, ob ein eigener Text ihn schon enthält)."""
    if english(config):
        return f'Functions of an AI were used in creating this book, for example for {join_en(functions(config))}.'
    return f'Bei der Entstehung dieses Buchs wurden Funktionen einer KI genutzt, etwa für {join_de(functions(config))}.'


def minimum(config):
    """Mindestangabe (#356): Mustersatz mit Autor; steht in jedem Buch."""
    author = (((config or {}).get('project') or {}).get('author') or '').strip()
    if english(config):
        end = (f'{author} has reviewed all content and is responsible for the text.' if author
               else 'All content has been reviewed; the author is responsible for the text.')
    else:
        end = (f'{author} hat alle Inhalte geprüft und trägt die Verantwortung für den Text.' if author
               else 'Alle Inhalte wurden geprüft; die Verantwortung für den Text trägt der Autor bzw. die Autorin.')
    return f'{minimum_sentence(config)} {end}'


def suggest(base, config, mode=None, name_services=None):
    """Vorgeschlagener Zusatz zur Mindestangabe (str); '' ohne protokollierte KI-Läufe oder bei functions/custom."""
    s = settings(config)
    mode = mode or (s['mode'] if s['mode'] in SUGGESTED else 'short')
    if mode not in SUGGESTED:
        return ''
    name_services = s['name_services'] if name_services is None else name_services
    used = usage(base)
    if not used:
        return ''
    tasks = [t for t in dict.fromkeys(TASKS.values()) if t in used]
    names = provider_names()
    if mode == 'detailed':
        lines = ['Darüber hinaus wurden KI-Werkzeuge eingesetzt:', '']
        for t in tasks:
            who = service_text(used[t], names, dative=True) if name_services else ''
            lines.append(f'- {t}' + (f' (mit {who})' if who else ''))
        return '\n'.join(lines)
    who = service_text(set().union(*used.values()), names) if name_services else ''
    return (f'Darüber hinaus wurden KI-Werkzeuge für {join_de(tasks)} eingesetzt'
            + (f' ({who})' if who else '') + '.')


def book_text(config):
    """Wortlaut im Buch: Mindestangabe, danach ein bestätigter Zusatz (ohne Doppelung des Mustersatzes)."""
    s = settings(config)
    extra = (s.get('text') or '').strip() if s['mode'] != 'functions' else ''
    norm = lambda t: ' '.join(t.split())
    if extra and norm(minimum_sentence(config)) in norm(extra):
        return extra
    return minimum(config) + (f'\n\n{extra}' if extra else '')


def block(s):
    out = ['ai_disclosure:', f'  mode: {s["mode"]}', f'  placement: {s["placement"]}',
           f'  name_services: {"true" if s["name_services"] else "false"}']
    if s.get('functions'):
        out.append('  functions: ' + yaml.safe_dump([str(x) for x in s['functions']], allow_unicode=True, width=10**6,
                                                    default_flow_style=True).rstrip('\n'))
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
    keys = list(DEFAULT) + ['functions']
    if {k: check.get(k, DEFAULT.get(k)) or None for k in keys} != {k: s.get(k, DEFAULT.get(k)) or None for k in keys}:
        raise SystemExit('ghostwriter.yml ließ sich nicht sicher ändern; bitte von Hand eintragen.')
    path.write_text(new, encoding='utf-8')


def parse_functions(value):
    """„Rechtschreibung, Grammatik und Stil“ → Liste; leer = Vorgabe."""
    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = re.split(r'\s*(?:,|;|\bund\b)\s*', str(value or ''))
    return [str(x).strip() for x in items if str(x).strip()]


def apply(base, mode=None, placement=None, name_services=None, text=None, from_suggestion=False, clear=False,
          functions_=None):
    config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
    s = settings(config)
    before = (s['mode'], s['name_services'])
    if mode == 'none':
        raise SystemExit('„Keine Angabe“ gibt es nicht mehr: Die Mindestangabe steht in jedem Buch (#356). '
                         'Für nur die Mindestangabe: --mode functions')
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
    if functions_ is not None:
        s['functions'] = parse_functions(functions_)
        if not s['functions']:
            s.pop('functions', None)
    if (s['mode'], s['name_services']) != before:
        s['text'] = ''   # Zusatz bei jeder Änderung neu bestätigen
    if s['mode'] == 'functions' or clear:
        s['text'] = ''
    if from_suggestion and s['mode'] != 'functions':
        if s['mode'] not in SUGGESTED:
            raise SystemExit('Für einen eigenen Text gibt es keinen Vorschlag; bitte --text verwenden.')
        s['text'] = suggest(base, config, s['mode'], s['name_services'])
        if not s['text']:
            raise SystemExit('Keine KI-Läufe protokolliert; es gibt keinen Zusatz vorzuschlagen.')
    if text is not None and s['mode'] != 'functions':
        s['text'] = text.strip()
    write_settings(base, s)
    return s


def problems(config, has_part):
    """Hinderungsgründe für eine Auflage. has_part(kind) -> bool: freigegebener Teil vorhanden."""
    s = settings(config)
    out = []
    if s['mode'] != 'functions' and not s.get('text'):
        out.append('KI-Angabe: Der Zusatz zur Mindestangabe ist noch nicht bestätigt (Befehl „KI-Angabe“; '
                   'oder „nur Mindestangabe“ wählen).')
    place = placement(config)
    if place == 'imprint' and not ((config.get('typesetting') or {}).get('imprint', True)):
        out.append('KI-Angabe: Ort ist das Impressum, das Impressum ist aber ausgeschaltet (Projekteinstellungen).')
    if place in ('foreword', 'afterword') and not has_part(place):
        name = 'Vorwort' if place == 'foreword' else 'Nachwort'
        out.append(f'KI-Angabe: Ort ist das {name}, es gibt aber kein freigegebenes {name}.')
    return out


def for_book(config):
    """(Ort, Wortlaut) für den Satz; die Mindestangabe gibt es immer (#356)."""
    return placement(config), book_text(config)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['suggest', 'set'])
    ap.add_argument('--mode')
    ap.add_argument('--placement')
    ap.add_argument('--name-services', dest='name_services', action='store_true', default=None)
    ap.add_argument('--no-name-services', dest='name_services', action='store_false')
    ap.add_argument('--functions', help='Aufzählung für den Mustersatz „Funktionen einer KI“; leer = Vorgabe')
    ap.add_argument('--text')
    ap.add_argument('--text-from-suggestion', action='store_true')
    ap.add_argument('--clear-text', action='store_true')
    a = ap.parse_args(argv[1:])
    base = Path(a.project)
    config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
    if a.cmd == 'suggest':
        print(minimum(config))
        if a.mode != 'functions':
            text = suggest(base, config, a.mode, a.name_services)
            print('\n' + text if text else '\n(Keine KI-Läufe protokolliert; kein Zusatz vorgeschlagen.)')
        return 0
    s = apply(base, a.mode, a.placement, a.name_services, a.text, a.text_from_suggestion, a.clear_text, a.functions)
    print(f'✓ KI-Angabe: {MODES[s["mode"]]}, {PLACEMENTS[s["placement"]]}'
          + ('' if s['mode'] == 'functions' else (', Zusatz bestätigt' if s['text'] else ', Zusatz noch nicht bestätigt')))
    print('Commit-Nachricht: KI-Angabe geändert')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
