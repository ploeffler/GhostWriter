#!/usr/bin/env python3
"""Wandelt ein Einzelbuch-Repository in eine Bibliothek um (#40).

Aufruf (Action „In Bibliothek umwandeln“, .github/workflows/convert.yml, auf dem Standard-Branch):
  python scripts/convert_to_library.py [--short KURZTITEL] [--dry-run] [--remote origin]

Ablauf, jeder Schritt erst nach erfolgreichem vorherigen:
  1. Prüfen: Der Standard-Branch ist ein Buch (hat Kapitel), es gibt keine offenen
     Änderungen im Arbeits-Branch ghostwriter/<standard-branch> (sonst zuerst
     „Änderungen übernehmen“), der Name buch/<slug> ist frei und eindeutig.
  2. Buch-Branch buch/<slug> mit der vollständigen Historie des Standard-Branchs
     anlegen (gleicher Commit) und prüfen (Projektprüfung).
  3. Erst dann pushen und auf dem Standard-Branch einen Commit
     „In Bibliothek umgewandelt“ anlegen: Buchdateien (manifest → book) entfernen,
     ghostwriter.yml durch den Starter (templates/ghostwriter-starter.yml) ersetzen,
     library.json schreiben. .ghostwriter/ (Programmstand) bleibt.
Nichts wird überschrieben oder gelöscht, was nicht in der Historie bleibt: Tags und
Releases zeigen weiter auf ihre Commits. Rückweg: den Commit „In Bibliothek
umgewandelt“ auf dem Standard-Branch rückgängig machen (git revert) und danach
buch/<slug> löschen (docs/UPDATES.md, „Von v0.5 auf v0.6“).

--dry-run prüft und zeigt, was passieren würde, ohne etwas zu ändern.
Exit 0 = umgewandelt bzw. Probelauf in Ordnung, 1 = Hindernis (Text auf stdout).
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import library  # noqa: E402

STARTER = 'templates/ghostwriter-starter.yml'
TRAILER = 'GhostWriter-Aktion: library.convert'
BOT = ['-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com']


def git(*args, cwd=ROOT, check=True):
    r = subprocess.run(['git', *args], cwd=cwd, text=True, capture_output=True)
    if check and r.returncode:
        raise RuntimeError(f'git {" ".join(args)}: {r.stderr.strip() or r.stdout.strip()}')
    return r.stdout.strip()


def current_branch(cwd):
    return os.environ.get('GHOSTWRITER_DEFAULT_BRANCH') or git('rev-parse', '--abbrev-ref', 'HEAD', cwd=cwd)


def check_book(cwd):
    """Projektprüfung (scripts/validate_project.py) in einem Ordner; Liste der Probleme.
    Die Übersichtsdatei prüft sie nicht: Die Action „Übersichtsdatei aktualisieren“ erzeugt sie neu."""
    script = Path(cwd, 'scripts', 'validate_project.py')
    if not script.is_file():
        return []
    r = subprocess.run([sys.executable, str(script), str(cwd)], capture_output=True, text=True)
    return [f'Projektprüfung: {(r.stdout + r.stderr).strip()[:800]}'] if r.returncode else []


def plan(cwd, remote, short):
    """Prüft die Voraussetzungen; gibt (info, hindernisse) zurück."""
    manifest = yaml.safe_load(Path(cwd, library.MANIFEST).read_text(encoding='utf-8'))
    default = current_branch(cwd)
    cfg = yaml.safe_load(Path(cwd, 'ghostwriter.yml').read_text(encoding='utf-8')) or {}
    problems = []
    up = (manifest.get('upstream') or {}).get('repo')
    if up and os.environ.get('GITHUB_REPOSITORY') == up:
        problems.append('Das ist das GhostWriter-Hauptrepository; hier gibt es nichts umzuwandeln.')
    if not library.has_chapters(cfg):
        problems.append(f'{default} hat keine Kapitel; das Repository ist schon eine Bibliothek oder noch nicht eingerichtet.')
    if not Path(cwd, STARTER).is_file():
        problems.append(f'{STARTER} fehlt; zuerst GhostWriter aktualisieren (mindestens 0.6).')
    git('fetch', '-q', '--prune', remote, f'+refs/heads/*:refs/remotes/{remote}/*', cwd=cwd, check=False)
    ns = f'refs/remotes/{remote}'
    work = library.work_branch(default, manifest)
    if git('rev-parse', '-q', '--verify', f'{ns}/{work}', cwd=cwd, check=False):
        ahead = git('rev-list', '--count', f'HEAD..{ns}/{work}', cwd=cwd, check=False) or '0'
        if int(ahead):
            problems.append(f'Es gibt {ahead} offene Änderungen im Arbeits-Branch {work}. Bitte zuerst im Chat '
                            '„Änderungen übernehmen“ (oder den Pull Request schließen) und dann erneut umwandeln.')
    title_short = short or library.short_title(cfg)
    found = [b for b in library.books(library.branch_configs(ns, cwd), manifest, default) if b['branch'] != default]
    r = library.name_check(title_short, found, manifest)
    if git('rev-parse', '-q', '--verify', f'{ns}/{r["branch"]}', cwd=cwd, check=False):
        r['taken'].append(f'Branch {r["branch"]} gibt es schon')
    problems += [f'Name: {t}' for t in dict.fromkeys(r['taken'])]
    problems += check_book(cwd)
    return {'default': default, 'branch': r['branch'], 'slug': r['slug'], 'manifest': manifest,
            'head': git('rev-parse', 'HEAD', cwd=cwd), 'title_short': title_short}, problems


def strip_book(cwd, manifest):
    """Buchdateien entfernen, Starter einsetzen. Gibt die entfernten Pfade zurück."""
    removed = []
    for entry in manifest.get('book') or []:
        name = entry.rstrip('/')
        if name in ('ghostwriter.yml', '.ghostwriter', 'library.json'):
            continue
        p = Path(cwd, name)
        if p.exists():
            git('rm', '-r', '-q', '--', name, cwd=cwd)
            removed.append(entry)
    shutil.copyfile(Path(cwd, STARTER), Path(cwd, 'ghostwriter.yml'))
    git('add', 'ghostwriter.yml', cwd=cwd)
    return removed


def convert(cwd=ROOT, remote='origin', short='', dry_run=False):
    info, problems = plan(cwd, remote, short)
    lines = [f'Standard-Branch: {info["default"]}', f'Neuer Buch-Branch: {info["branch"]} (Commit {info["head"][:7]})']
    if problems:
        return 1, lines + [''] + [f'✗ {p}' for p in problems]
    if dry_run:
        return 0, lines + ['', 'Probelauf: Voraussetzungen erfüllt, nichts geändert.']
    # 2. Buch-Branch anlegen und in einem eigenen Worktree prüfen
    tmp = tempfile.mkdtemp(prefix='gw-conv-')
    try:
        git('worktree', 'add', '-q', '-b', info['branch'], tmp, info['head'], cwd=cwd)
        bad = check_book(Path(tmp))
    finally:
        git('worktree', 'remove', '--force', tmp, cwd=cwd, check=False)
        shutil.rmtree(tmp, ignore_errors=True)
    if bad:
        git('branch', '-D', info['branch'], cwd=cwd, check=False)
        return 1, lines + [''] + [f'✗ Prüfung des Buch-Branchs: {p}' for p in bad]
    git('push', '-q', remote, f'{info["branch"]}:refs/heads/{info["branch"]}', cwd=cwd)
    # 3. Standard-Branch auf den Programmstand bringen
    removed = strip_book(cwd, info['manifest'])
    git('fetch', '-q', remote, f'+refs/heads/*:refs/remotes/{remote}/*', cwd=cwd, check=False)
    os.environ.setdefault('GHOSTWRITER_DEFAULT_BRANCH', info['default'])
    data = library.build_library(f'refs/remotes/{remote}', cwd, info['manifest'])
    data['books'] = [b for b in data['books'] if b['branch'] != info['default']]   # ist ab diesem Commit kein Buch mehr
    import json
    Path(cwd, 'library.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    git('add', 'library.json', cwd=cwd)
    git(*BOT, 'commit', '-q', '-m', f'In Bibliothek umgewandelt: Buch nach {info["branch"]}',
        '-m', f'Das Buch „{info["title_short"]}“ liegt mit vollständiger Historie auf {info["branch"]}.\n'
              f'Entfernt vom Standard-Branch: {", ".join(removed) or "–"}; ghostwriter.yml ist wieder der Starter.\n'
              f'Rückweg: diesen Commit rückgängig machen (git revert), danach {info["branch"]} löschen.\n\n{TRAILER}', cwd=cwd)
    git('push', '-q', remote, f'HEAD:refs/heads/{info["default"]}', cwd=cwd)
    return 0, lines + ['', f'✓ Buch nach {info["branch"]} übertragen und geprüft',
                       f'✓ {info["default"]} enthält nur noch das Programm (entfernt: {", ".join(removed) or "–"})',
                       f'✓ Bücherregal: {len(data["books"])} Buch/Bücher']


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--short', default='', help='Kurztitel für den Buch-Branch (sonst aus ghostwriter.yml)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--remote', default='origin')
    ap.add_argument('--repo', default=str(ROOT))
    a = ap.parse_args(argv[1:])
    try:
        code, lines = convert(Path(a.repo), a.remote, a.short, a.dry_run)
    except RuntimeError as e:
        code, lines = 1, [f'✗ {e}']
    text = '\n'.join(lines)
    print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write('## In Bibliothek umwandeln\n\n```\n' + text + '\n```\n')
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv))
