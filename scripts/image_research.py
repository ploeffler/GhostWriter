#!/usr/bin/env python3
"""Externe Bildrecherche (#218, D15, A05): Kandidaten mit Quelle, Urheber und Lizenz.

Die Recherche selbst macht der Chat mit seinen vorhandenen Werkzeugen oder der Benutzer
(Link oder eigene Datei). Es gibt keine neue Such- oder KI-Anbieteranbindung. Dieses Skript
hält nur fest, was gefunden wurde, und übernimmt einen Kandidaten erst nach ausdrücklicher
Bestätigung als gespeichertes Bild.

Drei Stufen, nie vermischt:
  Kandidat              research/images/candidates.yml – nur Angaben, keine Bilddatei
  gespeichertes Bild    reference-images/ref-img-*.yml, Status „stored“ (reference_images.py)
  freigegebene Abbildung eigene Freigabe über die Bildverwaltung bzw. „approve“; nie automatisch

Rechte: Ein Kandidat gilt als „geklärt“ nur mit Urheber *und* Lizenzangabe. Fehlt eins davon,
heißt er „ungeklärt“. Das Skript erfindet keine Nutzungserlaubnis; „geklärt“ heißt nur, dass
die Angaben vorliegen, nicht, dass sie rechtlich geprüft sind.

Aufruf:
  python3 scripts/image_research.py <buch> propose --title T --url BILD-URL [--page SEITE] [--author A]
        [--license L] [--license-url U] [--found-by chat|user] [--for person:char-…] [--note N]
  python3 scripts/image_research.py <buch> list [--status candidate|adopted|rejected]
  python3 scripts/image_research.py <buch> adopt <cand-id> --file <bild.png|jpg> --confirm [--accept-unclear]
        [--role visual_reference|book_image] [--confirm-large-collection]
  python3 scripts/image_research.py <buch> reject <cand-id> [--reason R]
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

STATUSES = ('candidate', 'adopted', 'rejected')
FOUND_BY = ('chat', 'user')


def store(base):
    return Path(base) / 'research' / 'images' / 'candidates.yml'


def load_all(base):
    p = store(base)
    return (yaml.safe_load(p.read_text(encoding='utf-8')) or {}).get('candidates', []) if p.is_file() else []


def save_all(base, items):
    p = store(base)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump({'candidates': items}, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def rights(item):
    return 'clear' if str(item.get('author') or '').strip() and str(item.get('license') or '').strip() else 'unclear'


def _url(value, field):
    if value and urlparse(value).scheme not in ('http', 'https'):
        raise ValueError(f'{field} muss mit http:// oder https:// beginnen')
    return value or ''


def propose(base, title, url, page='', author='', license_info='', license_url='', found_by='chat', links=None, note=''):
    if not title.strip():
        raise ValueError('Titel fehlt')
    if not url:
        raise ValueError('Bild-URL fehlt')
    if found_by not in FOUND_BY:
        raise ValueError('found_by muss chat oder user sein')
    items = load_all(base)
    nums = [int(m.group(1)) for i in items if (m := re.match(r'cand-(\d+)$', i['id']))]
    item = {'id': f'cand-{max(nums, default=0) + 1:03d}', 'status': 'candidate', 'title': title.strip(),
            'url': _url(url, 'url'), 'page': _url(page, 'page'), 'author': author.strip(),
            'license': license_info.strip(), 'license_url': _url(license_url, 'license_url'),
            'found_by': found_by, 'found_at': now(), 'links': links or [], 'note': note.strip()}
    item['rights'] = rights(item)
    items.append(item)
    save_all(base, items)
    return item


def find(items, cid):
    hit = next((i for i in items if i['id'] == cid), None)
    if not hit:
        raise ValueError(f'Kandidat {cid} nicht gefunden')
    return hit


def adopt(base, cid, file, confirm=False, accept_unclear=False, role='visual_reference', confirm_large_collection=False):
    """Kandidat als gespeichertes Bild übernehmen. Ohne --confirm ändert sich nichts."""
    items = load_all(base)
    item = find(items, cid)
    if item['status'] != 'candidate':
        raise ValueError(f'{cid} ist schon {item["status"]}')
    if not confirm:
        raise ValueError('Übernahme abgebrochen: ohne ausdrückliche Bestätigung (--confirm) wird nichts gespeichert')
    if item['rights'] == 'unclear' and not accept_unclear:
        raise ValueError(f'{cid}: Rechte ungeklärt (Urheber oder Lizenz fehlt); nur mit --accept-unclear übernehmen')
    import reference_images
    origin = 'licensed' if item['rights'] == 'clear' else 'unknown'
    source = item['page'] or item['url']
    licence = item['license'] or 'ungeklärt'
    description = f'Quelle: {source}; Urheber: {item["author"] or "unbekannt"}; Lizenz: {licence}' + (
        f' ({item["license_url"]})' if item['license_url'] else '')
    meta = reference_images.add(base, file, item['title'], description=description,
                                purpose=item['note'], roles=[role], origin=origin, license_info=licence,
                                links=item['links'], confirm_large_collection=confirm_large_collection)
    item.update({'status': 'adopted', 'adopted_as': meta['id'], 'adopted_at': now()})
    save_all(base, items)
    return item, meta


def reject(base, cid, reason=''):
    items = load_all(base)
    item = find(items, cid)
    if item['status'] != 'candidate':
        raise ValueError(f'{cid} ist schon {item["status"]}')
    item.update({'status': 'rejected', 'rejected_at': now(), 'reason': reason.strip()})
    save_all(base, items)
    return item


def line(i):
    flag = 'Rechte geklärt' if i['rights'] == 'clear' else 'RECHTE UNGEKLÄRT'
    extra = f' → {i["adopted_as"]}' if i.get('adopted_as') else ''
    return (f'{i["id"]}  {i["status"]}{extra}  {flag}  {i["title"]}\n'
            f'    Quelle: {i["page"] or i["url"]} · Urheber: {i["author"] or "unbekannt"} · Lizenz: {i["license"] or "unbekannt"}')


def main(argv=None):
    import reference_images
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('propose')
    p.add_argument('--title', required=True); p.add_argument('--url', required=True); p.add_argument('--page', default='')
    p.add_argument('--author', default=''); p.add_argument('--license', default=''); p.add_argument('--license-url', default='')
    p.add_argument('--found-by', default='chat', choices=FOUND_BY)
    p.add_argument('--for', dest='links', action='append', type=reference_images.parse_link, default=[])
    p.add_argument('--note', default='')
    p = sub.add_parser('list'); p.add_argument('--status', choices=STATUSES); p.add_argument('--json', action='store_true')
    p = sub.add_parser('adopt'); p.add_argument('cid'); p.add_argument('--file', required=True)
    p.add_argument('--confirm', action='store_true'); p.add_argument('--accept-unclear', action='store_true')
    p.add_argument('--role', default='visual_reference', choices=sorted(reference_images.ROLES))
    p.add_argument('--confirm-large-collection', action='store_true')
    p = sub.add_parser('reject'); p.add_argument('cid'); p.add_argument('--reason', default='')
    a = ap.parse_args(argv)
    base = Path(a.project)
    try:
        if a.cmd == 'propose':
            i = propose(base, a.title, a.url, a.page, a.author, a.license, a.license_url, a.found_by, a.links, a.note)
            print(f'Kandidat {i["id"]} festgehalten ({"Rechte geklärt" if i["rights"] == "clear" else "Rechte ungeklärt"}); nichts gespeichert oder eingefügt.')
        elif a.cmd == 'list':
            items = [i for i in load_all(base) if not a.status or i['status'] == a.status]
            print(json.dumps(items, ensure_ascii=False, indent=2) if a.json else '\n'.join(map(line, items)) or 'Keine Kandidaten.')
        elif a.cmd == 'adopt':
            i, meta = adopt(base, a.cid, a.file, a.confirm, a.accept_unclear, a.role, a.confirm_large_collection)
            print(f'{i["id"]} als {meta["id"]} gespeichert (Status „stored“, nicht freigegeben, nicht im Buch).')
        else:
            reject(base, a.cid, a.reason)
            print(f'{a.cid} verworfen.')
        return 0
    except (ValueError, SystemExit) as exc:
        print(f'Fehler: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
