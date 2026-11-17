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
               Optionale cover.text_boxes überschreiben einzelne Textbereiche;
               image_mode: finished unterdrückt zusätzliche Vorderseitentexte.
               Farben je Fläche: cover.panel_backgrounds (front, spine, back).
  Rücken       Autor und Titel, gedreht (nur wenn breit genug und, bei KDP,
               ab 79 Seiten); cover.spine_direction: down (von oben nach unten,
               Vorgabe, international üblich) oder up (von unten nach oben)
  Rückseite    „## Klappentext“ und „## Über …“ (Autorentext) aus
               cover/rueckseite.md, optional Autorenbild (cover.author_image),
               ISBN der Druckausgabe als EAN-13-Strichcode, Preis (cover.price)

Vorderseite allein (#324, build_front): für Seite 1 des Bildschirm-PDF und das
EPUB-Cover, im Buchformat ohne Beschnitt. Quelle ist cover.front (fertige eigene
Vorderseite als PDF, JPG oder PNG; unverändert, ohne zusätzlichen Text) oder die
Covervorlage. Beschnitt einer PDF (TrimBox, sonst ringsum bzw. oben, unten und
außen bis 6,5 mm) wird weggelassen; bis 2 % abweichendes Seitenverhältnis wird
füllend skaliert, mehr bricht ab, statt zu verzerren.

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
    from cover_design import validate
    errors = validate(cv, w, h)
    if errors:
        raise SystemExit('Covergestaltung ungültig: ' + '; '.join(errors))
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
         '\\newsavebox{\\gwtextbox}',
         '\\pagestyle{empty}\\setlength{\\parindent}{0pt}\\setlength{\\parskip}{0.55em}',
         '\\begin{document}\\noindent',
         '\\begin{tikzpicture}[remember picture,overlay,shift={(current page.south west)}]',
         f'\\fill[gwbg] ({s:.2f}mm,{s:.2f}mm) rectangle ({W - s:.2f}mm,{H - s:.2f}mm);']
    # Die übernommene Farbe nur auf ausdrücklich gewählte Flächen anwenden.
    panels = {'back': (s, spine_x), 'spine': (spine_x, front_x), 'front': (front_x, W - s)}
    for panel, (left, right) in panels.items():
        value = (cv.get('panel_backgrounds') or {}).get(panel)
        if value is None:
            value = cv.get('background') if panel in cv.get('background_targets', list(panels)) else '#1F2A44'
        L += [f'\\definecolor{{gw{panel}bg}}{{HTML}}{{{color(value, "#1F2A44")}}}',
              f'\\fill[gw{panel}bg] ({left:.2f}mm,{s:.2f}mm) rectangle ({right:.2f}mm,{H - s:.2f}mm);']
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
    defaults = {
        'title': {'x': SAFE, 'y': h * .34, 'width': tw, 'height': 40, 'font_size': big, 'bold': True},
        'subtitle': {'x': SAFE, 'y': h * .34 + big * .5 + 8, 'width': tw, 'height': 25, 'font_size': 13},
        'author': {'x': SAFE, 'y': SAFE + 4, 'width': tw, 'height': 20, 'font_size': 15}}
    boxes = cv.get('text_boxes') or {}
    def custom(part, text):
        box = dict(defaults[part], **boxes[part])
        if not text or not box.get('visible', True):
            return ''
        if box.get('break_after'):
            # Dynamische Projektdaten behalten; nur Umbruchpositionen speichern.
            raw = p.get(part) or (p.get('working_title') if part == 'title' else '') or ''
            words = raw.split()
            if any(i >= len(words) for i in box['break_after']):
                raise SystemExit(f'Covertext {part}: Umbruchposition passt nicht mehr zum aktuellen Text.')
            text = ' '.join(esc(word) + ('\\\\' if i in box['break_after'] else '')
                            for i, word in enumerate(words, 1))
        size = box['font_size']
        font = '\\sffamily' if box.get('font', 'sans' if tpl == 'modern' else 'serif') == 'sans' else '\\rmfamily'
        align = {'left': '\\raggedright', 'center': '\\centering', 'right': '\\raggedleft'}[box.get('align', 'center')]
        weight = '\\bfseries' if box.get('bold', False) else ''
        fg = color(box.get('color'), cv.get('text_color') or '#FFFFFF')
        return (f'\\definecolor{{gwpart}}{{HTML}}{{{fg}}}\n'
                f'\\node[anchor=north west,inner sep=0,text=gwpart] at '
                f'({front_x + box["x"]:.2f}mm,{y0 + h - box["y"]:.2f}mm) {{'
                f'\\sbox{{\\gwtextbox}}{{\\begin{{minipage}}{{{box["width"]:.2f}mm}}'
                f'\\hyphenpenalty=10000{font}{weight}\\fontsize{{{size}}}{{{size * 1.2:.2f}}}\\selectfont '
                f'{align} {text}\\par\\end{{minipage}}}}\n'
                f'\\ifdim\\dimexpr\\ht\\gwtextbox+\\dp\\gwtextbox\\relax>{box["height"]:.2f}mm '
                f'\\errmessage{{Cover text overflow: {part}; increase area or reduce font size}}\\fi\n'
                f'\\usebox{{\\gwtextbox}}}};')
    # Bestehende Vorlagen unverändert verwenden; nur angegebene Teile ersetzen.
    original = {'title': title, 'subtitle': subtitle, 'author': author}
    finished = cv.get('image_mode') == 'finished'
    title, subtitle, author = [original[k] if k not in boxes and not finished else ''
                               for k in ('title', 'subtitle', 'author')]
    if tpl == 'modern':
        if title:
            L.append(node(fx, y0 + h * 0.42, 'south west', big + 4, f'\\bfseries {title}', align='left'))
        if subtitle:
            L.append(node(fx, y0 + h * 0.42 - 3, 'north west', 13, subtitle, align='left'))
        if author:
            L.append(node(fx, y0 + h - SAFE, 'north west', 14, author, align='left'))
    elif tpl == 'plain':
        if title:
            L.append(node(mid, y0 + h * 0.55, 'south', big, title))
        if subtitle:
            L.append(node(mid, y0 + h * 0.55 - 4, 'north', 13, subtitle, font='\\itshape'))
        if author:
            L.append(node(mid, y0 + h * 0.30, 'north', 14, author))
    else:   # classic
        if author:
            L.append(node(mid, y0 + h - SAFE - 4, 'north', 15, author))
        if title:
            L.append(node(mid, y0 + h * 0.66, 'north', big, f'\\bfseries {title}'))
        if subtitle:
            L.append(node(mid, y0 + h * 0.66 - big * 0.5 - 8, 'north', 13, subtitle, font='\\itshape'))
    if not finished:
        for part in boxes:
            L.append(custom(part, original[part]))
    title, subtitle, author = [original[k] for k in ('title', 'subtitle', 'author')]
    # Rücken: gedreht, von oben nach unten lesbar
    if dim['spine_text']:
        size = max(6, min(11, (sp - 2 * dim['spine_margin']) * 2.2))
        text = f'{author}\\quad{{\\bfseries {title}}}' if author else f'\\bfseries {title}'
        ser = config.get('_series') or {}
        if ser.get('volume'):   # Serie (#116): Bandnummer ans Ende des Rückens
            text += f'\\quad{{\\small {ser["volume"]}}}'
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


# ---------- Vorderseite im Bildschirm-PDF und als EPUB-Cover (#324) ----------

FRONT_TOLERANCE = 0.02   # Seitenverhältnis: bis 2 % Abweichung füllend zuschneiden, darüber nicht verzerren, sondern melden
MAX_BLEED = 6.5          # mm je Kante, die eine fertige PDF-Vorderseite als Beschnitt haben darf
BP = 72 / 25.4           # PostScript-Punkte je mm


def mm(value):
    return f'{value:.1f}'.replace('.', ',')


def front_source(base, config):
    """Quelle der Vorderseite: (art, Pfad, Hinweise). art = 'file' (fertige eigene Vorderseite, cover.front),
    'template' (Covervorlage aus `cover`) oder None (nichts hinterlegt)."""
    cv = config.get('cover') or {}
    template = any(k != 'front' for k in cv)
    notes = []
    if cv.get('front'):
        path = base / cv['front']
        if path.is_file():
            return 'file', path, notes
        notes.append(f'Eigene Vorderseite {cv["front"]} fehlt' + ('; verwendet die Covervorlage' if template else ''))
    return ('template' if template else None), None, notes


def pdf_size(path):
    """Größe der ersten Seite einer PDF in mm: TrimBox (Endformat), ohne sie MediaBox (pdfinfo zeigt dann dieselbe)."""
    out = subprocess.run(['pdfinfo', '-box', str(path)], capture_output=True, text=True).stdout
    m = re.search(r'TrimBox:\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', out)
    if not m:
        raise SystemExit(f'{path.name}: Seitengröße nicht lesbar (beschädigte PDF?)')
    x0, y0, x1, y1 = (float(v) for v in m.groups())
    return (x1 - x0) / BP, (y1 - y0) / BP


def front_fit(sw, sh, w, h, physical=True, name='Vorderseite'):
    """Sichtbarer Ausschnitt der Vorderseite (sw × sh) auf der Buchseite (w × h mm): (links, unten, rechts, oben)
    in Einheiten der Quelle, und ein Hinweis. physical: Quelle in mm (PDF), dann wird Beschnitt erkannt
    (ringsum oder oben, unten und außen); sonst Pixel (Bild), dann zählt nur das Seitenverhältnis.
    Weicht das Seitenverhältnis um mehr als FRONT_TOLERANCE ab, bricht es ab, statt zu verzerren."""
    if physical:
        dw, dh = sw - w, sh - h
        if abs(dw) <= 0.5 and abs(dh) <= 0.5:
            return (0, 0, 0, 0), ''
        if 0 < dh <= 2 * MAX_BLEED:
            b = dh / 2
            if abs(dw - dh) <= 0.5:
                return (b, b, b, b), f'{name}: Beschnitt {mm(b)} mm ringsum weggelassen'
            if abs(dw - b) <= 0.5:   # Vorderseite eines Umschlags: am Rücken kein Beschnitt
                return (0, b, b, b), f'{name}: Beschnitt {mm(b)} mm oben, unten und außen weggelassen'
    ratio = (sw / sh) / (w / h)
    shown = f'{mm(sw)} × {mm(sh)} mm' if physical else f'{sw} × {sh} Pixel'
    if abs(ratio - 1) > FRONT_TOLERANCE:
        raise SystemExit(f'{name} ({shown}) passt nicht zum Buchformat {w} × {h} mm: Das Seitenverhältnis weicht um '
                         f'{abs(ratio - 1) * 100:.0f} % ab. Vorderseite im Buchformat anlegen (gern mit Beschnitt) oder '
                         'das Seitenformat (typesetting.page_size) prüfen.')
    if ratio > 1:   # etwas zu breit: links und rechts gleich viel weglassen
        cut = (sw - sh * w / h) / 2
        trim = (cut, 0, cut, 0)
    else:
        cut = (sh - sw * h / w) / 2
        trim = (0, cut, 0, cut)
    note = f'{name} ({shown}) auf {w} × {h} mm skaliert' + (', Überstand mittig weggelassen' if cut > 0.005 * max(sw, sh) else '')
    return trim, (note if physical or cut > 0.005 * max(sw, sh) else '')


def front_tex(src, size, window, w, h, pdf=True, blank=True):
    """LaTeX-Dokument: Ausschnitt `window` (links, unten, rechts, oben) der Quelle `src` (Größe `size`) füllt eine
    Seite w × h mm; danach auf Wunsch eine Leerseite (damit die Titelseite rechts bleibt)."""
    sw, sh = size
    left, bottom, right, _ = window
    k = w / (sw - left - right)   # mm je Einheit der Quelle
    opts = f'width={sw * k:.3f}mm,height={sh * k:.3f}mm' + (',pagebox=trimbox' if pdf else '')
    return ('\\documentclass{article}\n'
            f'\\usepackage[paperwidth={w}mm,paperheight={h}mm,margin=0pt]{{geometry}}\n'
            '\\usepackage{graphicx}\\usepackage{tikz}\\pagestyle{empty}\n'
            '\\begin{document}\\noindent\n'
            '\\begin{tikzpicture}[remember picture,overlay,shift={(current page.south west)}]\n'
            f'\\clip (0,0) rectangle ({w}mm,{h}mm);\n'
            f'\\node[anchor=south west,inner sep=0,outer sep=0] at ({-left * k:.3f}mm,{-bottom * k:.3f}mm) '
            f'{{\\includegraphics[{opts}]{{{src}}}}};\n'
            '\\end{tikzpicture}\n' + ('\\clearpage\\null\n' if blank else '') + '\\end{document}\n')


def build_front(base, config, pages, out, blank=True):
    """Vorderseite allein im Buchformat, ohne Beschnitt, als PDF; danach auf Wunsch eine Leerseite.
    Quelle: die fertige eigene Vorderseite (cover.front, PDF oder Bild; darüber kommt kein Text) oder die
    Covervorlage (`cover`, wie auf dem Umschlag). Gibt die Hinweise zurück, None ohne Quelle.
    Bricht bei unpassendem Seitenformat ab (SystemExit), statt zu verzerren."""
    kind, path, notes = front_source(base, config)
    if not kind:
        if notes:   # cover.front angegeben, Datei fehlt, keine Covervorlage
            raise SystemExit(notes[0])
        return None
    ts = dict(TYPESETTING_DEFAULT)
    ts.update(config.get('typesetting') or {})
    w, h = PAGE.get(ts['page_size'], PAGE['a5'])
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if kind == 'template':
            dim = build(base, front_only(config), pages, tmp / 'umschlag.pdf')
            size = (dim['total_w'] + 2 * dim['slug'], dim['total_h'] + 2 * dim['slug'])
            x, y = dim['slug'] + dim['bleed'] + dim['w'] + dim['spine'], dim['slug'] + dim['bleed']
            src, window, pdf = 'umschlag.pdf', (x, y, size[0] - x - w, size[1] - y - h), True
        else:
            rel = path.relative_to(base).as_posix()
            pdf = path.suffix.lower() == '.pdf'
            src = 'vorderseite-quelle' + path.suffix.lower()   # Kopie: Leer- und Sonderzeichen im Pfad stören LaTeX nicht
            (tmp / src).write_bytes(path.read_bytes())
            size = pdf_size(path) if pdf else image_size(path)
            if not size:
                raise SystemExit(f'{rel}: Bildgröße nicht lesbar (nur PNG oder JPEG)')
            window, note = front_fit(*size, w, h, physical=pdf, name=f'Vorderseite {rel}')
            notes += [note] if note else []
            if not pdf:
                dpi = (size[0] - window[0] - window[2]) / (w / 25.4)
                if dpi < 150:
                    notes.append(f'Vorderseite {rel}: nur {dpi:.0f} dpi im Buchformat, wirkt unscharf (besser 300 dpi)')
        (tmp / 'vorne.tex').write_text(front_tex(src, size, window, w, h, pdf, blank), encoding='utf-8')
        for _ in range(2):   # zwei Läufe: TikZ braucht die Seitenposition (remember picture)
            r = subprocess.run(['xelatex', '-interaction=nonstopmode', '-halt-on-error', 'vorne.tex'], cwd=tmp,
                               capture_output=True, text=True)
            if r.returncode:
                raise SystemExit('Vorderseite konnte nicht gesetzt werden:\n' + r.stdout[-3000:])
        Path(out).write_bytes((tmp / 'vorne.pdf').read_bytes())
    return notes


def front_jpeg(pdf, jpg, dpi=150):
    """Erste Seite einer PDF als JPEG (EPUB-Cover; braucht pdftoppm). Gibt den Pfad der Bilddatei zurück."""
    stem = str(Path(jpg).with_suffix(''))
    subprocess.run(['pdftoppm', '-jpeg', '-r', str(dpi), '-singlefile', '-f', '1', '-l', '1', str(pdf), stem], check=True)
    return Path(stem + '.jpg')


def build(base, config, pages, out, front_jpg=None, guides=False):
    sources = {(base / value).resolve() for key, value in (config.get('cover') or {}).items()
               if key in ('image', 'author_image') and value}
    outputs = [Path(out).resolve()]
    if front_jpg:
        outputs.append(Path(front_jpg).with_suffix('.jpg').resolve())
    if any(path in sources for path in outputs):
        raise SystemExit('Coverausgabe darf kein Originalbild überschreiben. Anderen Ausgabepfad wählen.')
    dim = dimensions(config, pages)
    tex = cover_tex(base, config, dim, guides)
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'umschlag.tex').write_text(tex, encoding='utf-8')
        for _ in range(2):   # zwei Läufe: TikZ braucht die Seitenposition (remember picture)
            r = subprocess.run(['xelatex', '-interaction=nonstopmode', '-halt-on-error', 'umschlag.tex'], cwd=tmp,
                               capture_output=True, text=True)
            if r.returncode:
                raise SystemExit('Umschlag konnte nicht gesetzt werden:\n' + r.stdout[-3000:])
            log = (Path(tmp) / 'umschlag.log').read_text(errors='replace')
            if (config.get('cover') or {}).get('text_boxes') and re.search(r'Overfull \\[hv]box', log):
                raise SystemExit('Covertext passt nicht in den Textbereich. Breite/Höhe vergrößern oder Schrift verkleinern.')
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
    ap.add_argument('--preview', action='store_true', help='Vorderseitenvorschau mit Endformat, ohne Schnittmarken; --out und --front-jpg angeben')
    ap.add_argument('--info', action='store_true')
    a = ap.parse_args(argv[1:])
    base, config = load(a.project)
    if a.preview:
        if not a.out or not a.front_jpg:
            ap.error('--preview benötigt --out und --front-jpg')
        config = front_only(config)
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
