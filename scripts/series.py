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
  python scripts/series.py <repo> term-set <ser-id> "<Begriff>" "<Erklärung>"   Begriff der Serie (glossary.yml)
  python scripts/series.py <repo> term-remove <ser-id> "<Begriff>"
  python scripts/series.py <buch> context [<buch-branch>]             „Was bisher geschah“ aus den Vorbänden

Gemeinsame Inhalte (Stufe 2): Figuren unter series/<ser-id>/characters/ (wie
characters/ eines Buchs; bearbeiten mit scripts/characters.py series-add |
series-update), Begriffe in series/<ser-id>/glossary.yml (terms: [{term, text}]).
Sie gelten in jedem Band; ein Band kann eine Figur bzw. einen Begriff als eigene
Kopie führen (gleiche ID bzw. gleicher Begriff im Buch), die dann nur dort gilt.

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


class Source:
    """Lesezugriff auf series/: Ordner im Dateisystem oder ein Git-Stand (Standard-Branch)."""
    def __init__(self, base, root=None, ref=None):
        self.base, self.root, self.ref = Path(base), root, ref

    def files(self):
        if self.root is not None:
            return sorted(str(p.relative_to(self.root.parent)) for p in self.root.rglob('*') if p.is_file())
        out = _git(self.base, 'ls-tree', '-r', '--name-only', '-z', self.ref, '--', SERIES_DIR) or ''
        return sorted(x for x in out.split('\0') if x)

    def read(self, rel):
        if self.root is not None:
            return (self.root.parent / rel).read_text(encoding='utf-8')
        return _git(self.base, 'show', f'{self.ref}:{rel}')


def source(base):
    """Source für series/: im Ordner (Standard-Branch), GHOSTWRITER_SERIES_DIR, sonst Standard-Branch über git;
    None, wenn das ein Git-Repository ist, dessen Standard-Branch sich nicht lesen lässt."""
    base = Path(base)
    for d in [base / SERIES_DIR] + ([Path(os.environ['GHOSTWRITER_SERIES_DIR'])] if os.environ.get('GHOSTWRITER_SERIES_DIR') else []):
        if d.is_dir():
            return Source(base, root=d)
    if _git(base, 'rev-parse', '--git-dir') is None:
        return Source(base, root=base / SERIES_DIR)   # kein Git: keine Serien
    default = library.default_branch(base)
    refs = (f'origin/{default}', default) if default else ('origin/HEAD', 'origin/main', 'main')
    for ref in refs:
        if _git(base, 'rev-parse', '-q', '--verify', f'{ref}^{{commit}}'):
            return Source(base, ref=ref)
    return None


def load_all(base, src=None):
    """{ser-id: serie} vom Standard-Branch (siehe source)."""
    src = src or source(base)
    if src is None or (src.root is not None and not src.root.is_dir()):
        return {}
    out = {}
    for rel in src.files():
        parts = rel.split('/')
        if len(parts) == 3 and parts[2] == 'series.yml':
            s = yaml.safe_load(src.read(rel) or '') or {}
            out[s.get('id', parts[1])] = s
    return out


def branch_of(base):
    """Ausgecheckter Branch (in Actions GITHUB_HEAD_REF bzw. GITHUB_REF_NAME), sonst None."""
    b = (_git(base, 'rev-parse', '--abbrev-ref', 'HEAD') or '').strip()
    if b and b != 'HEAD':
        return b
    return os.environ.get('GITHUB_HEAD_REF') or os.environ.get('GITHUB_REF_NAME') or None


def characters(base, sid, src=None):
    """Figuren der Serie: [{id, name, path, _series, _text}] aus series/<sid>/characters/char-*.md."""
    src = src or source(base)
    if src is None or (src.root is not None and not src.root.is_dir()):
        return []
    out = []
    for rel in src.files():
        parts = rel.split('/')
        if len(parts) == 4 and parts[1] == sid and parts[2] == 'characters' and parts[3].endswith('.md'):
            text = src.read(rel) or ''
            m = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
            head = (yaml.safe_load(m.group(1)) or {}) if m else {}
            out.append({'id': head.get('id', parts[3][:-3]), 'name': head.get('name', parts[3][:-3]), 'path': rel,
                        '_series': sid, '_text': text})
    return out


def book_characters(base, branch=None):
    """Figuren der Serie des Buchs: (serie, [items]) bzw. (None, []); (None, None), wenn sich die Serie nicht lesen lässt."""
    src = source(base)
    if src is None:
        return None, None
    branch = branch or branch_of(base)
    if not branch:
        return None, []
    s, _ = of(load_all(base, src), branch)
    if not s:
        return None, []
    return s, characters(base, s['id'], src)


def glossary(base, sid, src=None):
    """Begriffe der Serie aus series/<sid>/glossary.yml: [{term, text}]."""
    src = src or source(base)
    if src is None or (src.root is not None and not src.root.is_dir()):
        return []
    rel = f'{SERIES_DIR}/{sid}/glossary.yml'
    if rel not in src.files():
        return []
    return list((yaml.safe_load(src.read(rel) or '') or {}).get('terms') or [])


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


# ---------- Begriffe der Serie (Stufe 2) ----------

def glossary_path(base, sid):
    return Path(base) / SERIES_DIR / sid / 'glossary.yml'


def term_key(term):
    return term.strip().casefold()


def term_set(base, sid, term, text):
    """Begriff der Serie aufnehmen bzw. ändern (series/<sid>/glossary.yml, sortiert nach DIN 5007-1)."""
    from render_view import german_key
    s, _ = get(base, sid)
    term, text = (term or '').strip(), (text or '').strip()
    if not term or not text:
        raise SystemExit('Begriff und Erklärung dürfen nicht leer sein')
    terms = [x for x in glossary(base, s['id'], Source(base, root=Path(base) / SERIES_DIR)) if term_key(x['term']) != term_key(term)]
    terms.append({'term': term, 'text': text})
    terms.sort(key=lambda x: german_key(x['term']))
    p = glossary_path(base, s['id'])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump({'terms': terms}, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')
    return s


def term_remove(base, sid, term):
    s, _ = get(base, sid)
    terms = glossary(base, s['id'], Source(base, root=Path(base) / SERIES_DIR))
    rest = [x for x in terms if term_key(x['term']) != term_key(term)]
    if len(rest) == len(terms):
        raise SystemExit(f'Begriff „{term}“ gibt es in der Serie nicht')
    glossary_path(base, s['id']).write_text(yaml.safe_dump({'terms': rest}, allow_unicode=True, sort_keys=False, width=10**6),
                                            encoding='utf-8')
    return s


def compare_terms(book_entries, series_terms):
    """Begriffe der Serie gegen das Glossar des Bandes: [{term, text, state, book_text}] mit state
    missing (nur in der Serie, gilt per Verweis), same (Kopie gleich), differs (Kopie weicht ab).
    Dazu die Begriffe nur im Buch: state own."""
    book = {term_key(t): (t, x) for t, x in book_entries}
    out = []
    for st in series_terms:
        hit = book.pop(term_key(st['term']), None)
        if hit is None:
            out.append({'term': st['term'], 'text': st['text'], 'state': 'missing', 'book_text': ''})
        else:
            out.append({'term': st['term'], 'text': st['text'], 'book_text': hit[1],
                        'state': 'same' if hit[1].strip() == st['text'].strip() else 'differs'})
    out += [{'term': t, 'text': '', 'book_text': x, 'state': 'own'} for t, x in book.values()]
    return out


# ---------- Kontinuität (Stufe 2) ----------

def _branch_file(base, branch, rel):
    for ref in (f'origin/{branch}', branch):
        text = _git(base, 'show', f'{ref}:{rel}')
        if text is not None:
            return text
    return None


def previous_volumes(base, branch=None):
    """Kurzfassung der Vorbände für Recherche und Ghostwriting: (serie, [{volume, branch, title, chapters:
    [{title, summary, goal}]}]) – nur die Bände vor diesem, gelesen aus ihren Branches."""
    src = source(base)
    branch = branch or branch_of(base)
    s, n = of(load_all(base, src), branch) if src else (None, None)
    if not s:
        return None, []
    out = []
    for i, br in enumerate(volumes(s)[:n - 1], start=1):
        cfg = yaml.safe_load(_branch_file(base, br, 'ghostwriter.yml') or '') or {}
        p = cfg.get('project') or {}
        chapters = []
        for ch in (cfg.get('structure') or {}).get('chapters') or []:
            readme = _branch_file(base, br, f'{ch["path"]}/README.md') or ''
            part = lambda name: (re.search(rf'(?ms)^## {name}\n\n(.*?)(?=^## |\Z)', readme) or [None, ''])[1].strip()
            summary, goal = part('Kurzbeschreibung'), part('Ziel des Kapitels')
            chapters.append({'title': ch.get('title', ''), 'summary': '' if summary == 'Offen.' else summary,
                             'goal': '' if goal == 'Offen.' else goal})
        out.append({'volume': i, 'branch': br, 'title': p.get('title') or p.get('working_title') or br, 'chapters': chapters})
    return s, out


def continuity_context(base, branch=None):
    """Markdown „Was bisher geschah“ (Kontext für Läufe in einem Band einer Serie); leer ohne Vorbände."""
    s, prev = previous_volumes(base, branch)
    if not prev:
        return ''
    out = [f'## Was bisher geschah – Serie „{s["title"]}“', '',
           'Kontext aus den Vorbänden. Widersprüche nicht still auflösen, sondern markieren: [KONTINUITÄT PRÜFEN: …].', '']
    for v in prev:
        out += [f'### Band {v["volume"]}: {v["title"]}', '']
        for ch in v['chapters']:
            line = f'- **{ch["title"]}**'
            if ch['summary']:
                line += f': {ch["summary"]}'
            elif ch['goal']:
                line += f' (Ziel: {ch["goal"]})'
            out.append(line)
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


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
        chars = sorted((p.parent / 'characters').glob('*.md')) if (p.parent / 'characters').is_dir() else []
        cschema = json.loads((ROOT / 'schemas' / 'character.schema.json').read_text(encoding='utf-8'))
        for cp in chars:   # Figuren der Serie (Stufe 2): Kopf wie im Buch
            m = re.match(r'\A---\n(.*?)\n---\n', cp.read_text(encoding='utf-8'), re.S)
            head = (yaml.safe_load(m.group(1)) or {}) if m else None
            if head is None:
                errors.append(f'{cp.relative_to(base)}: Kopf (--- … ---) fehlt')
                continue
            for e in Draft202012Validator(cschema).iter_errors(head):
                errors.append(f'{cp.relative_to(base)}: {"/".join(map(str, e.absolute_path)) or "(Kopf)"}: {e.message}')
            if head.get('id') != cp.stem:
                errors.append(f'{cp.relative_to(base)}: ID {head.get("id")} passt nicht zum Dateinamen')
        gp = p.parent / 'glossary.yml'
        if gp.is_file():
            terms = (yaml.safe_load(gp.read_text(encoding='utf-8')) or {}).get('terms') or []
            keys = [term_key(str(x.get('term', ''))) for x in terms]
            if any(not x.get('term') or not x.get('text') for x in terms):
                errors.append(f'{gp.relative_to(base)}: jeder Begriff braucht term und text')
            if len(set(keys)) != len(keys):
                errors.append(f'{gp.relative_to(base)}: Begriff doppelt')
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
    ap.add_argument('cmd', choices=['list', 'create', 'update', 'add', 'remove', 'reorder', 'of', 'term-set', 'term-remove',
                                    'context'])
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
    if a.cmd == 'context':
        sys.stdout.write(continuity_context(base, (a.args or [None])[0]) or 'Keine Vorbände.\n')
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
    elif a.cmd == 'term-set':
        if len(a.args) != 3:
            ap.error('term-set braucht Serie, Begriff und Erklärung')
        s = term_set(base, sid, a.args[1], a.args[2])
        print(f'✓ Begriff „{a.args[1]}“ in der Serie „{s["title"]}“\nCommit-Nachricht: Serie „{s["title"]}“: Begriff „{a.args[1]}“ eingetragen')
    elif a.cmd == 'term-remove':
        if len(a.args) != 2:
            ap.error('term-remove braucht Serie und Begriff')
        s = term_remove(base, sid, a.args[1])
        print(f'✓ Begriff „{a.args[1]}“ entfernt\nCommit-Nachricht: Serie „{s["title"]}“: Begriff „{a.args[1]}“ entfernt')
    elif a.cmd == 'reorder':
        s = reorder(base, sid, a.args[1:])
        print(f'✓ Reihenfolge von „{s["title"]}“ geändert\nCommit-Nachricht: Bandreihenfolge der Serie „{s["title"]}“ geändert')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
