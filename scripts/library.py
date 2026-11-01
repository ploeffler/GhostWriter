#!/usr/bin/env python3
"""Bibliothek: mehrere Bücher in einem Repository, je Buch ein Branch (#36).

Aufruf (im Repository, braucht alle Branches: git fetch origin '+refs/heads/*:refs/remotes/origin/*'):
  python scripts/library.py list [--json]       Bücher der Bibliothek
  python scripts/library.py name "<Kurztitel>"  Branch-Name, Tag-Slug und ob er schon vergeben ist
  python scripts/library.py check               Kurztitel bzw. Tag-Slugs eindeutig? (Exit 1 bei Doppelten)

Benennung (ghostwriter-manifest.yml → library):
  Buch-Branch     buch/<slug>                 slug aus dem Kurztitel, wie der Tag-Slug der Auflagen
  Arbeits-Branch  ghostwriter/<buch-branch>   z. B. ghostwriter/buch/adhs

Erkennungsregel, einheitlich für Bücherregal, Update-Action und Wiedereinstieg:
  1. Branches aus update.skip_branches sind nie Bücher (Arbeits-, Versions-, Bot-Branches,
     im Hauptrepository auch main).
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


def is_book(name, config, manifest=None):
    """Erkennungsregel (siehe oben). config = ghostwriter.yml des Branchs (dict, None = fehlt)."""
    s = settings(manifest)
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


def books(branch_configs, manifest=None):
    """branch_configs: {branch: config|None} -> Liste der Bücher (sortiert nach Branch)."""
    return [describe(n, c, manifest) for n, c in sorted(branch_configs.items()) if is_book(n, c, manifest)]


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


def load_manifest():
    return yaml.safe_load((ROOT / MANIFEST).read_text(encoding='utf-8'))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=['list', 'name', 'check'])
    ap.add_argument('title', nargs='?')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--namespace', default='refs/remotes/origin', help='Git-Namespace der Branches (Tests: refs/heads)')
    ap.add_argument('--repo', default=str(ROOT), help='Repository-Ordner (Standard: dieses)')
    a = ap.parse_args(argv[1:])
    manifest = load_manifest()
    found = books(branch_configs(a.namespace, a.repo), manifest)
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
