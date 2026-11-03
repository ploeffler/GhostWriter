#!/usr/bin/env python3
"""Serien: mehrere Bücher einer Bibliothek als Reihe mit Bänden (#116).

Aufruf (im Standard-Branch der Bibliothek):
  python scripts/series.py <repo> list [--json]
  python scripts/series.py <repo> create "<Titel>" [--subtitle U] [--kind continuous|standalone]
                                  [--description D] [--books buch/a buch/b …]
  python scripts/series.py <repo> update <ser-id> [--title …] [--subtitle …] [--kind …] [--description …]
  python scripts/series.py <repo> add <ser-id> <buch-branch> [--position N]
  python scripts/series.py <repo> remove <ser-id> <buch-branch>
  python scripts/series.py <repo> reorder <ser-id> <buch-branch> …   neue Reihenfolge aller Bände
  python scripts/series.py <repo> of <buch-branch>                    zu welcher Serie gehört das Buch?

Eine Serie liegt auf dem Standard-Branch unter series/<ser-id>/series.yml
(Schema schemas/series.schema.json): Titel, Untertitel, Art (continuous =
durchgehende Handlung, standalone = eigenständige Bände), Beschreibung und die
Bände als Liste der Buch-Branches in Bandreihenfolge (Band 1 = erster Eintrag).
Das Buch selbst speichert keine Zugehörigkeit; so gibt es nur eine Quelle.

Regeln (entschieden in #116):
  - Serien gibt es nur in Bibliotheken: Hat der Standard-Branch Kapitel
    (Einzelbuch), lehnt das Skript ab (vorher umwandeln, #40).
  - Ein Buch gehört zu höchstens einer Serie.

Lesen von einem Buch-Branch aus: load_all(base) liest series/ im Ordner, sonst
mit git vom Standard-Branch (origin/<standard> bzw. <standard>), sonst aus
GHOSTWRITER_SERIES_DIR. Ein Buch-Branch enthält series/ nicht: library.py new
--create entfernt den Ordner im Commit „Neues Buch angelegt“.

Die Commits schreibt der Assistent bzw. die Action direkt auf den
Standard-Branch (START.md, „Serien“); das Skript ändert nur Dateien.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import library  # noqa: E402

KINDS = {'continuous': 'durchgehende Handlung', 'standalone': 'eigenständige Bände'}
SERIES_DIR = 'series'


def series_file(base, sid):
    return Path(base) / SERIES_DIR / sid / 'series.yml'


def _git(base, *args):
    r = subprocess.run(['git', *args], cwd=base, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def load_all(base):
    """{ser-id: serie} aus series/ im Ordner, sonst vom Standard-Branch über git, sonst GHOSTWRITER_SERIES_DIR."""
    base = Path(base)
    for d in [base / SERIES_DIR] + ([Path(os.environ['GHOSTWRITER_SERIES_DIR'])] if os.environ.get('GHOSTWRITER_SERIES_DIR') else []):
        if d.is_dir():
            out = {}
            for p in sorted(d.glob('*/series.yml')):
                s = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
                out[s.get('id', p.parent.name)] = s
            return out
    if _git(base, 'rev-parse', '--git-dir') is None:
        return {}
    default = library.default_branch(base)
    refs = (f'origin/{default}', default) if default else ('origin/HEAD', 'origin/main', 'main')
    for ref in refs:
        listing = _git(base, 'ls-tree', '-r', '--name-only', ref, '--', SERIES_DIR)
        if listing is None:
            continue
        out = {}
        for path in sorted(listing.split()):
            if path.endswith('/series.yml'):
                s = yaml.safe_load(_git(base, 'show', f'{ref}:{path}') or '') or {}
                out[s.get('id', path.split('/')[1])] = s
        return out
    return {}


def volumes(s):
    return list(s.get('volumes') or [])


def of(all_series, branch):
    """(serie, bandnummer) des Buchs oder (None, None)."""
    for s in all_series.values():
        vols = volumes(s)
        if branch in vols:
            return s, vols.index(branch) + 1
    return None, None


def save(base, s):
    p = series_file(base, s['id'])
    p.parent.mkdir(parents=True, exist_ok=True)
    keys = ['id', 'title', 'subtitle', 'kind', 'description', 'volumes']
    data = {k: s[k] for k in keys if k in s and (s[k] or k in ('id', 'title', 'kind', 'volumes'))}
    data.update({k: v for k, v in s.items() if k not in keys})
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')
    return p


def require_library(base):
    """Serien nur in Bibliotheken: Der Standard-Branch (dieser Ordner) darf kein Buch sein."""
    cfg_path = Path(base) / 'ghostwriter.yml'
    cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {} if cfg_path.is_file() else {}
    if library.has_chapters(cfg):
        raise SystemExit('Serien gibt es nur in einer Bibliothek. Dieses Repository ist ein Einzelbuch; '
                         'erst umwandeln (Actions → In Bibliothek umwandeln, docs/UPDATES.md).')


def known_books(base):
    """Branches der Bücher (live aus git); None, wenn sich das nicht ermitteln lässt (dann keine Prüfung)."""
    try:
        found = library.books(library.branch_configs(cwd=base), library.load_manifest(), library.default_branch(base))
        found += [b for b in library.books(library.branch_configs('refs/heads', base), library.load_manifest(),
                                           library.default_branch(base)) if b['branch'] not in {x['branch'] for x in found}]
    except Exception:   # noqa: BLE001
        return None
    return {b['branch'] for b in found} or None


def check_book(base, all_series, branch, sid=None):
    books = known_books(base)
    if books is not None and branch not in books:
        raise SystemExit(f'„{branch}“ ist kein Buch dieser Bibliothek')
    other, _ = of(all_series, branch)
    if other and other['id'] != sid:
        raise SystemExit(f'„{branch}“ gehört schon zur Serie „{other["title"]}“; ein Buch gehört zu höchstens einer Serie.')
    if other and other['id'] == sid:
        raise SystemExit(f'„{branch}“ ist schon Band {volumes(other).index(branch) + 1} dieser Serie')


def create(base, title, subtitle='', kind='continuous', description='', books=()):
    require_library(base)
    if not (title or '').strip():
        raise SystemExit('Titel der Serie fehlt')
    if kind not in KINDS:
        raise SystemExit(f'Art: {", ".join(KINDS)}')
    all_s = load_all(base)
    sid = 'ser-' + (library.slug(title)[:40].strip('-') or 'serie')
    if sid in all_s:
        raise SystemExit(f'Es gibt schon eine Serie „{all_s[sid]["title"]}“ ({sid})')
    s = {'id': sid, 'title': title.strip(), 'subtitle': (subtitle or '').strip(), 'kind': kind,
         'description': (description or '').strip(), 'volumes': []}
    for b in books:
        check_book(base, {**all_s, sid: s}, b, sid)
        s['volumes'].append(b)
    save(base, s)
    return s


def get(base, sid):
    all_s = load_all(base)
    if sid not in all_s:
        # auch über den Titel finden
        hit = [s for s in all_s.values() if s.get('title', '').lower() == (sid or '').lower()]
        if not hit:
            raise SystemExit(f'Serie „{sid}“ nicht gefunden')
        return hit[0], all_s
    return all_s[sid], all_s


def update(base, sid, fields):
    require_library(base)
    s, _ = get(base, sid)
    for k in ('title', 'subtitle', 'description'):
        if fields.get(k) is not None:
            s[k] = str(fields[k]).strip()
    if fields.get('kind'):
        if fields['kind'] not in KINDS:
            raise SystemExit(f'Art: {", ".join(KINDS)}')
        s['kind'] = fields['kind']
    if not s.get('title'):
        raise SystemExit('Titel der Serie fehlt')
    save(base, s)   # die ID bleibt beim Umbenennen gleich
    return s


def add(base, sid, branch, position=None):
    require_library(base)
    s, all_s = get(base, sid)
    check_book(base, all_s, branch, s['id'])
    vols = volumes(s)
    pos = len(vols) if not position else max(0, min(len(vols), int(position) - 1))
    vols.insert(pos, branch)
    s['volumes'] = vols
    save(base, s)
    return s, pos + 1


def remove(base, sid, branch):
    require_library(base)
    s, _ = get(base, sid)
    vols = volumes(s)
    if branch not in vols:
        raise SystemExit(f'„{branch}“ ist kein Band dieser Serie')
    vols.remove(branch)
    s['volumes'] = vols
    save(base, s)
    return s


def reorder(base, sid, order):
    require_library(base)
    s, _ = get(base, sid)
    if sorted(order) != sorted(volumes(s)):
        raise SystemExit('Neue Reihenfolge muss genau die Bände der Serie enthalten')
    s['volumes'] = list(order)
    save(base, s)
    return s


def problems(base, all_series=None, books=None):
    """Prüfung für validate_project (Standard-Branch): Schema, eindeutige Zuordnung, nur in Bibliotheken."""
    base = Path(base)
    if not (base / SERIES_DIR).is_dir():
        return []
    errors = []
    from jsonschema import Draft202012Validator
    schema = json.loads((ROOT / 'schemas' / 'series.schema.json').read_text(encoding='utf-8'))
    seen = {}
    cfg_path = base / 'ghostwriter.yml'
    cfg = (yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {}) if cfg_path.is_file() else {}
    if library.has_chapters(cfg):
        errors.append(f'{SERIES_DIR}/: Serien gibt es nur in einer Bibliothek, dieses Repository ist ein Einzelbuch')
    for p in sorted((base / SERIES_DIR).glob('*/series.yml')):
        rel = p.relative_to(base)
        s = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
        for e in Draft202012Validator(schema).iter_errors(s):
            errors.append(f'{rel}: {"/".join(map(str, e.absolute_path)) or "(Wurzel)"}: {e.message}')
        if s.get('id') and s['id'] != p.parent.name:
            errors.append(f'{rel}: id {s["id"]} passt nicht zum Ordner {p.parent.name}')
        vols = volumes(s)
        if len(set(vols)) != len(vols):
            errors.append(f'{rel}: ein Buch steht mehrfach in der Serie')
        for b in vols:
            if b in seen and seen[b] != s.get('id'):
                errors.append(f'{rel}: {b} gehört schon zur Serie {seen[b]}; ein Buch gehört zu höchstens einer Serie')
            seen.setdefault(b, s.get('id'))
            if books is not None and b not in books:
                errors.append(f'{rel}: {b} ist kein Buch dieser Bibliothek')
    return errors


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('repo')
    ap.add_argument('cmd', choices=['list', 'create', 'update', 'add', 'remove', 'reorder', 'of'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--subtitle')
    ap.add_argument('--kind')
    ap.add_argument('--description')
    ap.add_argument('--title')
    ap.add_argument('--books', nargs='*', default=[])
    ap.add_argument('--position', type=int)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv[1:])
    base = Path(a.repo)
    if a.cmd == 'list':
        all_s = load_all(base)
        if a.json:
            print(json.dumps(list(all_s.values()), ensure_ascii=False, indent=2))
        for s in all_s.values() if not a.json else []:
            print(f'{s["id"]:<32} {s["title"]}  ({len(volumes(s))} Bände: {", ".join(volumes(s)) or "–"})')
        if not all_s and not a.json:
            print('keine Serien')
        return 0
    if a.cmd == 'of':
        s, n = of(load_all(base), (a.args or [''])[0])
        print(f'Band {n} der Serie „{s["title"]}“ ({s["id"]})' if s else 'gehört zu keiner Serie')
        return 0 if s else 1
    if a.cmd == 'create':
        s = create(base, (a.args or [a.title or ''])[0], a.subtitle or '', a.kind or 'continuous', a.description or '', a.books)
        print(f'✓ Serie „{s["title"]}“ angelegt: {series_file(".", s["id"])}' + (f' mit {len(s["volumes"])} Bänden' if s['volumes'] else ''))
        print(f'Commit-Nachricht: Serie „{s["title"]}“ angelegt')
        return 0
    if not a.args:
        ap.error('Serie fehlt')
    sid = a.args[0]
    if a.cmd == 'update':
        s = update(base, sid, {'title': a.title, 'subtitle': a.subtitle, 'kind': a.kind, 'description': a.description})
        print(f'✓ Serie „{s["title"]}“ geändert\nCommit-Nachricht: Serie „{s["title"]}“ geändert')
    elif a.cmd == 'add':
        if len(a.args) < 2:
            ap.error('add braucht Serie und Buch-Branch')
        s, n = add(base, sid, a.args[1], a.position)
        print(f'✓ {a.args[1]} ist Band {n} von „{s["title"]}“\nCommit-Nachricht: Band {n} zur Serie „{s["title"]}“ hinzugefügt')
    elif a.cmd == 'remove':
        if len(a.args) < 2:
            ap.error('remove braucht Serie und Buch-Branch')
        s = remove(base, sid, a.args[1])
        print(f'✓ {a.args[1]} aus „{s["title"]}“ entfernt\nCommit-Nachricht: Band aus der Serie „{s["title"]}“ entfernt')
    elif a.cmd == 'reorder':
        s = reorder(base, sid, a.args[1:])
        print(f'✓ Reihenfolge von „{s["title"]}“ geändert\nCommit-Nachricht: Bandreihenfolge der Serie „{s["title"]}“ geändert')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
