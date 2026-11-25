#!/usr/bin/env python3
"""Zentrale Modellvorgaben, Fehlerklasse „Modell nicht mehr verfügbar“ und lesende Modellprüfung (#554, #529).

Vorgaben stehen in `providers.yml` unter `model_defaults` (je Anbieter und Aufgabe `model` und `checked_at`),
nicht im Code. Ein Buch überschreibt sie in den Einstellungen (`ai_providers.services.<id>.model`). Fehlt die
Datei oder der Eintrag, gilt die eingebaute Rückfallvorgabe des aufrufenden Skripts.

  python3 scripts/model_defaults.py show                 # Vorgaben mit Datum der letzten Prüfung
  python3 scripts/model_defaults.py check [buch]         # Modelle gegen die kostenlosen Listen der Anbieter prüfen

`check` ruft nur die Listen-Endpunkte auf (lesend, kostenlos) und nur für Anbieter, deren Schlüssel
in der Umgebung steht. Es schaltet nie von selbst auf ein anderes Modell um.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TASKS = ('research', 'image')

# Meldungen der Anbieter, wenn ein Modell abgekündigt oder unbekannt ist.
UNAVAILABLE = re.compile(r'no longer available|deprecated|decommission|retired|discontinued|sunset|not found|'
                         r'does not exist|is not supported|no longer supported|unknown model|invalid model|model_not_found',
                         re.I)
REPLACEMENT = re.compile(r'\b(?:use|using|migrate to|switch to|replace(?:d)? (?:with|by))\s+(?:the\s+)?(?:models/)?'
                         r'([A-Za-z][\w.\-]*\d[\w.\-]*)', re.I)


def read_catalog(root=ROOT):
    try:
        return yaml.safe_load((Path(root) / 'providers.yml').read_text(encoding='utf-8')) or {}
    except (OSError, yaml.YAMLError):
        return {}


def entry(provider, task, root=ROOT):
    """{'model', 'checked_at'} oder {} aus providers.yml."""
    found = ((read_catalog(root).get('model_defaults') or {}).get(provider) or {}).get(task)
    return found if isinstance(found, dict) and str(found.get('model') or '').strip() else {}


def default_model(provider, task, fallback='', root=ROOT):
    """Vorgabemodell aus providers.yml; `fallback`, wenn dort nichts steht."""
    return str(entry(provider, task, root).get('model') or '').strip() or fallback


def is_unavailable(code, detail):
    """Meldet der Anbieter, dass das Modell fehlt? HTTP 404 genügt bei passendem Text, 400 nur mit eindeutigem Hinweis."""
    if code not in (400, 404):
        return False
    text = str(detail or '')
    return bool(UNAVAILABLE.search(text)) and (code == 404 or bool(re.search(r'model', text, re.I)))


def unavailable_message(provider_name, model, detail):
    """Handlungsorientierte Meldung statt der Rohmeldung des Anbieters."""
    hint = REPLACEMENT.search(str(detail or ''))
    named = f' Der Anbieter nennt {hint.group(1)} als Ersatz.' if hint else ''
    return (f'Das Modell {model} von {provider_name} ist nicht mehr verfügbar.{named} Im Formular „KI-Dienste“ ein anderes '
            f'Modell eintragen oder GhostWriter aktualisieren und den Auftrag danach erneut versuchen '
            f'(Warteschlange: „Erneut versuchen“). Es wird nie automatisch ein anderes Modell gewählt. '
            f'Meldung des Anbieters: {" ".join(str(detail or "").split())[:200]}')


def classify_http_error(code, detail, provider_name, model):
    """Text für einen HTTP-Fehler eines Anbieters; bei einem fehlenden Modell die Meldung oben."""
    if is_unavailable(code, detail):
        return unavailable_message(provider_name, model, detail)
    return f'Der Anbieter antwortet mit HTTP {code}: {str(detail)[:300]}'


# --- lesende Modellprüfung (Vorschlag 4 von #554) -----------------------------------------------

def _get(url, headers, timeout=30):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


LISTS = {
    'google': lambda key: ('https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000', {'x-goog-api-key': key},
                           lambda d: {m.get('name', '').replace('models/', '') for m in d.get('models') or []}),
    'anthropic': lambda key: ('https://api.anthropic.com/v1/models?limit=1000',
                              {'x-api-key': key, 'anthropic-version': '2023-06-01'},
                              lambda d: {m.get('id') for m in d.get('data') or []}),
    'openai': lambda key: ('https://api.openai.com/v1/models', {'authorization': f'Bearer {key}'},
                           lambda d: {m.get('id') for m in d.get('data') or []}),
}


RETIRE_WARN_DAYS = 90


def retirement_lines(today=None, root=ROOT):
    """Warnungen zu Vorgabemodellen, deren Abschaltung (`retire_at` in providers.yml) nah ist oder vorbei ist (#596).
    Braucht keinen Schlüssel: die Angaben stammen aus den öffentlichen Abkündigungsseiten der Anbieter."""
    today = today or datetime.date.today()
    out = []
    for pid, tasks in (read_catalog(root).get('model_defaults') or {}).items():
        for task, e in (tasks or {}).items():
            try:
                when = datetime.date.fromisoformat(str((e or {}).get('retire_at') or ''))
            except ValueError:
                continue
            days = (when - today).days
            if days > RETIRE_WARN_DAYS:
                continue
            state = f'wird am {when.isoformat()} abgeschaltet' if days >= 0 else f'ist seit dem {when.isoformat()} abgeschaltet'
            out.append(f'Das Vorgabemodell {e.get("model")} ({pid}, {"Bild" if task == "image" else "Recherche"}) {state}'
                       + (f' ({e["note"]})' if e.get('note') else '')
                       + '. Im Formular „KI-Dienste“ ein anderes Modell eintragen oder die Vorgabe in providers.yml prüfen; '
                         'es wird nie automatisch umgestellt.')
    return out


def wanted_models(base=None, root=ROOT):
    """[(Anbieter, Aufgabe, Modell, Secret-Name)] der eingestellten bzw. vorgegebenen Modelle."""
    cfg = {}
    if base:
        try:
            cfg = yaml.safe_load((Path(base) / 'ghostwriter.yml').read_text(encoding='utf-8')) or {}
        except (OSError, yaml.YAMLError):
            cfg = {}
    services = ((cfg.get('ai_providers') or {}).get('services')) or {}
    catalog = {p['id']: p for p in read_catalog(root).get('providers') or [] if isinstance(p, dict) and p.get('id')}
    out = []
    for pid, tasks in (read_catalog(root).get('model_defaults') or {}).items():
        service = services.get(pid) or {}
        secret = service.get('api_key_secret') or (catalog.get(pid) or {}).get('api_key_secret') or ''
        for task in tasks or {}:
            set_model = str(service.get('model') or '').strip()
            if set_model and (('image' in set_model) == (task == 'image')):
                out.append((pid, task, set_model, secret))
            else:
                out.append((pid, task, default_model(pid, task, root=root), secret))
    return out


def check(base=None, env=None, fetch=_get, root=ROOT, today=None):
    """Zeilen für Modelle, die in der Liste des Anbieters fehlen, und für nahe Abschaltungen (`retire_at`).
    Ohne Schlüssel oder bei Netzfehler gibt es zur Liste keine Aussage."""
    env = os.environ if env is None else env
    lines, lists = retirement_lines(today, root), {}
    for pid, task, model, secret in wanted_models(base, root):
        key = env.get(secret or '')
        if not key or pid not in LISTS:
            continue
        if pid not in lists:
            url, headers, pick = LISTS[pid](key)
            try:
                lists[pid] = pick(fetch(url, headers))
            except (OSError, ValueError, urllib.error.URLError):
                lists[pid] = None
        if lists[pid] and model not in lists[pid]:
            lines.append(f'Das Modell {model} ({pid}, {"Bild" if task == "image" else "Recherche"}) steht nicht mehr in der '
                         f'Modellliste des Anbieters. Im Formular „KI-Dienste“ ein anderes Modell eintragen oder GhostWriter aktualisieren.')
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=['show', 'check'])
    ap.add_argument('base', nargs='?')
    ap.add_argument('--report', action='store_true', help='check: Hinweise in den täglichen Bericht schreiben, Exit-Code immer 0')
    a = ap.parse_args(argv)
    if a.cmd == 'show':
        for pid, tasks in (read_catalog().get('model_defaults') or {}).items():
            for task, e in (tasks or {}).items():
                print(f'{pid}\t{task}\t{e.get("model")}\tgeprüft {e.get("checked_at") or "unbekannt"}'
                      + (f'\tabgeschaltet {e["retire_at"]}' if e.get('retire_at') else ''))
        return 0
    lines = check(a.base)
    print('\n'.join(lines) or 'Alle geprüften Modelle stehen in den Listen der Anbieter (oder es ist kein Schlüssel hinterlegt).')
    if lines and a.report:   # #596: Hinweis im täglichen Bericht und in der Zusammenfassung der Action
        text = '\n'.join(['', '### KI-Modelle', ''] + [f'- {x}' for x in lines]) + '\n'
        for target in dict.fromkeys(t for t in (os.environ.get('GITHUB_STEP_SUMMARY'), os.environ.get('DAILY_UPDATE_REPORT_PATH')) if t):
            with open(target, 'a', encoding='utf-8') as f:
                f.write(text)
    return 0 if a.report else (1 if lines else 0)


if __name__ == '__main__':
    sys.exit(main())
