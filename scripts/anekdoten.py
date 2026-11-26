#!/usr/bin/env python3
"""Anekdoten und Erlebnisse sammeln und in Abschnitte einbauen (#643).

Eine Anekdote hält ein eigenes Erlebnis des Autors **im Original** fest (Originalnamen, Orte, Zeit). Anonymisiert oder
abgewandelt wird erst beim Einbau in einen Abschnitt; die Zuordnung Original ↔ Fassung im Buch bleibt am Eintrag
(`verwendungen`). Ebene: ein Buch (`anekdoten/<id>.yml` auf dem Buch-Branch) oder eine Reihe
(`series/<ser-id>/anekdoten/<id>.yml` auf dem Standard-Branch, für alle Bände sichtbar). Nur Eigentümer und Bearbeiter (#455);
Anekdoten kommen nie in Leser-Ansichten, Auflagen oder Exporte, nur als eingebaute Fassung im Text. Der Skript ändert nur
Dateien; committen tut der Assistent (START.md, „Anekdoten“).

  python3 scripts/anekdoten.py <buch> add --titel T --text TEXT [--kurzfassung K] [--person "Name:Rolle" …] [--ort O]
                               [--zeit Z] [--thema T …] [--quelle Q] [--von V] [--series <ser-id>] [--actor LOGIN]
  python3 scripts/anekdoten.py <buch> list [--state frei|eingeplant|verwendet] [--json]
  python3 scripts/anekdoten.py <buch> show <id>
  python3 scripts/anekdoten.py <buch> suggest (--section <sec-id> | --text "…[PLATZHALTER-ANEKDOTE: …]") [--json]
  python3 scripts/anekdoten.py <buch> plan <id> --section <sec-id>      (vormerken; --clear hebt es auf)
  python3 scripts/anekdoten.py <buch> use <id> --section <sec-id> --fassung anonymisiert|abgewandelt|original
                               --wahrheit woertlich|frei|anlass --einverstaendnis anonymisiert|liegt_vor|nicht_noetig
                               [--ersetzung "Original=Im Buch" …] [--notiz T] [--actor LOGIN]
  python3 scripts/anekdoten.py <buch> check                              (Hinweise für Auflage und Probedruck)

`use` hält fest, was der Benutzer in der Auswahlkarte bestätigt hat; der Text im Abschnitt entsteht als Vorschlag und wird
nur nach Bestätigung übernommen. Ist ein Eintrag schon verwendet (in einer Reihe auch in einem anderen Band), kommt eine Warnung.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

DIR = 'anekdoten'
ID_RE = re.compile(r'^anek-(\d{3,})(?:-[a-z0-9-]+)?$')
FASSUNG = ('anonymisiert', 'abgewandelt', 'original')
WAHRHEIT = ('woertlich', 'frei', 'anlass')
STAND = ('anonymisiert', 'liegt_vor', 'nicht_noetig')
MARKER = re.compile(r'\[PLATZHALTER-ANEKDOTE(?::\s*([^\]]*))?\]')
STOP = set('der die das und oder ein eine einer eines mit von zu im in am an auf für den dem des ist sind war wurde nicht auch als wie bei aus nach über um es sich sie er wir ich the and for of to a'.split())


def slug(text):
    t = (text or '').translate(str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue', 'ß': 'ss'}))
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')[:40].strip('-')


def now():
    return datetime.date.today().isoformat()


def read_yaml(path):
    try:
        data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def write_yaml(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')


def config(base):
    return read_yaml(Path(base) / 'ghostwriter.yml') or {}


def book_name(base):
    project = config(base).get('project') or {}
    return str(project.get('title_short') or project.get('working_title') or project.get('title') or Path(base).resolve().name)


def folder(base, series=None):
    return Path(base) / ('series/' + series + '/' + DIR if series else DIR)


def require_author(base, actor):
    """Nur Eigentümer und Bearbeiter (#455); ohne `team` gilt jeder mit Schreibrecht als Eigentümer."""
    import team
    if actor is None:
        return
    info = team.role(base, config(base), actor)
    if not info['write']:
        raise ValueError(f'Anekdoten bearbeiten dürfen nur Eigentümer und Bearbeiter (du bist: {info["role_text"]}).')


def series_entries(base):
    """Anekdoten der Reihe des Buchs (vom Standard-Branch), wenn das Buch zu einer Reihe gehört: [(Eintrag, Pfad)]."""
    try:
        import series
        src = series.source(base)
        if src is None:
            return []
        s, _ = series.of(series.load_all(base, src), series.branch_of(base) or '')
        if not s:
            return []
        out = []
        prefix = f'series/{s["id"]}/{DIR}/'
        for rel in src.files():
            if rel.startswith(prefix) and rel.endswith('.yml'):
                try:
                    data = yaml.safe_load(src.read(rel))
                except yaml.YAMLError:
                    continue
                if isinstance(data, dict):
                    data['_series'] = s['id']
                    out.append((data, rel))
        return out
    except Exception:   # noqa: BLE001 – ohne lesbare Reihe gibt es nur die Anekdoten des Buchs
        return []


def entries(base, series_id=None):
    """Alle sichtbaren Anekdoten: [(Eintrag, relativer Pfad)], Buch zuerst, dann die der Reihe."""
    out = []
    if series_id:
        for p in sorted(folder(base, series_id).glob('anek-*.yml')):
            d = read_yaml(p)
            if d:
                d['_series'] = series_id
                out.append((d, str(p.relative_to(base))))
        return out
    for p in sorted(folder(base).glob('anek-*.yml')):
        d = read_yaml(p)
        if d:
            out.append((d, str(p.relative_to(base))))
    return out + series_entries(base)


def state(entry):
    if entry.get('verwendungen'):
        return 'verwendet'
    return 'eingeplant' if entry.get('eingeplant_fuer') else 'frei'


def find(base, anek_id, series_id=None):
    hits = [(e, p) for e, p in entries(base, series_id) if e.get('id') == anek_id or str(e.get('id', '')).startswith(anek_id + '-')]
    if len(hits) != 1:
        raise ValueError(f'Anekdote nicht eindeutig gefunden: {anek_id}' if hits else f'Anekdote nicht gefunden: {anek_id}')
    return hits[0]


def next_id(base, title, series_id=None):
    nums = [int(m.group(1)) for e, _ in entries(base, series_id) if (m := ID_RE.match(str(e.get('id', ''))))]
    return f'anek-{max(nums, default=0) + 1:03d}-{slug(title) or "ohne-titel"}'


def validate(data):
    import jsonschema
    schema = json.loads((ROOT / 'schemas' / 'anecdote.schema.json').read_text(encoding='utf-8'))
    clean = {k: v for k, v in data.items() if not k.startswith('_')}
    jsonschema.validate(clean, schema)


def add(base, titel, text, kurzfassung=None, personen=None, ort=None, zeit=None, themen=None, quelle=None, von=None,
        series_id=None, actor=None):
    """Erfassen: der Text bleibt, wie der Autor ihn erzählt hat."""
    require_author(base, actor)
    if not (titel or '').strip() or not (text or '').strip():
        raise ValueError('Titel und Text der Anekdote angeben.')
    if series_id:
        import series
        if not series.series_file(base, series_id).is_file():
            raise ValueError(f'Reihe {series_id} nicht gefunden (Reihen-Anekdoten liegen auf dem Standard-Branch).')
    data = {'id': next_id(base, titel, series_id), 'titel': titel.strip()}
    if kurzfassung:
        data['kurzfassung'] = kurzfassung.strip()
    data['text'] = text.strip('\n')
    people = []
    for p in personen or []:
        name, _, rolle = str(p).partition(':')
        if name.strip():
            people.append({'name': name.strip(), **({'rolle': rolle.strip()} if rolle.strip() else {})})
    for key, val in (('personen', people), ('ort', ort), ('zeit', zeit), ('themen', [t.strip() for t in themen or [] if t.strip()]),
                     ('quelle', quelle)):
        if val:
            data[key] = val
    data['erfasst_am'] = now()
    if von:
        data['von'] = von
    validate(data)
    path = folder(base, series_id) / (data['id'] + '.yml')
    write_yaml(path, data)
    return path, data


def words(text):
    return {w for w in re.findall(r'[a-zäöüß0-9]{4,}', (text or '').lower()) if w not in STOP}


def section_id(base, section):
    """Abschnitt als Kennung (sec-…) oder sichtbare Nummer (1.2) → Kennung; Unbekanntes bleibt, wie es ist."""
    s = str(section or '').strip()
    if not re.fullmatch(r'\d+\.\d+', s):
        return s
    ci, si = (int(x) for x in s.split('.'))
    chapters = (config(base).get('structure') or {}).get('chapters') or []
    try:
        return chapters[ci - 1]['sections'][si - 1]['id']
    except (IndexError, KeyError, TypeError):
        raise ValueError(f'Abschnitt {s} nicht gefunden.')


def suggest(base, section=None, text=''):
    """Freie Einträge, die zu Abschnitt bzw. Platzhalter passen (Themen, Personen, Ort, Zeit, Wörter); lesend.
    Verwendete Einträge erscheinen nicht, eingeplante nur für ihren Abschnitt."""
    context = text or ''
    section = section_id(base, section) if section else section
    if section:
        cfg = config(base)
        for ch in (cfg.get('structure') or {}).get('chapters') or []:
            for sec in ch.get('sections') or []:
                if sec.get('id') == section:
                    p = Path(base) / sec.get('path', '')
                    context += '\n' + sec.get('title', '') + '\n' + (p.read_text(encoding='utf-8') if p.is_file() else '')
        if not context.strip():
            raise ValueError(f'Abschnitt {section} nicht gefunden.')
    m = MARKER.search(context)
    focus = words(m.group(1) if m and m.group(1) else '')
    ctx_words = words(context)
    ranked = []
    for e, path in entries(base):
        st = state(e)
        if st == 'verwendet' or (st == 'eingeplant' and section and e.get('eingeplant_fuer') != section):
            continue
        own = words(' '.join([e.get('titel', ''), e.get('kurzfassung', ''), ' '.join(e.get('themen') or []), e.get('ort', ''),
                              e.get('zeit', ''), ' '.join(p.get('name', '') for p in e.get('personen') or [])]))
        score = 3 * len(own & focus) + len(own & ctx_words) + (5 if e.get('eingeplant_fuer') == section and section else 0)
        if score:
            ranked.append({'id': e['id'], 'titel': e['titel'], 'score': score, 'state': st, 'path': path,
                           'series': e.get('_series') or '', 'passt': sorted((own & focus) | (own & ctx_words))[:6]})
    return sorted(ranked, key=lambda r: (-r['score'], r['id']))


def plan(base, anek_id, section=None, clear=False, actor=None):
    require_author(base, actor)
    entry, rel = find(base, anek_id)
    if entry.get('_series') and not (Path(base) / rel).is_file():
        raise ValueError('Reihen-Anekdoten werden auf dem Standard-Branch geändert (--series).')
    if clear:
        entry['eingeplant_fuer'] = None
    elif section:
        entry['eingeplant_fuer'] = section_id(base, section)
    else:
        raise ValueError('--section angeben oder --clear.')
    validate(entry)
    write_yaml(Path(base) / rel, {k: v for k, v in entry.items() if not k.startswith('_')})
    return entry


def use(base, anek_id, section, fassung, wahrheit, einverstaendnis, ersetzungen=None, notiz=None, actor=None, series_id=None):
    """Verwendung festhalten (nach Bestätigung der Auswahlkarte). Gibt (Eintrag, Warnungen) zurück."""
    require_author(base, actor)
    if fassung not in FASSUNG or wahrheit not in WAHRHEIT or einverstaendnis not in STAND:
        raise ValueError(f'Fassung: {", ".join(FASSUNG)}; Wahrheitsgehalt: {", ".join(WAHRHEIT)}; Einverständnis: {", ".join(STAND)}')
    section = section_id(base, section)
    entry, rel = find(base, anek_id, series_id)
    path = Path(base) / rel
    if not path.is_file():
        raise ValueError('Eine Reihen-Anekdote wird auf dem Standard-Branch festgehalten (--series <ser-id>).')
    book = book_name(base)
    warnings = []
    for u in entry.get('verwendungen') or []:
        if u.get('abschnitt') == section and u.get('buch') == book:
            raise ValueError(f'Schon in {section} verwendet ({u.get("am")}); nichts doppelt festhalten.')
        warnings.append(f'Schon verwendet: {u.get("buch")}, {u.get("abschnitt")} ({u.get("fassung")}, {u.get("am")})')
    if fassung == 'original' and einverstaendnis == 'anonymisiert':
        raise ValueError('Fassung „original“ kann nicht „anonymisiert“ sein: Einverständnis „liegt_vor“ oder „nicht_noetig“ mit Notiz wählen.')
    if einverstaendnis == 'nicht_noetig' and not (notiz or '').strip():
        raise ValueError('„nicht_noetig“ braucht eine Begründung (--notiz).')
    reps = []
    for r in ersetzungen or []:
        orig, sep, im = str(r).partition('=')
        if not sep or not orig.strip() or not im.strip():
            raise ValueError(f'Ersetzung als „Original=Im Buch“ angeben, nicht: {r}')
        reps.append({'original': orig.strip(), 'im_buch': im.strip()})
    if fassung in ('anonymisiert', 'abgewandelt') and not reps and entry.get('personen'):
        warnings.append('Keine Ersetzungen angegeben, obwohl der Eintrag Personen nennt: Namen im Text prüfen.')
    use_ = {'abschnitt': section, 'buch': book, 'fassung': fassung, 'wahrheit': wahrheit}
    if reps:
        use_['ersetzungen'] = reps
    use_['einverstaendnis'] = {'stand': einverstaendnis, **({'notiz': notiz.strip()} if (notiz or '').strip() else {})}
    use_['am'] = now()
    entry.setdefault('verwendungen', []).append(use_)
    entry['eingeplant_fuer'] = None
    validate(entry)
    write_yaml(path, {k: v for k, v in entry.items() if not k.startswith('_')})
    return entry, warnings


def check(base):
    """Hinweise für Auflage und Probedruck: Verwendung `original` ohne Einverständnisvermerk (oder „anonymisiert“)."""
    out = []
    for e, path in entries(base):
        for u in e.get('verwendungen') or []:
            if u.get('buch') != book_name(base):
                continue
            stand = (u.get('einverstaendnis') or {}).get('stand')
            if u.get('fassung') == 'original' and stand not in ('liegt_vor', 'nicht_noetig'):
                out.append(f'{e["id"]} in {u.get("abschnitt")}: Original ohne Einverständnisvermerk')
    return out


def line(e):
    n = len(e.get('verwendungen') or [])
    return (f'{e["id"]} · {state(e)}' + (f' ({e["eingeplant_fuer"]})' if e.get('eingeplant_fuer') else '') + f' · {e["titel"]}'
            + (f' · Themen: {", ".join(e["themen"])}' if e.get('themen') else '') + (f' · {n} Verwendung(en)' if n else '')
            + (f' · Reihe {e["_series"]}' if e.get('_series') else ''))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('base')
    ap.add_argument('cmd', choices=['add', 'list', 'show', 'suggest', 'plan', 'use', 'check'])
    ap.add_argument('id', nargs='?')
    ap.add_argument('--titel')
    ap.add_argument('--text')
    ap.add_argument('--kurzfassung')
    ap.add_argument('--person', action='append', default=[])
    ap.add_argument('--ort')
    ap.add_argument('--zeit')
    ap.add_argument('--thema', action='append', default=[])
    ap.add_argument('--quelle')
    ap.add_argument('--von')
    ap.add_argument('--series')
    ap.add_argument('--actor')
    ap.add_argument('--state', choices=['frei', 'eingeplant', 'verwendet'])
    ap.add_argument('--section')
    ap.add_argument('--clear', action='store_true')
    ap.add_argument('--fassung')
    ap.add_argument('--wahrheit')
    ap.add_argument('--einverstaendnis')
    ap.add_argument('--ersetzung', action='append', default=[])
    ap.add_argument('--notiz')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    base = Path(a.base)
    try:
        if a.cmd == 'add':
            path, data = add(base, a.titel, a.text, a.kurzfassung, a.person, a.ort, a.zeit, a.thema, a.quelle, a.von, a.series, a.actor)
            print(path.relative_to(base))
        elif a.cmd == 'list':
            rows = [e for e, _ in entries(base, a.series) if not a.state or state(e) == a.state]
            if a.json:
                print(json.dumps([{'id': e['id'], 'titel': e['titel'], 'state': state(e), 'eingeplant_fuer': e.get('eingeplant_fuer'),
                                   'themen': e.get('themen') or [], 'series': e.get('_series') or ''} for e in rows], ensure_ascii=False, indent=1))
            else:
                print('\n'.join(f'- {line(e)}' for e in rows) or '- Keine Anekdoten.')
        elif a.cmd == 'show':
            if not a.id:
                raise ValueError('Kennung angeben.')
            e, _ = find(base, a.id, a.series)
            print(yaml.safe_dump({k: v for k, v in e.items() if not k.startswith('_')}, allow_unicode=True, sort_keys=False, width=10**6))
        elif a.cmd == 'suggest':
            if not a.section and not a.text:
                raise ValueError('--section oder --text angeben.')
            rows = suggest(base, a.section, a.text or '')
            print(json.dumps(rows, ensure_ascii=False, indent=1) if a.json else
                  '\n'.join(f'- {r["id"]} ({r["score"]}): {r["titel"]} [{", ".join(r["passt"])}]' for r in rows) or '- Keine passende freie Anekdote.')
        elif a.cmd == 'plan':
            if not a.id:
                raise ValueError('Kennung angeben.')
            e = plan(base, a.id, a.section, a.clear, a.actor)
            print(line(e))
        elif a.cmd == 'use':
            if not (a.id and a.section and a.fassung and a.wahrheit and a.einverstaendnis):
                raise ValueError('Kennung, --section, --fassung, --wahrheit und --einverstaendnis angeben.')
            e, warnings = use(base, a.id, a.section, a.fassung, a.wahrheit, a.einverstaendnis, a.ersetzung, a.notiz, a.actor, a.series)
            for w in warnings:
                print(f'Warnung: {w}')
            print(line(e))
        else:
            hints = check(base)
            print('\n'.join(f'- {h}' for h in hints) or 'Keine Hinweise.')
            return 1 if hints else 0
        return 0
    except ValueError as e:
        print(f'::error::{e}')
        return 2
    except Exception as e:   # noqa: BLE001 – Schemafehler u. a. verständlich melden
        if e.__class__.__name__ == 'ValidationError':
            print(f'::error::Ungültige Anekdote: {getattr(e, "message", e)}')
            return 2
        raise


if __name__ == '__main__':
    sys.exit(main())
