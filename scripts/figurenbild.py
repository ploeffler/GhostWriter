#!/usr/bin/env python3
"""Figurenbild-Assistent (#540): Bildstil des Projekts, Prompt aus Profil und Stil, Bildvarianten je Figur.

Aufruf:
  python scripts/figurenbild.py <buch> stil [show] [--serie <stil.yml der Serie>] [--json]
  python scripts/figurenbild.py <buch> stil set '<json>' [--serie-stil <datei>]        speichern: images/stil.yml
  python scripts/figurenbild.py <buch> prompt <figur> [--art portraet|szene] [--kleidung T] [--ausdruck T]
                                [--ort T] [--ausschnitt T] [--szene T] [--serie <stil.yml>] [--json]
  python scripts/figurenbild.py <buch> variante <figur> <bilddatei> --prompt-datei <datei> [--art erzeugung|aenderung]
                                [--eingabe bild-001 …] [--werkzeug W] [--modell M] [--kleidung T] [--status idee]
  python scripts/figurenbild.py <buch> waehlen <figur> <bild-id> --status idee|gewaehlt|referenz [--referenz ref-img-001]
  python scripts/figurenbild.py <buch> liste [<figur>] [--json]
  python scripts/figurenbild.py <buch> pruefen                  Prüfsummen der abgelegten Bilder, doppelte Kleidung

Bildstil (`images/stil.yml`, Schema schemas/image-style.schema.json): Medium (`foto`, `comic`, `illustration`,
`aquarell`, `frei`), Realismus, Farbigkeit, Licht, Ausschnitt, Hintergrund, wiederkehrende Merkmale, Ausschlüsse,
Freitext. Er gehört dem Projekt und ist von der literarischen Erzählstimme (`style` in ghostwriter.yml) getrennt.
Eine Serie führt ihn unter `series/<ser-id>/stil.yml`; der Band erbt ihn und überschreibt Felder in `images/stil.yml`.

Je Figur liegt `characters/<char-id>/bilder.yml` (Schema schemas/figure-images.schema.json) mit den Bildern unter
`characters/<char-id>/bilder/`: je Variante `datei`, `sha256`, der vollständig gesendete `prompt`, `art` (`erzeugung` |
`aenderung`), `eingabe` (Bild-IDs), `werkzeug` und `modell` (sonst `unbekannt`), `quelle_profil` (Stand des Profils),
`herkunft` je Angabe (`profil` | `autor` | `bildgestaltung`) und `status` (`idee` | `gewaehlt` | `referenz`). Originale werden nie überschrieben.

Grenzen: Das Skript ändert weder Figurenprofil noch Manuskript und gibt nichts frei. `referenz` setzt der Status nur,
wenn die Referenzfreigabe (#417, `reference_images.py`) vorliegt; ein Bild allein ist keine Freigabe. Bilder entstehen im
Chat des Benutzers; das Skript ruft keinen Bilddienst auf.
"""
import argparse
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

MEDIEN = {'foto': 'fotorealistisch', 'comic': 'Comic', 'illustration': 'Illustration', 'aquarell': 'Aquarell', 'frei': 'frei beschrieben'}
STIL_FELDER = ('medium', 'realismus', 'farbigkeit', 'licht', 'ausschnitt', 'hintergrund', 'merkmale', 'ausschluesse', 'freitext')
STATUS = ('idee', 'gewaehlt', 'referenz')
ARTEN = ('erzeugung', 'aenderung')
HERKUNFT = ('profil', 'autor', 'bildgestaltung')
EXT = {'.png', '.jpg', '.jpeg', '.webp'}
STIL_DATEI = Path('images') / 'stil.yml'
ABSCHLUSS = 'Keine Beschriftung, kein Wasserzeichen.'


class FigurenbildError(Exception):
    pass


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def read_yaml(path):
    try:
        data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    except OSError:
        return None
    except yaml.YAMLError as e:
        raise FigurenbildError(f'{path}: nicht lesbar ({e})')
    return data if isinstance(data, dict) else None


def write_yaml(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10 ** 6), encoding='utf-8')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


# ---------- Bildstil ----------

def clean_style(data):
    """Nur bekannte Felder, Listen als Listen, leere Werte weg."""
    out = {}
    for key in STIL_FELDER:
        value = (data or {}).get(key)
        if value in (None, '', []):
            continue
        if key in ('merkmale', 'ausschluesse'):
            value = [str(v).strip() for v in (value if isinstance(value, list) else str(value).split(',')) if str(v).strip()]
            if not value:
                continue
        else:
            value = str(value).strip()
        out[key] = value
    if out.get('medium') and out['medium'] not in MEDIEN:
        raise FigurenbildError(f'medium: {", ".join(MEDIEN)} (nicht: {out["medium"]})')
    unknown = sorted(set(data or {}) - set(STIL_FELDER))
    if unknown:
        raise FigurenbildError('Unbekannte Felder im Bildstil: ' + ', '.join(unknown))
    return out


def merged_style(base, series_file=None):
    """Stil des Bands über dem der Serie: (Stil, Herkunft je Feld `serie`|`buch`)."""
    series = clean_style(read_yaml(series_file) or {}) if series_file else {}
    book = clean_style(read_yaml(Path(base) / STIL_DATEI) or {})
    merged = {**series, **book}
    origin = {k: ('buch' if k in book else 'serie') for k in merged}
    return merged, origin


def style_text(style):
    """Der Stil als Satzteile für den Prompt."""
    parts = []
    if style.get('medium'):
        parts.append(MEDIEN[style['medium']] if style['medium'] != 'frei' else '')
    for key, label in (('realismus', 'Realismus: '), ('farbigkeit', 'Farben: '), ('licht', 'Licht: '), ('hintergrund', 'Hintergrund: ')):
        if style.get(key):
            parts.append(label + style[key])
    if style.get('merkmale'):
        parts.append('wiederkehrend: ' + ', '.join(style['merkmale']))
    if style.get('freitext'):
        parts.append(style['freitext'])
    return '; '.join(p for p in parts if p)


def cmd_stil(base, args):
    sub = args.args[0] if args.args else 'show'
    if sub == 'set':
        if len(args.args) != 2:
            raise FigurenbildError('stil set braucht ein JSON mit den Stilfeldern.')
        try:
            new = clean_style(json.loads(args.args[1]))
        except json.JSONDecodeError as e:
            raise FigurenbildError(f'JSON nicht lesbar: {e}')
        if not new:
            raise FigurenbildError('Mindestens ein Stilfeld angeben (medium, realismus, …).')
        old = read_yaml(Path(base) / STIL_DATEI) or {}
        write_yaml(Path(base) / STIL_DATEI, {**clean_style(old), **new})
        print(f'✓ Bildstil gespeichert: {STIL_DATEI.as_posix()}')
        print('Commit-Nachricht: Bildstil des Projekts gespeichert')
        return 0
    if sub != 'show':
        raise FigurenbildError('stil show | stil set')
    style, origin = merged_style(base, args.serie)
    if args.json:
        print(json.dumps({'stil': style, 'herkunft': origin}, ensure_ascii=False, indent=1))
        return 0
    if not style:
        print('Noch kein Bildstil festgelegt (images/stil.yml). Medium zur Wahl: ' + ', '.join(f'{k} ({v})' for k, v in MEDIEN.items()))
        return 0
    for k, v in style.items():
        print(f'- {k}: {", ".join(v) if isinstance(v, list) else v}' + (' (Serie)' if origin[k] == 'serie' else ''))
    return 0


# ---------- Figuren ----------

def figure(base, key):
    from render_view import character_file, find_character, load
    _, config = load(Path(base))
    item = find_character(config, key)
    if not item:
        raise FigurenbildError(f'Figur nicht gefunden: {key}')
    head, description, _ = character_file(Path(base), item)
    return item, head, description


def figure_dir(base, char_id):
    return Path(base) / 'characters' / char_id


def images_file(base, char_id):
    return figure_dir(base, char_id) / 'bilder.yml'


def load_images(base, char_id):
    data = read_yaml(images_file(base, char_id)) or {}
    data.setdefault('figur', char_id)
    data.setdefault('bilder', [])
    return data


def profile_digest(item, head, description):
    h = hashlib.sha256(json.dumps([head, description], ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()
    return h[:16]


def cmd_prompt(base, args):
    if len(args.args) != 1:
        raise FigurenbildError('prompt braucht die Figur (ID oder Name).')
    item, head, description = figure(base, args.args[0])
    style, _ = merged_style(base, args.serie)
    parts, origin = [], {}

    def add(key, text, source):
        if text:
            parts.append((key, text))
            origin[key] = source
    add('bildart', 'Szenenbild' if args.art == 'szene' else 'Porträt einer Romanfigur', 'bildgestaltung')
    add('figur', f'{item["name"]}' + (f', {head["age"]} Jahre' if str(head.get('age') or '').isdigit() else (f', {head["age"]}' if head.get('age') else '')), 'profil')
    add('aussehen', str(head.get('appearance') or '').strip(), 'profil')
    add('merkmale', str(head.get('visual') or '').strip(), 'profil')
    add('kleidung', args.kleidung, 'autor')
    add('ausdruck', args.ausdruck, 'autor')
    add('szene', args.szene, 'autor')
    add('ort', args.ort, 'autor')
    add('ausschnitt', args.ausschnitt or style.get('ausschnitt'), 'autor' if args.ausschnitt else 'bildgestaltung')
    add('stil', style_text(style), 'bildgestaltung')
    ausschluesse = ', '.join(style.get('ausschluesse') or [])
    add('grenzen', (f'Ohne: {ausschluesse}. ' if ausschluesse else '') + ABSCHLUSS, 'bildgestaltung')
    offen = [k for k in ('aussehen', 'kleidung', 'ausdruck', 'ort') if k not in origin]
    prompt = '\n'.join(f'{k.capitalize()}: {t}' for k, t in parts)
    data = {'figur': item['id'], 'prompt': prompt, 'herkunft': origin, 'offen': offen, 'profil_stand': profile_digest(item, head, description),
            'stil_gesetzt': bool(style)}
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return 0
    print(prompt)
    print('\n---')
    print('Herkunft: ' + ', '.join(f'{k}={v}' for k, v in origin.items()))
    if offen:
        print('Noch offen (nicht im Profil, Vorschlag der Bildgestaltung, kein Manuskriptfakt): ' + ', '.join(offen))
    if not style:
        print('Hinweis: Noch kein Bildstil festgelegt (stil set).')
    return 0


# ---------- Varianten ----------

def next_id(images):
    nums = [int(i['id'][5:]) for i in images if str(i.get('id', '')).startswith('bild-') and str(i['id'][5:]).isdigit()]
    return f'bild-{max(nums, default=0) + 1:03d}'


def cmd_variante(base, args):
    if len(args.args) != 2:
        raise FigurenbildError('variante braucht Figur und Bilddatei.')
    item, head, description = figure(base, args.args[0])
    src = Path(args.args[1])
    if not src.is_file() or src.suffix.lower() not in EXT:
        raise FigurenbildError('Bilddatei fehlt oder ist kein PNG/JPEG/WebP.')
    if not args.prompt_datei or not Path(args.prompt_datei).is_file():
        raise FigurenbildError('--prompt-datei: der vollständig gesendete Prompt gehört zu jedem Bild.')
    prompt = Path(args.prompt_datei).read_text(encoding='utf-8').strip()
    if not prompt:
        raise FigurenbildError('Der Prompt ist leer.')
    if args.status not in ('idee', 'gewaehlt'):
        raise FigurenbildError('Neue Bilder sind „idee“ oder „gewaehlt“; „referenz“ setzt `waehlen` nach der Referenzfreigabe.')
    data = load_images(base, item['id'])
    known = {i['id'] for i in data['bilder']}
    for ref in args.eingabe or []:
        if ref not in known:
            raise FigurenbildError(f'Eingabebild unbekannt: {ref}')
    if args.art == 'aenderung' and not args.eingabe:
        raise FigurenbildError('Eine Änderung braucht das Eingabebild (--eingabe bild-NNN).')
    bid = next_id(data['bilder'])
    target_dir = figure_dir(base, item['id']) / 'bilder'
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f'{bid}{src.suffix.lower()}'
    if target.exists():
        raise FigurenbildError(f'{target} gibt es schon; Originale werden nie überschrieben.')
    shutil.copyfile(src, target)
    entry = {'id': bid, 'datei': f'bilder/{target.name}', 'sha256': sha256(target), 'angelegt': now(), 'art': args.art,
             'prompt': prompt, 'eingabe': list(args.eingabe or []), 'werkzeug': args.werkzeug or 'unbekannt', 'modell': args.modell or 'unbekannt',
             'quelle_profil': profile_digest(item, head, description), 'status': args.status}
    if args.kleidung:
        entry['kleidung'] = args.kleidung
    if args.herkunft:
        entry['herkunft'] = dict(h.split('=', 1) for h in args.herkunft if '=' in h and h.split('=', 1)[1] in HERKUNFT)
    data['bilder'].append(entry)
    write_yaml(images_file(base, item['id']), data)
    print(f'✓ Bild {bid} für {item["name"]} abgelegt: characters/{item["id"]}/{entry["datei"]} (Status {args.status})')
    print(f'Commit-Nachricht: Figurenbild {bid} für „{item["name"]}“ abgelegt')
    return 0


def cmd_waehlen(base, args):
    if len(args.args) != 2:
        raise FigurenbildError('waehlen braucht Figur und Bild-ID.')
    item, _, _ = figure(base, args.args[0])
    if args.status not in STATUS:
        raise FigurenbildError('--status idee|gewaehlt|referenz')
    data = load_images(base, item['id'])
    hit = next((i for i in data['bilder'] if i['id'] == args.args[1]), None)
    if not hit:
        raise FigurenbildError(f'Bild nicht gefunden: {args.args[1]}')
    if args.status == 'referenz':
        import reference_images
        ref = (reference_images.all_references(Path(base)).get(args.referenz or '') or (None,))[0]
        if not ref or ref.get('status') != 'approved':
            raise FigurenbildError('„referenz“ nur mit freigegebenem Referenzbild (--referenz ref-img-…, Freigabe nach #417).')
        hit['referenz'] = args.referenz
    hit['status'] = args.status
    write_yaml(images_file(base, item['id']), data)
    print(f'✓ {hit["id"]}: {args.status}')
    return 0


def cmd_liste(base, args):
    from render_view import character_items, load
    _, config = load(Path(base))
    keys = [args.args[0]] if args.args else [i['id'] for i in character_items(config)]
    rows = []
    for key in keys:
        item = figure(base, key)[0]
        for img in load_images(base, item['id'])['bilder']:
            rows.append({'figur': item['id'], 'name': item['name'], **{k: img.get(k) for k in ('id', 'datei', 'art', 'status', 'kleidung', 'werkzeug', 'modell')}})
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        print('\n'.join(f'- {r["name"]}: {r["id"]} ({r["art"]}, {r["status"]})' + (f', Kleidung: {r["kleidung"]}' if r.get('kleidung') else '')
                        + f' – {r["datei"]}' for r in rows) or 'Keine Figurenbilder.')
    return 0


def cmd_pruefen(base, args):
    from render_view import character_items, load
    _, config = load(Path(base))
    problems, clothing = [], {}
    for item in character_items(config):
        if '_series' in item:
            continue
        for img in load_images(base, item['id'])['bilder']:
            path = figure_dir(base, item['id']) / img['datei']
            if not path.is_file():
                problems.append(f'{item["id"]}/{img["id"]}: Datei fehlt ({img["datei"]})')
            elif sha256(path) != img.get('sha256'):
                problems.append(f'{item["id"]}/{img["id"]}: Prüfsumme weicht ab (Bild verändert?)')
            if not str(img.get('prompt') or '').strip():
                problems.append(f'{item["id"]}/{img["id"]}: Prompt fehlt')
            if img.get('kleidung') and img.get('status') in ('gewaehlt', 'referenz'):
                clothing.setdefault(str(img['kleidung']).strip().casefold(), set()).add(item['name'])
    for text, names in clothing.items():
        if len(names) > 1:
            problems.append(f'gleiche Kleidung bei {", ".join(sorted(names))}: „{text}“ (Stil gemeinsam, Kleidung je Figur unterscheiden)')
    print('\n'.join(f'- {p}' for p in problems) if problems else '✓ Figurenbilder in Ordnung')
    return 1 if problems else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['stil', 'prompt', 'variante', 'waehlen', 'liste', 'pruefen'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--serie', help='stil.yml der Serie (series/<ser-id>/stil.yml); der Band erbt davon')
    ap.add_argument('--art', default=None)
    ap.add_argument('--kleidung')
    ap.add_argument('--ausdruck')
    ap.add_argument('--ort')
    ap.add_argument('--ausschnitt')
    ap.add_argument('--szene')
    ap.add_argument('--prompt-datei')
    ap.add_argument('--eingabe', action='append')
    ap.add_argument('--werkzeug')
    ap.add_argument('--modell')
    ap.add_argument('--herkunft', action='append', metavar='ANGABE=profil|autor|bildgestaltung')
    ap.add_argument('--status', default='idee')
    ap.add_argument('--referenz')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'variante':
            a.art = a.art or 'erzeugung'
            if a.art not in ARTEN:
                raise FigurenbildError('--art erzeugung|aenderung')
        elif a.cmd == 'prompt':
            a.art = a.art or 'portraet'
            if a.art not in ('portraet', 'szene'):
                raise FigurenbildError('--art portraet|szene')
        return {'stil': cmd_stil, 'prompt': cmd_prompt, 'variante': cmd_variante, 'waehlen': cmd_waehlen,
                'liste': cmd_liste, 'pruefen': cmd_pruefen}[a.cmd](a.project, a)
    except FigurenbildError as e:
        print(f'::error::{e}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
