#!/usr/bin/env python3
"""Material einbringen (#574): Foto, Foto vom Foto, Dokument oder Rückgabe ablegen, aufbereiten, markieren.

  python3 scripts/material.py <buch> add <datei> --art foto|foto-vom-foto|dokument|rueckgabe --name <kurzname>
                                         [--date JJJJ-MM-TT] [--minors]
      legt `quellen/<datum>-<kurzname>/original.<endung>` unverändert ab und schreibt `material.yml`
  python3 scripts/material.py <buch> prepare <ordner>
      bereitet auf (OpenCV): Blatt erkennen und gerade richten, zuschneiden, Ausleuchtung angleichen, CLAHE, leichtes
      Entrauschen → `bearbeitet.jpg`; Schwarz-Weiß bleibt Schwarz-Weiß, kein KI-Hochrechnen, keine Retusche
  python3 scripts/material.py <buch> mark <ordner> --items items.yml
      zeichnet Nummern neben die Rahmen und eine Legende unten → `markiert.jpg`; Zuordnungen kommen nur aus Angaben von
      Autor oder Zeitzeugen, nie aus dem Gesicht
  python3 scripts/material.py <buch> list [--write]
      Verzeichnis des Materials (`--write`: `quellen/verzeichnis.md`)

Grenzen: Das Original wird nie verändert oder überschrieben. Fotos mit Minderjährigen und Dokumente gehen nie an externe
Dienste (`external_allowed`). Personen werden nicht am Gesicht erkannt. Nichts wird ins Buch übernommen ohne Bestätigung.
"""
import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

import yaml

DIR = 'quellen'
ARTS = ('foto', 'foto-vom-foto', 'dokument', 'rueckgabe')


def slug(text):
    t = (text or '').translate(str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue', 'ß': 'ss'}))
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')


def read(folder):
    return yaml.safe_load((Path(folder) / 'material.yml').read_text(encoding='utf-8')) or {}


def write(folder, data):
    (Path(folder) / 'material.yml').write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')


def add(base, source, art, name, date=None, minors=False):
    """Original unverändert ablegen; gibt den Ordner zurück. Ein vorhandener Ordner wird nie überschrieben."""
    if art not in ARTS:
        raise ValueError(f'Art: {", ".join(ARTS)}')
    source = Path(source)
    if not source.is_file():
        raise ValueError(f'Datei nicht gefunden: {source}')
    short = slug(name)
    if not short:
        raise ValueError('Kurzname angeben (--name)')
    date = date or datetime.date.today().isoformat()
    datetime.date.fromisoformat(date)
    folder = Path(base) / DIR / f'{date}-{short}'
    if folder.exists():
        raise ValueError(f'{folder.relative_to(base)} gibt es schon; anderen Kurznamen wählen')
    folder.mkdir(parents=True)
    original = f'original{source.suffix.lower()}'
    shutil.copyfile(source, folder / original)
    write(folder, {'art': art, 'name': name, 'datum': date, 'original': original, 'minderjaehrige': bool(minors),
                   'beschreibung': '', 'offen': [], 'bearbeitung': [], 'personen': []})
    return folder


def external_allowed(meta):
    """(erlaubt, Grund): Fotos mit Minderjährigen und Dokumente gehen nie an externe Dienste (Programmgrenze)."""
    if meta.get('minderjaehrige') is not False:
        return False, 'Minderjährige zu sehen oder unklar: nie an externe Dienste'
    if meta.get('art') in ('dokument', 'rueckgabe'):
        return False, 'Dokumente und Rückgaben gehen nie an externe Dienste'
    return True, ''


def _imports():
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise ValueError('Aufbereiten braucht OpenCV (pip install opencv-python-headless numpy)') from exc
    return cv2, np


def _order(pts):
    s, d = pts.sum(axis=1), (pts[:, 0] - pts[:, 1])
    return [pts[s.argmin()], pts[d.argmax()], pts[s.argmax()], pts[d.argmin()]]   # oben links, oben rechts, unten rechts, unten links


def enhance(img):
    """Bild aufbereiten (OpenCV): (Ergebnis, Schritte). Gemeinsam für `prepare` und die Rückgabe (scripts/checkin.py)."""
    cv2, np = _imports()
    steps = []
    gray_src = float(np.abs(img[..., 0].astype(int) - img[..., 2].astype(int)).mean()) < 6   # Schwarz-Weiß bleibt Schwarz-Weiß
    h, w = img.shape[:2]
    scale = 800 / max(h, w)
    small = cv2.resize(img, None, fx=scale, fy=scale) if scale < 1 else img
    g = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (7, 7), 0)
    edges = cv2.dilate(cv2.Canny(g, 40, 120), None, iterations=2)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    quad = None
    for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:5]:
        if cv2.contourArea(c) < 0.2 * small.shape[0] * small.shape[1]:
            break
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4:
            quad = approx.reshape(4, 2).astype('float32') / scale
            break
    if quad is not None:
        tl, tr, br, bl = _order(quad)
        wd = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        ht = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
        m = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl], dtype='float32'),
                                        np.array([[0, 0], [wd, 0], [wd, ht], [0, ht]], dtype='float32'))
        img = cv2.warpPerspective(img, m, (wd, ht))
        steps.append('Blatt erkannt, gerade gerichtet und zugeschnitten')
    else:
        steps.append('kein Blattrand erkannt, nicht zugeschnitten')
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    blur = cv2.GaussianBlur(l, (0, 0), max(img.shape[:2]) / 20).astype('float32') + 1
    flat = np.clip(l.astype('float32') / blur * float(blur.mean()), 0, 255).astype('uint8')
    steps.append('Ausleuchtung angeglichen')
    flat = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(flat)
    steps.append('Kontrast (CLAHE)')
    out = cv2.cvtColor(cv2.merge([flat, a, b]), cv2.COLOR_LAB2BGR)
    out = cv2.fastNlMeansDenoisingColored(out, None, 3, 3, 7, 21)
    steps.append('leichtes Entrauschen')
    if gray_src:
        out = cv2.cvtColor(cv2.cvtColor(out, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
        steps.append('Schwarz-Weiß beibehalten')
    return out, steps


def prepare(folder):
    """`bearbeitet.jpg` aus dem Original; die Schritte stehen in `bearbeitung`. Original bleibt unverändert."""
    cv2, _ = _imports()
    folder = Path(folder)
    meta = read(folder)
    img = cv2.imread(str(folder / meta['original']), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError('Original lässt sich nicht als Bild lesen (PDF zuerst in Bilder wandeln)')
    out, steps = enhance(img)
    cv2.imwrite(str(folder / 'bearbeitet.jpg'), out, [cv2.IMWRITE_JPEG_QUALITY, 92])
    meta['bearbeitet'] = 'bearbeitet.jpg'
    meta['bearbeitung'] = steps
    write(folder, meta)
    return steps


def mark(folder, items):
    """Nummern neben die Rahmen (nie auf dem Rahmeninhalt) und eine Legende unten → `markiert.jpg`."""
    cv2, np = _imports()
    folder = Path(folder)
    meta = read(folder)
    src = folder / (meta.get('bearbeitet') or meta['original'])
    img = cv2.imread(str(src), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError('Bild lässt sich nicht lesen')
    h, w = img.shape[:2]
    font, size = cv2.FONT_HERSHEY_SIMPLEX, max(0.6, w / 1400)
    for it in items:
        if not it.get('rahmen'):
            continue
        x, y, bw, bh = it['rahmen']
        cv2.rectangle(img, (x, y), (x + bw, y + bh), (0, 0, 255), max(2, w // 600))
        label = str(it['nr'])
        (tw, th), _ = cv2.getTextSize(label, font, size, 2)
        tx, ty = min(max(0, x), w - tw - 6), y - 8 if y - th - 14 > 0 else min(h - 4, y + bh + th + 10)   # über oder unter dem Rahmen
        cv2.rectangle(img, (tx - 3, ty - th - 5), (tx + tw + 3, ty + 5), (255, 255, 255), -1)
        cv2.putText(img, label, (tx, ty), font, size, (0, 0, 200), 2, cv2.LINE_AA)
    lines = [f'{it["nr"]}: {it.get("name") or "unbekannt"} ({it.get("sicher", "unbekannt")})' for it in items]
    pad = int(30 * size) + 10
    legend = np.full((pad * (len(lines) + 1), w, 3), 255, dtype='uint8')
    for k, line in enumerate(lines, start=1):
        cv2.putText(legend, line, (10, k * pad - 6), font, size * 0.7, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(str(folder / 'markiert.jpg'), np.vstack([img, legend]), [cv2.IMWRITE_JPEG_QUALITY, 92])
    meta['markiert'] = 'markiert.jpg'
    meta['personen'] = [{k: v for k, v in it.items()} for it in items]
    write(folder, meta)
    return folder / 'markiert.jpg'


def folders(base):
    root = Path(base) / DIR
    return sorted(p.parent for p in root.glob('*/material.yml')) if root.is_dir() else []


def listing(base):
    lines = ['# Material', '', '| Ordner | Art | Name | Minderjährige | Aufbereitet | Offene Fragen |', '|---|---|---|---|---|---|']
    for f in folders(base):
        m = read(f)
        lines.append(f'| {f.name} | {m.get("art", "")} | {m.get("name", "")} | {"ja" if m.get("minderjaehrige") else "nein"} | '
                     f'{"ja" if m.get("bearbeitet") else "nein"} | {len(m.get("offen") or [])} |')
    return '\n'.join(lines) + '\n'


def problems(base):
    """Prüfung für validate: Schema, Original vorhanden, verweisene Dateien vorhanden."""
    import json
    from jsonschema import Draft202012Validator
    schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas/material.schema.json').read_text(encoding='utf-8'))
    out = []
    for f in folders(base):
        rel = f.relative_to(base).as_posix()
        try:
            data = read(f)
        except yaml.YAMLError as exc:
            out.append(f'{rel}/material.yml: {exc}')
            continue
        out += [f'{rel}/material.yml: {"/".join(map(str, e.absolute_path)) or "(Wurzel)"}: {e.message}'
                for e in Draft202012Validator(schema).iter_errors(data)]
        for key in ('original', 'bearbeitet', 'markiert'):
            if data.get(key) and not (f / data[key]).is_file():
                out.append(f'{rel}: {key} „{data[key]}“ fehlt')
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('add')
    a.add_argument('file')
    a.add_argument('--art', required=True, choices=ARTS)
    a.add_argument('--name', required=True)
    a.add_argument('--date')
    a.add_argument('--minors', action='store_true')
    p = sub.add_parser('prepare')
    p.add_argument('folder')
    m = sub.add_parser('mark')
    m.add_argument('folder')
    m.add_argument('--items', required=True)
    li = sub.add_parser('list')
    li.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)
    base = Path(args.project)
    try:
        if args.cmd == 'add':
            f = add(base, args.file, args.art, args.name, args.date, args.minors)
            print(f'{f.relative_to(base)}: abgelegt (Original unverändert)')
        elif args.cmd == 'prepare':
            for s in prepare(base / args.folder if not Path(args.folder).is_absolute() else args.folder):
                print(f'- {s}')
        elif args.cmd == 'mark':
            items = yaml.safe_load(Path(args.items).read_text(encoding='utf-8'))
            print(mark(base / args.folder if not Path(args.folder).is_absolute() else args.folder,
                       items['personen'] if isinstance(items, dict) else items))
        elif args.cmd == 'list':
            text = listing(base)
            if args.write:
                (base / DIR / 'verzeichnis.md').write_text(text, encoding='utf-8')
                print(f'{DIR}/verzeichnis.md geschrieben')
            else:
                print(text, end='')
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
