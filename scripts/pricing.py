#!/usr/bin/env python3
"""Preistabelle und Währungsumrechnung für die automatische Kostenschätzung (#66).

Preise stehen in `providers.yml` unter `prices` (je Anbieter und Modell, mit Quelle und Prüfdatum). Aus der Nutzung
einer Antwort (Tokens, Suchanfragen) entsteht ein Eintrag „geschätzt“; ein Modell ohne Preis bleibt „unbekannt“,
nie 0. Rechnungen bleiben „tatsächlich“ von Hand (`costs.py add`); Anbieterabrechnungen werden nicht abgeholt.

Umrechnung in die Währung der Bibliothek (Vorgabe EUR) mit dem Referenzkurs der Europäischen Zentralbank des Tages
(`eurofxref-daily.xml`, für ältere Tage `eurofxref-hist-90d.xml`). Kurs und Datum stehen am Eintrag, der Originalbetrag
bleibt erhalten. Ohne Kurs (offline) bleibt der Betrag in der Originalwährung und ist als nicht umgerechnet markiert.

  python3 scripts/pricing.py show                      # Preistabelle mit Prüfdatum
  python3 scripts/pricing.py estimate anthropic claude-sonnet-5-5 --input 12000 --output 3000 --searches 4 [--currency EUR]
"""
import argparse
import datetime
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ECB_DAILY = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'
ECB_HIST = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml'
SOURCE = 'ECB'


def table(root=ROOT):
    try:
        data = yaml.safe_load((Path(root) / 'providers.yml').read_text(encoding='utf-8')) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return data.get('prices') or {}


def lookup(provider, model, prices=None):
    """Preiseintrag für Anbieter und Modell oder None. Genau der Modellname, oder ein Name mit Datumsanhang
    (`<modell>-20261126`); nie ein ähnliches Modell."""
    entries = (prices if prices is not None else table()).get(provider) or {}
    model = str(model or '')
    if model in entries:
        return entries[model]
    for name, entry in entries.items():
        if re.fullmatch(re.escape(name) + r'-\d{8}', model):
            return entry
    return None


def estimate(provider, model, tokens_in, tokens_out, searches=0, prices=None):
    """Geschätzter Betrag in der Währung der Preistabelle plus Preisgrundlage, oder None ohne Preis.
    `search_priced` ist False, wenn Suchanfragen angefallen sind, aber kein Suchpreis vorliegt (Betrag dann ohne Suche)."""
    entry = lookup(provider, model, prices)
    if not entry or entry.get('input_per_mtok') is None or entry.get('output_per_mtok') is None:
        return None
    amount = Decimal(str(tokens_in or 0)) / 1000000 * Decimal(str(entry['input_per_mtok'])) \
        + Decimal(str(tokens_out or 0)) / 1000000 * Decimal(str(entry['output_per_mtok']))
    search_priced = True
    if searches:
        if entry.get('search_per_1k') is None:
            search_priced = False
        else:
            amount += Decimal(str(searches)) / 1000 * Decimal(str(entry['search_per_1k']))
    return {'amount': amount, 'currency': str(entry.get('currency') or 'USD').upper(), 'search_priced': search_priced,
            'input_unit_price': float(entry['input_per_mtok']), 'output_unit_price': float(entry['output_per_mtok']),
            'pricing_basis': 'per_million_tokens', 'pricing_source': str(entry.get('source') or ''),
            'pricing_checked_at': str(entry.get('checked_at') or '')}


def fetch_url(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as r:   # noqa: S310 (feste ECB-Adresse)
        return r.read().decode('utf-8')


def parse_ecb(xml_text):
    """{Datum: {Währung: Kurs je 1 EUR}} aus einer ECB-Referenzkurs-Datei (täglich oder 90 Tage)."""
    root = ET.fromstring(xml_text)
    out = {}
    for cube in root.iter():
        if cube.tag.endswith('Cube') and cube.get('time'):
            out[cube.get('time')] = {c.get('currency'): Decimal(c.get('rate')) for c in cube if c.get('currency')}
    return out


def rates_for(day, fetch=None):
    """(Kursdatum, {Währung: Kurs}) für den Tag: der Tag selbst oder der letzte Handelstag davor; None ohne Kurse.
    Für heute/gestern die Tagesdatei, sonst die 90-Tage-Datei. Netzfehler und kaputte Dateien ergeben None."""
    fetch = fetch or fetch_url
    day = str(day)[:10]
    today = datetime.date.today().isoformat()
    for url in ((ECB_DAILY, ECB_HIST) if day >= today else (ECB_HIST, ECB_DAILY)):
        try:
            data = parse_ecb(fetch(url))
        except Exception:   # noqa: BLE001 (offline, gesperrt, kaputt: dann ohne Kurs)
            continue
        days = sorted(d for d in data if d <= day)
        if days:
            return days[-1], data[days[-1]]
    return None


def convert(amount, source, target, rates):
    """Betrag zwischen Währungen über den EUR-Kurs; None, wenn ein Kurs fehlt."""
    source, target = source.upper(), target.upper()
    amount = Decimal(str(amount))
    if source == target:
        return amount, Decimal(1)
    try:
        to_eur = Decimal(1) if source == 'EUR' else Decimal(1) / rates[source]
        rate = to_eur * (Decimal(1) if target == 'EUR' else rates[target])
    except (KeyError, ZeroDivisionError):
        return None
    return amount * rate, rate


def cost_fields(est, target_currency, day, fetch=None):
    """Felder für den Kosteneintrag: Betrag (umgerechnet, wenn ein Kurs vorliegt), Originalbetrag, Kurs mit Datum,
    Preisgrundlage. Ohne Kurs: Betrag in der Originalwährung, `exchange_rate_status: unavailable`."""
    out = {'cost_status': 'estimated', 'input_unit_price': est['input_unit_price'], 'output_unit_price': est['output_unit_price'],
           'pricing_basis': est['pricing_basis'], 'pricing_source': est['pricing_source'],
           'pricing_checked_at': est['pricing_checked_at']}
    original = est['amount']
    target = (target_currency or est['currency']).upper()
    if target == est['currency']:
        out.update(currency=target, cost_amount=float(round(original, 4)))
        return out
    got = rates_for(day, fetch)
    result = convert(original, est['currency'], target, got[1]) if got else None
    if result is None:
        out.update(currency=est['currency'], cost_amount=float(round(original, 4)), exchange_rate_status='unavailable')
        return out
    amount, rate = result
    out.update(currency=target, cost_amount=float(round(amount, 4)), original_currency=est['currency'],
               original_amount=float(round(original, 4)), exchange_rate=float(round(rate, 6)), exchange_rate_date=got[0],
               exchange_rate_source=SOURCE, exchange_rate_status='applied')
    return out


def enrich(entry, tokens_in, tokens_out, searches=0, fetch=None):
    """Ergänzt einen Kosteneintrag ohne Betrag (`cost_amount` None) aus der Preistabelle. Ein Betrag aus den Einstellungen
    des Buchs (eigener Preis je Dienst) bleibt unberührt; ohne Tabellenpreis bleibt der Eintrag „unbekannt“.
    Die Währung des Eintrags ist die Projektwährung, in die umgerechnet wird. Gibt den Preis-Hinweis zurück
    (`'no_search_price'`, wenn Suchanfragen ohne Suchpreis geschätzt wurden) oder None."""
    if entry.get('cost_amount') is not None:
        return None
    est = estimate(entry.get('provider'), entry.get('model'), tokens_in, tokens_out, searches)
    if est is None:
        return None
    entry.update(cost_fields(est, entry.get('currency'), str(entry.get('occurred_at'))[:10], fetch))
    return None if est['search_priced'] else 'no_search_price'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('show')
    e = sub.add_parser('estimate')
    e.add_argument('provider')
    e.add_argument('model')
    e.add_argument('--input', type=int, default=0)
    e.add_argument('--output', type=int, default=0)
    e.add_argument('--searches', type=int, default=0)
    e.add_argument('--currency', default='EUR')
    e.add_argument('--day', default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)
    if a.cmd == 'show':
        for provider, models in sorted(table().items()):
            for model, p in sorted(models.items()):
                print(f'{provider}/{model}: {p.get("input_per_mtok")}/{p.get("output_per_mtok")} {p.get("currency")} je Mio. Tokens'
                      + (f', Suche {p["search_per_1k"]} je 1000' if p.get('search_per_1k') is not None else '')
                      + f' (geprüft {p.get("checked_at")})')
        return 0
    est = estimate(a.provider, a.model, a.input, a.output, a.searches)
    if est is None:
        print('Kein Preis in providers.yml: Betrag unbekannt.')
        return 1
    fields = cost_fields(est, a.currency, a.day)
    print(f'{fields["cost_amount"]} {fields["currency"]} (geschätzt)'
          + (f'; Original {fields["original_amount"]} {fields["original_currency"]}, Kurs {fields["exchange_rate"]} vom {fields["exchange_rate_date"]}'
             if fields.get('exchange_rate_status') == 'applied' else '')
          + ('; nicht umgerechnet (kein Kurs)' if fields.get('exchange_rate_status') == 'unavailable' else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
