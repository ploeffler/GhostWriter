#!/usr/bin/env python3
"""Limits prüfen: unter 10 % keine Automatik, ab 20 % Vorwarnung (#62).

Aufruf:
  python scripts/limits.py <projektordner> check [--live] [--json datei] [--month JJJJ-MM]
  python scripts/limits.py <projektordner> check --automation [--live]   in einer Action (siehe update.yml)

Geprüft wird, was sich ohne Backend prüfen lässt:
  ai_budget        KI-Budget des Monats (limits.ai_budget_monthly) gegen die
                   KI-API-Kosten über das Backend im laufenden Monat (costs/,
                   nur source: backend_api, #13); ohne Budget keine Prüfung
  actions_minutes  GitHub-Actions-Minuten (limits.actions_minutes_monthly, z. B.
                   2000 bei privaten Repositorys im Free-Plan) gegen die
                   abrechenbaren Minuten der Läufe dieses Repositorys im Monat
                   (nur mit --live: GitHub-API); ohne Angabe keine Prüfung
  api_rate         GitHub-API-Rate-Limit (core) des Tokens (nur mit --live)
Kontingente bei KI-Anbietern kommen mit dem Backend (#19, #66).

Stufen je Limit: ok, warn (weniger als limits.warn_below_percent übrig, Vorgabe
20), pause (weniger als limits.pause_below_percent, Vorgabe 10; aufgebraucht
zählt als pause). Neuer Monat: neue Rechnung, die Automatik läuft beim nächsten
Termin von selbst weiter.

--automation: Exit-Code immer 0 („pausiert“ ist kein Fehler). In GitHub Actions
schreibt das Skript paused=true|false und text=… nach $GITHUB_OUTPUT, damit
die folgenden Schritte übersprungen werden können, und eine Zeile in die
Zusammenfassung. Ohne --automation: Exit-Code 3 bei pause, sonst 0.

--json schreibt den Stand für die Projektübersicht (render_view.py project
--limits datei).
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from render_view import counted, load  # noqa: E402

DEFAULT = {'ai_budget_monthly': None, 'actions_minutes_monthly': None, 'pause_below_percent': 10, 'warn_below_percent': 20}
LABEL = {'ai_budget': 'KI-Budget', 'actions_minutes': 'Actions-Minuten', 'api_rate': 'GitHub-API'}
ISSUE_TITLE = 'GhostWriter-Automatik pausiert'


def settings(config):
    s = dict(DEFAULT)
    s.update((config or {}).get('limits') or {})
    return s


def month_costs(base, month):
    """Summe der Backend-API-Kosten im Monat (JJJJ-MM) in Projektwährung; Einträge in anderer Währung zählen
    mit ihrem Betrag (Umrechnung kommt mit #66)."""
    files = sorted(base.glob('chapters/*/costs/*.yml'))
    if (base / 'costs' / 'project.yml').is_file():
        files.append(base / 'costs' / 'project.yml')
    total = 0.0
    for path in files:
        entries = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}).get('entries') or []
        for e in counted(entries):
            if str(e.get('occurred_at', ''))[:7] == month and e.get('cost_amount') is not None:
                total += float(e['cost_amount'])
    return total


def gh_json(path):
    r = subprocess.run(['gh', 'api', path], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def live_data(month):
    """Rate-Limit und Actions-Minuten des Monats über die GitHub-API (gh); None bei Fehlern."""
    out = {}
    rate = gh_json('rate_limit')
    if rate:
        core = rate.get('resources', {}).get('core', {})
        out['api_rate'] = (core.get('limit', 0) - core.get('remaining', 0), core.get('limit', 0))
    repo = os.environ.get('GITHUB_REPOSITORY')
    if repo:
        start = f'{month}-01'
        runs = gh_json(f'repos/{repo}/actions/runs?created=>={start}&per_page=100') or {}
        ms = 0
        for run in runs.get('workflow_runs') or []:
            timing = gh_json(f'repos/{repo}/actions/runs/{run["id"]}/timing') or {}
            for os_name, v in (timing.get('billable') or {}).items():
                ms += int(v.get('total_ms') or 0) * (1 if os_name == 'UBUNTU' else 2 if os_name == 'WINDOWS' else 10)
        out['actions_minutes_used'] = round(ms / 60000)
    return out


def evaluate(base, config, month=None, live=None):
    """[{key, label, used, total, left_pct, state, text}] nur für Limits, die sich prüfen lassen."""
    s = settings(config)
    month = month or datetime.date.today().strftime('%Y-%m')
    live = live or {}
    pause, warn = float(s['pause_below_percent']), float(s['warn_below_percent'])
    rows = []
    def add(key, used, total, unit):
        if not total:
            return
        left = max(0.0, (total - used) / total * 100)
        state = 'pause' if left < pause else 'warn' if left < warn else 'ok'
        fmt = (lambda v: f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')) if unit == '€' else (lambda v: f'{int(v)}')
        rows.append({'key': key, 'label': LABEL[key], 'used': used, 'total': total, 'left_pct': round(left, 1), 'state': state,
                     'text': f'{LABEL[key]} {round(left):d} % übrig ({fmt(used)} von {fmt(total)}{" " + unit if unit else ""})'})
    if s['ai_budget_monthly']:
        add('ai_budget', month_costs(base, month), float(s['ai_budget_monthly']), '€')
    if s['actions_minutes_monthly'] and 'actions_minutes_used' in live:
        add('actions_minutes', float(live['actions_minutes_used']), float(s['actions_minutes_monthly']), 'min')
    if 'api_rate' in live and live['api_rate'][1]:
        add('api_rate', float(live['api_rate'][0]), float(live['api_rate'][1]), '')
    return rows


def summary(rows):
    paused = [r for r in rows if r['state'] == 'pause']
    warned = [r for r in rows if r['state'] == 'warn']
    if paused:
        return 'pause', 'Automatik pausiert: ' + '; '.join(r['text'] for r in paused)
    if warned:
        return 'warn', 'Vorwarnung: ' + '; '.join(r['text'] for r in warned)
    return 'ok', ''


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['check'])
    ap.add_argument('--live', action='store_true', help='GitHub-API abfragen (Rate-Limit, Actions-Minuten)')
    ap.add_argument('--automation', action='store_true')
    ap.add_argument('--json')
    ap.add_argument('--month')
    a = ap.parse_args(argv[1:])
    base, config = load(a.project)
    month = a.month or datetime.date.today().strftime('%Y-%m')
    rows = evaluate(base, config, month, live_data(month) if a.live else None)
    state, text = summary(rows)
    for r in rows:
        print(f'{ {"ok": "✓", "warn": "⚠", "pause": "⏸"}[r["state"]] } {r["text"]}')
    if not rows:
        print('Keine Limits eingestellt bzw. prüfbar.')
    if a.json:
        Path(a.json).write_text(json.dumps({'month': month, 'state': state, 'text': text, 'limits': rows},
                                           ensure_ascii=False, indent=1), encoding='utf-8')
    if a.automation:
        gh_out, gh_sum = os.environ.get('GITHUB_OUTPUT'), os.environ.get('GITHUB_STEP_SUMMARY')
        if gh_out:
            with open(gh_out, 'a', encoding='utf-8') as f:
                f.write(f'paused={"true" if state == "pause" else "false"}\ntext={text}\n')
        if gh_sum and state != 'ok':
            with open(gh_sum, 'a', encoding='utf-8') as f:
                f.write(f'## {"⏸ pausiert" if state == "pause" else "⚠ Vorwarnung"}\n\n{text}\n')
        if state == 'pause':
            print(f'pausiert: {text}')
        return 0
    return 3 if state == 'pause' else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
