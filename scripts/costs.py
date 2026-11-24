#!/usr/bin/env python3
"""Kosten eines Buchs: Übersicht nach Kostenart und manueller Eintrag (#66, v1.0-Umfang).

Kostenarten (`cost_status` in den Kostendateien, schemas/costs.schema.json):
  actual            tatsächlich (vom Anbieter gemeldet)
  estimated         geschätzt (aus Nutzung und Preistabelle)
  manually_entered  von Hand eingetragen (z. B. aus einer Rechnung)
  unavailable       unbekannt: Aufruf erfasst, Betrag fehlt

Gezählt werden nur KI-API-Aufrufe (`backend_api`, `action_api`); Chat-Arbeit über ein Abo
kostet nichts zusätzlich, alte Chat-Schätzungen (`legacy_chat_estimate`) zählen nicht (D08/D25).
Der automatische Import der Anbieterabrechnung kommt nach v1.0.

Aufruf:
  python3 scripts/costs.py <buch> summary [--month JJJJ-MM] [--json]
  python3 scripts/costs.py <buch> add --amount 1.20 --provider openai --model gpt-x \\
      [--section sec-…] [--activity research] [--currency EUR] [--at 2026-11-24] [--note "Rechnung 42"]
"""
import argparse
import datetime
import json
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_view import counted, load  # noqa: E402

STATUSES = ('actual', 'estimated', 'manually_entered', 'unavailable')
LABEL = {'actual': 'tatsächlich', 'estimated': 'geschätzt', 'manually_entered': 'manuell', 'unavailable': 'unbekannt'}
ACTIVITIES = ('research', 'brainstorming', 'writing', 'revision', 'fact_check', 'other')


def cost_files(base):
    files = sorted(Path(base).glob('chapters/*/costs/*.yml'))
    project = Path(base) / 'costs' / 'project.yml'
    return files + ([project] if project.is_file() else [])


def entries(base):
    out = []
    for path in cost_files(base):
        for e in (yaml.safe_load(path.read_text(encoding='utf-8')) or {}).get('entries') or []:
            out.append(e)
    return out


def summary(base, month=None):
    """Summen je Kostenart und Währung; unbekannte Beträge werden gezählt, nie als 0 ausgegeben."""
    rows = [e for e in counted(entries(base)) if not month or str(e.get('occurred_at', ''))[:7] == month]
    result = {s: {'count': 0, 'amounts': {}} for s in STATUSES}
    for e in rows:
        status = e.get('cost_status') if e.get('cost_status') in STATUSES else 'unavailable'
        if e.get('cost_amount') is None:
            status = 'unavailable'
        slot = result[status]
        slot['count'] += 1
        if status != 'unavailable':
            cur = e.get('currency', 'EUR')
            slot['amounts'][cur] = slot['amounts'].get(cur, Decimal(0)) + Decimal(str(e['cost_amount']))
    known = {}
    for s in ('actual', 'estimated', 'manually_entered'):
        for cur, amount in result[s]['amounts'].items():
            known[cur] = known.get(cur, Decimal(0)) + amount
    return {'month': month, 'by_status': result, 'known_total': known,
            'complete': result['unavailable']['count'] == 0, 'calls': len(rows)}


def fmt(amounts):
    return ', '.join(f'{a:.2f} {c}' for c, a in sorted(amounts.items())) or '–'


def text(info):
    lines = [f'Kosten {info["month"] or "gesamt"}: {info["calls"]} KI-API-Aufrufe']
    for s in STATUSES:
        slot = info['by_status'][s]
        if slot['count']:
            value = 'Betrag unbekannt' if s == 'unavailable' else fmt(slot['amounts'])
            lines.append(f'- {LABEL[s]}: {slot["count"]} · {value}')
    total = fmt(info['known_total'])
    lines.append(f'Bekannte Summe: {total}' + ('' if info['complete'] else
                 f' (ohne {info["by_status"]["unavailable"]["count"]} Aufrufe mit unbekanntem Betrag)'))
    return '\n'.join(lines)


def add(base, amount, provider, model='', section=None, activity='other', currency='EUR', at=None, note=None):
    if Decimal(str(amount)) < 0:
        raise ValueError('Betrag darf nicht negativ sein')
    if activity not in ACTIVITIES:
        raise ValueError(f'Art muss eine von {", ".join(ACTIVITIES)} sein')
    _, config = load(base)
    if section:
        chapter = next((c for c in config['structure']['chapters'] for s in c['sections'] if s['id'] == section), None)
        if not chapter:
            raise ValueError(f'Abschnitt {section} nicht gefunden')
        path, head = Path(base) / chapter['path'] / 'costs' / f'{section}.yml', {'section_id': section}
    else:
        path, head = Path(base) / 'costs' / 'project.yml', {'scope': 'project'}
    data = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}) if path.is_file() else dict(head)
    data.setdefault('entries', [])
    occurred = at or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    if len(occurred) == 10:
        occurred += 'T12:00:00Z'
    entry = {'activity_id': f'manual-{uuid.uuid4().hex[:12]}', 'occurred_at': occurred, 'source': 'backend_api',
             'provider': provider, 'model': model, 'activity_type': activity, 'currency': currency.upper(),
             'cost_amount': float(amount), 'cost_status': 'manually_entered'}
    if section:
        entry['section_id'] = section
    if note:
        entry['note'] = note
    data['entries'].append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return path, entry


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('summary'); s.add_argument('--month'); s.add_argument('--json', action='store_true')
    a = sub.add_parser('add')
    a.add_argument('--amount', required=True); a.add_argument('--provider', required=True)
    a.add_argument('--model', default=''); a.add_argument('--section'); a.add_argument('--activity', default='other')
    a.add_argument('--currency', default='EUR'); a.add_argument('--at'); a.add_argument('--note')
    args = ap.parse_args(argv)
    base, _ = load(args.project)
    try:
        if args.cmd == 'summary':
            info = summary(base, args.month)
            if args.json:
                print(json.dumps(info, ensure_ascii=False, default=str, indent=2))
            else:
                print(text(info))
            return 0
        path, entry = add(base, args.amount, args.provider, args.model, args.section, args.activity,
                          args.currency, args.at, args.note)
        print(f'Eingetragen in {Path(path).relative_to(base)}: {entry["cost_amount"]:.2f} {entry["currency"]} (manuell)')
        return 0
    except ValueError as exc:
        print(f'Fehler: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
