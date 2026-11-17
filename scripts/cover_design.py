#!/usr/bin/env python3
"""Buchbezogene Covergestaltung: prüfen, Farben lesen und Einstellungen speichern."""
import argparse
import copy
import json
import math
from pathlib import Path

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parent.parent
PARTS = ('title', 'subtitle', 'author')


def validate(cover, width, height):
    schema = json.loads((ROOT / 'schemas/ghostwriter.schema.json').read_text())['properties']['cover']
    errors = [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(cover)]
    if errors:
        return errors
    if cover.get('image_mode') == 'finished' and not cover.get('image'):
        errors.append('cover.image_mode: finished benötigt cover.image')
    for part, box in (cover.get('text_boxes') or {}).items():
        if not isinstance(box, dict) or not all(k in box for k in ('x', 'y', 'width', 'height')):
            continue
        if any(not isinstance(box[k], (int, float)) or not math.isfinite(box[k])
               for k in ('x', 'y', 'width', 'height', 'font_size') if k in box):
            errors.append(f'cover.text_boxes.{part}: endliche Maße erforderlich')
            continue
        if box.get('visible', True) and (box['x'] < 10 or box['y'] < 10 or
                box['x'] + box['width'] > width - 10 or box['y'] + box['height'] > height - 10):
            errors.append(f'cover.text_boxes.{part}: Textbereich muss innerhalb des Sicherheitsrands von 10 mm liegen')
    return errors


def image_colors(base, cover, point=None):
    """Unverändertes Originalbild, Koordinaten 0–1 ab linker oberer Bildecke (vor Beschnitt)."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError('Farbauswahl benötigt Pillow: python -m pip install pillow') from exc
    name = cover.get('image')
    if not name:
        raise ValueError('Zuerst cover.image auswählen')
    path = (base / name).resolve()
    if not path.is_relative_to((base / 'cover').resolve()):
        raise ValueError('Bild muss im Coverordner liegen')
    with Image.open(path) as source:
        im = source.convert('RGBA')
        bg = Image.new('RGBA', im.size, 'white')
        bg.alpha_composite(im)
        im = bg.convert('RGB')
        hexcolor = lambda rgb: '#' + ''.join(f'{v:02X}' for v in rgb)
        if point is not None:
            if any(not math.isfinite(v) or not 0 <= v <= 1 for v in point):
                raise ValueError('Bildstelle: x und y zwischen 0 und 1')
            return [hexcolor(im.getpixel((round(point[0] * (im.width - 1)),
                                         round(point[1] * (im.height - 1)))))]
        im.thumbnail((256, 256))
        # Ecken separat anbieten: freie helle Flächen müssen nicht dominant sein.
        colors = [im.getpixel(p) for p in ((0, 0), (im.width - 1, 0),
                                          (0, im.height - 1), (im.width - 1, im.height - 1))]
        pal = im.quantize(colors=6).convert('RGB')
        colors += [rgb for _, rgb in sorted(pal.getcolors(im.width * im.height), reverse=True)]
        return list(dict.fromkeys(hexcolor(c) for c in colors))


def propose(config, patch):
    """Geprüfte Coverdaten für Vorschau oder Speicherung, ohne Schreibzugriff."""
    from build_cover import PAGE
    cover = copy.deepcopy(config.get('cover') or {})
    if not isinstance(patch, dict):
        raise ValueError('Coveränderung muss ein JSON-Objekt sein')
    for key, value in patch.items():
        if key == 'text_boxes' and isinstance(value, dict):
            boxes = cover.setdefault(key, {})
            for part, box in value.items():
                if box is None:
                    boxes.pop(part, None)
                else:
                    if not isinstance(box, dict):
                        raise ValueError(f'Textbereich {part} muss ein JSON-Objekt sein')
                    boxes[part] = dict(boxes.get(part) or {}, **box)
        elif key == 'panel_backgrounds' and isinstance(value, dict):
            panels = cover.setdefault(key, {})
            for panel, color in value.items():
                if color is None:
                    panels.pop(panel, None)
                else:
                    panels[panel] = color
        elif value is None:
            cover.pop(key, None)
        else:
            cover[key] = value
    w, h = PAGE.get((config.get('typesetting') or {}).get('page_size', 'a5'), PAGE['a5'])
    errors = validate(cover, w, h)
    if errors:
        raise ValueError('; '.join(errors))
    return cover


def save(base, patch):
    """Nur explizit angegebene Coverfelder ändern; Texte bleiben in project.*."""
    path = base / 'ghostwriter.yml'
    config = yaml.safe_load(path.read_text(encoding='utf-8'))
    cover = propose(config, patch)
    config['cover'] = cover
    path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return cover


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('project', type=Path)
    sub = ap.add_subparsers(dest='action', required=True)
    sub.add_parser('show')
    colors = sub.add_parser('colors')
    colors.add_argument('--point', nargs=2, type=float, metavar=('X', 'Y'))
    setter = sub.add_parser('set')
    setter.add_argument('patch', help='JSON-Objekt mit zu ändernden Coverfeldern')
    preview = sub.add_parser('preview', help='Vorschlag ohne Speichern mit dem echten Coverrenderer prüfen')
    preview.add_argument('patch', nargs='?', default='{}')
    preview.add_argument('--pages', type=int, default=0)
    preview.add_argument('--out', type=Path, required=True)
    preview.add_argument('--front-jpg', type=Path, required=True)
    args = ap.parse_args()
    try:
        config = yaml.safe_load((args.project / 'ghostwriter.yml').read_text(encoding='utf-8'))
        cover = config.get('cover') or {}
        if args.action == 'set':
            result = save(args.project, json.loads(args.patch))
        elif args.action == 'preview':
            from build_cover import build, front_only
            config['cover'] = propose(config, json.loads(args.patch))
            build(args.project, front_only(config), args.pages, args.out, args.front_jpg)
            result = {'preview': str(args.front_jpg.with_suffix('.jpg')), 'cover': config['cover']}
        elif args.action == 'colors':
            result = image_colors(args.project, cover, args.point)
        else:
            result = cover
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        ap.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
