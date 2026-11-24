#!/usr/bin/env python3
"""Bereich zum Gegenlesen auschecken und sperren (#572, Teil 1 zu #209).

Ein Checkout sperrt einzelne Kapitel, eine Kapitelfolge oder das ganze Buch gegen alle regulären Schreibwege,
bis er ausdrücklich beendet wird. Die Sperre ist keine Freigabe und kein Abschließen. Gesperrt ist nur, was
die ausgecheckten Kapitel verändert; andere Kapitel und buchweite Angaben bleiben bearbeitbar.

  python3 scripts/checkout.py <buch> start (--chapters 3-5 | --book) --reader <name> [--until JJJJ-MM-TT] [--by <login>]
  python3 scripts/checkout.py <buch> status [--id GW-…]
  python3 scripts/checkout.py <buch> end <id> --reason "…" [--abort] [--by <login>]
  python3 scripts/checkout.py <buch> extend <id> --until JJJJ-MM-TT
  python3 scripts/checkout.py <buch> release <id> --chapters 5      Teil vorzeitig zurückholen, Rest bleibt gesperrt
  python3 scripts/checkout.py <buch> overdue [--today JJJJ-MM-TT]   überfällige Checkouts (nie automatisch entsperrt)
  python3 scripts/checkout.py <buch> check <abschnitt>…             Exit 1 + Meldung, wenn gesperrt
  python3 scripts/checkout.py <buch> verify [--json]                ausgecheckte Abschnitte seit Checkout verändert?
  python3 scripts/checkout.py <buch> gate --base <commit>           Prüfung in `validate`: Exit 1, wenn das Änderungspaket
                                                                    Abschnitte berührt, die im Ausgangsstand ausgecheckt waren

Daten: `checkouts.yml` im Buch (Schema `schemas/checkouts.schema.json`). Beenden, Abbrechen, Verlängern und
Zurückholen dürfen der Eigentümer (`team`; ohne `team` jeder mit Schreibrecht) und wer ausgecheckt hat; der
Gegenleser muss nicht zustimmen. Nach Ablauf der Frist gibt es nur einen Hinweis, nie ein automatisches Entsperren.
Die Datei- und QR-Erzeugung (DOCX und PDF) folgt in Teil 2; bis dahin trägt `dateien` nichts ein.
Grenze: Direktes Bearbeiten auf GitHub verhindert die Sperre nicht; `verify` und die Prüfung `validate` melden es.
"""
import argparse
import datetime
import json
import re
import secrets
import subprocess
import sys
from pathlib import Path

import yaml

FILE = 'checkouts.yml'
ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'   # Base32 ohne 0, O, 1, I
ID_RE = re.compile(r'^GW-[A-HJ-NP-Z2-9]{4}$')
STATES = ('ausgecheckt', 'beendet', 'abgebrochen')


def path(base):
    return Path(base) / FILE


def load(base):
    p = path(base)
    if not p.is_file():
        return {'checkouts': []}
    data = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    data.setdefault('checkouts', [])
    return data


def save(base, data):
    path(base).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')


def new_id(existing, rng=None):
    """GW- plus vier Zeichen, eindeutig im Buch (auch gegenüber beendeten Einträgen)."""
    taken = {e['id'] for e in existing}
    pick = rng or secrets.choice
    while True:
        cid = 'GW-' + ''.join(pick(ALPHABET) for _ in range(4))
        if cid not in taken:
            return cid


# ---------- Bereich ----------

def chapter_ids(config):
    return [c['id'] for c in config['structure']['chapters']]


def parse_chapters(config, spec):
    """„3-5“, „3,5“ oder Kapitel-IDs → Kapitel-IDs in Buchreihenfolge."""
    ids = chapter_ids(config)
    out = []
    for part in str(spec).replace(' ', '').split(','):
        if not part:
            continue
        m = re.fullmatch(r'(\d+)(?:[-–](\d+))?', part)
        if m:
            a, b = int(m.group(1)), int(m.group(2) or m.group(1))
            if not 1 <= a <= b <= len(ids):
                raise ValueError(f'Kapitel {part} gibt es nicht (1 bis {len(ids)})')
            out += ids[a - 1:b]
        elif part in ids:
            out.append(part)
        else:
            raise ValueError(f'Unbekanntes Kapitel: {part}')
    return [c for c in ids if c in out]


def sections_of(config, chapters):
    return [s['id'] for c in config['structure']['chapters'] if c['id'] in chapters for s in c['sections']]


def matter_ids(config):
    import checks
    return [i['id'] for i in checks.matter(config)]


def scope_sections(config, entry):
    """Abschnitts- und Teil-IDs, die der Checkout heute noch sperrt (ohne zurückgeholte Kapitel)."""
    back = {c for r in entry.get('zurueckgeholt') or [] for c in r.get('chapters') or []}
    if entry['bereich'].get('book'):
        chapters = [c for c in chapter_ids(config) if c not in back]
        return sections_of(config, chapters) + (matter_ids(config) if not back else [])
    return sections_of(config, [c for c in entry['bereich'].get('chapters') or [] if c not in back])


def scope_text(config, entry):
    if entry['bereich'].get('book'):
        return 'ganzes Buch'
    ids, chapters = chapter_ids(config), entry['bereich'].get('chapters') or []
    nums = sorted(ids.index(c) + 1 for c in chapters if c in ids)
    if not nums:
        return ', '.join(chapters)
    runs, start = [], nums[0]
    for a, b in zip(nums, nums[1:] + [None]):
        if b != a + 1:
            runs.append(str(start) if start == a else f'{start}–{a}')
            start = b
    return 'Kapitel ' + ', '.join(runs)


# ---------- Sperre ----------

def active(base):
    return [e for e in load(base)['checkouts'] if e.get('status') == 'ausgecheckt']


def locked_by_checkout(base, config, section_id):
    """Der aktive Checkout, der den Abschnitt sperrt, sonst None. Zum Import für andere Skripte."""
    for e in active(base):
        if section_id in scope_sections(config, e):
            return e
    return None


def lock_message(entry, config=None, section=None):
    who = f' an {entry["gegenleser"]}' if entry.get('gegenleser') else ''
    what = f'„{section}“ ist' if section else 'ist'
    return f'{what} ausgecheckt{who} ({entry["id"]}); erst den Checkout beenden (python3 scripts/checkout.py . end {entry["id"]} --reason …).'


def check_sections(base, config, *section_ids):
    """Meldungen für gesperrte Abschnitte (leer = frei)."""
    out = []
    for sid in section_ids:
        e = locked_by_checkout(base, config, sid)
        if e:
            out.append(f'Abschnitt {lock_message(e, section=sid)}')
    return out


# ---------- Rechte ----------

def may_manage(base, config, entry, actor):
    """Eigentümer (ohne `team`: jeder mit Schreibrecht) und wer ausgecheckt hat; keine Zustimmung des Gegenlesers."""
    if not actor or actor == entry.get('ausgecheckt_von'):
        return True
    import team
    return team.role(base, config, actor)['role'] == 'owner'


def _require(base, config, entry, actor):
    if not may_manage(base, config, entry, actor):
        raise ValueError(f'{actor} darf {entry["id"]} nicht ändern (nur Eigentümer und wer ausgecheckt hat)')


# ---------- Fingerabdrücke ----------

def fingerprints(base, config, ids):
    import checks
    return {sid: checks.digest(checks.manuscript(base, config, sid)) for sid in ids}


def head_commit(base):
    r = subprocess.run(['git', '-C', str(base), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ''


def now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().replace(microsecond=0).isoformat()


# ---------- Befehle ----------

def start(base, config, reader, chapters=None, book=False, by='', until=None, commit=None, rng=None, when=None):
    if not reader:
        raise ValueError('Gegenleser angeben (--reader)')
    if bool(chapters) == bool(book):
        raise ValueError('Entweder Kapitel (--chapters) oder das ganze Buch (--book)')
    scope = {'book': True} if book else {'chapters': parse_chapters(config, chapters)}
    data = load(base)
    probe = {'bereich': scope}
    wanted = set(scope_sections(config, probe))
    for e in data['checkouts']:
        if e.get('status') == 'ausgecheckt':
            clash = sorted(wanted & set(scope_sections(config, e)))
            if clash:
                raise ValueError(f'Schon ausgecheckt ({e["id"]}, {scope_text(config, e)}): {", ".join(clash[:3])}'
                                 + (' …' if len(clash) > 3 else ''))
    if until:
        datetime.date.fromisoformat(str(until))
    entry = {'id': new_id(data['checkouts'], rng), 'status': 'ausgecheckt', 'bereich': scope, 'gegenleser': reader,
             'ausgecheckt_von': by or '', 'zeit': when or now()}
    if until:
        entry['frist'] = str(until)
    entry['commit'] = commit if commit is not None else head_commit(base)
    entry['abschnitte'] = fingerprints(base, config, sorted(wanted))
    entry['dateien'] = []   # DOCX und PDF mit QR-Code: Teil 2 (#572)
    data['checkouts'].append(entry)
    save(base, data)
    return entry


def _find(data, cid):
    for e in data['checkouts']:
        if e['id'] == cid:
            return e
    raise ValueError(f'Checkout {cid} nicht gefunden')


def end(base, config, cid, reason, abort=False, by=''):
    if not reason:
        raise ValueError('Grund angeben (--reason)')
    data = load(base)
    e = _find(data, cid)
    if e['status'] != 'ausgecheckt':
        raise ValueError(f'{cid} ist schon {e["status"]}')
    _require(base, config, e, by)
    e['status'] = 'abgebrochen' if abort else 'beendet'
    e['beendet'] = {'zeit': now(), 'von': by, 'grund': reason}
    save(base, data)
    return e


def extend(base, config, cid, until, by=''):
    datetime.date.fromisoformat(str(until))
    data = load(base)
    e = _find(data, cid)
    if e['status'] != 'ausgecheckt':
        raise ValueError(f'{cid} ist schon {e["status"]}')
    _require(base, config, e, by)
    e['frist'] = str(until)
    save(base, data)
    return e


def release(base, config, cid, chapters, by=''):
    """Teil des Bereichs vorzeitig zurückholen; der Rest bleibt gesperrt. Ist nichts mehr gesperrt, ist der Checkout beendet."""
    data = load(base)
    e = _find(data, cid)
    if e['status'] != 'ausgecheckt':
        raise ValueError(f'{cid} ist schon {e["status"]}')
    _require(base, config, e, by)
    ids = parse_chapters(config, chapters)
    inside = set(chapter_ids(config)) if e['bereich'].get('book') else set(e['bereich'].get('chapters') or [])
    back = {c for r in e.get('zurueckgeholt') or [] for c in r.get('chapters') or []}
    new = [c for c in ids if c in inside and c not in back]
    if not new:
        raise ValueError('Diese Kapitel sind nicht ausgecheckt oder schon zurückgeholt')
    e.setdefault('zurueckgeholt', []).append({'chapters': new, 'zeit': now(), 'von': by})
    if not scope_sections(config, e):
        e['status'] = 'beendet'
        e['beendet'] = {'zeit': now(), 'von': by, 'grund': 'alle Kapitel zurückgeholt'}
    save(base, data)
    return e


def remaining_text(config, entry):
    if entry['status'] != 'ausgecheckt':
        return 'nichts'
    left = set(scope_sections(config, entry))
    chapters = [c['id'] for c in config['structure']['chapters'] if left & {s['id'] for s in c['sections']}]
    return scope_text(config, {'bereich': {'chapters': chapters}})


def overdue(base, today=None):
    today = datetime.date.fromisoformat(str(today)) if today else datetime.date.today()
    out = []
    for e in active(base):
        if e.get('frist') and datetime.date.fromisoformat(str(e['frist'])) < today:
            out.append((e, (today - datetime.date.fromisoformat(str(e['frist']))).days))
    return out


def verify(base, config):
    """Ausgecheckte Abschnitte, deren Manuskript sich seit dem Checkout geändert hat: [(Checkout, [Abschnitt, …])]."""
    out = []
    for e in active(base):
        now_fp = fingerprints(base, config, [s for s in scope_sections(config, e) if s in (e.get('abschnitte') or {})])
        changed = [s for s, fp in now_fp.items() if fp != e['abschnitte'][s]]
        if changed:
            out.append((e, changed))
    return out


def verify_text(found):
    return ''.join(f'{e["id"]} ({e.get("gegenleser", "")}): geändert seit dem Checkout: {", ".join(changed)}\n'
                   for e, changed in found)


def status_text(base, config, only=None):
    data = load(base)
    rows = [e for e in data['checkouts'] if not only or e['id'] == only]
    if not rows:
        return 'Keine Checkouts.\n'
    lines = []
    for e in rows:
        line = f'{e["id"]} · {e["status"]} · {scope_text(config, e)} · {e.get("gegenleser", "")} · seit {str(e.get("zeit", ""))[:10]}'
        if e.get('frist'):
            line += f' · Frist {e["frist"]}'
        if e['status'] != 'ausgecheckt' and e.get('beendet'):
            line += f' · {e["beendet"].get("grund", "")}'
        lines.append(line)
    return '\n'.join(lines) + '\n'


# ---------- Prüfung (validate_project.py) ----------

def problems(base, config):
    """Datei und Bereich prüfen: Format, eindeutige Kennungen, bekannte Kapitel, keine Überschneidung aktiver Checkouts."""
    import json as _json
    from jsonschema import Draft202012Validator
    p = path(base)
    if not p.is_file():
        return []
    try:
        data = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    except yaml.YAMLError as exc:
        return [f'{FILE}: {exc}']
    schema = _json.loads((Path(__file__).resolve().parents[1] / 'schemas/checkouts.schema.json').read_text(encoding='utf-8'))
    errs = [f'{FILE}: {"/".join(map(str, e.absolute_path)) or "(Wurzel)"}: {e.message}'
            for e in Draft202012Validator(schema).iter_errors(data)]
    if errs:
        return errs
    ids = [e['id'] for e in data['checkouts']]
    errs += [f'{FILE}: Kennung doppelt: {i}' for i in sorted({i for i in ids if ids.count(i) > 1})]
    known = set(chapter_ids(config))
    for e in data['checkouts']:
        errs += [f'{FILE}: {e["id"]}: Kapitel {c} unbekannt'
                 for c in (e['bereich'].get('chapters') or []) if c not in known]
    seen = {}
    for e in data['checkouts']:
        if e['status'] != 'ausgecheckt':
            continue
        for sid in scope_sections(config, e):
            if sid in seen:
                errs.append(f'{FILE}: {sid} ist doppelt ausgecheckt ({seen[sid]}, {e["id"]})')
            seen[sid] = e['id']
    return errs


def changed_locked(base, config, ref):
    """Für `validate`: Abschnitte, die ein Änderungspaket gegenüber `ref` verändert, obwohl sie ausgecheckt sind (laut
    Checkout-Datei des Ausgangsstands). [(Kennung, Abschnitt)]."""
    r = subprocess.run(['git', '-C', str(base), 'show', f'{ref}:{FILE}'], capture_output=True, text=True)
    if r.returncode != 0:
        return []
    old = (yaml.safe_load(r.stdout) or {}).get('checkouts') or []
    out = []
    import checks
    for e in old:
        if e.get('status') != 'ausgecheckt':
            continue
        for sid in scope_sections(config, e):
            if sid not in (e.get('abschnitte') or {}):
                continue
            if checks.digest(checks.manuscript(base, config, sid)) != e['abschnitte'][sid]:
                out.append((e['id'], sid))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('start')
    s.add_argument('--chapters')
    s.add_argument('--book', action='store_true')
    s.add_argument('--reader', required=True)
    s.add_argument('--until')
    s.add_argument('--by', default='')
    st = sub.add_parser('status')
    st.add_argument('--id')
    e = sub.add_parser('end')
    e.add_argument('id')
    e.add_argument('--reason', required=True)
    e.add_argument('--abort', action='store_true')
    e.add_argument('--by', default='')
    x = sub.add_parser('extend')
    x.add_argument('id')
    x.add_argument('--until', required=True)
    x.add_argument('--by', default='')
    r = sub.add_parser('release')
    r.add_argument('id')
    r.add_argument('--chapters', required=True)
    r.add_argument('--by', default='')
    o = sub.add_parser('overdue')
    o.add_argument('--today')
    c = sub.add_parser('check')
    c.add_argument('sections', nargs='+')
    g = sub.add_parser('gate')
    g.add_argument('--base', required=True)
    v = sub.add_parser('verify')
    v.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_view import load as load_project
    base, config = load_project(args.project)
    try:
        if args.cmd == 'start':
            en = start(base, config, args.reader, args.chapters, args.book, args.by, args.until)
            print(f'{en["id"]}: {scope_text(config, en)} an {en["gegenleser"]} ausgecheckt und gesperrt'
                  + (f' (Frist {en["frist"]})' if en.get('frist') else ''))
        elif args.cmd == 'status':
            print(status_text(base, config, args.id), end='')
        elif args.cmd == 'end':
            en = end(base, config, args.id, args.reason, args.abort, args.by)
            print(f'{en["id"]}: {en["status"]}' + ('; nicht zurückgeführte externe Änderungen können verloren gehen'
                                                    if args.abort else ''))
        elif args.cmd == 'extend':
            en = extend(base, config, args.id, args.until, args.by)
            print(f'{en["id"]}: Frist {en["frist"]}')
        elif args.cmd == 'release':
            en = release(base, config, args.id, args.chapters, args.by)
            print(f'{en["id"]}: {en["status"]}; noch gesperrt: {remaining_text(config, en)}')
        elif args.cmd == 'overdue':
            rows = overdue(base, args.today)
            for en, days in rows:
                print(f'{en["id"]}: überfällig seit {days} Tagen ({en.get("gegenleser", "")}, {scope_text(config, en)})')
            if not rows:
                print('Nichts überfällig.')
        elif args.cmd == 'check':
            msgs = check_sections(base, config, *args.sections)
            if msgs:
                print('\n'.join(msgs), file=sys.stderr)
                return 1
            print('frei')
        elif args.cmd == 'gate':
            hits = changed_locked(base, config, args.base)
            for cid, sid in hits:
                print(f'Abschnitt {sid} ist ausgecheckt ({cid}) und darf nicht geändert werden; zuerst den Checkout beenden.',
                      file=sys.stderr)
            return 1 if hits else 0
        elif args.cmd == 'verify':
            found = verify(base, config)
            if args.json:
                print(json.dumps([{'id': en['id'], 'changed': ch} for en, ch in found], ensure_ascii=False))
            else:
                print(verify_text(found) or 'Keine Änderungen an ausgecheckten Abschnitten.', end='')
            return 1 if found else 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
