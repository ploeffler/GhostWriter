#!/usr/bin/env python3
"""Team und Rollen je Buch (#455, Teil 1; D03).

`team` in ghostwriter.yml ordnet GitHub-Logins eine Rolle zu:

  team:
    - {github: anna, role: owner}
    - {github: ben, role: editor, name: "Ben Muster", email: "123+ben@users.noreply.github.com", approve: false}
    - {github: cleo, role: reader}

Rollen: owner (Eigentümer), editor (Bearbeiter), reader (Leser). `approve: true` macht einen Bearbeiter
freigabeberechtigt (abschließen, wieder öffnen, Auflage, Sammelband). Eigentümer dürfen das immer.
Fehlt `team`, gilt alles wie bisher: wer Schreibrecht hat, ist Eigentümer. Steht ein Login nicht in der
Liste, ist er Leser. Die GitHub-Rechte begrenzen immer; eine Rolle erweitert sie nie.

Aufruf:
  python3 scripts/team.py <buch> role <login> [--push true|false] [--json]
      Rolle, Rechte und Git-Benutzer für Commits dieser Person (aus dem Team-Eintrag, sonst assistant.yml)
  python3 scripts/team.py <buch> check
      Team-Liste prüfen (genau gelesen auch von validate_project.py)

Teil 1 legt Rollen und Git-Benutzer fest; der Assistent bietet danach nur erlaubte Aktionen an. Die Prüfung
im Änderungspaket (Abschlüsse nur durch Freigabeberechtigte) folgt in Teil 2. Bis dahin ist die Rolle eine
Regel für den Assistenten, keine technische Sperre: Wer Schreibrecht hat, kann auch selbst Dateien ändern.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

ROLES = ('owner', 'editor', 'reader')
ROLE_DE = {'owner': 'Eigentümer', 'editor': 'Bearbeiter', 'reader': 'Leser'}
ROLE_EN = {'owner': 'owner', 'editor': 'editor', 'reader': 'reader'}
# Aktionen, die Freigabeberechtigung brauchen (D03): Bestätigungen „Freigabe“ (abschließen, wieder öffnen,
# Schreiben erlauben, Bildfreigabe), Auflagen und Sammelbände. Übernehmen eines Änderungspakets bleibt erlaubt.
APPROVAL_ACTIONS = ('approval.open', 'approval.confirm', 'edition.create.open', 'edition.create',
                    'series.omnibus.approve', 'series.omnibus.revoke', 'series.omnibus.publish')


def team(config):
    return (config or {}).get('team') or []


def problems(config):
    """Fehler in der Team-Liste (ohne Schemaprüfung)."""
    out, seen = [], set()
    entries = team(config)
    for e in entries:
        login = str(e.get('github', '')).lower()
        if login in seen:
            out.append(f'team: {e.get("github")} doppelt')
        seen.add(login)
        if e.get('approve') and e.get('role') != 'editor':
            out.append(f'team: {e.get("github")}: approve nur bei role: editor (Eigentümer dürfen immer, Leser nie)')
    if entries and not any(e.get('role') == 'owner' for e in entries):
        out.append('team: mindestens ein Eintrag mit role: owner nötig')
    return out


def git_user(base, entry):
    """Git-Benutzer für Commits: Team-Eintrag, sonst assistant.yml (Standard-Branch bzw. dieses Verzeichnis)."""
    if entry and entry.get('name') and entry.get('email'):
        return {'name': entry['name'], 'email': entry['email'], 'source': 'team'}
    p = Path(base) / 'assistant.yml'
    prof = (yaml.safe_load(p.read_text(encoding='utf-8')) or {}) if p.is_file() else {}
    g = prof.get('git') or {}
    if g.get('name') and g.get('email') and (not entry or entry.get('role') == 'owner'):
        return {'name': g['name'], 'email': g['email'], 'source': 'assistant.yml'}
    return None


def role(base, config, login, push=None):
    """Rolle und Rechte eines Logins. push: tatsächliches GitHub-Schreibrecht (None = unbekannt)."""
    entries = team(config)
    entry = next((e for e in entries if str(e.get('github', '')).lower() == str(login or '').lower()), None)
    if not entries:
        r, source = 'owner', 'ohne team'
    elif entry:
        r, source = entry['role'], 'team'
    else:
        r, source = 'reader', 'nicht im team'
    write = r in ('owner', 'editor')
    approve = r == 'owner' or (r == 'editor' and bool((entry or {}).get('approve')))
    limited = push is False
    if limited:                       # GitHub-Rechte begrenzen immer (D03)
        write = approve = False
    user = git_user(base, entry) if write else None
    return {'login': login, 'role': r, 'role_text': ROLE_DE[r], 'source': source, 'write': write, 'approve': approve,
            'github_push': push, 'git': user,
            'not_offered': [] if approve else list(APPROVAL_ACTIONS) if write else ['alle Schreibaktionen']}


def summary(info):
    who = f'{info["login"]}: {info["role_text"]}'
    if info['source'] == 'ohne team':
        who += ' (kein Team eingetragen)'
    elif info['source'] == 'nicht im team':
        who += ' (nicht im Team)'
    rights = ('schreiben und abschließen' if info['approve'] else 'schreiben, nicht abschließen' if info['write']
              else 'nur lesen')
    if info['github_push'] is False and info['role'] != 'reader':
        rights += ' (ohne GitHub-Schreibrecht)'
    git = f' · Commits als {info["git"]["name"]} <{info["git"]["email"]}>' if info.get('git') else ''
    return f'{who} – {rights}{git}'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('role')
    r.add_argument('login')
    r.add_argument('--push', choices=['true', 'false'], help='GitHub-Schreibrecht (permissions.push)')
    r.add_argument('--json', action='store_true')
    sub.add_parser('check')
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_view import load
    base, config = load(a.project)
    if a.cmd == 'check':
        errs = problems(config)
        ok = f'✓ Team: {len(team(config))} Einträge' if team(config) else '✓ kein Team eingetragen'
        print('\n'.join(errs) or ok)
        return 1 if errs else 0
    info = role(base, config, a.login, None if a.push is None else a.push == 'true')
    print(json.dumps(info, ensure_ascii=False) if a.json else summary(info))
    return 0


if __name__ == '__main__':
    sys.exit(main())
