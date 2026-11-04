#!/usr/bin/env python3
"""Lesende Hilfen für Kapitelmaterial und den Abgleich von Buch- und Arbeitsstand."""
import argparse
import json
import subprocess
from pathlib import Path

import yaml


def historical_candidates(config, approvals):
    """Verwaiste Abschnitts- und Kapitelverweise zur Prüfung nennen; nichts bestätigen."""
    chapters = config.get('structure', {}).get('chapters') or []
    chapter_ids = {c['id'] for c in chapters}
    section_ids = {s['id'] for c in chapters for s in c.get('sections') or []}
    marked = {x['entry'] for x in approvals.get('historical_references') or []}
    candidates = []
    for number, entry in enumerate(approvals.get('entries') or [], 1):
        kind, ident = entry.get('kind'), entry.get('id', '')
        applicable = (kind == 'chapter' and ident not in chapter_ids) or (
            (kind == 'section' or (kind == 'writing' and ident.startswith('sec-'))) and ident not in section_ids)
        if applicable and number not in marked:
            candidates.append({'entry': number, 'kind': kind, 'id': ident,
                               'commit': entry.get('commit'), 'action': entry.get('action')})
    return candidates


def chapter_material(base, chapter):
    """Zugehörige Dateien und erkennbare Hinweise anzeigen, ohne Relevanz zu behaupten."""
    base = Path(base)
    results = []
    root = base / chapter['path']
    if root.is_dir():
        for path in sorted(root.rglob('*')):
            if path.is_file() and not path.is_symlink():
                results.append({'path': path.relative_to(base).as_posix(), 'relation': 'kapitelordner'})
    # Nur Metadaten bzw. kleine Textdateien durchsuchen; kein ganzes Buch ausgeben.
    terms = {chapter.get('title', '').casefold(), chapter['id'].casefold()}
    terms |= {s['id'].casefold() for s in chapter.get('sections') or []}
    terms.discard('')
    for folder in ('planning', 'story', 'research'):
        root = base / folder
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            if not path.is_file() or path.is_symlink() or path.suffix.lower() not in ('.md', '.yml', '.yaml', '.json'):
                continue
            try:
                if path.stat().st_size > 1024 * 1024:
                    continue
                value = path.read_text(encoding='utf-8').casefold()
            except (OSError, UnicodeError):
                continue
            if any(term in value for term in terms):
                results.append({'path': path.relative_to(base).as_posix(), 'relation': 'texttreffer'})
    return results


def git(base, *args):
    p = subprocess.run(['git', '-C', str(base), *args], text=True, capture_output=True)
    if p.returncode:
        raise ValueError(p.stderr.strip() or 'Git-Abfrage fehlgeschlagen')
    return p.stdout


def tree_files(base, ref):
    """Abgebildete Pfade mit Typ, Dateimodus und Git-Objekt-ID; auch Löschungen erkennbar."""
    output = git(base, 'ls-tree', '-rz', '--full-tree', ref)
    result = {}
    for record in output.split('\0'):
        if not record:
            continue
        meta, path = record.split('\t', 1)
        mode, typ, oid = meta.split(' ', 2)
        result[path] = (mode, typ, oid)
    return result


def compare_book_work(base, book, work):
    """Drei-Wege-Vergleich auf Dateiebene, ohne Schätzung von Inhaltskonflikten."""
    # Refs mit --end-of-options auflösen, bevor sie als Git-Argumente genutzt werden.
    def resolve(ref):
        return git(base, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}').strip()
    bsha, wsha = resolve(book), resolve(work)
    msha = git(base, 'merge-base', bsha, wsha).strip()
    common, current, proposed = (tree_files(base, ref) for ref in (msha, bsha, wsha))
    rows = []
    for path in sorted(common.keys() | current.keys() | proposed.keys()):
        old, now, new = common.get(path), current.get(path), proposed.get(path)
        if old == new:
            continue
        if now == new:
            state = 'bereits_identisch'
        elif now == old:
            state = 'nur_arbeitsfassung'
        else:
            state = 'beide_geaendert'
        rows.append({'path': path, 'state': state, 'work_deleted': new is None, 'book_deleted': now is None})
    return {'book_head': bsha, 'work_head': wsha, 'common_head': msha, 'files': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('project')
    sub = p.add_subparsers(dest='action', required=True)
    material = sub.add_parser('material')
    material.add_argument('chapter', help='Kapitelnummer oder ID')
    compare = sub.add_parser('compare')
    compare.add_argument('book_ref')
    compare.add_argument('work_ref')
    sub.add_parser('historical-candidates')
    args = p.parse_args()
    try:
        if args.action == 'compare':
            result = compare_book_work(args.project, args.book_ref, args.work_ref)
        elif args.action == 'historical-candidates':
            base = Path(args.project)
            config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
            log = base / 'approvals.yml'
            approvals = yaml.safe_load(log.read_text(encoding='utf-8')) if log.is_file() else {}
            result = {'candidates': historical_candidates(config, approvals or {})}
        else:
            base = Path(args.project)
            config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
            chapters = config['structure']['chapters']
            candidates = ([chapters[int(args.chapter) - 1]] if args.chapter.isdigit() and 1 <= int(args.chapter) <= len(chapters)
                          else [c for c in chapters if c['id'] == args.chapter])
            if not candidates:
                p.error('Kapitel nicht gefunden')
            result = {'chapter': candidates[0]['id'], 'files': chapter_material(base, candidates[0])}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        p.exit(1, f'Prüfung nicht möglich: {exc}\n')


if __name__ == '__main__':
    main()
