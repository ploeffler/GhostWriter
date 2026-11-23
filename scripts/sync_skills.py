#!/usr/bin/env python3
"""Allgemeine Skills aus einem festgelegten lokalen Git-Stand übernehmen oder prüfen.

Kein Netzwerkzugriff, keine Installation von Konto-Skills. Persönliche Skills
werden nicht angefasst. Änderungen werden nur vorbereitet, nie committet.
"""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'ghostwriter-skills.yml'
REPOSITORY = 'ploeffler/ghostwriter-skills'
NAMES = ('ghostwriter', 'ghostwriter-buchgedaechtnis', 'ghostwriter-lektorat')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def target(root, name):
    path = Path(root) / '.claude' / 'skills' / name / 'SKILL.md'
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Verlinkte Skill-Ablage wird nicht überschrieben')
    return path


def check(root=ROOT):
    """Ohne externe Quelle: lokale Kopien gegen den festgelegten Fingerabdruck prüfen."""
    root = Path(root)
    try:
        lock = yaml.safe_load((root / LOCK).read_text(encoding='utf-8'))
        if (not isinstance(lock, dict) or lock.get('format') != 1
                or lock.get('repository') != REPOSITORY
                or not re.fullmatch(r'[0-9a-f]{40}', str(lock.get('commit', '')))
                or not isinstance(lock.get('skills'), dict)
                or set(lock['skills']) != set(NAMES)):
            raise ValueError('Ungültige Skill-Quellenangabe')
        for name in NAMES:
            if digest(target(root, name).read_bytes()) != lock['skills'][name]:
                raise ValueError('Skill-Kopie weicht von der festgelegten Quelle ab: ' + name)
    except (OSError, yaml.YAMLError) as error:
        raise ValueError('Skill-Quellenangabe oder lokale Kopie fehlt bzw. ist ungültig') from error
    return lock


def sync(source, commit, root=ROOT):
    """Nur explizite Commit-ID, kein bewegliches main und keine Arbeitsdateien kopieren."""
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Vollständige Quellcommit-ID erforderlich')
    root, source = Path(root), Path(source)
    files = {}
    for name in NAMES:
        target(root, name)  # Alle Zielpfade prüfen, bevor eine Datei geschrieben wird.
        spec = f'{commit}:skills/{name}/SKILL.md'
        mode = subprocess.run(['git', '-C', str(source), 'ls-tree', commit, '--',
                               f'skills/{name}/SKILL.md'], capture_output=True, check=True).stdout
        if not mode.startswith(b'100644 blob '):
            raise ValueError('Quelle enthält keine normale Skill-Datei: ' + name)
        data = subprocess.run(['git', '-C', str(source), 'show', spec],
                              capture_output=True, check=True).stdout
        text = data.decode('utf-8')
        match = re.match(r'\A---\n(.*?)\n---(?:\n|$)', text, re.S)
        meta = yaml.safe_load(match[1]) if match else None
        if (not isinstance(meta, dict) or meta.get('name') != name
                or not isinstance(meta.get('description'), str) or not meta['description'].strip()):
            raise ValueError('Ungültige Skill-Kopfzeilen: ' + name)
        files[name] = data
    lock_path = root / LOCK
    if lock_path.is_symlink():
        raise ValueError('Verlinkte Quellenangabe wird nicht überschrieben')
    for name, data in files.items():
        path = target(root, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    lock = {'format': 1, 'repository': REPOSITORY, 'commit': commit,
            'skills': {name: digest(data) for name, data in files.items()}}
    lock_path.write_text(yaml.safe_dump(lock, sort_keys=False), encoding='utf-8')
    return check(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Lokaler Klon von ghostwriter-skills')
    parser.add_argument('--commit', help='Bewusst ausgewählte vollständige Quellcommit-ID')
    args = parser.parse_args()
    try:
        if args.source is not None or args.commit is not None:
            if args.source is None or args.commit is None:
                raise ValueError('--source und --commit gemeinsam angeben')
            sync(args.source, args.commit)
        else:
            check()
    except (ValueError, OSError, subprocess.CalledProcessError, yaml.YAMLError):
        parser.exit(1, 'Skill-Abgleich fehlgeschlagen; Quelle, Commit und lokale Kopien prüfen.\n')
    print('✓ Allgemeine Skills entsprechen der festgelegten Quelle')


if __name__ == '__main__':
    main()
