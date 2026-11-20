#!/usr/bin/env python3
"""Abschluss-Check „Bevor du gehst …“ (#298, #372).

Trägt in einem Durchgang zusammen, was beim Verabschieden oder am Ende einer Befragung bzw.
Ideensammlung offen ist, damit keine Arbeit verloren geht:

- ungesicherte Gesprächsarbeit: weiß nur der Assistent; er gibt sie mit --chat an
  (none = nichts Neues seit der letzten Sicherung, new = Neues entschieden, verworfen oder gesammelt)
- lokale Änderungen: nicht committete Dateien und nicht hochgeladene Commits im Klon
- offene Sicherungs-PRs (`ghostwriter/chat/<id>`), wenn --repo angegeben und `gh` verfügbar ist
- Abschnitte und Teile, die auf Freigabe warten (`status: ready_for_approval`)

Nur lesend. Das Skript sichert, lädt hoch oder übernimmt nichts; es schlägt nur die Auswahl vor
(„Alles sichern und hochladen“ · „Nur das Gespräch sichern“ · „Nichts, bis morgen“).
Freigaben und `Session übernehmen` sind nie Teil dieser Auswahl (START.md, „Freigaben“).

Aufruf:
  python3 scripts/session_end.py <buch> status [--chat none|new] [--repo owner/repo] [--json]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_view import load, matter_items, section_file  # noqa: E402


def git(base, *args):
    r = subprocess.run(['git', '-C', str(base), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def local_changes(base):
    status = git(base, 'status', '--porcelain')
    if status is None:
        return {'git': False, 'uncommitted': [], 'unpushed': 0}
    files = [line[3:] for line in status.splitlines() if line.strip()]
    ahead = git(base, 'rev-list', '--count', '@{upstream}..HEAD')
    if ahead is None:   # kein Upstream: alle Commits des Branches gelten als nicht hochgeladen, wenn es welche gibt
        ahead = '0' if git(base, 'rev-parse', '--verify', '-q', 'HEAD') is None else git(base, 'rev-list', '--count', 'HEAD')
        upstream = False
    else:
        upstream = True
    return {'git': True, 'uncommitted': files, 'unpushed': int(ahead or 0), 'upstream': upstream}


def waiting(base, config):
    out = []
    for ci, ch in enumerate((config.get('structure') or {}).get('chapters') or [], start=1):
        for si, s in enumerate(ch.get('sections') or [], start=1):
            try:
                head = section_file(base, s)[0]
            except (OSError, IndexError, AttributeError):
                continue
            if head.get('status') == 'ready_for_approval':
                out.append({'id': s['id'], 'label': f'Abschnitt {ci}.{si}', 'title': s.get('title', '')})
    for _, item in matter_items(config):
        try:
            head = section_file(base, item)[0]
        except (OSError, IndexError, AttributeError):
            continue
        if head.get('status') == 'ready_for_approval':
            out.append({'id': item['id'], 'label': item.get('title', item['id']), 'title': ''})
    return out


def chat_prs(repo):
    if not repo:
        return None
    r = subprocess.run(['gh', 'api', f'repos/{repo}/pulls?state=open&per_page=100',
                        '--jq', '[.[]|select(.head.ref|startswith("ghostwriter/chat/"))|{number,title,branch:.head.ref}]'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout or '[]')
    except json.JSONDecodeError:
        return None


def status(base, chat=None, repo=None):
    base, config = load(base)
    data = {'chat': chat, 'local': local_changes(base), 'chat_prs': chat_prs(repo), 'waiting': waiting(base, config)}
    local = data['local']
    data['open'] = bool(chat == 'new' or local['uncommitted'] or local['unpushed'] or data['chat_prs'] or data['waiting'])
    choices = []
    if chat == 'new' or local['uncommitted'] or local['unpushed']:
        choices.append('Alles sichern und hochladen')
    if chat == 'new':
        choices.append('Nur das Gespräch sichern')
    if choices:
        choices.append('Nichts, bis morgen')
    data['choices'] = choices
    return data


def text(data):
    if not data['open']:
        return 'Nichts offen. Bis zum nächsten Mal!\n'
    lines = ['Bevor du gehst …']
    if data['chat'] == 'new':
        lines.append('- Gespräch: Neues seit der letzten Sicherung')
    local = data['local']
    if local['uncommitted']:
        lines.append(f'- {len(local["uncommitted"])} Datei(en) geändert, noch nicht gespeichert')
    if local['unpushed']:
        lines.append(f'- {local["unpushed"]} Änderung(en) gespeichert, aber noch nicht hochgeladen')
    if data['chat_prs']:
        nums = ', '.join(f'#{p["number"]}' for p in data['chat_prs'])
        lines.append(f'- {len(data["chat_prs"])} gesicherte(s) Gespräch(e) noch nicht übernommen ({nums}); erst danach im Wissensstand')
    if data['waiting']:
        names = ', '.join(w['label'] for w in data['waiting'][:5]) + (' …' if len(data['waiting']) > 5 else '')
        lines.append(f'- {len(data["waiting"])} warten auf Freigabe: {names}')
    if data['choices']:
        lines.append('Auswahl: ' + ' · '.join(data['choices']))
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='Abschluss-Check (nur lesend)')
    ap.add_argument('project')
    ap.add_argument('action', choices=['status'])
    ap.add_argument('--chat', choices=['none', 'new'], help='ungesicherte Gesprächsarbeit laut Assistent')
    ap.add_argument('--repo', help='owner/repo für offene Sicherungs-PRs')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    data = status(args.project, args.chat, args.repo)
    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else text(data), end='\n' if args.json else '')


if __name__ == '__main__':
    main()
