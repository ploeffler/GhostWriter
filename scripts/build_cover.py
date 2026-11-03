#!/usr/bin/env python3
"""Umschlag für den Druck und EPUB-Cover (#68, Teil 2).

Aufruf:
  python scripts/build_cover.py <projektordner> --pages N --out umschlag.pdf [--front-jpg vorne.jpg] [--guides]
  python scripts/build_cover.py <projektordner> --pages N --info      nur Maße ausgeben

Der Umschlag ist ein PDF über Rückseite, Buchrücken und Vorderseite mit
Beschnittzugabe ringsum:

  Breite = Beschnitt + Seitenbreite + Rücken + Seitenbreite + Beschnitt
  Höhe   = Beschnitt + Seitenhöhe + Beschnitt

Rückenbreite = Seitenzahl × Papierstärke je Seite (Profil) oder `print.spine_mm`.
Profile (ghostwriter.yml → print.profile):
  kdp     Amazon KDP Taschenbuch: Beschnitt 3,2 mm; je Seite 0,0572 mm (weiß,
          Standardfarbe), 0,0635 mm (creme), 0,0596 mm (Premiumfarbe);
          Rückentext erst ab 79 Seiten, 1,6 mm Abstand zur Kante
  bod     Books on Demand Taschenbuch: Beschnitt 5 mm; die Rückenbreite nennt
          nur der BoD-Rechner, daher `print.spine_mm` Pflicht; Strichcode-Fläche
          etwa 4 × 3 cm unten auf der Rückseite
  custom  eigene Werte: `bleed_mm` (Vorgabe 3) und `spine_mm` oder
          `paper_mm_per_page`
Vorgaben der Anbieter ändern sich; vor dem Hochladen mit deren Rechner abgleichen.

Inhalt (ghostwriter.yml → cover, Texte in cover/rueckseite.md):
  Vorderseite  Titel, Untertitel, Autor; Hintergrundfarbe, Textfarbe, optional
               Bild (cover.image, füllt die Vorderseite samt Beschnitt);
               Vorlage classic (Titel oben, Serifen), modern (Titel unten links,
               serifenlos), plain (alles mittig)
  Rücken       Autor und Titel, gedreht (nur wenn breit genug und, bei KDP,
               ab 79 Seiten); cover.spine_direction: down (von oben nach unten,
               Vorgabe, international üblich) oder up (von unten nach oben)
  Rückseite    „## Klappentext“ und „## Über …“ (Autorentext) aus
               cover/rueckseite.md, optional Autorenbild (cover.author_image),
               ISBN der Druckausgabe als EAN-13-Strichcode, Preis (cover.price)

--guides zeichnet Schnitt-, Falz- und Sicherheitslinien ein (Probedruck);
print.crop_marks legt einen Rand mit Schnittmarken um den Umschlag.
--front-jpg schreibt die Vorderseite (ohne Beschnitt) als Bild fürs EPUB-Cover
(braucht pdftoppm).

Benötigt: xelatex mit TikZ, TeX Gyre; für --front-jpg pdftoppm (poppler-utils).
"""
import argparse
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from render_view import TYPESETTING_DEFAULT, load  # noqa: E402

PAGE = {'a5': (148, 210), '12x19': (120, 190), '13.5x21.5': (135, 215), 'a4': (210, 297)}
PROFILES = {
    'kdp': {'name': 'Amazon KDP', 'bleed': 3.2, 'paper': {'white': 0.0572, 'cream': 0.0635, 'premium_color': 0.0596},
            'spine_text_min_pages': 79, 'spine_margin': 1.6},
    'bod': {'name': 'Books on Demand', 'bleed': 5.0, 'paper': {}, 'spine_text_min_pages': 0, 'spine_margin': 2.0},
    'custom': {'name': 'eigene Werte', 'bleed': 3.0, 'paper': {}, 'spine_text_min_pages': 0, 'spine_margin': 2.0},
}
SLUG = 8.0          # Rand für Schnittmarken (mm)
SAFE = 10.0         # Sicherheitsabstand zum Schnitt für Text (mm)
MIN_SPINE_TEXT = 6  # Rückentext erst ab dieser Rückenbreite (mm)
FONTS = {'serif': 'TeX Gyre Pagella', 'sans': 'TeX Gyre Heros'}


# ---------- Maße ----------

def dimensions(config, pages):
    """Maße in mm und Hinweise: dict mit w, h, bleed, spine, slug, total_w, total_h, spine_text, notes."""
    ts = dict(TYPESETTING_DEFAULT)
    ts.update(config.get('typesetting') or {})
    pr = config.get('print') or {}
    prof = PROFILES.get(pr.get('profile') or '', None)
    if not prof:
        raise SystemExit('Kein Druckprofil: print.profile (kdp, bod oder custom) in den Ausgabeoptionen festlegen.')
    w, h = PAGE.get(ts['page_size'], PAGE['a5'])
    bleed = float(pr.get('bleed_mm', prof['bleed']))
    notes = []
    if pr.get('spine_mm') is not None:
        spine = float(pr['spine_mm'])
    elif pr.get('paper_mm_per_page') is not None:
        spine = pages * float(pr['paper_mm_per_page'])
    elif prof['paper']:
        paper = pr.get('paper', 'white')
        if paper not in prof['paper']:
            raise SystemExit(f'Papier {paper} gibt es im Profil {prof["name"]} nicht: {", ".join(prof["paper"])}')
        spine = pages * prof['paper'][paper]
    else:
        raise SystemExit(f'Für {prof["name"]} die Rückenbreite angeben: print.spine_mm (aus dem Rechner des Anbieters) '
                         'oder print.paper_mm_per_page.')
    spine_text = spine >= MIN_SPINE_TEXT and pages >= prof['spine_text_min_pages']
    if not spine_text:
        notes.append(f'Kein Rückentext: Rücken {spine:.1f} mm' + (f', {pages} Seiten (Rückentext bei {prof["name"]} erst ab '
                     f'{prof["spine_text_min_pages"]} Seiten)' if pages < prof['spine_text_min_pages'] else ''))
    slug = SLUG if pr.get('crop_marks') else 0.0
    return {'w': w, 'h': h, 'bleed': bleed, 'spine': spine, 'slug': slug, 'pages': pages, 'profile': prof,
            'total_w': 2 * bleed + 2 * w + spine, 'total_h': 2 * bleed + h, 'spine_text': spine_text,
            'spine_margin': prof['spine_margin'], 'notes': notes}


# ---------- EAN-13 ----------

L_CODES = ['0001101', '0011001', '0010011', '0111101', '0100011', '0110001', '0101111', '0111011', '0110111', '0001011']
G_CODES = [c[::-1].translate(str.maketrans('01', '10')) for c in L_CODES]
R_CODES = [c.translate(str.maketrans('01', '10')) for c in L_CODES]
PARITY = ['LLLLLL', 'LLGLGG', 'LLGGLG', 'LLGGGL', 'LGLLGG', 'LGGLLG', 'LGGGLL', 'LGLGLG', 'LGLGGL', 'LGGLGL']


def isbn13(value):
    """ISBN-13 aus einer ISBN-10 oder -13 (Ziffern); None, wenn ungültig."""
    d = re.sub(r'[^0-9Xx]', '', value or '').upper()
    if len(d) == 10:
        d = '978' + d[:9]
        d += str((10 - sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d)) % 10) % 10)
    if len(d) != 13 or not d.isdigit() or sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d)) % 10:
        return None
    return d


def ean13_modules(digits):
    """95 Module ('1' = Strich) und die Positionen der verlängerten Randzeichen."""
    first, left, right = int(digits[0]), digits[1:7], digits[7:]
    bits = '101'
    for p, c in zip(PARITY[first], left):
        bits += (L_CODES if p == 'L' else G_CODES)[int(c)]
    bits += '01010'
    for c in right:
        bits += R_CODES[int(c)]
    bits += '101'
    guards = set(range(0, 3)) | set(range(45, 50)) | set(range(92, 95))
    return bits, guards


def barcode_tikz(isbn, x, y, module=0.33, height=20.0):
    """TikZ-Befehle für einen EAN-13 mit Klarschrift, linke untere Ecke (x, y) in mm."""
    d = isbn13(isbn)
    if not d:
        return ''
    bits, guards = ean13_modules(d)
    quiet = 11 * module
    out = [f'\\fill[white] ({x:.2f}mm,{y:.2f}mm) rectangle ({x + 95 * module + 2 * quiet:.2f}mm,{y + height + 4.5:.2f}mm);']
    bx = x + quiet
    for i, b in enumerate(bits):
        if b == '1':   # Randzeichen reichen 1,6 mm tiefer, zwischen die Ziffern
            bottom = y + 4.2 - (1.6 if i in guards else 0)
            out.append(f'\\fill[black] ({bx + i * module:.3f}mm,{bottom:.2f}mm) rectangle '
                       f'({bx + (i + 1) * module:.3f}mm,{y + height:.2f}mm);')
    # Klarschrift wie eingegeben (die Bindestriche hängen von der Ländergruppe ab und lassen sich nicht berechnen)
    shown = isbn.strip() if re.sub(r'[^0-9]', '', isbn) == d else d
    fmt = f'ISBN {shown}'
    out.append(f'\\node[anchor=south,font=\\sffamily\\fontsize{{7}}{{8}}\\selectfont,text=black] at '
               f'({bx + 47.5 * module:.2f}mm,{y + height + 0.3:.2f}mm) {{{fmt}}};')
    digits_font = '\\sffamily\\fontsize{8}{9}\\selectfont'
    out.append(f'\\node[anchor=base east,font={digits_font},text=black] at ({bx - 0.5:.2f}mm,{y + 1.0:.2f}mm) {{{d[0]}}};')
    out.append(f'\\node[anchor=base,font={digits_font},text=black] at ({bx + 24 * module:.2f}mm,{y + 1.0:.2f}mm) {{{d[1:7]}}};')
    out.append(f'\\node[anchor=base,font={digits_font},text=black] at ({bx + 71 * module:.2f}mm,{y + 1.0:.2f}mm) {{{d[7:]}}};')
    return '\n'.join(out)


# ---------- Bilder ----------

def image_size(path):
    """(Breite, Höhe) in Pixeln für PNG und JPEG, sonst None."""
    data = Path(path).read_bytes()
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', data[16:24])
    if data[:2] == b'\xff\xd8':
        i = 2
        while i < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack('>HH', data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
    return None


# ---------- Texte ----------

def back_texts(base):
    """(Klappentext, Autorentext) aus cover/rueckseite.md als Markdown."""
    path = base / 'cover' / 'rueckseite.md'
    if not path.is_file():
        return '', ''
    text = path.read_text(encoding='utf-8')
    def part(pattern):
        m = re.search(rf'(?ms)^## {pattern}[^\n]*\n(.*?)(?=^## |\Z)', text)
        return m.group(1).strip() if m else ''
    blurb, bio = part('Klappentext'), part('Über')
    # Platzhalter der Vorlage (templates/cover-rueckseite.md) nicht setzen
    return ('' if blurb.startswith('<') else blurb), ('' if bio.startswith('<') else bio)


def latex_text(md):
    """Markdown-Absätze nach LaTeX (über pandoc, damit *kursiv* usw. stimmen)."""
    if not md:
        return ''
    r = subprocess.run(['pandoc', '--from', 'markdown+smart', '--to', 'latex'], input=md, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else md


def esc(s):
    return (s or '').replace('\\', '\\textbackslash{}').replace('&', '\\&').replace('%', '\\%').replace('#', '\\#') \
        .replace('_', '\\_').replace('$', '\\$').replace('{', '\\{').replace('}', '\\}')


def color(value, default):
    v = (value or default).lstrip('#')
    return v.upper() if re.fullmatch(r'[0-9A-Fa-f]{6}', v) else default.lstrip('#')


# ---------- Satz ----------

def cover_tex(base, config, dim, guides=False):
    p = config['project']
    cv = config.get('cover') or {}
    tpl = cv.get('template', 'classic')
    title = esc(p.get('title') or p.get('working_title') or 'Ohne Titel')
    subtitle = esc(p.get('subtitle') or '')
    author = esc(p.get('author') or '')
    bg, fg = color(cv.get('background'), '#1F2A44'), color(cv.get('text_color'), '#FFFFFF')
    s, b, w, h, sp = dim['slug'], dim['bleed'], dim['w'], dim['h'], dim['spine']
    W, H = dim['total_w'] + 2 * s, dim['total_h'] + 2 * s
    back_x, spine_x, front_x = s + b, s + b + w, s + b + w + sp
    y0 = s + b
    head_font = FONTS['sans'] if tpl == 'modern' else FONTS['serif']
    L = ['\\documentclass{article}',
         f'\\usepackage[paperwidth={W:.2f}mm,paperheight={H:.2f}mm,margin=0pt]{{geometry}}',
         '\\usepackage{fontspec}\\usepackage{xcolor}\\usepackage{tikz}\\usepackage{graphicx}',
         f'\\setmainfont{{{FONTS["serif"]}}}\\setsansfont{{{FONTS["sans"]}}}',
         f'\\newfontfamily\\headfont{{{head_font}}}',
         f'\\definecolor{{gwbg}}{{HTML}}{{{bg}}}\\definecolor{{gwfg}}{{HTML}}{{{fg}}}',
         '\\pagestyle{empty}\\setlength{\\parindent}{0pt}\\setlength{\\parskip}{0.55em}',
         '\\begin{document}\\noindent',
         '\\begin{tikzpicture}[remember picture,overlay,shift={(current page.south west)}]',
         f'\\fill[gwbg] ({s:.2f}mm,{s:.2f}mm) rectangle ({W - s:.2f}mm,{H - s:.2f}mm);']
    # Vorderseite: Bild füllt Vorderseite samt Beschnitt (rechts, oben, unten), zugeschnitten
    img = cv.get('image')
    if img and (base / img).is_file():
        size = image_size(base / img)
        fw, fh = w + b, h + 2 * b
        if size:
            scale = max(fw / size[0], fh / size[1])
            iw, ih = size[0] * scale, size[1] * scale
        else:
            iw, ih = fw, fh
        cx, cy = front_x + fw / 2, s + fh / 2
        L += ['\\begin{scope}', f'\\clip ({front_x:.2f}mm,{s:.2f}mm) rectangle ({front_x + fw:.2f}mm,{s + fh:.2f}mm);',
              f'\\node[inner sep=0] at ({cx:.2f}mm,{cy:.2f}mm) {{\\includegraphics[width={iw:.2f}mm,height={ih:.2f}mm]'
              f'{{{(base / img).resolve().as_posix()}}}}};', '\\end{scope}']
    tw = w - 2 * SAFE
    fx = front_x + SAFE
    def node(x, y, anchor, size, text, font='\\headfont', align='center', width=tw):
        return (f'\\node[anchor={anchor},text=gwfg,text width={width:.2f}mm,align={align},inner sep=0] at '
                f'({x:.2f}mm,{y:.2f}mm) {{\\hyphenpenalty=10000{font}\\fontsize{{{size}}}{{{size * 1.2:.1f}}}\\selectfont {text}\\par}};')
    mid = front_x + w / 2
    big = 28 if w >= 140 else 24
    if tpl == 'modern':
        L.append(node(fx, y0 + h * 0.42, 'south west', big + 4, f'\\bfseries {title}', align='left'))
        if subtitle:
            L.append(node(fx, y0 + h * 0.42 - 3, 'north west', 13, subtitle, align='left'))
        if author:
            L.append(node(fx, y0 + h - SAFE, 'north west', 14, author, align='left'))
    elif tpl == 'plain':
        L.append(node(mid, y0 + h * 0.55, 'south', big, title))
        if subtitle:
            L.append(node(mid, y0 + h * 0.55 - 4, 'north', 13, subtitle, font='\\itshape'))
        if author:
            L.append(node(mid, y0 + h * 0.30, 'north', 14, author))
    else:   # classic
        if author:
            L.append(node(mid, y0 + h - SAFE - 4, 'north', 15, author))
        L.append(node(mid, y0 + h * 0.66, 'north', big, f'\\bfseries {title}'))
        if subtitle:
            L.append(node(mid, y0 + h * 0.66 - big * 0.5 - 8, 'north', 13, subtitle, font='\\itshape'))
    # Rücken: gedreht, von oben nach unten lesbar
    if dim['spine_text']:
        size = max(6, min(11, (sp - 2 * dim['spine_margin']) * 2.2))
        text = f'{author}\\quad{{\\bfseries {title}}}' if author else f'\\bfseries {title}'
        rot = 90 if cv.get('spine_direction') == 'up' else -90   # up: von unten nach oben (deutsche Tradition)
        L.append(f'\\node[rotate={rot},text=gwfg,inner sep=0] at ({spine_x + sp / 2:.2f}mm,{y0 + h / 2:.2f}mm) '
                 f'{{\\headfont\\fontsize{{{size:.1f}}}{{{size * 1.2:.1f}}}\\selectfont {text}}};')
    # Rückseite: Klappentext oben, Autorentext darunter, Strichcode und Preis unten rechts
    blurb, bio = back_texts(base)
    bx = back_x + SAFE
    if blurb:
        L.append(f'\\node[anchor=north west,text=gwfg,text width={tw:.2f}mm,align=justify,inner sep=0] at '
                 f'({bx:.2f}mm,{y0 + h - SAFE:.2f}mm) {{\\setlength{{\\parskip}}{{0.6em}}\\fontsize{{10.5}}{{14}}\\selectfont {latex_text(blurb)}\\par}};')
    aimg = cv.get('author_image')
    bio_y = y0 + 48
    if aimg and (base / aimg).is_file():
        L.append(f'\\node[anchor=south west,inner sep=0] at ({bx:.2f}mm,{bio_y:.2f}mm) '
                 f'{{\\includegraphics[width=22mm,height=28mm,keepaspectratio]{{{(base / aimg).resolve().as_posix()}}}}};')
        bio_x, bio_w = bx + 26, tw - 26
    else:
        bio_x, bio_w = bx, tw
    if bio:
        L.append(f'\\node[anchor=south west,text=gwfg,text width={bio_w:.2f}mm,align=left,inner sep=0] at '
                 f'({bio_x:.2f}mm,{bio_y:.2f}mm) {{\\fontsize{{8.5}}{{11}}\\selectfont {latex_text(bio)}\\par}};')
    isbn = (config.get('publication') or {}).get('isbn_print')
    code_w = 95 * 0.33 + 2 * 11 * 0.33
    code_x, code_y = back_x + w - SAFE - code_w, y0 + SAFE
    if isbn:
        L.append(barcode_tikz(isbn, code_x, code_y))
    if cv.get('price'):
        L.append(f'\\node[anchor=south east,text=gwfg,inner sep=0] at ({back_x + w - SAFE:.2f}mm,{code_y + 31:.2f}mm) '
                 f'{{\\sffamily\\fontsize{{9}}{{11}}\\selectfont {esc(cv["price"])}}};')
    # Hilfslinien (Probedruck): Schnitt rot, Falz blau, Sicherheitsabstand grau
    if guides:
        L += [f'\\draw[red,dashed,line width=0.3pt] ({s + b:.2f}mm,{s + b:.2f}mm) rectangle ({W - s - b:.2f}mm,{H - s - b:.2f}mm);',
              f'\\draw[blue,dashed,line width=0.3pt] ({spine_x:.2f}mm,{s:.2f}mm) -- ({spine_x:.2f}mm,{H - s:.2f}mm);',
              f'\\draw[blue,dashed,line width=0.3pt] ({front_x:.2f}mm,{s:.2f}mm) -- ({front_x:.2f}mm,{H - s:.2f}mm);',
              f'\\draw[gray,dotted,line width=0.3pt] ({back_x + SAFE:.2f}mm,{y0 + SAFE:.2f}mm) rectangle '
              f'({spine_x - SAFE:.2f}mm,{y0 + h - SAFE:.2f}mm);',
              f'\\draw[gray,dotted,line width=0.3pt] ({front_x + SAFE:.2f}mm,{y0 + SAFE:.2f}mm) rectangle '
              f'({front_x + w - SAFE:.2f}mm,{y0 + h - SAFE:.2f}mm);']
    # Schnittmarken im Rand: an den Ecken des Schnitts und an den Falzen
    if s:
        mark = 'line width=0.25pt,black'
        for x in (s + b, W - s - b):
            L += [f'\\draw[{mark}] ({x:.2f}mm,0) -- ({x:.2f}mm,{s - 1:.2f}mm);',
                  f'\\draw[{mark}] ({x:.2f}mm,{H - s + 1:.2f}mm) -- ({x:.2f}mm,{H:.2f}mm);']
        for y in (s + b, H - s - b):
            L += [f'\\draw[{mark}] (0,{y:.2f}mm) -- ({s - 1:.2f}mm,{y:.2f}mm);',
                  f'\\draw[{mark}] ({W - s + 1:.2f}mm,{y:.2f}mm) -- ({W:.2f}mm,{y:.2f}mm);']
        for x in (spine_x, front_x):
            L += [f'\\draw[{mark},dashed] ({x:.2f}mm,0) -- ({x:.2f}mm,{s - 1:.2f}mm);',
                  f'\\draw[{mark},dashed] ({x:.2f}mm,{H - s + 1:.2f}mm) -- ({x:.2f}mm,{H:.2f}mm);']
    L += ['\\end{tikzpicture}', '\\end{document}']
    return '\n'.join(L) + '\n'


def front_only(config):
    """Konfiguration für die Vorderseite allein (EPUB-Cover): ohne Druckprofil ein Rücken von 0 mm."""
    cfg = dict(config)
    if not (config.get('print') or {}).get('profile'):
        cfg['print'] = {'profile': 'custom', 'spine_mm': 0}
    else:
        cfg['print'] = dict(config['print'], crop_marks=False)
    return cfg


def build(base, config, pages, out, front_jpg=None, guides=False):
    dim = dimensions(config, pages)
    tex = cover_tex(base, config, dim, guides)
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'umschlag.tex').write_text(tex, encoding='utf-8')
        for _ in range(2):   # zwei Läufe: TikZ braucht die Seitenposition (remember picture)
            r = subprocess.run(['xelatex', '-interaction=nonstopmode', '-halt-on-error', 'umschlag.tex'], cwd=tmp,
                               capture_output=True, text=True)
            if r.returncode:
                raise SystemExit('Umschlag konnte nicht gesetzt werden:\n' + r.stdout[-3000:])
        Path(out).write_bytes((Path(tmp) / 'umschlag.pdf').read_bytes())
    if front_jpg:
        dpi = 150
        px = lambda mm: int(round(mm / 25.4 * dpi))
        x = dim['slug'] + dim['bleed'] + dim['w'] + dim['spine']
        y = dim['slug'] + dim['bleed']
        stem = str(Path(front_jpg).with_suffix(''))
        subprocess.run(['pdftoppm', '-jpeg', '-r', str(dpi), '-singlefile', '-x', str(px(x)), '-y', str(px(y)),
                        '-W', str(px(dim['w'])), '-H', str(px(dim['h'])), str(out), stem], check=True)
    return dim


def summary(dim):
    return (f'Umschlag {dim["total_w"]:.1f} × {dim["total_h"]:.1f} mm ({dim["profile"]["name"]}): Seite {dim["w"]} × {dim["h"]} mm, '
            f'Rücken {dim["spine"]:.1f} mm bei {dim["pages"]} Seiten, Beschnitt {dim["bleed"]:g} mm'
            + (', mit Schnittmarken' if dim['slug'] else ''))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('--pages', type=int, required=True, help='Seitenzahl des Innenteils (PDF)')
    ap.add_argument('--out')
    ap.add_argument('--front-jpg')
    ap.add_argument('--guides', action='store_true')
    ap.add_argument('--info', action='store_true')
    a = ap.parse_args(argv[1:])
    base, config = load(a.project)
    if a.info or not a.out:
        dim = dimensions(config, a.pages)
    else:
        dim = build(base, config, a.pages, a.out, a.front_jpg, a.guides)
    print(summary(dim))
    for n in dim['notes']:
        print(f'ⓘ {n}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
