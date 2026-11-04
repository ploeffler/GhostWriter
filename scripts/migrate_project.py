#!/usr/bin/env python3
"""Bringt die Buchdateien auf die Datenstruktur der installierten GhostWriter-Version (#59).

Aufruf:
  python scripts/migrate_project.py <projektordner>            Migrationen ausführen
  python scripts/migrate_project.py <projektordner> --check    nur prüfen, nichts ändern (Exit 1, wenn nötig)
  python scripts/migrate_project.py --fingerprint              Fingerabdruck der Schemas neu schreiben (Entwicklung)

Datenversion: `data_version` in ghostwriter.yml (fehlt = 0). Das Programm kennt
die aktuelle Datenversion (DATA_VERSION). Migrationen sind je Zielversion
geordnet und laufen nacheinander, auch über mehrere Versionen hinweg (ein Buch
auf 0 kommt direkt auf die neueste). Danach steht die neue Datenversion in
ghostwriter.yml.

Regeln:
- Nur Struktur, nie Inhalt: neue Pflichtfelder mit Vorgaben, Umbenennungen,
  Umzüge von Dateien. Texte, Freigaben, Läufe und Kosten bleiben unverändert.
- Jede Migration ist idempotent (ein zweiter Lauf ändert nichts).
- Kein Zurücksetzen: Ist das Buch neuer als das Programm, bricht das Skript
  ab (Exit 2) und ändert nichts.
- Wer ein Schema in schemas/ ändert, erhöht DATA_VERSION, ergänzt hier eine
  Migration und schreibt den Fingerabdruck neu (--fingerprint). check_docs.py
  prüft das in validate.yml.

Läuft nach jedem Update (scripts/update_from_upstream.py). Die Ausgabe
(„migriert: …“) kommt in die Commit-Nachricht des Updates und in
.ghostwriter/update.yml (`migration`), damit der Chat einmal darauf hinweist.
"""
import hashlib
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FINGERPRINT = ROOT / 'schemas' / 'data-version.yml'

# Aktuelle Datenversion dieses Programms. 1 = Stand GhostWriter 0.5.
DATA_VERSION = 1


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
        '#   kind: writing (Schreibfreigabe) | section (Abschnitt) | chapter (Kapitel) | matter (Vor-/Nachspann)\n'
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


# Zielversion → Migrationen, die ein Buch auf diese Datenversion bringen (in Reihenfolge)
MIGRATIONS = {
    1: [ensure_approvals_log, ensure_available_list, mark_legacy_costs],   # bis GhostWriter 0.5
}


# ---------- Datenversion ----------

def get_version(base):
    config = yaml.safe_load(read(base, 'ghostwriter.yml') or '{}') or {}
    v = config.get('data_version', 0)
    return v if isinstance(v, int) and v >= 0 else 0


def set_version(base, version):
    """data_version in ghostwriter.yml setzen, ohne die Datei umzuformatieren."""
    path = base / 'ghostwriter.yml'
    text = path.read_text(encoding='utf-8')
    line = f'data_version: {version}   # Datenstruktur-Version des Buchs (scripts/migrate_project.py), nicht von Hand ändern'
    if re.search(r'(?m)^data_version:', text):
        text = re.sub(r'(?m)^data_version:.*$', line, text, count=1)
    else:
        text = line + '\n' + text if not text.startswith('#') else re.sub(r'\A((?:#.*\n)*)', lambda m: m.group(1) + line + '\n', text, count=1)
    path.write_text(text, encoding='utf-8')


def pending(base):
    """(aktuelle Version, [Zielversionen, die noch fehlen]); ValueError, wenn das Buch neuer ist."""
    current = get_version(base)
    if current > DATA_VERSION:
        raise ValueError(f'Das Buch hat Datenversion {current}, dieses Programm kennt nur bis {DATA_VERSION}. '
                         'Kein Zurücksetzen: zuerst GhostWriter aktualisieren.')
    return current, [v for v in sorted(MIGRATIONS) if current < v <= DATA_VERSION]


def migrate(base):
    """Führt alle fehlenden Migrationen aus. Gibt (von, bis, [Meldungen]) zurück."""
    current, steps = pending(base)
    done = []
    for v in steps:
        for m in MIGRATIONS[v]:
            msg = m(base)
            if msg:
                done.append(msg)
    # Idempotente Migrationen der aktuellen Version auch bei gleicher Datenversion prüfen
    # (Bücher, die vor Einführung der Datenversion teilweise migriert wurden)
    if not steps:
        for m in MIGRATIONS.get(DATA_VERSION, []):
            msg = m(base)
            if msg:
                done.append(msg)
    if current != DATA_VERSION:
        set_version(base, DATA_VERSION)
    return current, DATA_VERSION, done


# ---------- Fingerabdruck der Schemas ----------

def schema_hash():
    h = hashlib.sha256()
    for p in sorted((ROOT / 'schemas').glob('*.schema.json')):
        if p.name in {'workflow.schema.json', 'reference-image.schema.json'}:  # keine Buchstruktur-Schemas
            continue
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def write_fingerprint():
    FINGERPRINT.write_text(
        '# Fingerabdruck der Buch-Schemas je Datenversion (scripts/migrate_project.py --fingerprint).\n'
        '# Ändert sich ein Schema, muss DATA_VERSION steigen und eine Migration dazukommen –\n'
        '# oder die Änderung ist rückwärtskompatibel (nur neue, optionale Felder); dann nur hier neu schreiben.\n'
        + yaml.safe_dump({'data_version': DATA_VERSION, 'schema_sha256': schema_hash()}, sort_keys=False),
        encoding='utf-8')
    return FINGERPRINT


def fingerprint_problem():
    """Text, wenn Schema und Fingerabdruck nicht zusammenpassen, sonst None (für check_docs.py)."""
    if not FINGERPRINT.is_file():
        return 'schemas/data-version.yml fehlt (python scripts/migrate_project.py --fingerprint)'
    fp = yaml.safe_load(FINGERPRINT.read_text(encoding='utf-8')) or {}
    if fp.get('data_version') != DATA_VERSION:
        return (f'schemas/data-version.yml nennt Datenversion {fp.get("data_version")}, migrate_project.py {DATA_VERSION}; '
                'Fingerabdruck neu schreiben (--fingerprint)')
    if fp.get('schema_sha256') != schema_hash():
        return ('Ein Buch-Schema in schemas/ wurde geändert, ohne Migration: DATA_VERSION in scripts/migrate_project.py '
                'erhöhen und eine Migration ergänzen (#59), oder – nur bei neuen optionalen Feldern – den Fingerabdruck '
                'neu schreiben (python scripts/migrate_project.py --fingerprint)')
    return None


def main(argv):
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 2
    if argv[1] == '--fingerprint':
        print(f'{write_fingerprint().relative_to(ROOT)}: Datenversion {DATA_VERSION}')
        return 0
    base = Path(argv[1])
    if not (base / 'ghostwriter.yml').is_file():
        print(f'{base}: keine ghostwriter.yml, nichts zu migrieren')
        return 0
    try:
        if '--check' in argv[2:]:
            current, steps = pending(base)
            if steps:
                print(f'Migration nötig: Datenversion {current} → {DATA_VERSION}')
                return 1
            print(f'Datenversion {current} ist aktuell')
            return 0
        frm, to, done = migrate(base)
    except ValueError as e:
        print(f'✗ {e}')
        return 2
    for msg in done:
        print(f'migriert: {msg}')
    if frm != to:
        print(f'Datenversion {frm} → {to}')
    elif not done:
        print('keine Migration nötig')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
