#!/usr/bin/env python3
"""Bibliothek: mehrere Bücher in einem Repository, je Buch ein Branch (#36).

Aufruf (im Repository, braucht alle Branches: git fetch origin '+refs/heads/*:refs/remotes/origin/*'):
  python scripts/library.py list [--json]       Bücher der Bibliothek
  python scripts/library.py name "<Kurztitel>"  Branch-Name, Tag-Slug und ob er schon vergeben ist
  python scripts/library.py check               Kurztitel bzw. Tag-Slugs eindeutig? (Exit 1 bei Doppelten)
  python scripts/library.py build [--out library.json]   Übersicht der Bibliothek schreiben (#37)
  python scripts/library.py check-program      Hauptrepository: keine Buchinhalte (#48); Fehler bei
                                                Kapiteln/Auflagen auf dem Standard-Branch, Warnung
                                                bei Buch-Branches und Auflagen-Tags
  python scripts/library.py is <branch> [--dir .]  Ist dieser Branch ein Buch? (Exit 0 ja, 1 nein; liest
                                                ghostwriter.yml aus --dir, z. B. in einer Action)
  python scripts/library.py new "<Arbeitstitel>" [--short K] [--author A] [--create]
                                                Neues Buch (#38): prüft den Namen und zeigt den
                                                Branch; mit --create Branch buch/<slug> vom
                                                aktuellen Stand anlegen, ein Commit

library.json (Action „Bücherregal aktualisieren“, auf dem Standard-Branch): je Buch
Titel, Kurztitel, Branch, Status, Auflage, freigegebene Kapitel und Abschnitte,
KI-API-Kosten, offene Änderungen im Arbeits-Branch, letzter Commit, Datenversion,
„sofort übernehmen“, letzte Auflage (Tag); dazu Programmstand und, mit
SECRETS_PRESENT, welche Secrets hinterlegt sind (nur Namen, nie Werte; #71). Kein
Manuskripttext und kein Zeitstempel des Laufs, damit sich die Datei nur ändert,
wenn sich ein Buch ändert.

Benennung (ghostwriter-manifest.yml → library):
  Buch-Branch     buch/<slug>                 slug aus dem Kurztitel, wie der Tag-Slug der Auflagen
  Arbeits-Branch  ghostwriter/<buch-branch>   z. B. ghostwriter/buch/adhs

Erkennungsregel, einheitlich für Bücherregal, Update-Action und Wiedereinstieg:
  0. Der Standard-Branch ist ein Buch, wenn er Kapitel hat (Einzelbuch), sonst nicht
     (Bibliothek: nur Programm und Starter; im Hauptrepository main).
  1. Branches aus update.skip_branches sind nie Bücher (Arbeits-, Versions-, Bot-Branches).
  2. Jeder buch/*-Branch ist ein Buch, auch ohne Kapitel (neu angelegt, Wizard läuft).
  3. Jeder andere Branch mit Kapiteln (structure.chapters) ist ein Buch (Altbestand,
     Einzelbuch auf dem Standard-Branch, test/test-book).
Bibliotheksmodus: Der Standard-Branch hat keine Kapitel (nur Programm und Starter).
Einzelbuch: Der Standard-Branch ist selbst das Buch (bisheriger Weg, bleibt gültig).
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = 'ghostwriter-manifest.yml'
DEFAULTS = {'book_prefix': 'buch/', 'work_prefix': 'ghostwriter/'}


def slug(text):
    """Wie der Tag-Slug der Auflagen (render_view.tag_slug): klein, ASCII, Bindestriche."""
    t = (text or '').translate(str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue', 'ß': 'ss'}))
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')


def settings(manifest):
    s = dict(DEFAULTS)
    s.update((manifest or {}).get('library') or {})
    s['skip'] = ((manifest or {}).get('update') or {}).get('skip_branches') or []
    return s


def book_branch(title_short, manifest=None):
    return settings(manifest)['book_prefix'] + slug(title_short)


def work_branch(branch, manifest=None):
    return settings(manifest)['work_prefix'] + branch


def short_title(config):
    p = (config or {}).get('project') or {}
    return p.get('title_short') or p.get('title') or p.get('working_title') or ''


def has_chapters(config):
    return bool(((config or {}).get('structure') or {}).get('chapters'))


def default_branch(cwd=ROOT):
    """Standard-Branch: GHOSTWRITER_DEFAULT_BRANCH (Actions), sonst origin/HEAD, sonst None."""
    import os
    env = os.environ.get('GHOSTWRITER_DEFAULT_BRANCH')
    if env:
        return env
    head = git('symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD', cwd=cwd).strip()
    return head.split('/', 1)[1] if '/' in head else None


def is_book(name, config, manifest=None, default=None):
    """Erkennungsregel (siehe oben). config = ghostwriter.yml des Branchs (dict, None = fehlt).
    default = Standard-Branch: Er ist ein Buch, wenn er Kapitel hat (Einzelbuch), auch wenn er in skip_branches steht."""
    s = settings(manifest)
    if default and name == default:
        return has_chapters(config)
    if any(fnmatch.fnmatch(name, pat) for pat in s['skip']):
        return False
    if name.startswith(s['book_prefix']):
        return config is not None
    return has_chapters(config)


def describe(name, config, manifest=None):
    p = (config or {}).get('project') or {}
    short = short_title(config)
    return {'branch': name, 'title': p.get('title') or p.get('working_title') or '', 'title_short': short,
            'slug': slug(short), 'status': 'ready' if has_chapters(config) else 'setup',
            'current_edition': p.get('current_edition', 0) or 0,
            'work_branch': work_branch(name, manifest)}


def books(branch_configs, manifest=None, default=None):
    """branch_configs: {branch: config|None} -> Liste der Bücher (sortiert nach Branch)."""
    return [describe(n, c, manifest) for n, c in sorted(branch_configs.items()) if is_book(n, c, manifest, default)]


def duplicates(book_list):
    """{slug: [branches]} für Kurztitel, die mehr als ein Buch hat (Auflagen-Tags wären nicht eindeutig)."""
    seen = {}
    for b in book_list:
        if b['slug']:
            seen.setdefault(b['slug'], []).append(b['branch'])
    return {k: v for k, v in seen.items() if len(v) > 1}


def name_check(title_short, book_list, manifest=None):
    """Branch-Name und Tag-Slug für ein neues Buch; taken = Liste der Gründe, warum er vergeben ist."""
    s = slug(title_short)
    branch = book_branch(title_short, manifest)
    taken = []
    if not s:
        taken.append('Kurztitel ergibt keinen Namen (nur Sonderzeichen)')
    for b in book_list:
        if b['branch'] == branch:
            taken.append(f'Branch {branch} gibt es schon')
        elif s and b['slug'] == s:
            taken.append(f'Kurztitel wie bei {b["branch"]} (Auflagen-Tags wären nicht eindeutig)')
    return {'branch': branch, 'slug': s, 'work_branch': work_branch(branch, manifest), 'taken': taken}


# ---------- Git ----------

def git(*args, cwd=ROOT):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True).stdout


def branch_configs(namespace='refs/remotes/origin', cwd=ROOT):
    """{branch: ghostwriter.yml als dict oder None} für alle Branches unter namespace."""
    out = {}
    for ref in git('for-each-ref', '--format=%(refname)', namespace, cwd=cwd).split():
        name = ref[len(namespace) + 1:]
        if name == 'HEAD':
            continue
        text = subprocess.run(['git', 'show', f'{ref}:ghostwriter.yml'], cwd=cwd, capture_output=True, text=True)
        try:
            out[name] = (yaml.safe_load(text.stdout) or {}) if text.returncode == 0 else None
        except yaml.YAMLError:
            out[name] = None
    return out


def book_stats(ref, cwd=ROOT):
    """Kennzahlen eines Buch-Branchs aus einem temporären Worktree (wie die Übersichtsdatei)."""
    import shutil
    import tempfile
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_index
    from render_view import load
    tmp = tempfile.mkdtemp(prefix='gw-lib-')
    try:
        subprocess.run(['git', 'worktree', 'add', '-q', '--detach', tmp, ref], cwd=cwd, check=True, capture_output=True)
        base, config = load(tmp)
        import migrate_project
        dv = migrate_project.get_version(base)
        extra = {'data_version': dv, 'migration_pending': dv < migrate_project.DATA_VERSION,
                 'auto_merge': (config.get('changes') or {}).get('auto_merge') is True,
                 'secret_names': sorted(build_index.secret_names(config))}
        if not has_chapters(config):
            return {'chapters_total': 0, 'chapters_approved': 0, 'sections_total': 0, 'sections_approved': 0,
                    'cost': build_index.cost(0, False), **extra}
        idx = build_index.build(base, config)
        chs = idx['chapters']
        return {'chapters_total': len(chs), 'chapters_approved': sum(c['status'] == 'approved' for c in chs),
                'sections_total': sum(c['sections_total'] for c in chs),
                'sections_approved': sum(c['sections_approved'] for c in chs), 'cost': idx['project']['cost'], **extra}
    finally:
        subprocess.run(['git', 'worktree', 'remove', '--force', tmp], cwd=cwd, capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)


def build_library(namespace='refs/remotes/origin', cwd=ROOT, manifest=None):
    manifest = manifest or load_manifest()
    configs = branch_configs(namespace, cwd)
    out = []
    for b in books(configs, manifest, default_branch(cwd)):
        ref = f'{namespace}/{b["branch"]}'
        p = (configs[b['branch']] or {}).get('project') or {}
        entry = dict(b, author=p.get('author') or '')
        entry.update(book_stats(ref, cwd))
        work = f'{namespace}/{b["work_branch"]}'
        ahead = git('rev-list', '--count', f'{ref}..{work}', cwd=cwd).strip() if git('rev-parse', '-q', '--verify', work, cwd=cwd).strip() else ''
        entry['pending'] = int(ahead or 0)
        entry['updated_at'] = git('log', '-1', '--format=%cI', ref, cwd=cwd).strip()
        entry['last_commit'] = git('log', '-1', '--format=%s', ref, cwd=cwd).strip()
        entry['last_edition'] = last_edition(entry['slug'], cwd)
        out.append(entry)
    names = sorted({'GHOSTWRITER_UPDATE_TOKEN'} | {n for b in out for n in b.pop('secret_names', [])})
    return {'format': 1, 'program': program_info(cwd, manifest), 'secret_names': names, 'books': out}


def last_edition(slug, cwd=ROOT):
    """Neueste Auflage eines Buchs aus den Tags <slug>-auflage-N: {tag, number, date} oder None."""
    if not slug:
        return None
    best = None
    for tag in git('tag', '--list', f'{slug}-auflage-*', cwd=cwd).split():
        m = re.fullmatch(re.escape(slug) + r'-auflage-(\d+)', tag)
        if m and (best is None or int(m.group(1)) > best[0]):
            best = (int(m.group(1)), tag)
    if not best:
        return None
    return {'tag': best[1], 'number': best[0], 'date': git('log', '-1', '--format=%cI', best[1], cwd=cwd).strip()}


def program_info(cwd=ROOT, manifest=None):
    """Installierte Programmversion, fester UI-Commit und letzter Update-Lauf (Standard-Branch)."""
    manifest = manifest or load_manifest()
    ui_path = Path(cwd, 'templates', 'ui', 'ghostwriter-ui.yml')
    ui = yaml.safe_load(ui_path.read_text(encoding='utf-8')) if ui_path.is_file() else {}
    st_path = Path(cwd, '.ghostwriter', 'update.yml')
    st = yaml.safe_load(st_path.read_text(encoding='utf-8')) if st_path.is_file() else {}
    up = manifest.get('upstream') or {}
    return {'version': str(manifest.get('version', '')), 'upstream': f'{up.get("repo", "")}:{up.get("ref", "main")}',
            'ui_version': str((ui or {}).get('version', '')), 'ui_commit': (ui or {}).get('commit', ''),
            'last_update': (st or {}).get('updated_at', ''), 'skipped_workflows': (st or {}).get('skipped_workflows') or []}


def secrets_presence(names, previous=None):
    """{name: True|False|None} aus SECRETS_PRESENT (scripts/secret_check.py); ohne SECRETS_PRESENT der bisherige Stand."""
    import secret_check
    return secret_check.state(names, previous)


# ---------- Neues Buch (#38) ----------

def set_project_fields(text, fields):
    """Felder im Block project: von ghostwriter.yml setzen, ohne Kommentare und Format zu ändern."""
    lines = text.splitlines(keepends=True)
    inside = False
    for i, line in enumerate(lines):
        if re.match(r'^project:\s*(#.*)?$', line):
            inside = True
            continue
        if inside and re.match(r'^\S', line):
            break
        m = re.match(r'^(  )([a-z_]+):(\s*)("[^"]*"|\S*)(\s*#.*)?(\n?)$', line) if inside else None
        if m and m.group(2) in fields:
            lines[i] = f'{m.group(1)}{m.group(2)}:{m.group(3) or " "}{json.dumps(fields[m.group(2)], ensure_ascii=False)}{m.group(5) or ""}{m.group(6)}'
    return ''.join(lines)


def new_book(title, short='', author='', found=(), manifest=None):
    """Prüfung und Werte für ein neues Buch: {branch, slug, work_branch, taken, fields}."""
    short = (short or title).strip()
    r = name_check(short, list(found), manifest)
    if not (title or '').strip():
        r['taken'].insert(0, 'Arbeitstitel fehlt')
    r['fields'] = {'working_title': title.strip(), 'title_short': short, 'author': (author or '').strip()}
    return r


def create_book(title, short='', author='', cwd=ROOT, namespace='refs/remotes/origin', manifest=None, base='HEAD'):
    """Lokal: Branch buch/<slug> von base anlegen, ghostwriter.yml setzen, ein Commit. Gibt das Ergebnis von new_book zurück."""
    import datetime
    manifest = manifest or load_manifest()
    found = books(branch_configs(namespace, cwd), manifest, default_branch(cwd))
    found += [b for b in books(branch_configs('refs/heads', cwd), manifest, default_branch(cwd)) if b['branch'] not in {x['branch'] for x in found}]
    r = new_book(title, short, author, found, manifest)
    if r['taken']:
        return r
    run = lambda *a: subprocess.run(['git', *a], cwd=cwd, check=True, capture_output=True, text=True)
    run('switch', '-q', '-c', r['branch'], base)
    cfg = Path(cwd, 'ghostwriter.yml')
    cfg.write_text(set_project_fields(cfg.read_text(encoding='utf-8'), r['fields']), encoding='utf-8')
    paths = ['ghostwriter.yml']
    state = Path(cwd, '.ghostwriter', 'update.yml')
    if not state.is_file():   # Programmstand des Standard-Branchs festhalten (wie nach einem Update)
        up = manifest.get('upstream') or {}
        state.parent.mkdir(exist_ok=True)
        state.write_text(yaml.safe_dump({
            'upstream': f'{up.get("repo", "")}:{up.get("ref", "main")}', 'version': str(manifest.get('version', '')),
            'commit': run('rev-parse', base).stdout.strip(),
            'updated_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'skipped_workflows': []}, sort_keys=False), encoding='utf-8')
        paths.append('.ghostwriter/update.yml')
    run('add', *paths)
    run('-c', 'user.name=GhostWriter', '-c', 'user.email=ghostwriter@users.noreply.github.com', 'commit', '-q',
        '-m', f'Neues Buch angelegt: {r["fields"]["working_title"]}', '-m', 'GhostWriter-Aktion: library.book.create')
    return r


def program_problems(cwd=ROOT, namespace='refs/remotes/origin', manifest=None):
    """Hauptrepository ohne Buchinhalte (#48): (fehler, warnungen)."""
    manifest = manifest or load_manifest()
    errors, warnings = [], []
    cfg_path = Path(cwd, 'ghostwriter.yml')
    cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8')) if cfg_path.is_file() else {}
    if has_chapters(cfg):
        errors.append('ghostwriter.yml im Programm-Repository hat Kapitel; Bücher gehören in ein eigenes Repository')
    for d in ('chapters', 'matter', 'research', 'costs'):
        files = [p for p in Path(cwd, d).rglob('*') if p.is_file() and p.name != '.gitkeep'] if Path(cwd, d).is_dir() else []
        if files:
            errors.append(f'{d}/ enthält Buchdateien ({len(files)})')
    eds = [p for p in Path(cwd, 'editions').glob('*.md')] if Path(cwd, 'editions').is_dir() else []
    if eds:
        errors.append(f'editions/ enthält Auflagen ({len(eds)})')
    default = default_branch(cwd)
    for b in books(branch_configs(namespace, cwd), manifest, default):
        warnings.append(f'Buch-Branch {b["branch"]} im Programm-Repository (#48: in ein eigenes privates Repository umziehen)')
    for tag in git('tag', '--list', '*-auflage-*', cwd=cwd).split():
        warnings.append(f'Auflagen-Tag {tag} im Programm-Repository (#48)')
    return errors, warnings


def load_manifest():
    return yaml.safe_load((ROOT / MANIFEST).read_text(encoding='utf-8'))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=['list', 'name', 'check', 'build', 'new', 'is', 'check-program'])
    ap.add_argument('title', nargs='?')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--namespace', default='refs/remotes/origin', help='Git-Namespace der Branches (Tests: refs/heads)')
    ap.add_argument('--repo', default=str(ROOT), help='Repository-Ordner (Standard: dieses)')
    ap.add_argument('--out', help='bei build: Zieldatei (sonst Ausgabe)')
    ap.add_argument('--short', default='', help='bei new: Kurztitel (sonst der Arbeitstitel)')
    ap.add_argument('--author', default='', help='bei new: Autor')
    ap.add_argument('--dir', default='.', help='bei is: Ordner mit ghostwriter.yml')
    ap.add_argument('--create', action='store_true', help='bei new: Branch lokal anlegen und committen')
    a = ap.parse_args(argv[1:])
    manifest = load_manifest()
    if a.cmd == 'check-program':
        import os
        errors, warnings = program_problems(a.repo, a.namespace, manifest)
        gha = os.environ.get('GITHUB_ACTIONS') == 'true'
        for w in warnings:
            print(f'::warning::{w}' if gha else f'⚠ {w}')
        for e in errors:
            print(f'::error::{e}' if gha else f'✗ {e}')
        if not errors:
            print('✓ keine Buchinhalte auf dem Standard-Branch' + (f' ({len(warnings)} Hinweise)' if warnings else ''))
        return 1 if errors else 0
    if a.cmd == 'is':
        cfg_path = Path(a.dir, 'ghostwriter.yml')
        cfg = (yaml.safe_load(cfg_path.read_text(encoding='utf-8')) or {}) if cfg_path.is_file() else None
        yes = is_book(a.title or '', cfg, manifest, default_branch(a.repo))
        print(f'{a.title}: {"Buch" if yes else "kein Buch"}')
        return 0 if yes else 1
    if a.cmd == 'build':
        data = build_library(a.namespace, a.repo, manifest)
        old = Path(a.out).read_text(encoding='utf-8') if a.out and Path(a.out).is_file() else None
        try:
            prev = (json.loads(old) or {}).get('secrets') if old else None
        except ValueError:
            prev = None
        sec = secrets_presence(data['secret_names'], prev)
        if sec is not None:
            data['secrets'] = sec
        text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        if a.out:
            if old != text:
                Path(a.out).write_text(text, encoding='utf-8')
            print(f'{a.out}: {"geschrieben" if old != text else "unverändert"}')
        else:
            sys.stdout.write(text)
        return 0
    if a.cmd == 'new':
        if a.create:
            r = create_book(a.title or '', a.short, a.author, a.repo, a.namespace, manifest)
        else:
            r = new_book(a.title or '', a.short, a.author, books(branch_configs(a.namespace, a.repo), manifest, default_branch(a.repo)), manifest)
        if a.json:
            print(json.dumps(r, ensure_ascii=False))
        else:
            print(f'{r["branch"]} (Arbeits-Branch {r["work_branch"]})' + ''.join(f'\n✗ {t}' for t in r['taken'])
                  + ('' if r['taken'] or not a.create else f'\n✓ angelegt'))
        return 1 if r['taken'] else 0
    found = books(branch_configs(a.namespace, a.repo), manifest, default_branch(a.repo))
    if a.cmd == 'list':
        if a.json:
            print(json.dumps(found, ensure_ascii=False, indent=2))
        else:
            for b in found:
                print(f'{b["branch"]:40} {"im Aufbau" if b["status"] == "setup" else "eingerichtet":12} {b["title_short"]}')
            if not found:
                print('keine Bücher gefunden')
        return 0
    if a.cmd == 'name':
        if not a.title:
            ap.error('Kurztitel fehlt')
        r = name_check(a.title, found, manifest)
        if a.json:
            print(json.dumps(r, ensure_ascii=False))
        else:
            print(f'{r["branch"]} (Tag-Slug {r["slug"]})' + ''.join(f'\n✗ {t}' for t in r['taken']))
        return 1 if r['taken'] else 0
    dup = duplicates(found)
    for s, br in dup.items():
        print(f'✗ Kurztitel „{s}“ mehrfach: {", ".join(br)} – Auflagen-Tags wären nicht eindeutig')
    if not dup:
        print(f'✓ {len(found)} Bücher, Kurztitel eindeutig')
    return 1 if dup else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
