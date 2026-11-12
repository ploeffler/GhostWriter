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
                   geschätzten Minuten aller Läufe dieses Repositorys im Monat
                   (nur mit --live: GitHub-API, je Lauf auf volle Minuten
                   aufgerundet, übersprungene Läufe zählen nicht, #277); ohne
                   Angabe keine Prüfung, außer in privaten Repositorys
                   (GHOSTWRITER_REPO_PRIVATE=true): dort gilt 2000
                   Zusätzlich feste Restminuten (#277): unter
                   limits.actions_minutes_warn_below (Vorgabe 300) Vorwarnung,
                   unter limits.actions_minutes_pause_below (Vorgabe 100) Pause –
                   es gilt die strengere Stufe von Prozent und Restminuten
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

DEFAULT = {'ai_budget_monthly': None, 'actions_minutes_monthly': None, 'pause_below_percent': 10, 'warn_below_percent': 20,
           'actions_minutes_warn_below': 300, 'actions_minutes_pause_below': 100}
PRIVATE_MINUTES = 2000   # Free-Plan, private Repositorys (#277)
MINUTES_ISSUE_TITLE = 'GhostWriter: Actions-Minuten knapp'
LABEL = {'ai_budget': 'KI-Budget', 'actions_minutes': 'Actions-Minuten', 'api_rate': 'GitHub-API'}
ISSUE_TITLE = 'GhostWriter-Automatik pausiert'


def settings(config):
    s = dict(DEFAULT)
    s.update((config or {}).get('limits') or {})
    if s['actions_minutes_monthly'] is None and os.environ.get('GHOSTWRITER_REPO_PRIVATE') == 'true':
        s['actions_minutes_monthly'] = PRIVATE_MINUTES
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


def _seconds(run):
    """Laufzeit eines abgeschlossenen Laufs in Sekunden (run_started_at bis updated_at); 0 = nicht gelaufen."""
    if run.get('status') != 'completed' or run.get('conclusion') in ('skipped', None):
        return 0
    try:
        start = datetime.datetime.fromisoformat(run['run_started_at'].replace('Z', '+00:00'))
        end = datetime.datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
    except (KeyError, AttributeError, ValueError):
        return 0
    return max(0, (end - start).total_seconds())


def estimate_minutes(runs):
    """Abgerechnete Minuten, geschätzt wie GitHub: je Lauf auf volle Minuten aufgerundet (#277).
    Läufe, die nie gestartet sind (übersprungen, „job was not started“), zählen nicht."""
    total = 0
    for run in runs:
        sec = _seconds(run)
        if sec >= 1:
            total += -(-int(sec) // 60)
    return total


def month_runs(repo, month, max_pages=100):
    """Alle Läufe des Monats (seitenweise, je 100); None, wenn die API nicht antwortet."""
    runs, page = [], 1
    while page <= max_pages:
        data = gh_json(f'repos/{repo}/actions/runs?created=>={month}-01&per_page=100&page={page}')
        if data is None:
            return None if page == 1 else runs
        batch = data.get('workflow_runs') or []
        runs += batch
        if len(batch) < 100 or len(runs) >= int(data.get('total_count') or 0):
            break
        page += 1
    return runs


def live_data(month):
    """Rate-Limit und Actions-Minuten des Monats über die GitHub-API (gh); None bei Fehlern."""
    out = {}
    rate = gh_json('rate_limit')
    if rate:
        core = rate.get('resources', {}).get('core', {})
        out['api_rate'] = (core.get('limit', 0) - core.get('remaining', 0), core.get('limit', 0))
    repo = os.environ.get('GITHUB_REPOSITORY')
    if repo:
        runs = month_runs(repo, month)
        if runs is not None:
            out['actions_minutes_used'] = estimate_minutes(runs)
    return out


def evaluate(base, config, month=None, live=None):
    """[{key, label, used, total, left_pct, state, text}] nur für Limits, die sich prüfen lassen."""
    s = settings(config)
    month = month or datetime.date.today().strftime('%Y-%m')
    live = live or {}
    pause, warn = float(s['pause_below_percent']), float(s['warn_below_percent'])
    rows = []
    order = {'ok': 0, 'warn': 1, 'pause': 2}
    def add(key, used, total, unit, warn_left=None, pause_left=None):
        if not total:
            return
        left = max(0.0, (total - used) / total * 100)
        state = 'pause' if left == 0 or left < pause else 'warn' if left < warn else 'ok'
        rest = max(0.0, total - used)
        if pause_left is not None and rest < float(pause_left):
            state = 'pause'
        elif warn_left is not None and rest < float(warn_left) and order[state] < 1:
            state = 'warn'
        fmt = (lambda v: f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')) if unit == '€' else (lambda v: f'{int(v)}')
        rows.append({'key': key, 'label': LABEL[key], 'used': used, 'total': total, 'left_pct': round(left, 1), 'state': state,
                     'left': rest,
                     'text': f'{LABEL[key]} {round(left):d} % übrig ({fmt(used)} von {fmt(total)}{" " + unit if unit else ""} verbraucht'
                             + (f', noch {int(rest)} min' if key == 'actions_minutes' else '') + ')'})
    if s['ai_budget_monthly']:
        add('ai_budget', month_costs(base, month), float(s['ai_budget_monthly']), '€')
    if s['actions_minutes_monthly'] and 'actions_minutes_used' in live:
        add('actions_minutes', float(live['actions_minutes_used']), float(s['actions_minutes_monthly']), 'min',
            s.get('actions_minutes_warn_below'), s.get('actions_minutes_pause_below'))
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
                m = next((r for r in rows if r['key'] == 'actions_minutes'), None)
                f.write(f'minutes_state={m["state"] if m else "ok"}\nminutes_text={m["text"] if m else ""}\n')
        if gh_sum and state != 'ok':
            with open(gh_sum, 'a', encoding='utf-8') as f:
                f.write(f'## {"⏸ pausiert" if state == "pause" else "⚠ Vorwarnung"}\n\n{text}\n')
        if state == 'pause':
            print(f'pausiert: {text}')
        return 0
    return 3 if state == 'pause' else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
