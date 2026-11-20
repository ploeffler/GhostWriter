#!/usr/bin/env python3
"""Hinweisdurchsicht (#367, Teil 1): offene Befunde aus Prüfberichten sammeln und den Dialog zum Durchsehen vorbereiten.

Befunde stehen maschinenlesbar neben dem Bericht in `editorial/<bericht>.yml` (Schema
`schemas/findings.schema.json`). Die Hinweisdurchsicht liest nur diese Dateien, keinen Freitext.

  python3 scripts/hinweise.py collect <buch> [--chapter kap-01 …] [--date JJJJ-MM-TT]
      sammelt alle offenen Befunde und schreibt editorial/durchsicht-<datum>.yml
  python3 scripts/hinweise.py show <buch> [--file editorial/durchsicht-….yml] [--open]
      Textfassung des Dialogs: kapitelweise alt und neu, darunter die Autorenentscheidungen
  python3 scripts/hinweise.py decide <buch> <eintrag> --decision ja|nein|geändert [--new TEXT] [--file …]
      schreibt nur `entscheidung` (und bei „geändert“ `neu`) in die Dialogdatei

Prüfung beim Anlegen: `alt` muss im heutigen Manuskript des Abschnitts genau einmal vorkommen, sonst wird
der Befund nicht aufgenommen und unter `ausgelassen` gemeldet. „Ohne Autor lösbar“ ist ein Eintrag nur bei
einer rein sprachlichen Art mit Vorschlag `neu`; alles andere – und im Zweifel – ist eine Autorenentscheidung.
Das Skript ändert kein Manuskript; Umsetzen, Wiederöffnen und Rückmeldung in die Berichte folgen in Teil 2.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

import yaml

LANGUAGE_KINDS = ('rechtschreibung', 'zeichensetzung', 'grammatik', 'wiederholung', 'satzbau', 'sprache')
AUTHOR_KINDS = ('fakt', 'ton', 'aufbau', 'buchweit')
KINDS = LANGUAGE_KINDS + AUTHOR_KINDS
SEVERITIES = ('gering', 'mittel', 'wesentlich', 'blockierend')
FINDING_STATES = ('offen', 'erledigt', 'entschieden')
DECISIONS = ('offen', 'ja', 'nein', 'geändert')
GUIDE = ('Je Eintrag entscheiden: ja = übernehmen, nein = nicht ändern, geändert = mit eigener Fassung in `neu`. '
         'Jede Antwort wird sofort als kleiner Nachtrag gespeichert (docs/SPEICHERN.md). Umgesetzt wird erst am '
         'Ende eines Kapitels oder auf Auftrag; Wiederöffnen abgeschlossener Kapitel braucht eine eigene Bestätigung.')
QUESTION = {'fakt': 'Welche Angabe ist richtig bzw. fehlt?', 'ton': 'Soll sich Ton oder Stimme hier ändern?',
            'aufbau': 'Soll der Aufbau so geändert werden?', 'buchweit': 'Soll das im ganzen Buch so gelten?'}
SENTENCE = re.compile(r'[^.!?…\n]+(?:[.!?…]+[»«“”"\')\]]*|\n|$)')


def editorial(base):
    return Path(base) / 'editorial'


def is_findings_file(path):
    return path.suffix == '.yml' and path.name != 'checks.yml' and not path.name.startswith('durchsicht-')


def findings_files(base):
    d = editorial(base)
    return sorted(p for p in d.glob('*.yml') if is_findings_file(p)) if d.is_dir() else []


def dialog_files(base):
    d = editorial(base)
    return sorted(d.glob('durchsicht-*.yml')) if d.is_dir() else []


def read_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}


def write_yaml(path, data):
    Path(path).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100), encoding='utf-8')


def section_index(config):
    """{section_id: (kapitelnummer.abschnittsnummer, kapitel, abschnitt)}"""
    out = {}
    for cn, ch in enumerate(config['structure']['chapters'], start=1):
        for sn, s in enumerate(ch['sections'], start=1):
            out[s['id']] = (f'{cn}.{sn}', ch, s)
    return out


def context(text, alt):
    """Betroffener Satz mit bis zu zwei Sätzen davor und danach (#367)."""
    start = text.index(alt)
    end = start + len(alt)
    spans = [m.span() for m in SENTENCE.finditer(text) if m.group().strip()]
    first = next((i for i, (a, b) in enumerate(spans) if b > start), 0)
    last = next((i for i, (a, b) in enumerate(spans) if b >= end), len(spans) - 1)
    a, b = spans[max(0, first - 2)][0], spans[min(len(spans) - 1, last + 2)][1]
    return re.sub(r'\s+', ' ', text[a:b]).strip()


def collect(base, config, chapters=None, date=None, commit=None):
    """Offene Befunde sammeln; Rückgabe (Pfad, Daten). Schreibt die Dialogdatei."""
    import checks
    base = Path(base)
    index = section_index(config)
    chapters = set(chapters or [])
    unknown = chapters - {ch['id'] for ch in config['structure']['chapters']}
    if unknown:
        raise ValueError(f'Unbekanntes Kapitel: {", ".join(sorted(unknown))}')
    auto, author, skipped, sources = [], [], [], []
    for path in findings_files(base):
        data = read_yaml(path)
        rel = path.relative_to(base).as_posix()
        for f in data.get('befunde') or []:
            if f.get('status', 'offen') != 'offen':
                continue
            ref = f'{rel}#{f.get("id")}'
            sid = f.get('abschnitt')
            if sid not in index:
                skipped.append({'befund': ref, 'grund': f'Abschnitt {sid} unbekannt'})
                continue
            number, ch, s = index[sid]
            if chapters and ch['id'] not in chapters:
                continue
            if rel not in sources:
                sources.append(rel)
            text = checks.manuscript(base, config, sid) or ''
            alt = f.get('alt') or ''
            entry = {'id': '', 'befund': ref, 'abschnitt': number, 'section_id': sid, 'chapter_id': ch['id'],
                     'chapter_status': ch.get('status', ''), 'datei': s['path']}
            if f.get('absatz') is not None:
                entry['absatz'] = f['absatz']
            entry.update({'art': f.get('art', ''), 'grund': f.get('befund', '')})
            if alt:
                hits = text.count(alt)
                if hits != 1:
                    skipped.append({'befund': ref, 'grund': f'alter Wortlaut kommt {hits}-mal vor (erwartet: genau einmal)'})
                    continue
                entry.update({'kontext': context(text, alt), 'alt': alt})
            else:
                entry.update({'kontext': '', 'alt': ''})
            entry['neu'] = f.get('neu') or ''
            entry['entscheidung'] = 'offen'
            solvable = f.get('art') in LANGUAGE_KINDS and alt and entry['neu'] and entry['neu'] != alt
            if solvable:
                auto.append(entry)
            else:
                kind = f.get('art') if f.get('art') in AUTHOR_KINDS else 'aufbau' if not alt else 'ton'
                entry['art'] = kind
                entry['frage'] = f.get('frage') or f.get('richtung') or QUESTION[kind]
                author.append(entry)
    for n, e in enumerate(auto + author, start=1):
        e['id'] = f'e-{n:03d}'
    date = str(date or datetime.date.today().isoformat())
    p = config.get('project') or {}
    data = {'buch': p.get('title') or p.get('working_title') or '', 'fassung': commit or checks.head_commit(base) or '',
            'erstellt': date, 'quelle': sources, 'anleitung': GUIDE,
            'ohne_autor': auto, 'autorenentscheidung': author}
    if not data['fassung']:
        del data['fassung']
    if skipped:
        data['ausgelassen'] = skipped
    out = editorial(base) / f'durchsicht-{date}.yml'
    out.parent.mkdir(parents=True, exist_ok=True)
    write_yaml(out, data)
    return out, data


def latest(base):
    files = dialog_files(base)
    return files[-1] if files else None


def entries(data):
    return [('ohne_autor', e) for e in data.get('ohne_autor') or []] + \
           [('autorenentscheidung', e) for e in data.get('autorenentscheidung') or []]


def decide(path, entry_id, decision, new=None):
    if decision not in DECISIONS:
        raise ValueError(f'Unbekannte Entscheidung: {decision}')
    if decision == 'geändert' and not new:
        raise ValueError('Bei „geändert“ gehört die eigene Fassung dazu (--new)')
    data = read_yaml(path)
    for _, e in entries(data):
        if e.get('id') == entry_id:
            e['entscheidung'] = decision
            if new is not None:
                e['neu'] = new
            write_yaml(path, data)
            return e
    raise ValueError(f'Eintrag {entry_id} nicht gefunden')


def show(data, only_open=False):
    def wanted(e):
        return not only_open or e.get('entscheidung', 'offen') == 'offen'
    auto = [e for e in data.get('ohne_autor') or [] if wanted(e)]
    author = [e for e in data.get('autorenentscheidung') or [] if wanted(e)]
    total = entries(data)
    done = sum(e.get('entscheidung', 'offen') != 'offen' for _, e in total)
    lines = [f'### 🧹 Hinweisdurchsicht · {data.get("buch", "")}',
             f'Stand {data.get("erstellt", "")} · {len(total)} Einträge · {done} entschieden · {len(total) - done} offen', '']
    if auto:
        lines += ['#### Ohne Autor lösbar', '']
        chapter = None
        for e in auto:
            if e['chapter_id'] != chapter:
                chapter = e['chapter_id']
                lines += [f'**Kapitel {e["abschnitt"].split(".")[0]}** ({e.get("chapter_status", "")})', '']
            lines += [f'`{e["id"]}` · {e["abschnitt"]} · {e["art"]} · **{e.get("entscheidung", "offen")}** – {e.get("grund", "")}',
                      f'> alt: {e["alt"]}', f'> neu: {e["neu"]}', '']
    if author:
        lines += ['#### Autorenentscheidung', '']
        for e in author:
            lines += [f'`{e["id"]}` · {e["abschnitt"]} · {e["art"]} · **{e.get("entscheidung", "offen")}** – {e.get("grund", "")}',
                      f'> Frage: {e.get("frage", "")}']
            if e.get('alt'):
                lines += [f'> alt: {e["alt"]}']
            if e.get('neu'):
                lines += [f'> Vorschlag: {e["neu"]}']
            lines += ['']
    if data.get('ausgelassen'):
        lines += ['#### Nicht aufgenommen', ''] + [f'- {s["befund"]}: {s["grund"]}' for s in data['ausgelassen']] + ['']
    if not auto and not author:
        lines += ['*Keine offenen Einträge.*', '']
    lines += ['Antwort je Eintrag: `<id> ja` · `<id> nein` · `<id> geändert: <eigene Fassung>`']
    return '\n'.join(lines) + '\n'


# ---------- Prüfung (validate_project.py) ----------

def errors(base, config):
    """Befunddateien und Dialogdateien: Schema, eindeutige IDs, bekannte Abschnitte."""
    import json
    from jsonschema import Draft202012Validator
    schemas = Path(__file__).resolve().parents[1] / 'schemas'
    fv = Draft202012Validator(json.loads((schemas / 'findings.schema.json').read_text(encoding='utf-8')))
    dv = Draft202012Validator(json.loads((schemas / 'notes-review.schema.json').read_text(encoding='utf-8')))
    index = section_index(config)
    out = []
    for path, v, kind in [(p, fv, 'f') for p in findings_files(base)] + [(p, dv, 'd') for p in dialog_files(base)]:
        try:
            data = read_yaml(path)
        except Exception as exc:   # noqa: BLE001
            out.append(f'{path}: {exc}')
            continue
        if kind == 'f' and 'befunde' not in data:
            continue   # andere YAML-Dateien unter editorial/ sind keine Befunde
        errs = [f'{path}: {"/".join(map(str, e.absolute_path)) or "(Wurzel)"}: {e.message}' for e in v.iter_errors(data)]
        if errs:
            out += errs
            continue
        items = data['befunde'] if kind == 'f' else [e for _, e in entries(data)]
        ids = [e['id'] for e in items]
        out += [f'{path}: ID doppelt: {i}' for i in sorted({i for i in ids if ids.count(i) > 1})]
        key = 'abschnitt' if kind == 'f' else 'section_id'
        out += [f'{path}: {e["id"]}: Abschnitt {e[key]} unbekannt' for e in items if e[key] not in index]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('collect', help='offene Befunde sammeln und Dialogdatei schreiben')
    c.add_argument('project')
    c.add_argument('--chapter', action='append', help='nur dieses Kapitel (mehrfach möglich)')
    c.add_argument('--date')
    s = sub.add_parser('show', help='Dialog als Text zeigen')
    s.add_argument('project')
    s.add_argument('--file')
    s.add_argument('--open', action='store_true', help='nur offene Einträge')
    d = sub.add_parser('decide', help='Entscheidung zu einem Eintrag speichern')
    d.add_argument('project')
    d.add_argument('entry')
    d.add_argument('--decision', required=True, choices=DECISIONS[1:])
    d.add_argument('--new')
    d.add_argument('--file')
    args = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_view import load
    base, config = load(args.project)
    base = Path(base)
    try:
        if args.cmd == 'collect':
            path, data = collect(base, config, args.chapter, args.date)
            print(f'{path.relative_to(base).as_posix()}: {len(data["ohne_autor"])} ohne Autor lösbar, '
                  f'{len(data["autorenentscheidung"])} Autorenentscheidungen, {len(data.get("ausgelassen") or [])} nicht aufgenommen')
            return 0
        path = Path(args.file) if args.file else latest(base)
        if path and not path.is_absolute() and not path.exists():
            path = base / path
        if not path or not path.is_file():
            print('Keine Durchsichtsdatei gefunden (zuerst collect).', file=sys.stderr)
            return 1
        if args.cmd == 'show':
            print(show(read_yaml(path), args.open), end='')
            return 0
        e = decide(path, args.entry, args.decision, args.new)
        print(f'{e["id"]}: {e["entscheidung"]}')
        return 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
