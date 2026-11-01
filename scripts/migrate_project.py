#!/usr/bin/env python3
"""Bringt die Buchdateien nach einem GhostWriter-Update auf den aktuellen Stand.

Aufruf:
  python scripts/migrate_project.py <projektordner>

Läuft nach jedem Update (scripts/update_from_upstream.py), nachdem die
Programmdateien ersetzt wurden. Jede Migration ist idempotent: Sie prüft, ob
etwas zu tun ist, und ändert sonst nichts. Migrationen ändern nur Strukturen
(neue Pflichtfelder, umbenannte Felder), nie Inhalte des Buchs.

Neue Pflichtfelder in schemas/ brauchen hier eine Migration, sonst schlägt die
Prüfung nach dem Update fehl und das Update wird nicht eingespielt.
"""
import re
import sys
from pathlib import Path

import yaml


def read(base, name):
    path = base / name
    return path.read_text(encoding='utf-8') if path.is_file() else None


# ---------- Migrationen ----------
# Jede Funktion bekommt den Projektordner und gibt eine kurze Beschreibung
# zurück, wenn sie etwas geändert hat, sonst None.

def ensure_approvals_log(base):
    """approvals.yml (Freigabe-Protokoll) anlegen, falls es fehlt."""
    if (base / 'approvals.yml').exists():
        return None
    (base / 'approvals.yml').write_text(
        '# Freigabe-Protokoll: jede erteilte oder zurückgenommene Freigabe als eigener\n'
        '# Eintrag (START.md, „Freigaben“). Nur anhängen, nie ändern oder löschen.\n'
        '#   kind: writing (Schreibfreigabe) | section (Abschnitt) | chapter (Kapitel)\n'
        '#   commit: Stand, den der Benutzer bestätigt hat (expected_head_sha)\n'
        'entries: []\n', encoding='utf-8')
    return 'approvals.yml angelegt'


def ensure_available_list(base):
    """ai_providers.available als Liste anlegen (seit 0.3), ohne die Datei umzuformatieren."""
    text = read(base, 'ghostwriter.yml')
    if text is None:
        return None
    config = yaml.safe_load(text) or {}
    ap = config.get('ai_providers')
    if not isinstance(ap, dict) or 'available' in ap:
        return None
    new, n = re.subn(r'(?m)^ai_providers:\n', 'ai_providers:\n  available: []\n', text, count=1)
    if not n:
        return None
    (base / 'ghostwriter.yml').write_text(new, encoding='utf-8')
    return 'ai_providers.available ergänzt'


def mark_legacy_costs(base):
    """Kosteneinträge ohne `source` (vor v0.4, meist Schätzungen für Chat-Läufe) als
    legacy_chat_estimate kennzeichnen. Sie bleiben erhalten, zählen aber nicht mehr mit (#13)."""
    files = sorted(base.glob('chapters/*/costs/*.yml')) + ([base / 'costs' / 'project.yml'] if (base / 'costs' / 'project.yml').is_file() else [])
    changed = 0
    for path in files:
        text = path.read_text(encoding='utf-8')
        data = yaml.safe_load(text) or {}
        entries = data.get('entries') or []
        todo = [e for e in entries if isinstance(e, dict) and 'source' not in e]
        if not todo:
            continue
        for e in todo:
            items = list(e.items())
            e.clear()
            e.update(items[:2] + [('source', 'legacy_chat_estimate')] + items[2:])
        head = ''
        for line in text.splitlines():
            if not line.startswith('#'):
                break
            head += line + '\n'
        path.write_text(head + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')
        changed += len(todo)
    return f'{changed} Kosteneinträge als legacy_chat_estimate gekennzeichnet' if changed else None


MIGRATIONS = [ensure_approvals_log, ensure_available_list, mark_legacy_costs]


def main(argv):
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 2
    base = Path(argv[1])
    if not (base / 'ghostwriter.yml').is_file():
        print(f'{base}: keine ghostwriter.yml, nichts zu migrieren')
        return 0
    done = [msg for msg in (m(base) for m in MIGRATIONS) if msg]
    for msg in done:
        print(f'migriert: {msg}')
    if not done:
        print('keine Migration nötig')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
