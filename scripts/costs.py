#!/usr/bin/env python3
"""Kosten eines Buchs: Übersicht nach Kostenart und manueller Eintrag (#66, v1.0-Umfang).

Kostenarten (`cost_status` in den Kostendateien, schemas/costs.schema.json):
  actual            tatsächlich (vom Anbieter gemeldet)
  estimated         geschätzt (aus Nutzung und Preistabelle)
  manually_entered  von Hand eingetragen (z. B. aus einer Rechnung)
  unavailable       unbekannt: Aufruf erfasst, Betrag fehlt

Gezählt werden nur KI-API-Aufrufe (`backend_api`, `action_api`); Chat-Arbeit über ein Abo
kostet nichts zusätzlich, alte Chat-Schätzungen (`legacy_chat_estimate`) zählen nicht (D08/D25).
Schätzungen entstehen automatisch je Aufruf aus der Nutzung und der Preistabelle (`providers.yml` → `prices`, #66); der
Betrag steht in der Projektwährung, mit Originalbetrag sowie Kurs und Datum des EZB-Referenzkurses am Eintrag. Ohne Kurs bleibt
er in der Originalwährung und gilt als „nicht umgerechnet“. Anbieterabrechnungen werden nicht abgeholt; Rechnungen trägt man
von Hand ein (`add`).

Aufruf:
  python3 scripts/costs.py <buch> summary [--month JJJJ-MM] [--by month|provider|activity|chapter|section] [--json]
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
BY = ('month', 'provider', 'activity', 'chapter', 'section')
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
            'complete': result['unavailable']['count'] == 0, 'calls': len(rows),
            'unconverted': sum(1 for e in rows if e.get('exchange_rate_status') == 'unavailable')}


def scoped_entries(base):
    """Alle Einträge mit dem Kapitel ihrer Datei (None bei Projektkosten)."""
    out = []
    for path in cost_files(base):
        chapter = path.parent.parent.name if path.parent.name == 'costs' and path.parent.parent.parent.name == 'chapters' else None
        for e in (yaml.safe_load(path.read_text(encoding='utf-8')) or {}).get('entries') or []:
            out.append((e, chapter))
    return out


def breakdown(base, by, month=None):
    """Auswertung je Monat, Anbieter, Aufgabe, Kapitel oder Abschnitt (#66): je Zeile Aufrufe, Summen je Kostenart und Währung,
    unbekannte Beträge gezählt. Geschätzt, tatsächlich und manuell bleiben getrennt."""
    if by not in BY:
        raise ValueError(f'Auswertung je {", ".join(BY)}')
    keyed = {id(e): (e, ch) for e, ch in scoped_entries(base)}
    rows = {}
    for e in counted([e for e, _ in keyed.values()]):
        if month and str(e.get('occurred_at', ''))[:7] != month:
            continue
        ch = keyed[id(e)][1]
        key = {'month': str(e.get('occurred_at', ''))[:7], 'provider': e.get('provider') or '–',
               'activity': e.get('activity_type') or '–', 'chapter': ch or '(Projekt)',
               'section': e.get('section_id') or '(Projekt)'}[by]
        row = rows.setdefault(key, {'key': key, 'calls': 0, 'unavailable': 0, 'amounts': {s: {} for s in STATUSES[:3]}})
        row['calls'] += 1
        status = e.get('cost_status') if e.get('cost_status') in STATUSES else 'unavailable'
        if e.get('cost_amount') is None or status == 'unavailable':
            row['unavailable'] += 1
            continue
        cur = e.get('currency', 'EUR')
        row['amounts'][status][cur] = row['amounts'][status].get(cur, Decimal(0)) + Decimal(str(e['cost_amount']))
    return [rows[k] for k in sorted(rows)]


def breakdown_text(rows, by):
    names = {'month': 'Monat', 'provider': 'Dienst', 'activity': 'Aufgabe', 'chapter': 'Kapitel', 'section': 'Abschnitt'}
    lines = [f'Kosten je {names[by]}']
    for r in rows:
        parts = [f'{LABEL[s]} {fmt(r["amounts"][s])}' for s in STATUSES[:3] if r['amounts'][s]]
        if r['unavailable']:
            parts.append(f'{r["unavailable"]} unbekannt')
        lines.append(f'- {r["key"]}: {r["calls"]} Aufrufe · ' + ('; '.join(parts) or 'kein Betrag'))
    return '\n'.join(lines) if rows else lines[0] + '\n- keine Einträge'


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
    if info.get('unconverted'):
        lines.append(f'Nicht umgerechnet (kein Wechselkurs): {info["unconverted"]} Einträge, Betrag in der Originalwährung')
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
    s = sub.add_parser('summary'); s.add_argument('--month'); s.add_argument('--by', choices=BY); s.add_argument('--json', action='store_true')
    a = sub.add_parser('add')
    a.add_argument('--amount', required=True); a.add_argument('--provider', required=True)
    a.add_argument('--model', default=''); a.add_argument('--section'); a.add_argument('--activity', default='other')
    a.add_argument('--currency', default='EUR'); a.add_argument('--at'); a.add_argument('--note')
    args = ap.parse_args(argv)
    base, _ = load(args.project)
    try:
        if args.cmd == 'summary' and args.by:
            rows = breakdown(base, args.by, args.month)
            print(json.dumps(rows, ensure_ascii=False, default=str, indent=2) if args.json else breakdown_text(rows, args.by))
            return 0
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
