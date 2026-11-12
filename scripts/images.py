#!/usr/bin/env python3
"""Illustrationen (#54): Bild-Auftrag (Prompt), Ablegen, Verweise im Text.

Aufruf:
  python scripts/images.py <projektordner> list [<abschnitt>]
  python scripts/images.py <projektordner> prompt <abschnitt N.M|sec-…|mat-…> --scene "…" [--characters Name …]
  python scripts/images.py <projektordner> add <abschnitt> <bilddatei> --caption "…" [--alt "…"] [--prompt "…"]
                           [--source chat|copy|own] [--provider ID] [--model M] [--characters Name …]
                           [--variants N] [--credit "…"]
  python scripts/images.py <projektordner> ref <img-id>

prompt setzt den Bild-Auftrag zusammen: Bildstil des Buchs (images.style), die
Szene und für jede beteiligte Figur ihre feste Bildbeschreibung (`visual`, sonst
`appearance`, aus #53). Gleiche Figuren bekommen so in jedem Auftrag dieselben
Merkmale. Ohne --characters gelten die Figuren aus dem Kopf des Abschnitts.

add legt ein Bild ab: chapters/<kapitel>/images/<abschnitt>/img-<slug>.<png|jpg>
(bei Vor-/Nachspann matter/images/<mat-id>/), dazu img-<slug>.yml (Beschreibung,
Schema schemas/image.schema.json) und den Lauf run-NNN.md (unveränderlich).
Status ist zunächst `draft`; ins Buch kommt ein Bild erst nach der Freigabe
(START.md, „Illustrationen“). Pillow prüft Uploads. images.max_px (Vorgabe 3000)
begrenzt die Buchfassung; Verkleinerung nur nach Bestätigung, Original bleibt erhalten.
--source: chat (im Chat erzeugt), copy (Auftrag bei einem anderen Dienst),
own (eigenes Bild, nicht KI-erzeugt).

ref gibt die Zeile für das Manuskript aus: `![](bild:img-…)`; die
Bildunterschrift kommt aus der Beschreibung. Den Text ändert der Assistent nur
mit Schreibfreigabe.

Den Commit schreibt der Assistent (START.md, „Illustrationen“).
"""
import argparse
import datetime
import hashlib
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from render_view import (character_file, character_items, find_character, find_matter, load,  # noqa: E402
                         section_file, tag_slug)

IMAGE_REF = re.compile(r'!\[([^\]]*)\]\(bild:(img-[a-z0-9][a-z0-9-]*)\)(\{[^}]*\})?')
DEFAULT_MAX_PX = 3000
EXT = {'.png': '.png', '.jpg': '.jpg', '.jpeg': '.jpg'}


def settings(config):
    s = {'style': '', 'credit_in_imprint': True, 'max_px': DEFAULT_MAX_PX}
    s.update((config or {}).get('images') or {})
    return s


def find_target(config, key):
    """Abschnitt (N.M, sec-…) bzw. Teil (mat-…, Name) → (eintrag, ordner relativ zum Projekt)."""
    chapters = config['structure']['chapters']
    if re.fullmatch(r'\d+\.\d+', key or ''):
        c, s = (int(x) for x in key.split('.'))
        sec = chapters[c - 1]['sections'][s - 1]
        return sec, f'{chapters[c - 1]["path"]}/images/{sec["id"]}'
    for ch in chapters:
        for s in ch['sections']:
            if s['id'] == key:
                return s, f'{ch["path"]}/images/{s["id"]}'
    item = find_matter(config, key)
    if item:
        return item, f'matter/images/{item["id"]}'
    raise SystemExit(f'Abschnitt bzw. Teil „{key}“ nicht gefunden')


def image_folders(config):
    """Alle Bildordner des Buchs: [(eintrag, ordner)]."""
    out = []
    for ch in config['structure']['chapters']:
        for s in ch['sections']:
            out.append((s, f'{ch["path"]}/images/{s["id"]}'))
    for area in ('front_matter', 'back_matter'):
        for item in (config.get('structure') or {}).get(area) or []:
            out.append((item, f'matter/images/{item["id"]}'))
    return out


def all_images(base, config):
    """{img-id: (beschreibung, bilddatei Path, ordner)} über alle Bildordner."""
    out = {}
    for _, folder in image_folders(config):
        d = base / folder
        if not d.is_dir():
            continue
        for meta_path in sorted(d.glob('img-*.yml')):
            meta = yaml.safe_load(meta_path.read_text(encoding='utf-8')) or {}
            out[meta.get('id', meta_path.stem)] = (meta, d / str(meta.get('file', '')), folder, meta_path)
    return out


def image_size(path):
    import build_cover
    return build_cover.image_size(path)


def character_lines(base, config, ids):
    by_id = {c['id']: c for c in character_items(config)}
    lines = []
    for cid in ids:
        item = by_id.get(cid)
        if not item:
            continue
        head = character_file(base, item)[0]
        look = head.get('visual') or head.get('appearance') or head.get('short') or ''
        lines.append(f'- {item["name"]}: {look}'.rstrip(': '))
    return lines


def build_prompt(base, config, key, scene, names=None, reference_ids=None):
    target, _ = find_target(config, key)
    if names:
        ids = []
        for n in names:
            c = find_character(config, n)
            if not c:
                raise SystemExit(f'Figur „{n}“ nicht gefunden')
            ids.append(c['id'])
    else:
        ids = section_file(base, target)[0].get('characters') or []
    s = settings(config)
    parts = []
    if s['style']:
        parts.append(f'Stil: {s["style"]}')
    parts.append(f'Szene: {scene.strip()}')
    chars = character_lines(base, config, ids)
    if chars:
        parts.append('Figuren (immer genau so darstellen):\n' + '\n'.join(chars))
    if reference_ids:
        from reference_images import select as select_reference_images
        refs = select_reference_images(base, reference_ids)
        lines = []
        for ref in refs:
            detail = ref.get('description') or ref.get('purpose') or ref['caption']
            lines.append(f'- {ref["id"]} ({ref["caption"]}): {detail}')
        parts.append('Ausdrücklich ausgewählte visuelle Referenzen (Bilddateien zusätzlich an den Bilddienst übergeben):\n' + '\n'.join(lines))
    parts.append('Ohne Schrift, Buchstaben oder Logos im Bild. Hochformat oder Querformat passend zur Szene.')
    return '\n\n'.join(parts), ids


def next_run(folder):
    nums = [int(p.stem[4:]) for p in folder.glob('run-[0-9][0-9][0-9].md')]
    return f'run-{max(nums, default=0) + 1:03d}'


def add(base, key, file, caption, alt='', prompt='', source='chat', provider='', model='', names=None,
        variants=1, credit='', reference_ids=None, *, confirm_resize=False, confirm_large_collection=False):
    _, config = load(base)
    target, folder_rel = find_target(config, key)
    src = Path(file)
    if not src.is_file():
        raise SystemExit(f'{file}: Datei fehlt')
    ext = EXT.get(src.suffix.lower())
    if not ext:
        raise SystemExit('Nur PNG oder JPEG.')
    reference_records = []
    if reference_ids:
        if source == 'own':
            raise SystemExit('Eigene, nicht KI-erzeugte Bilder können keine KI-Referenzen protokollieren.')
        from reference_images import select as select_reference_images
        for ref in select_reference_images(base, reference_ids):
            ref_path = Path(ref['file'])
            if not ref_path.is_file():
                raise SystemExit(f'Referenzdatei fehlt: {ref_path}')
            reference_records.append({
                'id': ref['id'],
                'file': ref_path.name,
                'sha256': hashlib.sha256(ref_path.read_bytes()).hexdigest(),
                'caption': ref['caption']
            })
    from media_policy import prepare_upload, safe_destination
    data = prepare_upload(base, src, confirm_large_collection=confirm_large_collection)
    max_px = int(settings(config)['max_px'])
    if max_px < 1:
        raise ValueError('Ungültige maximale Bildkante')
    from io import BytesIO
    from PIL import Image
    with Image.open(BytesIO(data)) as image:
        if image.format not in ('PNG', 'JPEG'):
            raise ValueError('Nur PNG oder JPEG.')
        size = image.size
        image.verify()
    resized = None
    if max(size) > max_px:
        if not confirm_resize:
            raise ValueError('Verkleinerung ausdrücklich bestätigen; Original bleibt unverändert')
        with Image.open(BytesIO(data)) as image:
            image.thumbnail((max_px, max_px))
            out = BytesIO()
            image.save(out, format='JPEG' if ext == '.jpg' else 'PNG', **({'quality': 90} if ext == '.jpg' else {}))
            resized = out.getvalue()
            size = image.size
        prepare_upload(base, src, additional_bytes=len(resized),
                       confirm_large_collection=confirm_large_collection)
    folder = safe_destination(base, folder_rel)
    taken = set(all_images(base, config))
    slug = tag_slug(caption or target['title'])[:40].strip('-') or 'bild'
    iid, n = f'img-{slug}', 2
    while (iid in taken or (folder / f'{iid}{ext}').exists()
           or (folder / 'originals' / f'{iid}{ext}').exists()):
        iid = f'img-{slug}-{n}'
        n += 1
    dest = folder / f'{iid}{ext}'
    original_name = f'originals/{iid}{ext}' if resized is not None else dest.name
    original = safe_destination(base, Path(folder_rel) / original_name)
    folder.mkdir(parents=True, exist_ok=True)
    original.parent.mkdir(parents=True, exist_ok=True)
    with original.open('xb') as output:
        output.write(data)
    if resized is not None:
        with dest.open('xb') as output:
            output.write(resized)
    ids = []
    for nme in names or []:
        c = find_character(config, nme)
        if c:
            ids.append(c['id'])
    run = next_run(folder)
    meta = {'id': iid, 'section_id': target['id'], 'file': dest.name, 'caption': caption.strip(), 'alt': (alt or caption).strip(),
            'status': 'draft', 'ai_generated': source != 'own', 'source': source,
            'original_file': original_name, 'original_sha256': hashlib.sha256(data).hexdigest()}
    if provider:
        meta['provider'] = provider
    if model:
        meta['model'] = model
    if prompt:
        meta['prompt'] = prompt.strip()
    if ids:
        meta['characters'] = ids
    if source != 'own':
        meta['run'] = run
    if credit:
        meta['credit'] = credit
    if size[0]:
        meta['width_px'], meta['height_px'] = size
    (folder / f'{iid}.yml').write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')
    if source != 'own':
        now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
        (folder / f'{run}.md').write_text(
            '---\n' + yaml.safe_dump({'id': run, 'type': 'illustration', 'section_id': target['id'], 'status': 'completed',
                                      'date': now[:10], 'created_at': now, 'provider': provider or 'chat',
                                      'model': model or '', 'source': source, 'characters': ids,
                                      'variants': int(variants), 'selected': dest.name,
                                      'visual_references': reference_records},
                                     allow_unicode=True, sort_keys=False) + '---\n\n'
            f'# Bildauftrag {run[4:]}\n\n## Prompt\n\n{prompt.strip() or "(nicht festgehalten)"}\n\n'
            + (('## Verwendete visuelle Referenzen\n\n' + '\n'.join(
                f'- {ref["id"]} ({ref["caption"]}), Datei `{ref["file"]}`, SHA-256 `{ref["sha256"]}`'
                for ref in reference_records) + '\n\n') if reference_records else '')
            + f'## Ergebnis\n\nAusgewählt: `{dest.name}` aus {int(variants)} Variante(n). Status: Entwurf, Freigabe offen.\n',
            encoding='utf-8')
    return meta, folder_rel


def refs_in(text):
    return [m.group(2) for m in IMAGE_REF.finditer(text or '')]


def placement_problems(texts):
    """Höchstens ein Medium je Abschnitt, jedes Bild nur einmal im Buch (D13, Medienplatzierung).

    texts: [(wo, text, abschnitt?)]. Gezählt werden nur Verweise im Text; Varianten und
    Referenzbilder ohne Verweis zählen nicht. Gibt Meldungen zurück."""
    out, seen = [], {}
    for where, text, is_section in texts:
        ids = refs_in(text)
        if is_section and len(ids) > 1:
            out.append(f'{where}: {len(ids)} Medien im Abschnitt, erlaubt ist eines ({", ".join(ids)})')
        for iid in ids:
            if iid in seen:
                out.append(f'{where}: Bild {iid} ist mehrfach eingefügt (auch in {seen[iid]})')
            else:
                seen[iid] = where
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['list', 'prompt', 'add', 'ref'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--scene', default='')
    ap.add_argument('--references', nargs='*', default=[], help='freigegebene ref-img-IDs für Prompt und Auftragsprotokoll')
    ap.add_argument('--characters', nargs='*')
    ap.add_argument('--caption', default='')
    ap.add_argument('--alt', default='')
    ap.add_argument('--prompt', default='')
    ap.add_argument('--confirm-resize', action='store_true', help='Verkleinerung bei unverändertem Original ausdrücklich bestätigen')
    ap.add_argument('--confirm-large-collection', action='store_true', help='Upload ab 500 MB Bildbestand ausdrücklich bestätigen')
    ap.add_argument('--source', default='chat', choices=['chat', 'copy', 'own'])
    ap.add_argument('--provider', default='')
    ap.add_argument('--model', default='')
    ap.add_argument('--variants', type=int, default=1)
    ap.add_argument('--credit', default='')
    a = ap.parse_args(argv[1:])
    base = Path(a.project)
    _, config = load(base)
    if a.cmd == 'list':
        imgs = all_images(base, config)
        if a.args:
            sid = find_target(config, a.args[0])[0]['id']
            imgs = {k: v for k, v in imgs.items() if v[0].get('section_id') == sid}
        for iid, (meta, path, folder, _) in imgs.items():
            print(f'{iid:<32} {meta.get("status"):<9} {meta.get("caption", "")}  ({folder}/{meta.get("file")})')
        return 0
    if a.cmd == 'prompt':
        if not a.args or not a.scene:
            ap.error('prompt braucht Abschnitt und --scene')
        print(build_prompt(base, config, a.args[0], a.scene, a.characters, a.references)[0])
        if a.references:
            from reference_images import select as select_reference_images
            print('\nDateien für die Referenzübergabe:')
            for ref in select_reference_images(base, a.references):
                print(f'- {ref["id"]}: {ref["file"]}')
        return 0
    if a.cmd == 'ref':
        if not a.args:
            ap.error('ref braucht eine Bild-ID')
        print(f'![](bild:{a.args[0]})')
        return 0
    if len(a.args) != 2:
        ap.error('add braucht Abschnitt und Bilddatei')
    if not a.caption:
        ap.error('add braucht --caption (Bildunterschrift)')
    meta, folder = add(base, a.args[0], a.args[1], a.caption, a.alt, a.prompt, a.source, a.provider, a.model,
                       a.characters, a.variants, a.credit, a.references,
                       confirm_resize=a.confirm_resize, confirm_large_collection=a.confirm_large_collection)
    print(f'✓ Bild {meta["id"]} abgelegt: {folder}/{meta["file"]} (Entwurf)')
    print(f'Im Text: ![](bild:{meta["id"]})')
    print(f'Commit-Nachricht: Bild „{meta["caption"]}“ abgelegt')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv))
    except (ValueError, OSError) as error:
        raise SystemExit(str(error)) from None
