#!/usr/bin/env python3
"""Gesamtsicherung: das Repository als lesbare und wiederherstellbare ZIP-Datei (#489).

  python3 scripts/sicherung.py erstellen <repo-ordner> [-o datei.zip] [--repo owner/name] [--ohne-github]
  python3 scripts/sicherung.py pruefen <datei.zip>

Die Datei enthält

  LIESMICH.html              zuerst öffnen: Inhalt, Lesen, Wiederherstellen, Grenzen
  buecher/<buch>/            Lesefassung (HTML, EPUB, wenn möglich PDF) und `quelltext/` (Kapitel, Buchprofil, Bilder)
  repository.bundle          vollständiges Git: alle Branches (auch `buch/*`), Tags, Historie
  github-einstellungen.json  Einstellungen, die nicht im Git liegen (Secrets nur mit Namen, nie mit Werten)
  github-daten/              Issues und Pull Requests mit Kommentaren (JSON und lesbare Fassung)
  wiederherstellen/          Skripte: auf GitHub oder einen eigenen Git-Server, lokal öffnen
  pruefsummen.txt            SHA-256 aller Dateien (`sha256sum -c`), Datum, Programmversion, Commit-Stände

Nie gelesen oder ausgegeben werden Secret-Werte. Die Datei enthält private Bucharbeit: nur als Download im Chat bzw. als
privates Workflow-Artefakt weitergeben, nie als Release oder öffentlich. Verschlüsselung und eine automatische
Wiederholung gibt es in dieser Fassung nicht.
"""
import argparse
import datetime
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SECRET_PATTERNS = [re.compile(p) for p in (
    r'ghp_[A-Za-z0-9]{30,}', r'github_pat_[A-Za-z0-9_]{30,}', r'gh[ousr]_[A-Za-z0-9]{30,}', r'sk-[A-Za-z0-9_-]{24,}',
    r'sk-ant-[A-Za-z0-9_-]{20,}', r'AIza[0-9A-Za-z_-]{35}', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]


def run(cmd, cwd=None, check=True, env=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    if check and r.returncode:
        raise RuntimeError(f'{" ".join(map(str, cmd[:4]))} …: {(r.stderr or r.stdout).strip()[:300]}')
    return r


def git(repo, *args, check=True):
    return run(['git', '-C', str(repo), *args], check=check)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', str(text).lower().translate(str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss'}))).strip('-') or 'buch'


# ---------- Git ----------

def mirror(repo, target):
    """Bares Repository mit allen Branches (lokale und die von `origin`), Tags und Historie; lokale Branches gewinnen.
    Ein flacher Klon liefert keine vollständige Historie und wird abgelehnt."""
    if git(repo, 'rev-parse', '--is-shallow-repository').stdout.strip() == 'true':
        raise RuntimeError('Der Klon ist flach (keine vollständige Historie). Zuerst `git fetch --unshallow`.')
    run(['git', 'init', '-q', '--bare', str(target)])
    fetch = ['git', '-C', str(target), 'fetch', '-q', '--no-tags', str(repo)]
    run(fetch + ['+refs/remotes/origin/*:refs/heads/*'], check=False)
    run(fetch + ['+refs/heads/*:refs/heads/*', '+refs/tags/*:refs/tags/*'])
    run(['git', '-C', str(target), 'update-ref', '-d', 'refs/heads/HEAD'], check=False)
    return target


def branches(bare):
    out = run(['git', '-C', str(bare), 'for-each-ref', '--format=%(refname:short) %(objectname)', 'refs/heads']).stdout
    return dict(line.split(' ', 1) for line in out.splitlines() if line.strip())


def tags(bare):
    out = run(['git', '-C', str(bare), 'for-each-ref', '--format=%(refname:short) %(objectname)', 'refs/tags']).stdout
    return dict(line.split(' ', 1) for line in out.splitlines() if line.strip())


def file_at(bare, ref, path):
    r = run(['git', '-C', str(bare), 'show', f'{ref}:{path}'], check=False)
    return r.stdout if r.returncode == 0 else None


def _head_of(repo_dir):
    return git(repo_dir, 'symbolic-ref', '-q', '--short', 'HEAD', check=False).stdout.strip()


def default_branch(bare, names, head=''):
    for cand in (head, 'main', 'master'):
        if cand in names:
            return cand
    return sorted(names)[0] if names else ''


def book_branches(bare, names, default):
    """Branches mit einem Buch: `buch/*` und der Standard-Branch, wenn er selbst Kapitel hat."""
    found = []
    for name in sorted(names):
        text = file_at(bare, name, 'ghostwriter.yml')
        try:
            cfg = yaml.safe_load(text) if text else {}
        except yaml.YAMLError:
            cfg = {}
        chapters = ((cfg or {}).get('structure') or {}).get('chapters') or []
        if name.startswith('buch/') or (name == default and chapters):
            found.append((name, cfg or {}, bool(chapters)))
    return found


def export_tree(bare, ref, target):
    target.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(['git', '-C', str(bare), 'archive', ref], capture_output=True)
    if archive.returncode:
        raise RuntimeError(f'git archive {ref}: {archive.stderr.decode("utf-8", "replace")[:200]}')
    subprocess.run(['tar', '-x', '-C', str(target)], input=archive.stdout, check=True)


# ---------- Lesefassung ----------

def which_pdf():
    return bool(shutil.which('xelatex'))


def build_reading(work, out, title, notes):
    """HTML (eigenständig), EPUB und, wenn möglich, PDF aus dem Arbeitsstand; nichts wird umformuliert."""
    out.mkdir(parents=True, exist_ok=True)
    md = out / 'buch.md'
    r = run([sys.executable, str(ROOT / 'scripts' / 'assemble.py'), str(work), 'manuscript', '-o', str(md)], check=False)
    if r.returncode or not md.is_file():
        notes.append(f'Lesefassung nicht erzeugt: {(r.stderr or r.stdout).strip()[:160]}')
        return []
    made = []
    base = ['pandoc', '--from', 'markdown+smart', '--standalone', '--metadata', f'title={title}', str(md)]
    for ext, extra in (('html', ['--embed-resources']), ('epub', [])):
        target = out / f'buch.{ext}'
        res = run(base + extra + ['-o', str(target), '--resource-path', str(work)], check=False)
        if res.returncode and ext == 'html':
            res = run(base + ['--self-contained', '-o', str(target), '--resource-path', str(work)], check=False)
        if res.returncode:
            notes.append(f'{ext.upper()} nicht erzeugt: {res.stderr.strip()[:160]}')
        else:
            made.append(target.name)
    if which_pdf():
        tmp = out / '_pdf'
        res = run([sys.executable, str(ROOT / 'scripts' / 'build_edition.py'), str(work), '--manuscript', '--formats', 'pdf', '--out', str(tmp)],
                  check=False)
        pdfs = sorted(tmp.glob('**/*.pdf')) if tmp.is_dir() else []
        if res.returncode == 0 and pdfs:
            shutil.copyfile(pdfs[0], out / 'buch.pdf')
            made.append('buch.pdf')
        else:
            notes.append(f'PDF nicht erzeugt: {(res.stderr or res.stdout).strip()[:160]}')
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        notes.append('PDF nicht erzeugt: kein LaTeX (xelatex) auf diesem Rechner; die Action „Gesamtsicherung“ baut es')
    md.unlink(missing_ok=True)
    return made


def copy_source(work, target):
    """Das Buch ohne Programm: die Pfade aus `book` des Manifests und die Kapitel."""
    manifest = yaml.safe_load((ROOT / 'ghostwriter-manifest.yml').read_text(encoding='utf-8')) or {}
    wanted = [p.rstrip('/') for p in manifest.get('book') or []] + ['chapters', 'matter', 'images']
    for rel in dict.fromkeys(wanted):
        src = Path(work) / rel
        if src.is_dir():
            shutil.copytree(src, target / rel, dirs_exist_ok=True)
        elif src.is_file():
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target / rel)


# ---------- GitHub ----------

def gh_fetch(path):
    """Eine GitHub-API-Antwort über `gh api` (eigene Anmeldung); Listen vollständig."""
    r = run(['gh', 'api', '--paginate', '-H', 'Accept: application/vnd.github+json', path], check=False)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[:200] or 'gh api fehlgeschlagen')
    text = r.stdout.strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError:   # --paginate hängt mehrere JSON-Dokumente aneinander
        merged, dec, i = [], json.JSONDecoder(), 0
        while i < len(text):
            obj, j = dec.raw_decode(text, i)
            merged += obj if isinstance(obj, list) else [obj]
            i = j
            while i < len(text) and text[i].isspace():
                i += 1
        return merged


def settings(repo, fetch):
    """Einstellungen, die nicht im Git stehen. Secrets nur mit Namen; jeder Abschnitt einzeln, damit ein fehlendes Recht nur
    diesen Abschnitt unlesbar macht."""
    out, base = {'repository': repo, 'hinweis': 'Secret-Werte werden nie gelesen. Nicht lesbare Abschnitte stehen mit Grund unter `nicht_lesbar`.'}, f'repos/{repo}'
    unreadable = {}

    def part(key, path, pick=None):
        try:
            data = fetch(f'{base}{path}')
            out[key] = pick(data) if pick else data
        except Exception as exc:   # noqa: BLE001 – jede Quelle einzeln
            unreadable[key] = str(exc)[:200]
    part('repository_einstellungen', '', lambda d: {k: d.get(k) for k in (
        'full_name', 'description', 'private', 'visibility', 'default_branch', 'has_issues', 'has_projects', 'has_wiki',
        'allow_merge_commit', 'allow_squash_merge', 'allow_rebase_merge', 'delete_branch_on_merge', 'archived', 'fork')})
    part('actions_rechte', '/actions/permissions')
    part('workflow_rechte', '/actions/permissions/workflow')
    part('workflows', '/actions/workflows', lambda d: [{'name': w.get('name'), 'pfad': w.get('path'), 'zustand': w.get('state')}
                                                          for w in (d.get('workflows') if isinstance(d, dict) else d) or []])
    part('secrets_namen', '/actions/secrets', lambda d: sorted(s['name'] for s in (d.get('secrets') if isinstance(d, dict) else d) or []))
    part('variablen', '/actions/variables', lambda d: [{'name': v['name'], 'wert': v.get('value', '')}
                                                        for v in (d.get('variables') if isinstance(d, dict) else d) or []])
    part('pages', '/pages')
    part('environments', '/environments', lambda d: [e.get('name') for e in (d.get('environments') if isinstance(d, dict) else d) or []])
    part('mitarbeitende', '/collaborators', lambda d: [{'login': c.get('login'), 'rechte': c.get('role_name') or c.get('permissions')} for c in d or []])
    default = (out.get('repository_einstellungen') or {}).get('default_branch')
    if default:
        part('branch_schutz', f'/branches/{default}/protection')
    out['installierte_apps'] = 'nicht über die API lesbar; bitte unter GitHub → Einstellungen → Installierte GitHub-Apps notieren'
    if unreadable:
        out['nicht_lesbar'] = unreadable
    return out


def discussions(repo, fetch):
    """Issues und Pull Requests mit Kommentaren: (Daten, Hinweise)."""
    base, notes = f'repos/{repo}', []

    def get(path):
        try:
            return fetch(path) or []
        except Exception as exc:   # noqa: BLE001
            notes.append(f'{path}: {str(exc)[:120]}')
            return []
    issues = [i for i in get(f'{base}/issues?state=all&per_page=100') if 'pull_request' not in i]
    pulls = get(f'{base}/pulls?state=all&per_page=100')
    comments = get(f'{base}/issues/comments?per_page=100')
    review = get(f'{base}/pulls/comments?per_page=100')
    by_issue, by_pull = {}, {}
    for c in comments:
        by_issue.setdefault(c.get('issue_url', '').rsplit('/', 1)[-1], []).append({k: c.get(k) for k in ('user', 'created_at', 'body')})
    for c in review:
        by_pull.setdefault(str(c.get('pull_request_url', '')).rsplit('/', 1)[-1], []).append(
            {k: c.get(k) for k in ('user', 'created_at', 'body', 'path')})
    trim = lambda c: dict(c, user=(c.get('user') or {}).get('login') if isinstance(c.get('user'), dict) else c.get('user'))   # noqa: E731
    out_i = [{'nummer': i['number'], 'titel': i.get('title'), 'zustand': i.get('state'), 'autor': (i.get('user') or {}).get('login'),
              'labels': [x['name'] for x in i.get('labels') or []], 'erstellt': i.get('created_at'), 'text': i.get('body') or '',
              'kommentare': [trim(c) for c in by_issue.get(str(i['number']), [])]} for i in issues]
    out_p = [{'nummer': p['number'], 'titel': p.get('title'), 'zustand': p.get('state'), 'autor': (p.get('user') or {}).get('login'),
              'von': (p.get('head') or {}).get('ref'), 'nach': (p.get('base') or {}).get('ref'), 'gemergt': bool(p.get('merged_at')),
              'erstellt': p.get('created_at'), 'text': p.get('body') or '',
              'kommentare': [trim(c) for c in by_issue.get(str(p['number']), [])],
              'code_kommentare': [trim(c) for c in by_pull.get(str(p['number']), [])]} for p in pulls]
    return {'issues': out_i, 'pulls': out_p}, notes


def discussions_md(data):
    lines = ['# Issues und Pull Requests', '']
    for kind, label in (('issues', 'Issue'), ('pulls', 'Pull Request')):
        lines += [f'## {label}s ({len(data[kind])})', '']
        for it in sorted(data[kind], key=lambda x: x['nummer']):
            lines += [f'### {label} {it["nummer"]}: {it["titel"]} ({it["zustand"]}, {it["autor"]}, {str(it["erstellt"])[:10]})', '', it['text'].strip(), '']
            for c in it['kommentare'] + it.get('code_kommentare', []):
                lines += [f'> **{c["user"]}** ({str(c["created_at"])[:10]}):', ''] + [f'> {x}' for x in str(c['body']).splitlines()] + ['']
    return '\n'.join(lines)


# ---------- Wiederherstellen ----------

RESTORE_SH = '''#!/usr/bin/env bash
# Wiederherstellen auf GitHub oder einem eigenen Git-Server (GhostWriter-Sicherung, #489).
# Aufruf:  ./auf-github.sh <ziel-url> [nur-git]   z. B. https://github.com/NAME/neues-repo.git (leeres Repository vorher anlegen)
#          nur-git überspringt Schritt 4 (Einstellungen), etwa für einen eigenen Git-Server ohne GitHub
# Der GitHub-Import nimmt keine Bundles an; deshalb: Spiegel klonen und mit `git push --mirror` übertragen.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
target="${1:-}"
[ -n "$target" ] || { echo "Ziel angeben: ./auf-github.sh https://github.com/NAME/neues-repo.git"; exit 1; }
cd "$here"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
echo "1/4 Prüfsummen und Bundle prüfen"
sha256sum -c pruefsummen.txt --quiet
git init -q "$work/pruefen" && git -C "$work/pruefen" bundle verify "$here/repository.bundle" >/dev/null
echo "2/4 Spiegel anlegen"
git clone --mirror -q repository.bundle "$work/spiegel.git"
echo "3/4 Auf das Ziel übertragen (alle Branches, Tags, Historie)"
git -C "$work/spiegel.git" push --mirror "$target"
if [ "${2:-}" = "nur-git" ]; then echo "Fertig (nur Git)."; exit 0; fi
echo "4/4 Einstellungen (nicht im Git)"
repo="$(echo "$target" | sed -E 's#^(https://[^/]+/|git@[^:]+:)##; s#\\.git$##')"
if command -v gh >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1 && [ -f github-einstellungen.json ]; then
  python3 - "$repo" <<'PY'
import json, subprocess, sys
repo = sys.argv[1]
s = json.load(open('github-einstellungen.json', encoding='utf-8'))
def gh(*a, **kw):
    return subprocess.run(['gh', *a], **kw)
gh('api', '-X', 'PUT', f'repos/{repo}/actions/permissions', '-F', 'enabled=true')
w = s.get('workflow_rechte') or {}
if w:
    gh('api', '-X', 'PUT', f'repos/{repo}/actions/permissions/workflow', '-f', f'default_workflow_permissions={w.get("default_workflow_permissions", "write")}',
       '-F', f'can_approve_pull_request_reviews={str(w.get("can_approve_pull_request_reviews", True)).lower()}')
for v in s.get('variablen') or []:
    gh('variable', 'set', v['name'], '--body', v['wert'], '--repo', repo)
offen = []
for name in s.get('secrets_namen') or []:
    print(f'Wert für das Secret {name} (Eingabe leer = überspringen): ', end='', flush=True)
    value = sys.stdin.readline().strip()
    if value:
        gh('secret', 'set', name, '--repo', repo, input=value, text=True)
    else:
        offen.append(name)
print('Noch offen (Secrets):', ', '.join(offen) or 'nichts')
PY
  echo "Probelauf: gh workflow run <Workflow> --repo $repo (zum Beispiel „Projektdateien prüfen“)."
else
  echo "Ohne gh und python3 die Schritte in LIESMICH.html („Einstellungen von Hand“) durchklicken."
fi
echo "Fertig. Prüfe auf GitHub: Actions aktiviert, Secrets gesetzt, Pages, Branch-Schutz."
'''

RESTORE_BAT = '''@echo off
rem Wiederherstellen auf GitHub oder einem eigenen Git-Server (GhostWriter-Sicherung, #489).
rem Aufruf:  auf-github.bat <ziel-url>
setlocal
if "%~1"=="" (echo Ziel angeben: auf-github.bat https://github.com/NAME/neues-repo.git & exit /b 1)
pushd "%~dp0.."
set WORK=%TEMP%\\gw-sicherung-%RANDOM%
git init -q "%WORK%\\pruefen" && git -C "%WORK%\\pruefen" bundle verify "%CD%\\repository.bundle" || (echo Bundle ist beschaedigt & exit /b 1)
git clone --mirror repository.bundle "%WORK%\\spiegel.git" || exit /b 1
git -C "%WORK%\\spiegel.git" push --mirror %1 || exit /b 1
rmdir /s /q "%WORK%"
echo Fertig. Einstellungen (Actions, Secrets, Pages) bitte nach LIESMICH.html durchklicken.
popd
'''

OPEN_SH = '''#!/usr/bin/env bash
# Lesefassung lokal öffnen (GhostWriter-Sicherung, #489): ohne Git und ohne GitHub.
here="$(cd "$(dirname "$0")/.." && pwd)"
first="$(ls "$here"/buecher/*/buch.html 2>/dev/null | head -n1)"
target="${first:-$here/LIESMICH.html}"
if command -v xdg-open >/dev/null 2>&1; then xdg-open "$target"; elif command -v open >/dev/null 2>&1; then open "$target"; else echo "$target"; fi
'''

OPEN_BAT = '''@echo off
rem Lesefassung lokal oeffnen (GhostWriter-Sicherung, #489)
for %%f in ("%~dp0..\\buecher\\*\\buch.html") do (start "" "%%f" & exit /b 0)
start "" "%~dp0..\\LIESMICH.html"
'''


def readme_html(info):
    e = html.escape
    books = ''.join(f'<li><b>{e(b["titel"])}</b> ({e(b["branch"])}) – Lesefassung: {e(", ".join(b["formate"]) or "keine")}</li>' for b in info['buecher']) \
        or '<li>Kein Buch in diesem Repository.</li>'
    notes = ''.join(f'<li>{e(n)}</li>' for n in info['hinweise']) or '<li>keine</li>'
    gh = 'Einstellungen und Issues/Pull Requests sind enthalten.' if info['github'] else \
        'Ohne GitHub-Zugang erstellt: <code>github-einstellungen.json</code> und <code>github-daten/</code> fehlen.'
    return f'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GhostWriter-Sicherung {e(info["repo"])}</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:48rem;margin:2rem auto;padding:0 1rem;color:#222}}code,pre{{background:#f3f3f3;padding:.1em .3em;border-radius:3px}}pre{{padding:.7em;overflow:auto}}h2{{margin-top:2rem}}</style></head>
<body>
<h1>GhostWriter-Sicherung</h1>
<p>Repository <b>{e(info["repo"])}</b>, erstellt am {e(info["datum"])}, GhostWriter {e(info["version"])}. <b>Diese Datei enthält private Bucharbeit.</b> Nicht öffentlich weitergeben, nicht als Release hochladen.</p>

<h2>Was ist drin?</h2>
<ul>
<li><b>Bücher lesen:</b> <code>buecher/&lt;buch&gt;/buch.html</code> im Browser (EPUB für E-Reader{', PDF zum Drucken' if info['pdf'] else ''}). Dazu <code>quelltext/</code> mit Kapiteln als Textdateien, Bildern und Buchprofil.</li>
<li><b>Alles in Git:</b> <code>repository.bundle</code> enthält alle Branches (auch <code>buch/*</code>), Tags und die ganze Historie.</li>
<li><b>Einstellungen:</b> <code>github-einstellungen.json</code> (Secrets nur mit Namen, nie mit Werten).</li>
<li><b>Issues und Pull Requests:</b> <code>github-daten/</code> (<code>lesbar.md</code> zum Lesen, JSON für Programme).</li>
<li><b>Prüfsummen:</b> <code>pruefsummen.txt</code> (SHA-256, Programmversion, Stand der Branches).</li>
</ul>
<p>{gh}</p>
<h3>Bücher in dieser Sicherung</h3><ul>{books}</ul>
<h3>Hinweise zu dieser Sicherung</h3><ul>{notes}</ul>

<h2>Lesen ohne Git und ohne GitHub</h2>
<p>Doppelklick auf <code>wiederherstellen/lokal-oeffnen.sh</code> bzw. <code>.bat</code> oder die Datei <code>buecher/…/buch.html</code> im Browser öffnen.</p>

<h2>Wiederherstellen</h2>
<p><b>Lokal:</b></p>
<pre>git clone repository.bundle mein-buch</pre>
<p>Danach lässt sich der Ordner auf jedes beliebige Ziel pushen (<code>git remote add</code>, <code>git push --mirror</code>).</p>
<p><b>Auf GitHub:</b> leeres Repository anlegen, dann</p>
<pre>./wiederherstellen/auf-github.sh https://github.com/NAME/neues-repo.git</pre>
<p>(Windows: <code>wiederherstellen\\auf-github.bat</code>). Das Skript prüft zuerst Prüfsummen und Bundle (<code>git bundle verify</code>), klont einen Spiegel und überträgt alle Branches, Tags und die Historie. Der GitHub-Import selbst nimmt keine Bundles an. Auf einem eigenen Git-Server (Gitea, Forgejo, nacktes Git) genügt dasselbe <code>git push --mirror</code>.</p>

<h2>Einstellungen von Hand (nicht im Git)</h2>
<ol>
<li>Settings → Actions → General: Actions erlauben; Workflow permissions: <b>Read and write</b>, „Allow GitHub Actions to create and approve pull requests“.</li>
<li>Settings → Secrets and variables → Actions: die Namen aus <code>github-einstellungen.json</code> (<code>secrets_namen</code>) als Secrets anlegen, die Werte hast nur du; Variablen (<code>variablen</code>) mit den gesicherten Werten.</li>
<li>Pages, Environments, Branch-Schutz, Mitarbeitende und installierte GitHub-Apps: wie in <code>github-einstellungen.json</code> notiert einrichten.</li>
<li>Probelauf: Actions → „Projektdateien prüfen“ → Run workflow. Läuft er, laufen die Actions.</li>
</ol>

<h2>Grenzen</h2>
<ul>
<li><b>Secret-Werte sind nie enthalten.</b> Sie müssen neu eingegeben werden.</li>
<li>Lauf-Verlauf, Logs und Artefakte der Actions gehen verloren.</li>
<li>Zeitpläne laufen auf Forks erst nach dem Einschalten der Actions und pausieren nach 60 Tagen ohne Aktivität.</li>
<li>Die Lesefassung zeigt den Arbeitsstand mit allen Abschnitten (auch nicht abgeschlossene), keine Auflage.</li>
</ul>
</body></html>
'''


# ---------- Erstellen und Prüfen ----------

def program_version():
    try:
        return str((yaml.safe_load((ROOT / 'ghostwriter-manifest.yml').read_text(encoding='utf-8')) or {}).get('version') or '?')
    except (OSError, yaml.YAMLError):
        return '?'


def erstellen(repo_dir, out=None, repo=None, github=True, fetch=None, today=None):
    """Sicherung erstellen; gibt (Pfad der ZIP-Datei, Bericht) zurück. Fehler: RuntimeError, nichts bleibt halb fertig liegen."""
    repo_dir = Path(repo_dir)
    today = today or datetime.date.today().isoformat()
    repo = repo or _repo_name(repo_dir)
    notes = []
    info = {'repo': repo, 'datum': today, 'version': program_version(), 'buecher': [], 'hinweise': notes, 'github': False, 'pdf': False}
    name = f'GhostWriter-Sicherung_{slug(repo.split("/")[-1])}_{today}'
    out = Path(out) if out else Path.cwd() / f'{name}.zip'
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        root = tmp / name
        root.mkdir()
        bare = mirror(repo_dir, tmp / 'spiegel.git')
        names = branches(bare)
        if not names:
            raise RuntimeError('Das Repository hat keine Branches')
        default = default_branch(bare, names, _head_of(repo_dir))
        run(['git', '-C', str(bare), 'symbolic-ref', 'HEAD', f'refs/heads/{default}'])
        run(['git', '-C', str(bare), 'bundle', 'create', str(root / 'repository.bundle'), '--all'])
        verify = run(['git', '-C', str(bare), 'bundle', 'verify', str(root / 'repository.bundle')], check=False)
        if verify.returncode:
            raise RuntimeError('Das Bundle ist nicht gültig: ' + (verify.stderr or verify.stdout).strip()[:200])
        used = set()
        for branch, cfg, has_chapters in book_branches(bare, names, default):
            title = ((cfg.get('project') or {}).get('title') or (cfg.get('project') or {}).get('working_title') or branch)
            folder = slug(branch.split('/', 1)[-1] if branch.startswith('buch/') else title)
            while folder in used:
                folder += '-2'
            used.add(folder)
            work = tmp / 'arbeit' / folder
            export_tree(bare, branch, work)
            target = root / 'buecher' / folder
            made = build_reading(work, target, str(title), notes) if has_chapters else []
            if has_chapters:
                copy_source(work, target / 'quelltext')
            else:
                notes.append(f'{branch}: noch keine Kapitel, nur das Git')
            info['buecher'].append({'branch': branch, 'titel': str(title), 'ordner': folder, 'formate': made, 'commit': names[branch]})
            info['pdf'] = info['pdf'] or 'buch.pdf' in made
            shutil.rmtree(work, ignore_errors=True)
        if github:
            fetch = fetch or gh_fetch
            try:
                data = settings(repo, fetch)
                (root / 'github-einstellungen.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                posts, more = discussions(repo, fetch)
                notes += [m for m in more if m not in notes]
                (root / 'github-daten').mkdir()
                (root / 'github-daten' / 'issues.json').write_text(json.dumps(posts['issues'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                (root / 'github-daten' / 'pull-requests.json').write_text(json.dumps(posts['pulls'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                (root / 'github-daten' / 'lesbar.md').write_text(discussions_md(posts), encoding='utf-8')
                info['github'] = not data.get('nicht_lesbar') or len(data['nicht_lesbar']) < 5
                for key, why in (data.get('nicht_lesbar') or {}).items():
                    notes.append(f'Einstellung „{key}“ nicht lesbar: {why}')
            except Exception as exc:   # noqa: BLE001 – ohne GitHub-Zugang bleibt die Sicherung gültig
                notes.append(f'GitHub-Daten nicht gesichert: {str(exc)[:160]}')
        (root / 'wiederherstellen').mkdir()
        for fname, text in (('auf-github.sh', RESTORE_SH), ('auf-github.bat', RESTORE_BAT), ('lokal-oeffnen.sh', OPEN_SH), ('lokal-oeffnen.bat', OPEN_BAT)):
            p = root / 'wiederherstellen' / fname
            p.write_text(text if fname.endswith('.sh') else text.replace('\n', '\r\n'), encoding='utf-8', newline='')
            if fname.endswith('.sh'):
                p.chmod(0o755)
        (root / 'LIESMICH.html').write_text(readme_html(info), encoding='utf-8')
        sums = []
        for p in sorted(root.rglob('*')):
            if p.is_file():
                sums.append(f'{sha256(p)}  {p.relative_to(root).as_posix()}')
        header = [f'# GhostWriter-Sicherung {repo}', f'# Datum: {today}', f'# Programmversion: {info["version"]}'] + \
                 [f'# Stand {b}: {c}' for b, c in sorted(names.items())] + [f'# Tag {t}: {c}' for t, c in sorted(tags(bare).items())]
        (root / 'pruefsummen.txt').write_text('\n'.join(header + sums) + '\n', encoding='utf-8')
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in sorted(root.rglob('*')):
                if p.is_file():
                    z.write(p, f'{name}/{p.relative_to(root).as_posix()}')
    problems = pruefen(out)
    if problems:
        out.unlink(missing_ok=True)
        raise RuntimeError('Die Sicherung besteht die eigene Prüfung nicht: ' + '; '.join(problems[:3]))
    info['hinweise'][:] = list(dict.fromkeys(info['hinweise']))
    info['datei'] = str(out)
    info['branches'] = len(names)
    return out, info


def _repo_name(repo_dir):
    r = git(repo_dir, 'config', '--get', 'remote.origin.url', check=False).stdout.strip()
    m = re.search(r'[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$', r)
    return m.group(1) if m else Path(repo_dir).resolve().name


def pruefen(path):
    """Eine Sicherung prüfen: Pflichtdateien, Prüfsummen, Bundle und Secret-Muster. → Liste der Probleme (leer = in Ordnung)."""
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        try:
            with zipfile.ZipFile(path) as z:
                bad = z.testzip()
                if bad:
                    return [f'ZIP beschädigt: {bad}']
                z.extractall(tmp)
        except (OSError, zipfile.BadZipFile) as exc:
            return [f'Datei nicht lesbar: {exc}']
        tops = [p for p in Path(tmp).iterdir() if p.is_dir()]
        if len(tops) != 1:
            return ['Unerwarteter Aufbau der ZIP-Datei']
        root = tops[0]
        for need in ('LIESMICH.html', 'repository.bundle', 'pruefsummen.txt', 'wiederherstellen/auf-github.sh', 'wiederherstellen/lokal-oeffnen.sh'):
            if not (root / need).is_file():
                problems.append(f'fehlt: {need}')
        if problems:
            return problems
        listed = {}
        for line in (root / 'pruefsummen.txt').read_text(encoding='utf-8').splitlines():
            if line and not line.startswith('#'):
                digest, _, rel = line.partition('  ')
                listed[rel] = digest
        for rel, digest in listed.items():
            f = root / rel
            if not f.is_file():
                problems.append(f'Prüfsumme ohne Datei: {rel}')
            elif sha256(f) != digest:
                problems.append(f'Prüfsumme weicht ab: {rel}')
        for p in root.rglob('*'):
            if p.is_file() and p.name != 'pruefsummen.txt' and p.relative_to(root).as_posix() not in listed:
                problems.append(f'ohne Prüfsumme: {p.relative_to(root).as_posix()}')
        scratch = Path(tmp) / '_pruefen'
        run(['git', 'init', '-q', str(scratch)])
        v = run(['git', 'bundle', 'verify', str(root / 'repository.bundle')], cwd=scratch, check=False)
        if v.returncode:
            problems.append('Bundle ungültig: ' + (v.stderr or v.stdout).strip()[:120])
        for p in root.rglob('*'):
            if not p.is_file() or p.name == 'repository.bundle' or p.suffix.lower() in ('.epub', '.pdf', '.png', '.jpg', '.jpeg', '.zip'):
                continue
            try:
                text = p.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue
            for pat in SECRET_PATTERNS:
                if pat.search(text):
                    problems.append(f'Secret-ähnlicher Wert in {p.relative_to(root).as_posix()}')
                    break
    return problems


def summary(info):
    lines = [f'✓ Sicherung erstellt: {info["datei"]}', f'  {len(info["buecher"])} Buch/Bücher, {info["branches"]} Branches']
    for b in info['buecher']:
        lines.append(f'  - {b["titel"]} ({b["branch"]}): {", ".join(b["formate"]) or "keine Lesefassung"}')
    lines.append('  GitHub-Einstellungen und Issues/PRs: ' + ('enthalten' if info['github'] else 'nicht enthalten'))
    for n in info['hinweise']:
        lines.append(f'  ⚠ {n}')
    lines.append('  Private Bucharbeit: nur als Download oder privates Artefakt weitergeben, nie als Release.')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('erstellen')
    e.add_argument('repo_dir')
    e.add_argument('-o', '--out')
    e.add_argument('--repo', help='owner/name (sonst aus origin)')
    e.add_argument('--ohne-github', action='store_true', help='keine Einstellungen, Issues und Pull Requests lesen')
    p = sub.add_parser('pruefen')
    p.add_argument('datei')
    a = ap.parse_args(argv)
    if a.cmd == 'pruefen':
        problems = pruefen(a.datei)
        print('\n'.join(problems) if problems else '✓ Sicherung ist in Ordnung (Prüfsummen, Bundle, keine Secret-Werte).')
        return 1 if problems else 0
    try:
        out, info = erstellen(a.repo_dir, a.out, a.repo, github=not a.ohne_github)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(summary(info), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
