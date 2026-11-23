#!/usr/bin/env python3
"""Setzt eine Auflage als PDF, DOCX und EPUB (#15).

Aufruf:
  python scripts/build_edition.py <projektordner> --edition N [--out ordner] [--date JJJJ-MM-TT]
                                   [--formats pdf,docx,epub] [--allow-markers]
  python scripts/build_edition.py <projektordner> --proof [--out ordner] [--formats pdf]
  python scripts/build_edition.py <projektordner> --preview N [--out ordner] [--formats pdf,epub]
  python scripts/build_edition.py <projektordner> --manuscript [--chapter N] [--out ordner]

Formate (--formats, sonst typesetting.formats): pdf (Bildschirm), pdf_print
(Druck-PDF des Innenteils, <tag>-druck.pdf, mit print.crop_marks Schnittmarken),
cover (Umschlag, <tag>-umschlag.pdf, scripts/build_cover.py; Rückenbreite aus
der Seitenzahl des Innenteils), booklet (Broschüre zum Selbstdrucken,
<tag>-broschuere.pdf: der Innenteil wie im Druck-PDF, ohne Schnittmarken, je zwei
Buchseiten nebeneinander auf einem Blatt quer – A4 bei A5 und kleineren Formaten,
A3 bei A4 – in Falzreihenfolge, mit Leerseiten auf eine durch 4 teilbare Seitenzahl
aufgefüllt; beidseitig über die kurze Kante drucken, Blätter aufeinanderlegen,
in der Mitte falten), docx, epub (mit Cover aus der Vorderseite, wenn es `cover` gibt).

Vorderseite im Bildschirm-PDF (#324, typesetting.pdf_cover): `proof` (Vorgabe) setzt sie
im Probedruck als Seite 1 vor das PDF, `always` auch in Auflagen, `never` nie; danach
folgt eine Leerseite, damit die Titelseite rechts bleibt. Quelle ist eine fertige eigene
Vorderseite (cover.front, PDF oder Bild, unverändert, ohne zusätzlichen Text) oder die
Covervorlage (`cover`). Beschnitt einer PDF wird weggelassen; ein abweichendes
Seitenverhältnis bricht die Auflage ab (im Probedruck nur Warnung). Der Probedruck-Vermerk
bleibt auf den Innenseiten. Druck-PDF und Broschüre enthalten keine Vorderseite; das EPUB
verwendet dieselbe Vorderseite als Cover. Zusammengefügt wird mit qpdf (behält die
Lesezeichen), ersatzweise mit pdfunite.

--proof baut einen Probedruck des aktuellen Stands: alle Kapitel und Abschnitte,
auch nicht abgeschlossene (mit Vermerk „Stand: Entwurf, nicht abgeschlossen“),
offene Marker farbig hervorgehoben, in der Fußzeile bzw. vorn der Hinweis
„Probedruck – nicht zur Veröffentlichung“. Kein Tag, kein Release; die Action
„Probedruck“ stellt die Dateien als Download bereit.

--preview N („Vorabfassung“, #348) baut wie --proof, aber mit dem Vermerk „Vorabfassung N“
und Dateinamen nach dem Tag <kurztitel>-vorab-N; die Action „Vorabfassung“ legt damit
Tag und Pre-Release an. Keine Auflage, current_edition bleibt.

--manuscript („Manuskript ausgeben“, #260) baut nur ein PDF des Arbeitsstands: wie
der Probedruck, aber Abschnitte ohne Manuskript erscheinen als Kasten „Geplant“ mit
Ziel und Kurzbeschreibung in Stichworten, erledigten Läufen und offenen Fragen
(scripts/assemble.py, ohne KI); vorn eine Übersicht „Arbeitsstand“, in der Fußzeile
„Manuskript … – nicht zur Veröffentlichung“. --chapter N nur Kapitel N (ohne Vor-
und Nachspann). Datei <kurztitel>-manuskript-<datum>.pdf; die Action „Manuskript
ausgeben“ stellt sie bereit, der Chat übergibt sie als Datei.

Vor- und Nachspann (#57): freigegebene Teile aus matter/ (scripts/assemble.py).
Die Widmung steht auf einer eigenen rechten Seite nach der Titelei, zentriert,
ohne Überschrift und ohne Eintrag im Inhaltsverzeichnis (PDF: vor dem
Inhaltsverzeichnis; DOCX: eigene Seite; EPUB: eigener Abschnitt mit Rolle
dedication). Prolog vor Kapitel 1, Epilog und Danksagung nach dem letzten
Kapitel, unnummeriert und im Inhaltsverzeichnis.

Ablauf: scripts/assemble.py prüft und fügt die freigegebenen Kapitel zusammen,
danach setzt Pandoc die Dateien. Die Buchsatz-Einstellungen kommen aus
ghostwriter.yml (`typesetting`, Projekteinstellungen): Seitenformat, Schrift,
Schriftgröße, Titelseite, Impressum, Inhaltsverzeichnis und dessen Tiefe.

Vorlagen in templates/book/:
  header.tex      Zusätze für den PDF-Satz (KOMA-Script scrbook, XeLaTeX)
  merkkasten.lua  Pandoc-Filter: Zitatblöcke „**Merkkasten** …“ als Kasten
  epub.css        Stil des EPUB
Die DOCX-Vorlage (reference.docx) entsteht bei jedem Lauf aus Pandocs Vorlage
mit Seitenformat, Schrift und dem Absatzformat „Merkkasten“ (python-docx).

Offene Marker im freigegebenen Text verhindern den Bau (Exit-Code 1), es sei
denn --allow-markers (nur für Proben, nie für eine veröffentlichte Auflage).

Benötigt: pandoc (≥ 3), xelatex mit KOMA-Script, tcolorbox, TeX Gyre
(texlive-xetex, texlive-latex-extra, texlive-lang-german,
texlive-fonts-recommended, fonts-texgyre), python-docx, pyyaml; für die Vorderseite im
PDF qpdf (sonst pdfunite) und für das EPUB-Cover pdftoppm (poppler-utils).
"""
import argparse
import datetime
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / 'templates' / 'book'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from assemble import (book_body, book_parts, chapter_selection, find_chapter, manuscript_overview,  # noqa: E402
                      matter_notes, matter_parts, metadata, problems, resolve_images, selection_text)
from render_view import load, tag_slug  # noqa: E402
import ai_disclosure  # noqa: E402
import build_cover  # noqa: E402

PAGE = {  # Breite, Höhe in mm
    'a5': (148, 210), '12x19': (120, 190), '13.5x21.5': (135, 215), 'a4': (210, 297)}
# Schrift → (PDF: TeX-Gyre-Schrift, DOCX: verbreitete Entsprechung, EPUB: Familie); nur freie Schriften (#68)
FONTS = {'serif': ('TeX Gyre Pagella', 'Palatino Linotype', 'serif'), 'sans': ('TeX Gyre Heros', 'Arial', 'sans-serif'),
         'pagella': ('TeX Gyre Pagella', 'Palatino Linotype', 'serif'), 'termes': ('TeX Gyre Termes', 'Times New Roman', 'serif'),
         'bonum': ('TeX Gyre Bonum', 'Bookman Old Style', 'serif'), 'schola': ('TeX Gyre Schola', 'Century Schoolbook', 'serif'),
         'heros': ('TeX Gyre Heros', 'Arial', 'sans-serif'), 'adventor': ('TeX Gyre Adventor', 'Century Gothic', 'sans-serif')}
MONTHS = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
DIV = {'standard': 'calc', 'classic': '9', 'modern': '13'}   # KOMA-Script: kleiner = breitere Ränder
SHEETS = {'a4': (297, 210), 'a3': (420, 297)}   # Bogen der Broschüre, quer (Breite, Höhe in mm)


def booklet_sheet(page_size):
    """Bogen der Broschüre: A4 quer, wenn zwei Buchseiten nebeneinander passen, sonst A3 quer.
    Passt das Format knapp nicht (13,5 × 21,5 cm), verkleinert pdfpages die Seiten leicht."""
    return 'a3' if PAGE.get(page_size, PAGE['a5'])[0] > 160 else 'a4'


def booklet_order(pages):
    """Seitenfolge der Broschüre: je Bogen Vorderseite (links, rechts), Rückseite (links, rechts);
    0 = Leerseite. Die Seitenzahl wird auf ein Vielfaches von 4 aufgefüllt."""
    n = -(-max(pages, 1) // 4) * 4
    order = []
    for i in range(n // 4):
        lo, hi = 2 * i + 1, n - 2 * i
        order += [hi, lo, lo + 1, hi - 1]
    return [p if p <= pages else 0 for p in order]


def booklet_tex(interior, pages, page_size):
    """LaTeX-Dokument, das den Innenteil als Broschüre ausschießt (pdfpages, in texlive-latex-recommended)."""
    sw, sh = SHEETS[booklet_sheet(page_size)]
    order = ','.join(str(p) if p else '{}' for p in booklet_order(pages))
    return ('\\documentclass{article}\n'
            f'\\usepackage[paperwidth={sw}mm,paperheight={sh}mm,margin=0mm]{{geometry}}\n'
            '\\usepackage{pdfpages}\n\\begin{document}\n'
            f'\\includepdf[pages={{{order}}},nup=2x1]{{{interior}}}\n'
            '\\end{document}\n')


def latex_escape(text):
    """Klartext in selbst erzeugten LaTeX-Blöcken als Text erhalten."""
    replacements = {
        '\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '#': r'\#',
        '_': r'\_', '$': r'\$', '{': r'\{', '}': r'\}',
        '~': r'\textasciitilde{}', '^': r'\textasciicircum{}',
    }
    return ''.join(replacements.get(char, char) for char in text)


def is_sans(font):
    return FONTS.get(font, FONTS['serif'])[2] == 'sans-serif'


def layout_tex(ts, meta):
    """Zusätze für den PDF-Satz aus den Ausgabeoptionen (#68); leer bei den Vorgaben (Satz wie bisher)."""
    out = []
    hf = ts.get('heading_font', 'same')
    if hf == 'sans' or (hf == 'same' and is_sans(ts['font'])):
        out.append('\\setkomafont{disposition}{\\sffamily\\bfseries}\\setkomafont{chapter}{\\sffamily\\Large\\bfseries}')
    elif hf == 'serif' and is_sans(ts['font']):
        out.append('\\setkomafont{disposition}{\\rmfamily\\bfseries}\\setkomafont{chapter}{\\rmfamily\\Large\\bfseries}')
    if not ts.get('hyphenation', True):
        out.append('\\hyphenpenalty=10000\\exhyphenpenalty=10000\\emergencystretch=3em')
    if ts.get('initials'):
        out.append('\\usepackage{lettrine}\\setcounter{DefaultLines}{2}')
    heads, numbers = ts.get('running_heads', 'sections'), ts.get('page_numbers', 'header')
    if (heads, numbers) != ('sections', 'header'):
        title = latex_escape(meta['title'])
        cfg = ['\\usepackage[automark]{scrlayer-scrpage}', '\\clearpairofpagestyles']
        if heads == 'sections':
            cfg.append('\\automark[section]{chapter}\\ihead{\\headmark}')
        elif heads == 'chapter':
            cfg.append('\\automark[chapter]{chapter}\\ihead{\\headmark}')
        elif heads == 'book':
            cfg.append('\\automark[chapter]{chapter}\\lehead{' + title + '}\\rohead{\\leftmark}')
        cfg.append({'header': '\\ohead*{\\pagemark}', 'footer_center': '\\cfoot*{\\pagemark}',
                    'footer_outer': '\\ofoot*{\\pagemark}'}[numbers])
        cfg.append('\\pagestyle{scrheadings}')
        out += cfg
    return '\n'.join(out) + ('\n' if out else '')


TITLE_STYLES = ('classic', 'rules', 'modern', 'spaced', 'band')   # typesetting.title_style (#310)
PROOF_MARKS = ('line', 'box', 'watermark', 'watermark_all')      # typesetting.proof_mark (#310)


def title_tex(ts):
    """Dateien für die gewählte Titelseite (#310); leer bei „classic“ (KOMA-\\maketitle wie bisher) und ohne Titelseite."""
    style = ts.get('title_style', 'classic')
    if not ts.get('title_page') or style == 'classic':
        return []
    if style not in TITLE_STYLES:
        raise SystemExit(f'Unbekannte Titelseite: {style} (möglich: {", ".join(TITLE_STYLES)})')
    return [BOOK / 'title-common.tex', BOOK / f'title-{style}.tex']


def proof_tex(ts, label, date, commit=''):
    """Kennzeichnung im Probedruck und bei „Manuskript ausgeben“ (#309, #310): Vermerk auf einer eigenen Zeile unter
    der Fußzeile (kollidiert nie mit Seitenzahl oder Kolumnentitel), dazu auf der Titelseite je nach proof_mark eine
    rote Zeile, ein Rahmen oder ein Wasserzeichen. Voraussetzung: scrlayer-scrpage ist geladen."""
    mark = ts.get('proof_mark', 'line')
    if mark not in PROOF_MARKS:
        raise SystemExit(f'Unbekannte Kennzeichnung: {mark} (möglich: {", ".join(PROOF_MARKS)})')
    day = date[8:10] + '.' + date[5:7] + '.' + date[:4]
    red = '\\color{red!65!black}'
    note = latex_escape(f'{label} {day} – nicht zur Veröffentlichung')
    out = ['\\usepackage{eso-pic}', '\\newif\\ifgwproofnote\\gwproofnotetrue',
           '\\DeclareNewLayer[foot,addvoffset=1.4\\baselineskip,contents={\\ifgwproofnote\\parbox[b]{\\layerwidth}{\\centering'
           '\\footnotesize\\sffamily' + red + ' ' + note + '}\\fi}]{gwproof}',
           '\\AddLayersToPageStyle{@everystyle@}{gwproof}']
    if mark in ('watermark', 'watermark_all'):
        wm = ('{\\AtPageCenter{\\makebox(0,0){\\rotatebox{55}{\\fontsize{54}{54}\\selectfont\\sffamily\\bfseries'
              '\\color{red!14}' + latex_escape(label.upper()) + '}}}}')
        if mark == 'watermark_all':
            out.append('\\AddToShipoutPictureBG' + wm)
    if not ts.get('title_page'):
        return '\n'.join(out) + '\n'
    head = latex_escape(f'{label} · {day}')
    if mark == 'line':
        title = ('\\put(0,\\LenToUnit{14mm}){\\makebox[\\paperwidth]{\\small\\sffamily' + red + ' ' + head + '}}')
    else:
        more = latex_escape('nicht zur Veröffentlichung' + (f' · Stand {commit[:7]}' if commit else ''))
        title = ('\\put(0,\\LenToUnit{12mm}){\\makebox[\\paperwidth]{\\fcolorbox{red!65!black}{white}{\\parbox{0.66\\paperwidth}'
                 '{\\centering\\small\\sffamily' + red + ' \\textbf{' + latex_escape(f'{label.upper()} · {day}') + '}\\\\'
                 '\\footnotesize ' + more + '}}}}')
    out += ['\\usepackage{letltxmacro}\\makeatletter\\LetLtxMacro\\gw@maketitle\\maketitle',
            '\\renewcommand*{\\maketitle}[1][1]{\\global\\gwproofnotefalse'
            + ('\\AddToShipoutPictureBG*' + wm if mark == 'watermark' else '')
            + '\\AddToShipoutPictureFG*{\\AtPageLowerLeft{' + title + '}\\global\\gwproofnotetrue}\\gw@maketitle}',
            '\\makeatother']
    return '\n'.join(out) + '\n'


# Titelseite im EPUB je title_style (#310). Pandoc setzt sie als section.titlepage mit h1.title, p.subtitle,
# p.author, p.date; die Reihenfolge Titel, Untertitel, Autor bleibt (Reader ordnen per CSS nicht zuverlässig um).
EPUB_TITLE = {
    'rules': ('section.titlepage { text-align: center; margin-top: 25%; }',
              'section.titlepage h1.title { border-top: 2px solid #222; border-bottom: 1px solid #222; padding: 0.45em 0; '
              'margin: 0 0 0.6em; font-weight: normal; font-size: 1.9em; }',
              'section.titlepage .subtitle { font-style: italic; }',
              'section.titlepage .author { font-variant: small-caps; letter-spacing: 0.05em; margin-top: 2.5em; }'),
    'modern': ('section.titlepage { text-align: left; margin-top: 45%; font-family: sans-serif; }',
               'section.titlepage h1.title { font-size: 2.4em; font-weight: bold; line-height: 1.1; margin: 0 0 0.4em; }',
               'section.titlepage .subtitle { border-top: 2px solid #999; padding-top: 0.5em; width: 40%; }',
               'section.titlepage .author { text-transform: uppercase; font-size: 0.8em; letter-spacing: 0.12em; '
               'margin-top: 2em; }'),
    'spaced': ('section.titlepage { text-align: center; margin-top: 30%; }',
               'section.titlepage h1.title { text-transform: uppercase; letter-spacing: 0.25em; font-weight: normal; hyphens: none; '
               'font-size: 1.6em; margin: 0 0 0.4em; }',
               'section.titlepage h1.title::after { content: "◆"; display: block; font-size: 0.4em; letter-spacing: 0; '
               'margin-top: 0.9em; }',
               'section.titlepage .subtitle { font-style: italic; }',
               'section.titlepage .author { font-variant: small-caps; letter-spacing: 0.08em; margin-top: 5em; }'),
    'band': ('section.titlepage { text-align: center; margin-top: 30%; }',
             'section.titlepage h1.title { background: #2b2f3a; color: #fff; padding: 0.9em 0.5em 0.3em; margin: 0; '
             'font-size: 1.8em; }',
             'section.titlepage .subtitle { background: #2b2f3a; color: #c9ccd4; font-style: italic; margin: 0; '
             'padding: 0 0.5em 1em; }',
             'section.titlepage .author { font-variant: small-caps; letter-spacing: 0.05em; margin-top: 1.5em; }'),
}


def epub_css(ts):
    """Zusätzliches EPUB-CSS aus den Ausgabeoptionen; leer bei den Vorgaben."""
    out = []
    style = ts.get('title_style', 'classic')
    if ts.get('title_page') and style in EPUB_TITLE:
        out += ['section.titlepage h1.title { page-break-before: avoid; }',
                'section.titlepage p { text-indent: 0; }', *EPUB_TITLE[style]]
    if is_sans(ts['font']):
        out.append('body { font-family: sans-serif; }')
    hf = ts.get('heading_font', 'same')
    if hf in ('serif', 'sans'):
        out.append(f'h1, h2, h3 {{ font-family: {"sans-serif" if hf == "sans" else "serif"}; }}')
    if ts.get('paragraph') == 'spacing':
        out.append('p { text-indent: 0; margin-bottom: 0.7em; }')
    if not ts.get('hyphenation', True):
        out.append('body { hyphens: manual; -epub-hyphens: manual; }')
    if ts.get('line_spacing', 1.1) != 1.1:
        out.append(f'body {{ line-height: {round(1.45 * float(ts["line_spacing"]) / 1.1, 2)}; }}')
    return '\n'.join(out)


W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def docx_float_images(path):
    """DOCX (#54): Pandoc setzt Bilder nur in die Zeile. Bilder mit dem Titel gwpos:left|right (aus merkkasten.lua)
    kommen samt Bildunterschrift in eine schwebende, rahmenlose Tabelle am linken bzw. rechten Rand, um die der Text
    fließt (Word und LibreOffice); gwpos:center wird zentriert. Der Titel wird danach entfernt."""
    import zipfile
    from lxml import etree
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        files = {n: z.read(n) for n in z.namelist()}
    root = etree.fromstring(files['word/document.xml'])
    nsdoc = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
    changed = False
    for pr in root.iter(nsdoc + 'docPr'):
        title = pr.get('title') or ''
        if not title.startswith('gwpos:'):
            continue
        pos = title.split(':', 1)[1]
        del pr.attrib['title']
        changed = True
        para = next(a for a in pr.iterancestors() if a.tag == W + 'p')
        if pos not in ('left', 'right'):
            ppr = para.find(W + 'pPr')
            if ppr is None:
                ppr = etree.Element(W + 'pPr')
                para.insert(0, ppr)
            jc = ppr.find(W + 'jc') if ppr.find(W + 'jc') is not None else etree.SubElement(ppr, W + 'jc')
            jc.set(W + 'val', 'center')
            cap = para.getnext()   # Bildunterschrift mittig wie das Bild
            if cap is not None and cap.tag == W + 'p' and 'Caption' in ''.join(cap.xpath('./w:pPr/w:pStyle/@w:val', namespaces={'w': W[1:-1]})):
                cppr = cap.find(W + 'pPr')
                (cppr.find(W + 'jc') if cppr.find(W + 'jc') is not None else etree.SubElement(cppr, W + 'jc')).set(W + 'val', 'center')
            continue
        ext = next((e for e in pr.getparent() if e.tag == nsdoc + 'extent'), None)
        width = int(int(ext.get('cx')) / 635) + 60 if ext is not None else 3000   # EMU → Twips
        caption = para.getnext()
        parts = [para] + ([caption] if caption is not None and caption.tag == W + 'p'
                          and 'Caption' in ''.join(caption.xpath('./w:pPr/w:pStyle/@w:val', namespaces={'w': W[1:-1]})) else [])
        parent, index = para.getparent(), para.getparent().index(para)
        tbl = etree.Element(W + 'tbl')
        tpr = etree.SubElement(tbl, W + 'tblPr')
        etree.SubElement(tpr, W + 'tblpPr', {W + 'leftFromText': '170', W + 'rightFromText': '170', W + 'bottomFromText': '113',
                                             W + 'vertAnchor': 'text', W + 'horzAnchor': 'margin', W + 'tblpXSpec': pos, W + 'tblpY': '1'})
        etree.SubElement(tpr, W + 'tblW', {W + 'w': str(width), W + 'type': 'dxa'})
        borders = etree.SubElement(tpr, W + 'tblBorders')
        for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            etree.SubElement(borders, W + side, {W + 'val': 'nil'})
        etree.SubElement(tpr, W + 'tblLayout', {W + 'type': 'fixed'})
        mar = etree.SubElement(tpr, W + 'tblCellMar')
        for side in ('left', 'right'):
            etree.SubElement(mar, W + side, {W + 'w': '0', W + 'type': 'dxa'})
        grid = etree.SubElement(tbl, W + 'tblGrid')
        etree.SubElement(grid, W + 'gridCol', {W + 'w': str(width)})
        tc = etree.SubElement(etree.SubElement(tbl, W + 'tr'), W + 'tc')
        etree.SubElement(etree.SubElement(tc, W + 'tcPr'), W + 'tcW', {W + 'w': str(width), W + 'type': 'dxa'})
        for p in parts:
            tc.append(p)
        parent.insert(index, tbl)
    if changed:
        files['word/document.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            for n, data in files.items():
                z.writestr(n, data)
    return changed


BABEL = {'de': 'ngerman', 'de-de': 'ngerman', 'de-at': 'naustrian', 'de-ch': 'nswissgerman', 'en': 'english',
         'en-us': 'american', 'en-gb': 'british'}


def babel_tex(lang):
    """PDF: Silbentrennung und Sprache über babel ohne bidi=default. Pandoc lädt babel bei gesetztem lang für XeLaTeX
    mit bidi=default; das verändert den Absatzbau und lässt umflossene Bilder (wrapfig, Medienplatzierung #54)
    verrutschen. Deshalb lang nicht an Pandoc geben und babel hier laden; pdflang setzt hyperref."""
    code = str(lang or 'de').lower()
    name = BABEL.get(code) or BABEL.get(code.split('-')[0], 'ngerman')
    return (f'\\usepackage{{babel}}\n\\babelprovide[main,import]{{{name}}}\n'
            f'\\AtBeginDocument{{\\hypersetup{{pdflang={lang}}}}}\n')


def image_notes(used, ts, formats=()):
    """Hinweise (#54): Auflösung unter etwa 300 dpi bei der gewählten Breite; Textumfluss, den DOCX nicht kann."""
    w = PAGE.get(ts['page_size'], PAGE['a5'])[0]
    full = (w - (30 if w < 160 else 50)) / 25.4 * 300 * 0.9
    out = []
    for m in used:
        pct = int(m.get('width_pct') or 100)
        need = int(full * pct / 100)
        if m.get('width_px') and m['width_px'] < need:
            out.append(f'Bild „{m.get("caption") or m["id"]}“ hat {m["width_px"]} px Breite; für den Druck bei '
                       + ('voller Satzbreite' if pct == 100 else f'{pct} % der Satzbreite') + f' sind etwa {need} px gut (300 dpi).')
    return out


def image_credit(used, config):
    """Bildnachweis im Impressum für KI-erzeugte Bilder (#54, images.credit_in_imprint, Vorgabe an)."""
    if (config.get('images') or {}).get('credit_in_imprint') is False:
        return ''
    ai = [m for m in used if m.get('ai_generated')]
    if not ai:
        return ''
    import ai_disclosure
    names = ai_disclosure.provider_names()
    services = sorted({names.get(m['provider'], m['provider']) for m in ai if m.get('provider') and m['provider'] != 'chat'})
    n = len(ai)
    return (f'{"Die Abbildung ist" if n == 1 else f"Die {n} Abbildungen sind"} mit KI erzeugt'
            + (f' ({", ".join(services)})' if services else '') + '.')


def pdf_pages(path):
    """Seitenzahl eines PDF (pdfinfo, sonst aus dem Seitenbaum gelesen)."""
    if path is None:
        return 0
    if shutil.which('pdfinfo'):
        out = subprocess.run(['pdfinfo', str(path)], capture_output=True, text=True).stdout
        m = re.search(r'(?m)^Pages:\s+(\d+)', out)
        if m:
            return int(m.group(1))
    counts = [int(c) for c in re.findall(rb'/Type\s*/Pages\b[^>]*?/Count\s+(\d+)', Path(path).read_bytes())]
    return max(counts) if counts else 0


def front_page(base, config, pages, out, proof, blank=True):
    """Vorderseite für PDF bzw. EPUB (#324, scripts/build_cover.py build_front): Hinweise, None ohne Vorderseite.
    Im Probedruck führt ein Fehler (z. B. unpassendes Seitenformat) nur zu einer Warnung; die Ausgabe entsteht ohne
    Vorderseite. In einer Auflage bricht er ab."""
    try:
        return build_cover.build_front(base, config, pages, out, blank=blank)
    except SystemExit as e:
        if not proof:
            raise
        print(f'⚠ Vorderseite nicht eingebunden: {e}')
        return None


def prepend_pdf(front, interior, target):
    """Setzt die Vorderseite (samt Leerseite) vor das Bildschirm-PDF (#324). qpdf behält Lesezeichen, Links und
    Seitenbezeichnungen des Innenteils; ohne qpdf fügt pdfunite zusammen, dann fehlen die Lesezeichen (Hinweis)."""
    if shutil.which('qpdf'):
        r = subprocess.run(['qpdf', str(interior), '--pages', str(front), '1-z', str(interior), '1-z', '--', str(target)],
                           capture_output=True, text=True)
        if r.returncode not in (0, 3):   # 3: nur Warnungen
            raise SystemExit('Vorderseite konnte nicht vor das PDF gesetzt werden:\n' + (r.stderr or r.stdout)[-2000:])
        return ''
    run(['pdfunite', str(front), str(interior), str(target)])
    return 'qpdf fehlt: Vorderseite mit pdfunite eingefügt, dabei gehen die Lesezeichen des PDF verloren'


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if r.returncode:
        raise SystemExit(f'Fehler bei {" ".join(map(str, cmd[:3]))} …:\n{r.stderr[-4000:]}')
    return r.stdout


def imprint_markdown(meta, release_name, commit, publication=None):
    year = meta['date'][:4]
    lines = [f'{meta["title"]}' + (f' – {meta["subtitle"]}' if meta.get('subtitle') else ''),
             f'{meta.get("edition_text", "")}, {meta["date"][8:10]}.{meta["date"][5:7]}.{year}',
             f'© {year} {meta.get("author", "")}'.rstrip()]
    pub = publication or {}   # Angaben im Impressum (#68)
    if pub.get('rights'):
        lines.append(pub['rights'].strip())
    if pub.get('publisher'):
        lines.append(pub['publisher'].strip() if pub['publisher'].strip().lower() == 'selbstverlag'
                     else f'Verlag: {pub["publisher"].strip()}')
    if pub.get('isbn_print'):
        lines.append(f'ISBN {pub["isbn_print"].strip()} (Druckausgabe)')
    if pub.get('isbn_ebook'):
        lines.append(f'ISBN {pub["isbn_ebook"].strip()} (E-Book)')
    if commit:
        lines.append(f'Stand: {release_name}, Commit {commit[:7]}')
    return lines


def docx_title(doc, ts):
    """Titelseite im DOCX je title_style (#310): Ausrichtung, Schrift, Linien bzw. Band über die Absatzformate
    Title, Subtitle, Author; „classic“ und ohne Titelseite bleibt Pandocs Vorlage unverändert."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor
    style = ts.get('title_style', 'classic')
    if not ts.get('title_page') or style == 'classic':
        return
    if style not in TITLE_STYLES:
        raise SystemExit(f'Unbekannte Titelseite: {style} (möglich: {", ".join(TITLE_STYLES)})')

    def get(name):
        try:
            return doc.styles[name]
        except KeyError:
            return None

    def ppr_child(st, tag, **attrs):
        ppr = st.element.get_or_add_pPr()
        for old in ppr.findall(qn(f'w:{tag}')):
            ppr.remove(old)
        el = OxmlElement(f'w:{tag}')
        for k, v in attrs.items():
            el.set(qn(f'w:{k}'), v)
        ppr.append(el)
        return el

    def border(st, sides):
        bdr = ppr_child(st, 'pBdr')
        for side, size in sides:
            e = OxmlElement(f'w:{side}')
            e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), str(size)); e.set(qn('w:space'), '6')
            e.set(qn('w:color'), '222222')
            bdr.append(e)

    title, sub, author = get('Title'), get('Subtitle'), get('Author')
    align = 0 if style == 'modern' else 1   # 0 links, 1 zentriert
    for st in (title, sub, author, get('Date')):
        if st is not None:
            st.paragraph_format.alignment = align
    if title is None:
        return
    title.paragraph_format.space_before = Pt(96 if style in ('rules', 'spaced', 'band') else 160)
    if style == 'rules':
        border(title, (('top', 8), ('bottom', 4)))
        title.font.bold = False
        if sub is not None:
            sub.font.italic = True
        if author is not None:
            author.font.small_caps = True
    elif style == 'modern':
        sans = FONTS['sans'][1]
        for st in (title, sub, author):
            if st is not None:
                st.font.name = sans
        title.font.bold, title.font.size = True, Pt(30)
        if author is not None:
            author.font.all_caps = True
            author.font.size = Pt(max(8.0, float(ts['font_size']) - 1.5))
    elif style == 'spaced':
        title.font.all_caps, title.font.bold = True, False
        rpr = title.element.get_or_add_rPr()
        sp = OxmlElement('w:spacing')
        sp.set(qn('w:val'), '80')   # Zeichenabstand in Twips/20: 4 pt gesperrt
        rpr.append(sp)
        if sub is not None:
            sub.font.italic = True
        if author is not None:
            author.font.small_caps = True
            author.paragraph_format.space_before = Pt(120)
    elif style == 'band':
        for st, color in ((title, 'FFFFFF'), (sub, 'C9CCD4')):
            if st is None:
                continue
            ppr_child(st, 'shd', val='clear', color='auto', fill='2B2F3A')
            st.font.color.rgb = RGBColor.from_string(color)
        if sub is not None:
            sub.font.italic = True
            sub.paragraph_format.space_before = Pt(0)
        title.paragraph_format.space_after = Pt(0)
        if author is not None:
            author.font.small_caps = True


def make_reference_docx(path, ts):
    """Pandocs Standardvorlage mit Seitenformat, Schrift und Merkkasten-Format."""
    from docx import Document
    from docx.enum.style import WD_STYLE_TYPE
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Mm, Pt
    path.write_bytes(subprocess.run(['pandoc', '--print-default-data-file', 'reference.docx'],
                                    capture_output=True, check=True).stdout)
    doc = Document(str(path))
    w, h = PAGE.get(ts['page_size'], PAGE['a5'])
    margin = 15 if w < 160 else 25
    for s in doc.sections:
        s.page_width, s.page_height = Mm(w), Mm(h)
        s.left_margin = s.right_margin = Mm(margin)
        s.top_margin, s.bottom_margin = Mm(margin + 3), Mm(margin + 5)
    font = FONTS.get(ts['font'], FONTS['serif'])[1]
    hf = ts.get('heading_font', 'same')
    head_font = font if hf == 'same' else FONTS['sans' if hf == 'sans' else 'serif'][1]
    explicit = ts.get('_explicit', set())   # nur ausdrücklich gesetzte Optionen ändern das bisherige DOCX
    for name in ('Normal', 'Body Text', 'First Paragraph', 'Compact'):
        try:
            st = doc.styles[name]
        except KeyError:
            continue
        st.font.name = font
        st.font.size = Pt(float(ts['font_size']))
        if 'line_spacing' in explicit:
            st.paragraph_format.line_spacing = float(ts['line_spacing'])
        if 'paragraph' in explicit and name in ('Body Text', 'First Paragraph'):
            indent = ts['paragraph'] == 'indent'
            st.paragraph_format.space_before = Pt(0)
            st.paragraph_format.space_after = Pt(0 if indent else 6)
            st.paragraph_format.first_line_indent = Mm(5) if indent and name == 'Body Text' else Mm(0)
    from docx.shared import RGBColor
    for name in ('Heading 1', 'Heading 2', 'Heading 3', 'Heading 4', 'Title', 'Subtitle'):
        try:
            doc.styles[name].font.name = head_font
            doc.styles[name].font.color.rgb = RGBColor(0x22, 0x22, 0x22)
        except KeyError:
            pass
    docx_title(doc, ts)   # gewählte Titelseite (#310)
    # Probedruck: Zeichenformate für Marker und Statusvermerke
    for name, color, bold, italic in (('Marker', RGBColor(0x8A, 0x1C, 0x1C), True, False),
                                      ('Stand', RGBColor(0x77, 0x77, 0x77), False, True)):
        try:
            doc.styles[name]
        except KeyError:
            cs = doc.styles.add_style(name, WD_STYLE_TYPE.CHARACTER)
            cs.font.color.rgb, cs.font.bold, cs.font.italic = color, bold, italic
            cs.font.size = Pt(float(ts['font_size']) - 1.5)
    try:
        doc.styles['Widmung']
    except KeyError:   # Widmung (#57): eigene Seite, zentriert, kursiv
        st = doc.styles.add_style('Widmung', WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = doc.styles['Normal']
        st.font.italic = True
        pf = st.paragraph_format
        pf.alignment = 1   # zentriert
        pf.space_before = Mm(h / 4)
        pf.page_break_before = True
        st2 = doc.styles.add_style('Widmung Text', WD_STYLE_TYPE.PARAGRAPH)   # weitere Absätze
        st2.base_style = doc.styles['Normal']
        st2.font.italic = True
        st2.paragraph_format.alignment = 1
    try:
        doc.styles['Signatur']
    except KeyError:   # Vorwort, Nachwort (#58): Verfasser und Ort/Datum rechtsbündig
        st = doc.styles.add_style('Signatur', WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = doc.styles['Normal']
        st.font.italic = True
        st.paragraph_format.alignment = 2   # rechts
        st.paragraph_format.space_before = Pt(12)
    try:
        doc.styles['Merkkasten']
    except KeyError:
        st = doc.styles.add_style('Merkkasten', WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = doc.styles['Normal']
        st.font.size = Pt(float(ts['font_size']) - 1)
        pf = st.paragraph_format
        pf.left_indent = pf.right_indent = Mm(4)
        pf.space_before = pf.space_after = Pt(4)
        ppr = st.element.get_or_add_pPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), 'EEEEEE')
        ppr.append(shd)
        bdr = OxmlElement('w:pBdr')
        for side in ('top', 'left', 'bottom', 'right'):
            e = OxmlElement(f'w:{side}')
            e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '4'); e.set(qn('w:space'), '4'); e.set(qn('w:color'), '999999')
            bdr.append(e)
        ppr.append(bdr)
    doc.save(str(path))


def render(base, config, ts, meta, common_meta, imprint, body, body_pdf, dedication, out, tag, formats, proof=False,
           proof_note='', date='', series_line='', ser=None, extra_tex='', top_level='chapter',
           footer_label='Probedruck', commit='', front_cover=None, badge=None):
    """Setzt die Formate (pdf, pdf_print, booklet, cover, epub, docx) aus fertigem Markdown; gibt die Dateien zurück.
    Gemeinsam für Auflagen und den Sammelband (scripts/build_omnibus.py, #116).
    front_cover (#324): None, 'proof' oder 'always' – die Vorderseite samt Leerseite kommt vor das Bildschirm-PDF;
    bei 'always' ohne hinterlegte Vorderseite ein Hinweis. Im Probedruck verhindert ein Fehler der Vorderseite
    den Bau nicht (Warnung), in einer Auflage bricht er ab.
    badge (#400): (Pfad, Alternativtext) des Kennzeichens zur KI-Angabe unter dem Impressum oder None."""
    fonts = FONTS.get(ts['font'], FONTS['serif'])
    w, h = PAGE.get(ts['page_size'], PAGE['a5'])
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        def write(name, text):
            (tmp / name).write_text(text, encoding='utf-8')
            return tmp / name

        order = ['pdf', 'pdf_print', 'booklet', 'cover', 'epub', 'docx']
        wanted = [f.strip() for f in formats.split(',') if f.strip()]
        unknown = [f for f in wanted if f not in order]
        if unknown:
            raise SystemExit(f'Unbekannte Formate: {", ".join(unknown)} (möglich: {", ".join(order)})')
        fmts = sorted(set(wanted), key=order.index)
        crop = bool((config.get('print') or {}).get('crop_marks'))
        if 'booklet' in fmts and ('pdf_print' not in fmts or crop):
            fmts.insert(fmts.index('booklet'), '_print')   # Innenteil wie Druck-PDF, ohne Schnittmarken, nicht ausgeliefert
        if 'cover' in fmts and not {'pdf', 'pdf_print', '_print'} & set(fmts):
            fmts.insert(0, '_pdf')   # Innenteil nur zum Zählen der Seiten (Rückenbreite), nicht ausgeliefert
        interior = print_interior = None
        for fmt in fmts:
            if fmt == 'booklet':   # Broschüre: Innenteil ohne Schnittmarken, je zwei Seiten pro Bogen
                src_pdf = print_interior or interior
                pages = pdf_pages(src_pdf)
                target = out / f'{tag}-broschuere.pdf'
                shutil.copyfile(src_pdf, tmp / 'broschuere-innen.pdf')
                tex = write('broschuere.tex', booklet_tex('broschuere-innen.pdf', pages, ts['page_size']))
                run(['xelatex', '-interaction=nonstopmode', '-halt-on-error', tex.name], cwd=tmp)
                shutil.copyfile(tmp / 'broschuere.pdf', target)
                sheets = len(booklet_order(pages)) // 4
                results.append(target)
                print(f'✓ {target} ({target.stat().st_size // 1024} KB) · {pages} Seiten auf {sheets} '
                      f'Blatt {booklet_sheet(ts["page_size"]).upper()} quer; beidseitig über die kurze Kante drucken')
                continue
            if fmt == 'cover':   # Umschlag (#68): braucht die Seitenzahl des Innenteils
                pages = pdf_pages(interior)
                target = out / f'{tag}-umschlag.pdf'
                dim = build_cover.build(base, config, pages, target, guides=proof)
                results.append(target)
                print(f'✓ {target} ({target.stat().st_size // 1024} KB) · {build_cover.summary(dim)}')
                for n in dim['notes']:
                    print(f'ⓘ {n}')
                continue
            hidden = fmt in ('_pdf', '_print')
            kind = 'pdf' if fmt in ('pdf', 'pdf_print', '_pdf', '_print') else fmt
            target = (tmp / f'innenteil{fmt.replace("_", "-")}.pdf') if hidden else \
                out / (f'{tag}-druck.pdf' if fmt == 'pdf_print' else f'{tag}.{fmt}')
            delivered = target
            if fmt == 'pdf' and front_cover:   # Vorderseite (#324): Innenteil bleibt ohne sie (Umschlag, Broschüre)
                target = tmp / 'innenteil-bildschirm.pdf'
            cmd = ['pandoc', '--from', 'markdown+smart', '--lua-filter', str(BOOK / 'merkkasten.lua'),
                   f'--top-level-division={top_level}', '-o', str(target)]
            if ts.get('toc'):
                cmd += ['--toc', f'--toc-depth={int(ts.get("toc_depth", 1))}']
            # Glossar-Verweise (#107): Kennzeichnung; im Druck-PDF ohne Link
            cmd += ['-M', f'gw-glossary-marks={ts.get("glossary_marks", "arrow")}']
            if fmt in ('pdf_print', '_print'):
                cmd += ['-M', 'gw-print=true']
            m = dict(common_meta)
            if kind == 'pdf':
                lines = '\\\\\n'.join(latex_escape(l) for l in imprint)
                if badge:   # Kennzeichen zur KI-Angabe (#400) unter dem Impressum
                    lines += ('\\\\[4pt]\n\\includegraphics[width=' + ai_disclosure.BADGE_WIDTH + ']{'
                              + badge[0].resolve().as_posix() + '}')
                imp, extra_header = '', []
                if ts.get('imprint') and ts.get('title_page'):
                    # Impressum auf die Rückseite der Titelseite (KOMA-Script)
                    extra_header = [str(write('imprint.tex', '\\lowertitleback{\\footnotesize\n' + lines + '\n}\n'))]
                elif ts.get('imprint'):
                    imp = '\\begin{flushleft}\\footnotesize\n' + lines + '\n\\end{flushleft}\\bigskip\n'
                before = imp
                if dedication:
                    before += run(['pandoc', '--from', 'markdown+smart', '--to', 'latex',
                                   '--lua-filter', str(BOOK / 'merkkasten.lua'), str(write('dedication.md', dedication))])
                    imp = ''
                    cmd += ['--include-before-body', str(write('before.tex', before))]
                m.update({'documentclass': 'scrbook',
                          'classoption': [f'paper={w}mm:{h}mm', f'fontsize={ts["font_size"]}pt',
                                          f'DIV={DIV.get(ts.get("margins", "standard"), "calc")}', 'BCOR=8mm',
                                          'titlepage=' + ('true' if ts.get('title_page') else 'false'),
                                          'open=' + ('right' if ts.get('chapter_start') == 'right' else 'any'),
                                          'parskip=' + ('half' if ts.get('paragraph') == 'spacing' else 'false')],
                          'mainfont': fonts[0], 'sansfont': 'TeX Gyre Heros', 'monofont': 'TeX Gyre Cursor',
                          'linestretch': float(ts.get('line_spacing', 1.1)), 'colorlinks': False, 'header-includes': '',
                          'include-before': imp})
                if ts.get('initials'):
                    cmd += ['-M', 'gw-initials=true']
                cmd += ['--pdf-engine=xelatex', '--include-in-header', str(BOOK / 'header.tex')]
                if m.get('lang'):   # Sprache selbst laden: Pandocs babel mit bidi=default stört wrapfig (#54)
                    extra_header.insert(0, str(write('sprache.tex', babel_tex(m.pop('lang')))))
                layout = layout_tex(ts, meta)
                if layout:
                    extra_header.append(str(write('layout.tex', layout)))
                if series_line and ts.get('title_page'):   # Reihe über dem Titel (KOMA \subject)
                    extra_header.append(str(write('series.tex', '\\subject{' + latex_escape(series_line) + '}\n')))
                extra_header += [str(f) for f in title_tex(ts)]   # gewählte Titelseite (#310)
                if proof:
                    if ts.get('title_page'):   # der Vermerk steht auf der Titelseite (proof_mark), nicht in der Datumszeile
                        m['date'] = ''
                    note = proof_tex(ts, footer_label, date, commit)
                    if 'scrlayer-scrpage' not in layout:   # Seitenzahl unten außen wie bisher im Probedruck
                        note = ('\\usepackage{scrlayer-scrpage}\\pagestyle{scrheadings}\\clearpairofpagestyles\n'
                                '\\ofoot*{\\pagemark}\n' + note)
                    extra_header.append(str(write('proof.tex', note)))
                if fmt == 'pdf_print' and (config.get('print') or {}).get('crop_marks'):
                    # Druck-PDF mit Schnittmarken: Papier ringsum 8 mm größer, Seite mittig
                    # (crop kennt XeTeX nicht als Treiber; die Papiergröße setzt daher ein eigenes \\special)
                    m['classoption'] = m['classoption'] + ['pagesize=false']
                    extra_header.append(str(write('crop.tex', f'\\usepackage[cam,center,noinfo,width={w + 16}mm,height={h + 16}mm]{{crop}}\n'
                                                              f'\\AtBeginDocument{{\\special{{papersize={w + 16}mm,{h + 16}mm}}}}\n')))
                for hdr in extra_header:   # nicht h: das ist die Seitenhöhe
                    cmd += ['--include-in-header', hdr]
                src = body_pdf
            else:
                pre = ''
                if ts.get('imprint'):
                    pre = '# Impressum {.unnumbered .unlisted .impressum}\n\n' + '\n\n'.join(
                        imprint + ([ai_disclosure.badge_markdown(config)] if badge else [])) + '\n\n'
                if proof:
                    pre = f'::: probedruck\n{proof_note}\n:::\n\n' + pre
                src = pre + body
                if fmt == 'epub':
                    cmd += ['--css', str(BOOK / 'epub.css'),
                            '--epub-title-page=' + ('true' if ts.get('title_page') else 'false')]
                    extra_css = epub_css(ts)
                    if extra_css:
                        cmd += ['--css', str(write('ausgabe.css', extra_css + '\n'))]
                    if ts.get('initials'):
                        cmd += ['-M', 'gw-initials=true']
                    m['description'] = meta.get('description', '')
                    if series_line:   # EPUB 3: Reihe und Band (belongs-to-collection, group-position)
                        m['belongs-to-collection'], m['group-position'] = ser['title'], str(ser['volume'])
                    isbn = (config.get('publication') or {}).get('isbn_ebook')
                    if isbn:
                        m['identifier'] = [{'scheme': 'ISBN-13', 'text': 'urn:isbn:' + re.sub(r'[^0-9Xx]', '', isbn)}]
                    if build_cover.front_source(base, config)[0] and shutil.which('pdftoppm'):
                        # EPUB-Cover = eigene Vorderseite (cover.front) oder Vorderseite des Umschlags (#324)
                        notes = front_page(base, config, pdf_pages(interior) if interior else 0, tmp / 'cover-epub.pdf',
                                           proof, blank=False)
                        if notes is not None:
                            front = build_cover.front_jpeg(tmp / 'cover-epub.pdf', tmp / 'cover-vorne.jpg')
                            cmd += ['--epub-cover-image', str(front)]
                elif fmt == 'docx':
                    ref = tmp / 'reference.docx'
                    make_reference_docx(ref, ts)
                    cmd += ['--reference-doc', str(ref)]
            src_path = write(f'book-{fmt}.md', '---\n' + yaml.safe_dump(m, allow_unicode=True, sort_keys=False) + '---\n\n' + src)
            run(cmd + [str(src_path)], cwd=tmp)
            if fmt == 'docx':   # Medienplatzierung (#54): Lage und Textumfluss im DOCX nachsetzen
                docx_float_images(target)
            if kind == 'pdf':
                interior = target
                if fmt == '_print' or (fmt == 'pdf_print' and not crop):
                    print_interior = target
            if hidden:
                continue
            if delivered != target:   # Bildschirm-PDF mit Vorderseite (#324)
                notes = front_page(base, config, pdf_pages(target), tmp / 'vorderseite.pdf', proof)
                if notes is None:
                    if front_cover == 'always':
                        print('ⓘ Keine Vorderseite im PDF: weder cover.front noch eine Covervorlage (cover) hinterlegt')
                    shutil.copyfile(target, delivered)
                else:
                    notes.append(prepend_pdf(tmp / 'vorderseite.pdf', target, delivered))
                    print('ⓘ Vorderseite als Seite 1 im PDF, danach eine Leerseite')
                for n in filter(None, notes or []):
                    print(f'ⓘ {n}')
                target = delivered
            results.append(target)
            print(f'✓ {target} ({target.stat().st_size // 1024} KB)')

    return results


def preview_tag(short, n):
    """Tag einer Vorabfassung (#348): <kurztitel-slug>-vorab-N; zählt nie als Auflage (-auflage-N)."""
    return f'{tag_slug(short)}-vorab-{n}'


def draft_note(body):
    """Zusatz zum Vermerk im Probedruck bzw. in der Vorabfassung (#348): nicht abgeschlossene Abschnitte und
    offene Marker nur erwähnen, wenn es sie gibt."""
    drafts, markers = '{.gwstatus}' in body, '{.gwmarker}' in body
    if drafts and markers:
        return 'Enthält auch nicht abgeschlossene Abschnitte; offene Marker sind hervorgehoben.'
    if drafts:
        return 'Enthält auch nicht abgeschlossene Abschnitte.'
    if markers:
        return 'Offene Marker sind hervorgehoben.'
    return ''


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('--edition', type=int)
    ap.add_argument('--proof', action='store_true', help='Probedruck des aktuellen Stands (keine Auflage)')
    ap.add_argument('--preview', type=int, metavar='N',
                    help='Vorabfassung N (#348): wie --proof, Vermerk „Vorabfassung N“, Tag <kurztitel>-vorab-N')
    ap.add_argument('--manuscript', action='store_true',
                    help='„Manuskript ausgeben“ (#260): PDF des Arbeitsstands, Geplantes in Stichworten')
    ap.add_argument('--chapter', help='mit --manuscript: nur dieses Kapitel (Nummer oder ID)')
    ap.add_argument('--chapters', help='mit --proof bzw. --preview: nur diese Kapitel, z. B. „1-4“ oder „1,3“ (#413)')
    ap.add_argument('--out', default='build')
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--formats', help='Formate, Komma-getrennt; ohne Angabe typesetting.formats (Vorgabe pdf,docx,epub)')
    ap.add_argument('--commit', default='')
    ap.add_argument('--allow-markers', action='store_true')
    args = ap.parse_args(argv[1:])

    if args.chapter and not args.manuscript:
        ap.error('--chapter nur mit --manuscript')
    if args.chapters and (args.manuscript or (args.preview is None and not args.proof)):
        ap.error('--chapters nur mit --proof oder --preview')
    if args.manuscript:
        args.proof, args.formats = True, 'pdf'
    if args.preview is not None:
        if args.preview < 1 or args.manuscript or args.edition is not None:
            ap.error('--preview N (N ≥ 1) nicht mit --edition oder --manuscript')
        args.proof = True
    if not args.proof and args.edition is None:
        ap.error('--edition N, --proof oder --manuscript angeben')
    base, config = load(args.project)
    if args.proof:
        args.edition = config['project'].get('current_edition') or 0
    only = find_chapter(config, str(args.chapter))[0] if args.chapter else None
    chosen = chapter_selection(config, args.chapters) if args.chapters else None
    parts = book_parts(base, config, proof=args.proof, plan=args.manuscript, only=only if only else chosen)
    matter = [] if only else matter_parts(base, config, proof=args.proof, plan=args.manuscript)
    found = [] if args.proof else problems(parts, config, matter, base)
    blocking = [p for p in found if not (args.allow_markers and p.startswith('Offener Marker'))]
    if args.proof and not parts:
        print(('Manuskript' if args.manuscript else 'Probedruck') + ': Das Buch hat noch keine Kapitel.')
        return 1
    if blocking:
        print(f'Auflage {args.edition} kann nicht gebaut werden:')
        for p in blocking:
            print(f'  ✗ {p}')
        return 1

    if not args.proof:
        import approval_authority
        try:
            approval_authority.verify(base, args.edition, config)
        except approval_authority.AuthorityError:
            print('✗ Persönlicher Inhaltsnachweis fehlt oder ist ungültig; keine Auflage gebaut.')
            return 1

    if not args.proof:
        for note in matter_notes(matter):
            print(f'ⓘ {note}')

    meta = metadata(config, args.edition, args.date)
    ts = meta['typesetting']
    ts['_explicit'] = set((config.get('typesetting') or {}).keys())
    if not args.formats:
        args.formats = ','.join(ts.get('formats') or ['pdf', 'docx', 'epub'])
    wf = yaml.safe_load((ROOT / 'workflow.yml').read_text(encoding='utf-8'))['book_releases']
    short = config['project'].get('title_short') or meta['title']
    release_name = wf['name_pattern'].format(title_short=short, edition=args.edition)
    tag = wf['tag_pattern'].format(title_short_slug=tag_slug(short), edition=args.edition)
    proof_note = ''
    shown = f'{args.date[8:10]}.{args.date[5:7]}.{args.date[:4]}'
    if args.manuscript:
        tag = f'{tag_slug(short)}-manuskript-{args.date}' + (f'-kapitel-{only}' if only else '')
        release_name = f'{short} – Manuskript vom {shown}' + (f' (Kapitel {only})' if only else '')
        proof_note = (f'Manuskript (Arbeitsstand) vom {shown} – nicht zur Veröffentlichung. '
                      'Abschnitte ohne Text erscheinen als „Geplant“ mit dem geplanten Inhalt in Stichworten.')
    elif args.preview:
        tag = preview_tag(short, args.preview)
        release_name = f'{short} – Vorabfassung {args.preview}'
        proof_note = f'Vorabfassung {args.preview} vom {shown} – nicht zur Veröffentlichung.'
    elif args.proof:
        tag = f'{tag_slug(short)}-probedruck-{args.date}'
        release_name = f'{short} – Probedruck vom {args.date[8:10]}.{args.date[5:7]}.{args.date[:4]}'
        proof_note = f'Probedruck vom {args.date[8:10]}.{args.date[5:7]}.{args.date[:4]} – nicht zur Veröffentlichung.'
    if chosen:   # Kapitelauswahl (#413): im Vermerk und im Release-Namen nennen
        sel = selection_text(chosen, len(config['structure']['chapters']))
        if sel:
            proof_note = (proof_note + ' ' + sel).strip()
            release_name += f' ({sel[8:-1]})'
    out = Path(args.out).resolve()   # Pandoc läuft im Arbeitsordner, daher absolut
    out.mkdir(parents=True, exist_ok=True)
    disc = ai_disclosure.for_book(config)   # KI-Angabe (#78): (Ort, Wortlaut) oder None
    in_body = disc if disc and disc[0] != 'imprint' else None
    overview = manuscript_overview(base, config, only, args.date, args.commit)[0] + '\n' if args.manuscript else ''
    body, used_images = resolve_images(base, config, overview + book_body(parts, matter, in_body), args.proof)
    if args.proof and not args.manuscript:   # #348: nur nennen, was es im Stand wirklich gibt
        proof_note = (proof_note + ' ' + draft_note(body)).strip()
    # PDF: Widmung vor dem Inhaltsverzeichnis (include-before), daher dort ohne Widmung im Text
    dedication = ''.join(m[2] for m in matter if m[1]['kind'] == 'dedication' and m[2])
    body_pdf = resolve_images(base, config, overview + book_body(parts, [m for m in matter if m[1]['kind'] != 'dedication'],
                                                                 in_body), args.proof)[0]
    for note in image_notes(used_images, ts, [f.strip() for f in str(args.formats or "").split(",")]):
        print(f'ⓘ {note}')
    imprint = imprint_markdown(meta, release_name, args.commit, config.get('publication'))
    ser = config.get('_series')   # Serie (#116): Reihe und Band im Impressum, „Ebenfalls in dieser Reihe“ am Ende
    if ser and ser.get('volume'):
        import series
        imprint[1:1] = series.edition_lines(ser)
        also = series.also_markdown(base, ser)
        if also:
            body = body.rstrip('\n') + '\n\n' + also
            body_pdf = body_pdf.rstrip('\n') + '\n\n' + also
    credit = image_credit(used_images, config)
    if credit:
        imprint.append(credit)
    disc_lines = [re.sub(r'^\s*[-*]\s+', '– ', line) for line in disc[1].splitlines() if line.strip()] \
        if disc and disc[0] == 'imprint' else []
    shown_date = f'{meta.get("edition_text", "")} · {MONTHS[int(meta["date"][5:7]) - 1]} {meta["date"][:4]}'.strip(' ·')
    common_meta = {k: meta[k] for k in ('title', 'subtitle', 'author', 'lang') if k in meta}
    common_meta['date'] = shown_date
    series_line = f'{ser["title"]} · Band {ser["volume"]}' if ser and ser.get('volume') else ''
    if args.proof:
        label = 'Manuskript' if args.manuscript else f'Vorabfassung {args.preview}' if args.preview else 'Probedruck'
        common_meta['date'] = f'{label} · {shown}'
        meta['edition_text'] = label
        imprint = [release_name, proof_note] + ([f'Commit {args.commit[:7]}'] if args.commit else [])
    imprint += disc_lines
    # Vorderseite im Bildschirm-PDF (#324): Vorgabe nur im Probedruck, nie bei „Manuskript ausgeben“
    pdf_cover = ts.get('pdf_cover', 'proof')
    front_cover = None if args.manuscript else ('always' if pdf_cover == 'always' else
                                                'proof' if pdf_cover == 'proof' and args.proof else None)
    results = render(base, config, ts, meta, common_meta, imprint, body, body_pdf, dedication, out, tag, args.formats,
                     args.proof, proof_note, args.date, series_line, ser,
                     footer_label=label if args.proof else 'Probedruck', commit=args.commit,
                     front_cover=front_cover, badge=ai_disclosure.badge(config) if disc_lines else None)

    if not args.proof:
        try:
            approval_authority.verify(base, args.edition)
        except approval_authority.AuthorityError:
            print('✗ Inhalt oder Freigaberecht während des Baus geändert; Ausgabe nicht veröffentlicht.')
            return 1

    (out / 'edition.yml').write_text(yaml.safe_dump({
        'edition': args.edition, **({'preview': args.preview} if args.preview else {}),
        'name': release_name, 'tag': tag, 'date': args.date,
        'chapters': [p[0] for p in parts], 'matter': [m[1]['id'] for m in matter if m[2]],
        'files': [r.name for r in results]},
        allow_unicode=True, sort_keys=False), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
