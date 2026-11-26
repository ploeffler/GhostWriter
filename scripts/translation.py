#!/usr/bin/env python3
"""Übersetzung des Buchs, Grundlagen (#75): Sprachfassung als eigenes Buch, Begriffsliste, Vorverarbeitung, Stand je Abschnitt.

Aufruf (im Buch der Sprachfassung, `<buch>` = Ordner dieses Buch-Branchs):
  python3 scripts/translation.py <buch> init --language en --source-branch buch/<kurztitel> --source-edition 1 [--style close|free]
  python3 scripts/translation.py <buch> terms [list|add|check] …             Begriffsliste (Pflicht vor dem ersten Auftrag)
      terms add "<Original>" "<Übersetzung>" [--kind name|place|term|address|keep] [--note "…"]
  python3 scripts/translation.py <buch> models [--json]                      Modelle, die für dieses Buch angeboten werden
  python3 scripts/translation.py <buch> prepare <abschnitt> --source <ordner der Ausgangsauflage> [--json]
  python3 scripts/translation.py <buch> record <abschnitt> --source <ordner> --model <name> [--state translated|checked|approved]
  python3 scripts/translation.py <buch> stale --source <ordner>              Abschnitte, deren Original sich geändert hat
  python3 scripts/translation.py <buch> imprint [--reviewer "Name"]          Impressum-Hinweis zur KI-Unterstützung

Grundsätze (Entscheidungen Peter 25./26.11.2026):
- Jede Sprachfassung ist ein **eigener Buch-Branch** (`buch/<kurztitel>-en`). Der Block `translation` in `ghostwriter.yml` verweist auf den
  Original-Branch und die Ausgangsauflage; Quelle ist ausschließlich eine **Auflage** des Originals, nie der laufende Stand.
- Die **Begriffsliste** `translation/terms.yml` ist Pflicht; ohne sie bereitet `prepare` nichts vor.
- Vorverarbeitung: **Trennstriche am Zeilenende** werden zusammengefügt (Texte aus Satz, PDF oder Gegenlesen), danach wird übersetzt.
- Der Stand je Abschnitt steht in `translation/status.yml` (Original-Fingerabdruck, Ausgangsauflage, Modell, Stand). Ändert sich das Original, ist
  der Abschnitt **veraltet** (`stale`).
- **Explizite Inhalte:** Trägt das Buchprofil `content.explicit: true`, bietet `models` TranslateGemma nicht an (Gemma Terms of Use und Prohibited Use
  Policy verbieten sexuell explizite Ausgaben). Gemma 4 steht laut Anbieterseite unter Apache 2.0 und bleibt möglich.
- Modellgewichte hostet oder spiegelt GhostWriter nie; der Benutzer lädt sie selbst. Das Skript ruft kein Modell auf und gibt nichts frei.
- Das Impressum der Sprachfassung nennt die KI-Unterstützung („Übersetzung mit KI-Unterstützung, überarbeitet von …“).
"""
import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

TERMS_FILE = Path('translation') / 'terms.yml'
STATUS_FILE = Path('translation') / 'status.yml'
KINDS = ('name', 'place', 'term', 'address', 'keep')
KIND_TEXT = {'name': 'Name', 'place': 'Ort', 'term': 'Fachbegriff', 'address': 'Anrede (Du/Sie)', 'keep': 'bleibt unübersetzt'}
STATES = ('open', 'translated', 'checked', 'approved')
STYLES = ('close', 'free')
STYLE_TEXT = {'close': 'nah am Original, natürlich in der Zielsprache',
              'free': 'freier: Redewendungen und Wortspiele an die Zielsprache anpassen'}
# Modelle für die Übersetzung. `explicit_allowed`: erlaubt die Lizenz sexuell explizite Ausgaben? (Gemma Terms of Use: nein, Gemma 4: Apache 2.0.)
MODELS = [
    {'id': 'translategemma', 'label': 'TranslateGemma (lokal)', 'license': 'Gemma Terms of Use', 'explicit_allowed': False,
     'note': 'Die Prohibited Use Policy verbietet sexuell explizite Ausgaben; nicht für Bücher mit expliziten Inhalten.'},
    {'id': 'gemma-4', 'label': 'Gemma 4 (lokal)', 'license': 'Apache License 2.0', 'explicit_allowed': True,
     'note': 'Lizenztext am 26.11.2026 auf gemma.ai gelesen: Apache 2.0 ohne Nutzungsbeschränkung auf Inhalte.'},
    {'id': 'chat', 'label': 'Modell des Chats', 'license': 'Bedingungen des Anbieters', 'explicit_allowed': True,
     'note': 'Es gelten die Nutzungsregeln des jeweiligen Anbieters.'},
    {'id': 'queue', 'label': 'Hintergrund-Warteschlange (eigener KI-Schlüssel)', 'license': 'Bedingungen des Anbieters', 'explicit_allowed': True,
     'note': 'Es gelten die Nutzungsregeln des jeweiligen Anbieters.'},
]
IMPRINT = {'de': 'Übersetzung mit KI-Unterstützung, überarbeitet von {reviewer}.',
           'en': 'Translated with AI assistance, revised by {reviewer}.'}


class TranslationError(Exception):
    pass


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def read_yaml(path):
    try:
        data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    except OSError:
        return {}
    except yaml.YAMLError as e:
        raise TranslationError(f'{path}: nicht lesbar ({e})')
    return data if isinstance(data, dict) else {}


def write_yaml(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10 ** 6), encoding='utf-8')


# ---------- Vorverarbeitung ----------

HYPHEN_BREAK = re.compile(r'(?<=[A-Za-zÄÖÜäöüß])[-­]\s*\n\s*(?=[a-zäöüß])')


def dehyphenate(text):
    """Trennstriche am Zeilenende zusammenfügen („entgegen-\\nkommt“ → „entgegenkommt“). Nur vor einem Kleinbuchstaben, damit
    Bindestrich-Wörter vor Eigennamen („Süd-\\nTirol“) und Aufzählungen („- Punkt“) unberührt bleiben. Absatzgrenzen bleiben."""
    return HYPHEN_BREAK.sub('', text)


def fingerprint(text):
    return hashlib.sha256(re.sub(r'\s+', ' ', text).strip().encode('utf-8')).hexdigest()[:16]


# ---------- Block translation ----------

def config_of(base):
    return read_yaml(Path(base) / 'ghostwriter.yml')


def translation_of(base):
    t = config_of(base).get('translation')
    if not isinstance(t, dict) or not t.get('language'):
        raise TranslationError('Dieses Buch ist keine Sprachfassung (Block `translation` fehlt); zuerst `translation.py <buch> init`.')
    return t


def cmd_init(base, a):
    path = Path(base) / 'ghostwriter.yml'
    text = path.read_text(encoding='utf-8')
    if re.search(r'(?m)^translation:', text):
        raise TranslationError('Der Block `translation` gibt es schon.')
    if not re.fullmatch(r'[a-z]{2,3}(-[A-Z]{2})?', a.language or ''):
        raise TranslationError('--language: Sprachcode wie en oder pt-BR.')
    if not a.source_branch or not a.source_edition:
        raise TranslationError('--source-branch und --source-edition angeben (Quelle ist eine Auflage des Originals).')
    block = {'translation': {'language': a.language, 'source_branch': a.source_branch, 'source_edition': int(a.source_edition),
                             'style': a.style, 'created_at': now()}}
    path.write_text(text.rstrip('\n') + '\n\n' + yaml.safe_dump(block, allow_unicode=True, sort_keys=False), encoding='utf-8')
    print(f'✓ Sprachfassung {a.language} angelegt (Original {a.source_branch}, Auflage {a.source_edition}, Stil: {STYLE_TEXT[a.style]})')
    print('Nächster Schritt: Begriffsliste anlegen (`terms add …`); ohne sie bereitet `prepare` nichts vor.')
    print(f'Commit-Nachricht: Sprachfassung {a.language} angelegt')
    return 0


# ---------- Begriffsliste ----------

def load_terms(base):
    return read_yaml(Path(base) / TERMS_FILE).get('terms') or []


def cmd_terms(base, a):
    sub = a.args[0] if a.args else 'list'
    t = translation_of(base)
    terms = load_terms(base)
    if sub == 'add':
        if len(a.args) != 3:
            raise TranslationError('terms add "<Original>" "<Übersetzung>"')
        src, dst = a.args[1].strip(), a.args[2].strip()
        if not src or not dst:
            raise TranslationError('Original und Übersetzung dürfen nicht leer sein.')
        if a.kind not in KINDS:
            raise TranslationError('--kind: ' + ', '.join(KINDS))
        entry = {'source': src, 'target': dst, 'kind': a.kind}
        if a.note:
            entry['note'] = a.note
        terms = [x for x in terms if str(x.get('source')).casefold() != src.casefold()] + [entry]
        write_yaml(Path(base) / TERMS_FILE, {'language': t['language'], 'terms': terms})
        print(f'✓ {src} → {dst} ({KIND_TEXT[a.kind]})')
        return 0
    if sub == 'check':
        if not terms:
            print('✗ Die Begriffsliste ist leer: Pflicht vor dem ersten Auftrag (Namen, Orte, Fachbegriffe, Anrede).')
            return 1
        print(f'✓ Begriffsliste: {len(terms)} Einträge')
        return 0
    if sub != 'list':
        raise TranslationError('terms list | add | check')
    if a.json:
        print(json.dumps(terms, ensure_ascii=False, indent=1))
    else:
        print('\n'.join(f'- {x["source"]} → {x["target"]} ({KIND_TEXT.get(x.get("kind"), "")})' + (f' – {x["note"]}' if x.get('note') else '')
                        for x in terms) or 'Noch keine Begriffe.')
    return 0


# ---------- Modelle ----------

def offered_models(config):
    """Modelle, die für dieses Buch angeboten werden: bei `content.explicit: true` ohne die, deren Lizenz sexuell explizite Ausgaben verbietet."""
    explicit = bool(((config or {}).get('content') or {}).get('explicit'))
    return [m for m in MODELS if m['explicit_allowed'] or not explicit]


def cmd_models(base, a):
    config = config_of(base)
    models = offered_models(config)
    if a.json:
        print(json.dumps(models, ensure_ascii=False, indent=1))
        return 0
    explicit = bool(((config.get('content') or {}).get('explicit')))
    print('Buch mit expliziten Inhalten (`content.explicit`): nur Modelle ohne Inhaltssperre.' if explicit else 'Angebotene Modelle:')
    for m in models:
        print(f'- {m["label"]} – {m["license"]}' + (f' ({m["note"]})' if m.get('note') else ''))
    return 0


# ---------- Abschnitte ----------

def source_section(source, section_id):
    from render_view import load, section_file
    _, config = load(Path(source))
    for ch in config['structure']['chapters']:
        for sec in ch['sections']:
            if sec['id'] == section_id:
                return section_file(Path(source), sec)[3]
    raise TranslationError(f'Abschnitt {section_id} gibt es im Original nicht (Ordner {source}).')


def status_of(base):
    return read_yaml(Path(base) / STATUS_FILE).get('sections') or {}


def cmd_prepare(base, a):
    t = translation_of(base)
    terms = load_terms(base)
    if not terms:
        raise TranslationError('Die Begriffsliste ist leer: zuerst `terms add …` (Pflicht, Entscheidung Peter 26.11.2026).')
    if not a.source or len(a.args) != 1:
        raise TranslationError('prepare <abschnitt> --source <ordner der Ausgangsauflage>')
    raw = source_section(a.source, a.args[0])
    text = dehyphenate(raw)
    lines = '\n'.join(f'- „{x["source"]}“ → „{x["target"]}“ ({KIND_TEXT.get(x.get("kind"), "")})' + (f': {x["note"]}' if x.get('note') else '') for x in terms)
    prompt = (f'Übersetze den folgenden Abschnitt ins Zielsprachen-Kürzel „{t["language"]}“. Stil: {STYLE_TEXT[t.get("style", "close")]}.\n'
              f'Halte dich an die Begriffsliste; eine Abweichung ist ein Befund, keine Freiheit.\n{lines}\n'
              'Nichts auslassen, nichts hinzuerfinden. Namen, Zahlen und Zeitangaben bleiben exakt. Unsichere Stellen mit '
              '[ÜBERSETZUNG PRÜFEN: …] markieren. Dialekt oder Mundart nicht stillschweigend glätten, sondern als Frage melden. '
              'Absatzschlüsse (Pointen, Doppelsinn) bewusst übertragen.\n\n---\n' + text)
    data = {'section': a.args[0], 'language': t['language'], 'source_edition': t['source_edition'], 'fingerprint': fingerprint(raw),
            'dehyphenated': text != raw, 'text': text, 'prompt': prompt, 'status': status_of(base).get(a.args[0], {}).get('state', 'open')}
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
    else:
        print(prompt)
        print(f'\n---\nOriginal-Fingerabdruck: {data["fingerprint"]} · Trennstriche zusammengefügt: {"ja" if data["dehyphenated"] else "nein"}')
    return 0


def cmd_record(base, a):
    t = translation_of(base)
    if not a.source or len(a.args) != 1 or not a.model:
        raise TranslationError('record <abschnitt> --source <ordner> --model <name> [--state …]')
    if a.state not in STATES:
        raise TranslationError('--state: ' + ', '.join(STATES))
    sid = a.args[0]
    raw = source_section(a.source, sid)
    sections = status_of(base)
    sections[sid] = {'source_fingerprint': fingerprint(raw), 'source_edition': t['source_edition'], 'model': a.model, 'state': a.state, 'updated_at': now()}
    write_yaml(Path(base) / STATUS_FILE, {'language': t['language'], 'sections': sections})
    print(f'✓ {sid}: {a.state} (Modell {a.model}, Original-Fingerabdruck {sections[sid]["source_fingerprint"]})')
    print(f'Commit-Nachricht: Übersetzung {sid} ({a.state}) festgehalten')
    return 0


def stale_sections(base, source):
    """Abschnitte, deren Original sich seit der Übersetzung geändert hat: [(id, alter Fingerabdruck, neuer Fingerabdruck)]."""
    out = []
    for sid, st in status_of(base).items():
        try:
            new = fingerprint(source_section(source, sid))
        except TranslationError:
            out.append((sid, st.get('source_fingerprint'), ''))
            continue
        if new != st.get('source_fingerprint'):
            out.append((sid, st.get('source_fingerprint'), new))
    return out


def cmd_stale(base, a):
    translation_of(base)
    if not a.source:
        raise TranslationError('stale --source <ordner der aktuellen Originalauflage>')
    rows = stale_sections(base, a.source)
    if a.json:
        print(json.dumps([{'section': s, 'was': o, 'now': n} for s, o, n in rows], ensure_ascii=False))
    else:
        print('\n'.join(f'- {s}: Original geändert ({"Abschnitt entfernt" if not n else f"{o} → {n}"}) → Übersetzung veraltet' for s, o, n in rows)
              or 'Keine veralteten Abschnitte.')
    return 0


def cmd_imprint(base, a):
    t = translation_of(base)
    text = IMPRINT.get(t['language'].split('-')[0], IMPRINT['en']).format(reviewer=a.reviewer or '…')
    print(text)
    if not a.reviewer:
        print('(Name der überarbeitenden Person noch offen)')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['init', 'terms', 'models', 'prepare', 'record', 'stale', 'imprint'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--language')
    ap.add_argument('--source-branch')
    ap.add_argument('--source-edition')
    ap.add_argument('--style', default='close', choices=STYLES)
    ap.add_argument('--kind', default='term')
    ap.add_argument('--note')
    ap.add_argument('--source')
    ap.add_argument('--model')
    ap.add_argument('--state', default='translated')
    ap.add_argument('--reviewer')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        return {'init': cmd_init, 'terms': cmd_terms, 'models': cmd_models, 'prepare': cmd_prepare, 'record': cmd_record,
                'stale': cmd_stale, 'imprint': cmd_imprint}[a.cmd](a.project, a)
    except TranslationError as e:
        print(f'::error::{e}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
