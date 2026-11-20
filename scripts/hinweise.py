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
  python3 scripts/hinweise.py plan <buch> [--chapter …] [--file …]
      vor dem Umsetzen (Teil 2): je Eintrag ✅ umsetzbar, ⚠️ von Hand, ⛔ abgeschlossen (erst wieder öffnen)
  python3 scripts/hinweise.py apply <buch> [--chapter …] [--file …]
      setzt die ✅-Einträge ins Manuskript um, schreibt den Befundstatus zurück und nennt die Nachprüfung

Prüfung beim Anlegen: `alt` muss im heutigen Manuskript des Abschnitts genau einmal vorkommen, sonst wird
der Befund nicht aufgenommen und unter `ausgelassen` gemeldet. „Ohne Autor lösbar“ ist ein Eintrag nur bei
einer rein sprachlichen Art mit Vorschlag `neu`; alles andere – und im Zweifel – ist eine Autorenentscheidung.
`collect`, `show` und `decide` ändern kein Manuskript. Erst `apply` setzt entschiedene Einträge um, und nur in
Abschnitten, die nicht abgeschlossen sind: Wiederöffnen bleibt eine eigene, ausdrücklich bestätigte Freigabe
(START.md, „Freigaben“). Eine Nachprüfung trägt `apply` nicht selbst ein; sie gehört nach dem Neulesen dazu.
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
            if e.get('umgesetzt'):
                raise ValueError(f'{entry_id} ist schon umgesetzt')
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


# ---------- Umsetzen (Teil 2) ----------

def _section(base, config, sid):
    number, ch, s = section_index(config)[sid]
    from render_view import section_file
    head = section_file(Path(base), s)[0]
    return number, ch, s, head


def plan(base, config, data, chapters=None):
    """[(zeichen, eintrag, grund)] für alle entschiedenen, noch nicht umgesetzten Einträge."""
    import checks
    chapters = set(chapters or [])
    out = []
    for _, e in entries(data):
        if e.get('umgesetzt') or e.get('entscheidung') not in ('ja', 'geändert'):
            continue
        if chapters and e['chapter_id'] not in chapters:
            continue
        if e['section_id'] not in section_index(config):
            out.append(('⛔', e, 'Abschnitt gibt es nicht mehr'))
            continue
        _, ch, _, head = _section(base, config, e['section_id'])
        text = checks.manuscript(base, config, e['section_id']) or ''
        if not e.get('alt') or not e.get('neu'):
            out.append(('⚠️', e, 'ohne alten Wortlaut oder Vorschlag: von Hand umsetzen'))
        elif ch.get('status') == 'approved':
            out.append(('⛔', e, f'Kapitel {e["abschnitt"].split(".")[0]} ist abgeschlossen: erst wieder öffnen'))
        elif head.get('status') == 'approved':
            out.append(('⛔', e, f'Abschnitt {e["abschnitt"]} ist abgeschlossen: erst wieder öffnen'))
        elif text.count(e['alt']) != 1:
            out.append(('⛔', e, f'alter Wortlaut kommt {text.count(e["alt"])}-mal vor: Text hat sich geändert'))
        else:
            out.append(('✅', e, 'umsetzbar'))
    return out


def plan_text(items):
    if not items:
        return 'Keine entschiedenen Einträge zum Umsetzen.\n'
    lines = [f'{mark} `{e["id"]}` · {e["abschnitt"]} · {why}' for mark, e, why in items]
    blocked = sorted({e['abschnitt'] for mark, e, _ in items if mark == '⛔' and 'abgeschlossen' in _})
    if blocked:
        lines += ['', 'Wieder öffnen braucht eine eigene Bestätigung (START.md, „Freigaben“): ' + ', '.join(blocked)]
    return '\n'.join(lines) + '\n'


def _replace_in_manuscript(path, alt, neu):
    text = Path(path).read_text(encoding='utf-8')
    marker = '\n## Manuskript\n'
    head, sep, body = text.partition(marker)
    if not sep or body.count(alt) != 1:
        raise ValueError(f'{path}: alter Wortlaut nicht genau einmal im Manuskript')
    Path(path).write_text(head + sep + body.replace(alt, neu, 1), encoding='utf-8')


def _write_back(base, data):
    """Befundstatus in die Befunddateien (Punkt 6): umgesetzt -> erledigt, nein -> entschieden."""
    targets = {}
    for _, e in entries(data):
        state = 'erledigt' if e.get('umgesetzt') else 'entschieden' if e.get('entscheidung') == 'nein' else None
        if state and e.get('befund'):   # Dialog ohne Befundverweis (z. B. aus Markdown-Lektorat, #386): nichts zurückschreiben
            f, _, fid = e['befund'].partition('#')
            targets.setdefault(f, {})[fid] = state
    changed = []
    for f, ids in targets.items():
        path = Path(base) / f
        if not path.is_file():
            continue
        fd = read_yaml(path)
        hit = False
        for b in fd.get('befunde') or []:
            if b.get('id') in ids and b.get('status') == 'offen':
                b['status'] = ids[b['id']]
                hit = True
        if hit:
            write_yaml(path, fd)
            changed.append(f)
    return changed


def apply(base, config, path, chapters=None):
    """✅-Einträge umsetzen. Rückgabe: {'applied', 'skipped', 'reports', 'chapters', 'context'}."""
    import checks
    base = Path(base)
    data = read_yaml(path)
    items = plan(base, config, data, chapters)
    applied, skipped, touched, ctx = [], [], [], []
    for mark, e, why in items:
        if mark != '✅':
            skipped.append((mark, e, why))
            continue
        _replace_in_manuscript(base / e['datei'], e['alt'], e['neu'])
        e['umgesetzt'] = True
        applied.append(e)
        if e['chapter_id'] not in touched:
            touched.append(e['chapter_id'])
        text = checks.manuscript(base, config, e['section_id']) or ''
        ctx.append((e, context(text, e['neu']) if text.count(e['neu']) == 1 else e['neu']))
    write_yaml(path, data)
    reports = _write_back(base, data)
    return {'applied': applied, 'skipped': skipped, 'reports': reports, 'chapters': touched, 'context': ctx}


def apply_text(result):
    lines = [f'{len(result["applied"])} Einträge umgesetzt, {len(result["skipped"])} nicht umgesetzt.', '']
    if result['context']:
        lines += ['**Im Zusammenhang neu lesen:**', '']
        lines += [f'`{e["id"]}` · {e["abschnitt"]}: {c}' for e, c in result['context']] + ['']
    if result['skipped']:
        lines += ['**Nicht umgesetzt:**', ''] + [f'{m} `{e["id"]}` · {e["abschnitt"]} · {w}' for m, e, w in result['skipped']] + ['']
    if result['reports']:
        lines += ['Befundstatus zurückgeschrieben: ' + ', '.join(result['reports']), '']
    if result['chapters']:
        scope = ' '.join(f'--scope {c}' for c in result['chapters'])
        lines += ['**Nachprüfung** nach dem Neulesen eintragen (nicht automatisch):',
                  f'`python3 scripts/checks.py record <buch> --kind proofreading {scope} --result … --notes <n>`',
                  f'`python3 scripts/checks.py record <buch> --kind quality_correction {scope} --result … --notes <n>`',
                  'Danach eigens fragen, ob die Kapitel neu abgeschlossen werden sollen; Abschließen bleibt eine eigene Entscheidung.']
    return '\n'.join(lines) + '\n'


# ---------- Widget (ghostwriter-ui, Vorlage hinweisdurchsicht) ----------

STATUS_TEXT = {'planned': 'geplant', 'in_progress': 'in Arbeit', 'ready_for_assembly': 'bereit zum Zusammenführen',
               'assembly': 'im Zusammenführen', 'review': 'in Prüfung', 'ready_for_approval': 'bereit zum Abschluss',
               'approved': 'abgeschlossen'}


def widget_values(base, path):
    """Werte für die Vorlage hinweisdurchsicht (#367): (values, blocks)."""
    data = read_yaml(path)
    all_entries = entries(data)
    done = sum(e.get('entscheidung', 'offen') != 'offen' for _, e in all_entries)
    y, m, d = (str(data.get('erstellt', '')).split('-') + ['', '', ''])[:3]

    def row(e, author):
        r = {'E_ID': e['id'], 'E_WHERE': e['abschnitt'],
             'E_CHAPTER_TEXT': f'Kapitel {e["abschnitt"].split(".")[0]} · '
                               + STATUS_TEXT.get(e.get('chapter_status', ''), e.get('chapter_status', '')),
             'E_KIND': e.get('art', ''), 'E_REASON': e.get('grund', ''), 'E_CONTEXT': e.get('kontext', ''),
             'E_OLD': e.get('alt', ''), 'E_NEW': e.get('neu', ''),
             'E_DECISION': 'umgesetzt' if e.get('umgesetzt') else e.get('entscheidung', 'offen')}
        if author:
            r['E_QUESTION'] = e.get('frage', '')
        return r
    rel = Path(path).resolve().relative_to(Path(base).resolve()).as_posix()
    values = {'REVIEW_FILE': rel, 'REVIEW_BOOK': data.get('buch', ''),
              'REVIEW_DATE_TEXT': f'Stand {d}.{m}.{y}' if d else '',
              'REVIEW_COUNT_TEXT': f'{len(all_entries)} Einträge · {done} entschieden · {len(all_entries) - done} offen'}
    blocks = {}
    auto = [row(e, False) for e in data.get('ohne_autor') or []]
    author = [row(e, True) for e in data.get('autorenentscheidung') or []]
    skipped = [{'SK_REF': s['befund'], 'SK_REASON': s['grund']} for s in data.get('ausgelassen') or []]
    if auto:
        blocks['AUTO'] = auto
    if author:
        blocks['AUTHOR'] = author
    if skipped:
        blocks['SKIPPED'] = skipped
    return values, blocks


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
    for name, text in (('plan', 'vor dem Umsetzen zeigen, was geht'), ('apply', 'entschiedene Einträge umsetzen')):
        x = sub.add_parser(name, help=text)
        x.add_argument('project')
        x.add_argument('--chapter', action='append')
        x.add_argument('--file')
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) > 1 and argv[1] in sub.choices and argv[0] not in sub.choices:
        argv[0], argv[1] = argv[1], argv[0]   # auch „hinweise.py <buch> <befehl>“ wie die übrigen Skripte (#383)
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
        if args.cmd == 'plan':
            print(plan_text(plan(base, config, read_yaml(path), args.chapter)), end='')
            return 0
        if args.cmd == 'apply':
            print(apply_text(apply(base, config, path, args.chapter)), end='')
            return 0
        e = decide(path, args.entry, args.decision, args.new)
        print(f'{e["id"]}: {e["entscheidung"]}')
        return 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
