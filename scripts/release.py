#!/usr/bin/env python3
"""Release vorbereiten und veröffentlichen (#488): Prüfungen und Hilfen für die Workflows.

Phase 1 (.github/workflows/release-prepare.yml, ohne Freigabe):
  prepare    Version im Manifest setzen, Release-Notes-Entwurf in docs/UPDATES*.md einfügen.
  languages  Sprachbericht: Schlüssel, Platzhalter und Doku-Seiten je Sprache gegenüber de.
  report     Gesamturteil „bereit zum Scharfschalten“ / „nicht bereit“ als Markdown.

Phase 2 (.github/workflows/release.yml, nur nach Freigabe):
  check   Freigabe prüfen: Version = Manifest = Bestätigung, Release Notes vorhanden.
  tag     Tag-Namen zur Version ausgeben (0.9.0 -> v0.9, 1.0.1 -> v1.0.1).
  notes   Release Notes der Version aus docs/UPDATES.md ausgeben.
  site    Öffentliche Website auf die Version prüfen (build-info.json und Seiten je Sprache).

Veröffentlicht selbst nichts; Tag, Release und Website legt der Workflow
.github/workflows/release.yml an.
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VERSION_RE = re.compile(r'^\d+\.\d+\.\d+$')
DRAFT = '<!-- Entwurf (#488): überarbeiten und diese Markierung entfernen -->'
PLACEHOLDER_RE = re.compile(r'\{[^{}]*\}')
LANG_FILE_RE = re.compile(r'^[a-z]{2}(-[A-Z]{2})?$')
CATALOGS = ('templates/ui/i18n', 'templates/i18n/views')


def manifest_version(root=ROOT):
    return str(yaml.safe_load((root / 'ghostwriter-manifest.yml').read_text(encoding='utf-8'))['version'])


def tag_name(version, prerelease=''):
    """Bisherige Tags heißen v0.7, v0.8, v0.9; nur ein Patch-Stand bekommt drei Stellen; Vorabversion -rc.N."""
    if not VERSION_RE.match(version):
        raise ValueError(f'Version „{version}“ hat nicht die Form X.Y.Z')
    major, minor, patch = version.split('.')
    base = f'v{major}.{minor}' if patch == '0' else f'v{version}'
    if prerelease:
        if not str(prerelease).isdigit() or int(prerelease) < 1:
            raise ValueError(f'Pre-release-Nummer „{prerelease}“ muss eine Zahl ab 1 sein')
        return f'{base}-rc.{int(prerelease)}'
    return base


def notes(version, root=ROOT, lang='de'):
    """Absatz „**<version>:** …“ bzw. „**<version>** …“ aus docs/UPDATES.md (bzw. UPDATES.en.md)."""
    name = 'UPDATES.md' if lang == 'de' else 'UPDATES.en.md'
    text = (root / 'docs' / name).read_text(encoding='utf-8')
    for paragraph in re.split(r'\n\s*\n', text):
        head = paragraph.strip()
        if head.startswith(f'**{version}:**') or head.startswith(f'**{version}** '):
            return paragraph.strip()
    return None


def check(version, confirm, root=ROOT, prerelease='', ref=''):
    """Liste der Gründe, warum nicht veröffentlicht werden darf (leer = darf)."""
    problems = []
    if prerelease:
        if not str(prerelease).isdigit() or int(prerelease) < 1:
            problems.append(f'Pre-release-Nummer „{prerelease}“ muss eine Zahl ab 1 sein')
        elif ref and ref != f'release/{version}':
            problems.append(f'Pre-release nur vom Branch release/{version}, nicht von {ref}')
    elif ref and ref != 'main':
        problems.append(f'Endgültiges Release nur von main, nicht von {ref}')
    if not VERSION_RE.match(version or ''):
        problems.append(f'Version „{version}“ hat nicht die Form X.Y.Z')
    current = manifest_version(root)
    if version != current:
        problems.append(f'Version {version} passt nicht zum Manifest ({current})')
    if confirm != version:
        problems.append(f'Bestätigung „{confirm}“ stimmt nicht mit der Version {version} überein')
    for lang in ('de', 'en'):
        name = f'docs/UPDATES{"" if lang == "de" else ".en"}.md'
        text = notes(version, root, lang) if VERSION_RE.match(version or '') else ''
        if VERSION_RE.match(version or '') and not text:
            problems.append(f'Release Notes für {version} fehlen in {name}')
        elif text and DRAFT in text:
            problems.append(f'Release Notes für {version} in {name} sind noch ein Entwurf')
    return problems


# ---------- Phase 1 ----------

def last_tag(root=ROOT):
    out = subprocess.run(['git', 'describe', '--tags', '--abbrev=0', '--match', 'v*'], cwd=root,
                         capture_output=True, text=True)
    return out.stdout.strip() or None


def merged_prs(since, root=ROOT):
    """[(nummer, titel)] der seit `since` nach main gemergten PRs (Merge-Commits)."""
    rng = f'{since}..HEAD' if since else 'HEAD'
    out = subprocess.run(['git', 'log', rng, '--merges', '--format=%s%x1f%b%x1e'], cwd=root,
                         capture_output=True, text=True, check=True).stdout
    prs = []
    for entry in out.split('\x1e'):
        if '\x1f' not in entry:
            continue
        subject, body = entry.strip().split('\x1f', 1)
        m = re.match(r'Merge pull request #(\d+)', subject)
        if m:
            title = (body.strip().splitlines() or [''])[0].strip() or subject
            prs.append((int(m.group(1)), title))
    return list(reversed(prs))


def draft_notes(version, prs, lang='de'):
    items = ' '.join(f'{title} (#{num}).' for num, title in prs) or ('Keine gemergten PRs gefunden.' if lang == 'de' else 'No merged PRs found.')
    head = f'**{version}:**' if lang == 'de' else f'**{version}**'
    return f'{head} {items} {DRAFT}'


def insert_notes(path, paragraph, version):
    text = path.read_text(encoding='utf-8')
    if f'**{version}:**' in text or f'**{version}** ' in text:
        return False
    m = re.search(r'^\*\*\d+\.\d+\.\d+', text, re.M)
    pos = m.start() if m else len(text)
    path.write_text(text[:pos] + paragraph + '\n\n' + text[pos:], encoding='utf-8')
    return True


def prepare(version, root=ROOT, prs=None):
    if not VERSION_RE.match(version):
        raise ValueError(f'Version „{version}“ hat nicht die Form X.Y.Z')
    manifest = root / 'ghostwriter-manifest.yml'
    text = manifest.read_text(encoding='utf-8')
    new, count = re.subn(r'^version: .*$', f'version: {version}', text, count=1, flags=re.M)
    if not count:
        raise ValueError('Keine Zeile „version:“ im Manifest')
    manifest.write_text(new, encoding='utf-8')
    prs = merged_prs(last_tag(root), root) if prs is None else prs
    for lang, name in (('de', 'UPDATES.md'), ('en', 'UPDATES.en.md')):
        insert_notes(root / 'docs' / name, draft_notes(version, prs, lang), version)
    return prs


def _catalog_languages(root):
    langs = set()
    for folder in CATALOGS:
        langs |= {p.stem for p in (root / folder).glob('*.json') if LANG_FILE_RE.match(p.stem)}
    return langs


def languages(root=ROOT):
    """{sprache: {'status': vollständig|Lücken|nur teilweise, 'gaps': [...]}} gegenüber de."""
    site = json.loads((root / 'docs/site.json').read_text(encoding='utf-8'))
    langs = _catalog_languages(root) | {lang for page in site['pages'] for lang in page['source']}
    langs.discard('de')
    report = {}
    for lang in sorted(langs):
        gaps, present = [], 0
        for folder in CATALOGS:
            base_path, path = root / folder / 'de.json', root / folder / f'{lang}.json'
            if not base_path.is_file():
                continue
            if not path.is_file():
                gaps.append(f'{folder}/{lang}.json fehlt'); continue
            present += 1
            base, other = (json.loads(p.read_text(encoding='utf-8')) for p in (base_path, path))
            missing = sorted(set(base) - set(other)); extra = sorted(set(other) - set(base))
            if missing: gaps.append(f'{folder}: {len(missing)} Schlüssel fehlen (z. B. {missing[0]})')
            if extra: gaps.append(f'{folder}: {len(extra)} überzählige Schlüssel (z. B. {extra[0]})')
            bad = [k for k in base if k in other and isinstance(base[k], str) and isinstance(other[k], str)
                   and sorted(PLACEHOLDER_RE.findall(base[k])) != sorted(PLACEHOLDER_RE.findall(other[k]))]
            if bad: gaps.append(f'{folder}: Platzhalter weichen ab bei {len(bad)} Schlüsseln (z. B. {bad[0]})')
        pages = [page['id'] for page in site['pages'] if lang not in page['source']]
        if pages:
            gaps.append(f'Doku-Seiten ohne Fassung: {", ".join(pages)}')
        else:
            present += 1
        status = 'vollständig' if not gaps else ('nur teilweise' if present == 0 else 'Lücken')
        report[lang] = {'status': status, 'gaps': gaps}
    report = {'de': {'status': 'vollständig', 'gaps': []}, **report}
    return report


def testplan(version, root=ROOT):
    """(Pfad, offene Zeilen) aus docs/TESTPLAN-v<X.Y>.md, falls vorhanden; offen = Zeile mit ⏳."""
    path = root / 'docs' / f'TESTPLAN-{tag_name(version)}.md'
    if not path.is_file():
        return None, 0
    rows = [l for l in path.read_text(encoding='utf-8').splitlines() if l.startswith('|') and '⏳' in l]
    return path.relative_to(root).as_posix(), len(rows)


def render_report(version, langs, steps, issues, milestone, plan=(None, 0)):
    """steps: {name: bool}, issues: [{'number','title','labels':[...]}] offen im Meilenstein."""
    blockers = []
    for lang in ('de', 'en'):
        if langs.get(lang, {}).get('status') != 'vollständig':
            blockers.append(f'Sprache {lang} nicht vollständig (v1.0 verlangt de und en, #74)')
    blockers += [f'{name} nicht bestanden' for name, ok in steps.items() if not ok]
    bugs = [i for i in issues if 'bug' in i.get('labels', [])]
    blockers += [f'offener Fehler #{i["number"]} im Meilenstein {milestone}: {i["title"]}' for i in bugs]
    ready = not blockers
    lines = [f'## Release {version} vorbereiten', '',
             f'**Gesamturteil: {"bereit zum Scharfschalten" if ready else "nicht bereit"}**', '']
    if blockers:
        lines += ['Offene Punkte:'] + [f'- {b}' for b in blockers] + ['']
    lines += ['| Prüfung | Ergebnis |', '|---|---|']
    lines += [f'| {name} | {"bestanden" if ok else "nicht bestanden"} |' for name, ok in steps.items()]
    lines += ['', '### Sprachen', '', '| Sprache | Stand | Lücken |', '|---|---|---|']
    for lang, info in langs.items():
        lines.append(f'| {lang} | {info["status"]} | {"; ".join(info["gaps"]) or "–"} |')
    lines += ['', f'### Offene Issues im Meilenstein {milestone or "–"}', '']
    lines += [f'- #{i["number"]} {i["title"]}{" (bug)" if i in bugs else ""}' for i in issues] or ['- keine']
    if plan[0]:
        lines += ['', '### Handabnahme', '', f'`{plan[0]}`: {plan[1]} Prüfungen offen (kein Hindernis für das Urteil; '
                  'vor dem Veröffentlichen durchsehen).']
    lines += ['', 'Tests: volle Suite über `validate` am Release-PR; vor dem Veröffentlichen muss sie grün sein.']
    lines += ['', 'Release Notes in `docs/UPDATES.md` und `docs/UPDATES.en.md` sind ein Entwurf: überarbeiten, '
              'Markierung entfernen. Veröffentlichen erst nach dem Satz „Release '
              f'{version} freigeben und veröffentlichen“ (Ablauf „Release veröffentlichen“).']
    return '\n'.join(lines) + '\n', ready


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as response:  # nosec - öffentliche Seite
        return response.read().decode('utf-8')


def check_site(base, version, get=fetch):
    """Öffentliche Dokumentation prüfen; liefert Liste der Probleme."""
    base = base.rstrip('/')
    problems = []
    try:
        info = json.loads(get(f'{base}/build-info.json'))
        if str(info.get('version')) != version:
            problems.append(f'Website zeigt Version {info.get("version")} statt {version}')
    except Exception as exc:  # noqa: BLE001 - jeder Fehler ist ein Befund
        problems.append(f'build-info.json nicht lesbar: {exc}')
    for lang in ('de', 'en'):
        try:
            page = get(f'{base}/{lang}/index.html')
            if f'<strong>{version}</strong>' not in page:
                problems.append(f'Startseite {lang} zeigt nicht Version {version}')
        except Exception as exc:  # noqa: BLE001
            problems.append(f'Startseite {lang} nicht erreichbar: {exc}')
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check'); c.add_argument('--version', required=True); c.add_argument('--confirm', required=True)
    c.add_argument('--prerelease', default=''); c.add_argument('--ref', default='')
    t = sub.add_parser('tag'); t.add_argument('--version', required=True); t.add_argument('--prerelease', default='')
    n = sub.add_parser('notes'); n.add_argument('--version', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--version', required=True)
    sub.add_parser('languages')
    r = sub.add_parser('report'); r.add_argument('--version', required=True)
    r.add_argument('--steps', default='{}', help='JSON {Prüfung: true/false}')
    r.add_argument('--issues', type=Path, help='JSON-Datei der offenen Meilenstein-Issues (GitHub-API)')
    r.add_argument('--milestone', default='')
    r.add_argument('--out', type=Path)
    s = sub.add_parser('site'); s.add_argument('--version', required=True)
    s.add_argument('--url', default='https://ploeffler.github.io/GhostWriter/documentation')
    args = parser.parse_args(argv)
    if args.cmd == 'prepare':
        prs = prepare(args.version)
        print(f'Version {args.version} gesetzt, Entwurf aus {len(prs)} PRs'); return 0
    if args.cmd == 'languages':
        print(json.dumps(languages(), ensure_ascii=False, indent=2)); return 0
    if args.cmd == 'report':
        raw = json.loads(args.issues.read_text()) if args.issues and args.issues.is_file() else []
        issues = [{'number': i['number'], 'title': i['title'], 'labels': [l['name'] for l in i.get('labels', [])]}
                  for i in raw if 'pull_request' not in i]
        text, ready = render_report(args.version, languages(), json.loads(args.steps), issues, args.milestone,
                                    testplan(args.version))
        (args.out.write_text(text, encoding='utf-8') if args.out else print(text))
        print('bereit' if ready else 'nicht bereit', file=sys.stderr); return 0
    if args.cmd == 'tag':
        print(tag_name(args.version, args.prerelease)); return 0
    if args.cmd == 'notes':
        de, en = notes(args.version), notes(args.version, lang='en')
        if not de:
            print(f'Release Notes für {args.version} fehlen', file=sys.stderr); return 1
        print(de + ('\n\n---\n\n' + en if en else '')); return 0
    problems = check(args.version, args.confirm, prerelease=args.prerelease, ref=args.ref) if args.cmd == 'check' else check_site(args.url, args.version)
    for problem in problems:
        print(f'- {problem}', file=sys.stderr)
    if problems:
        return 1
    print('in Ordnung')
    return 0


if __name__ == '__main__':
    sys.exit(main())
