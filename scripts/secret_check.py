#!/usr/bin/env python3
"""Welche Secrets hinterlegt sind – ohne die Werte je zu sehen (#71, Seite „Daten“; KI-Dienste).

Die Actions „Übersichtsdatei aktualisieren“ und „Bücherregal aktualisieren“ geben
nicht mehr alle Secrets weiter (toJSON(secrets) lässt GitHub Läufe in
öffentlichen Repositorys als verdächtig anhalten), sondern nur je bekanntem
Namen, ob es ihn gibt:

  SECRETS_PRESENT: >-
    {"GHOSTWRITER_UPDATE_TOKEN": ${{ secrets.GHOSTWRITER_UPDATE_TOKEN != '' }}, …}

Bekannt sind GHOSTWRITER_UPDATE_TOKEN und alle Schlüssel-Namen aus providers.yml
(api_key_secret bzw. <ID>_API_KEY, dazu api_key_alt). Ein eigener, abweichender
Name (ai_providers.services.<id>.api_key_secret) gilt als „unbekannt“.

Aufruf:
  python scripts/secret_check.py block     den Block für die Workflows ausgeben
  python scripts/secret_check.py check     prüfen, ob beide Workflows alle Namen enthalten (Exit 1 sonst)
"""
import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ['.github/workflows/index.yml', '.github/workflows/library.yml']
UPDATE_TOKEN = 'GHOSTWRITER_UPDATE_TOKEN'


def known_names():
    catalog = yaml.safe_load((ROOT / 'providers.yml').read_text(encoding='utf-8')) or {}
    names = {UPDATE_TOKEN}
    for sec in ('providers', 'search_tools', 'queue_agents'):
        for s in catalog.get(sec) or []:
            names.add(s.get('api_key_secret') or re.sub(r'[^A-Z0-9]+', '_', s['id'].upper()) + '_API_KEY')
            if s.get('api_key_alt'):
                names.add(s['api_key_alt'])
    return sorted(names)


def presence():
    """{name: True|False} aus SECRETS_PRESENT, oder None, wenn nicht gesetzt (außerhalb der Action)."""
    raw = os.environ.get('SECRETS_PRESENT')
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return {k: v is True or v == 'true' for k, v in data.items()} if isinstance(data, dict) else None


def state(names, previous=None):
    """{name: True|False|None} für die gebrauchten Namen; None = unbekannt (Name nicht prüfbar).
    Ohne SECRETS_PRESENT bleibt der bisherige Stand."""
    p = presence()
    if p is None:
        return previous
    return {n: p.get(n) for n in names}


def block(indent=10):
    pad = ' ' * indent
    items = [f'"{n}": ${{{{ secrets.{n} != \'\' }}}}' for n in known_names()]
    return (f'{pad[:-2]}SECRETS_PRESENT: >-\n{pad}{{' + f',\n{pad} '.join(items) + '}')


def check():
    missing = []
    for wf in WORKFLOWS:
        text = (ROOT / wf).read_text(encoding='utf-8')
        if re.search(r'\$\{\{\s*toJSON\(secrets\)', text):
            missing.append(f'{wf}: toJSON(secrets) nicht verwenden (hält Läufe in öffentlichen Repositorys an)')
        for n in known_names():
            if f'"{n}": ${{{{ secrets.{n} != \'\' }}}}' not in text:
                missing.append(f'{wf}: {n} fehlt in SECRETS_PRESENT (python scripts/secret_check.py block)')
    return missing


def main(argv):
    if len(argv) < 2 or argv[1] not in ('block', 'check'):
        print(__doc__)
        return 2
    if argv[1] == 'block':
        print(block())
        return 0
    problems = check()
    for p in problems:
        print(f'✗ {p}')
    if not problems:
        print(f'✓ {len(known_names())} Secret-Namen in {len(WORKFLOWS)} Workflows')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
