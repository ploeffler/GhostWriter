#!/usr/bin/env python3
"""Setzt eine Auflage als PDF, DOCX und EPUB (#15).

Aufruf:
  python scripts/build_edition.py <projektordner> --edition N [--out ordner] [--date JJJJ-MM-TT]
                                   [--formats pdf,docx,epub] [--allow-markers]
  python scripts/build_edition.py <projektordner> --proof [--out ordner] [--formats pdf]
  python scripts/build_edition.py <projektordner> --manuscript [--chapter N] [--out ordner]

Formate (--formats, sonst typesetting.formats): pdf (Bildschirm), pdf_print
(Druck-PDF des Innenteils, <tag>-druck.pdf, mit print.crop_marks Schnittmarken),
cover (Umschlag, <tag>-umschlag.pdf, scripts/build_cover.py; Rückenbreite aus
der Seitenzahl des Innenteils), docx, epub (mit Cover aus der Vorderseite,
wenn es `cover` gibt).

--proof baut einen Probedruck des aktuellen Stands: alle Kapitel und Abschnitte,
auch nicht freigegebene (mit Vermerk „Stand: Entwurf, nicht freigegeben“),
offene Marker farbig hervorgehoben, in der Fußzeile bzw. vorn der Hinweis
„Probedruck – nicht zur Veröffentlichung“. Kein Tag, kein Release; die Action
„Probedruck“ stellt die Dateien als Download bereit.

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
texlive-fonts-recommended, fonts-texgyre), python-docx, pyyaml.
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
from assemble import (book_body, book_parts, find_chapter, manuscript_overview, matter_notes,  # noqa: E402
                      matter_parts, metadata, problems, resolve_images)
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
        title = meta['title'].replace('&', '\\&').replace('%', '\\%').replace('#', '\\#')
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


def epub_css(ts):
    """Zusätzliches EPUB-CSS aus den Ausgabeoptionen; leer bei den Vorgaben."""
    out = []
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


def image_notes(used, ts):
    """Hinweise zur Auflösung (#54): unter etwa 300 dpi bei voller Satzbreite."""
    w = PAGE.get(ts['page_size'], PAGE['a5'])[0]
    need = int((w - (30 if w < 160 else 50)) / 25.4 * 300 * 0.9)
    return [f'Bild „{m.get("caption") or m["id"]}“ hat {m["width_px"]} px Breite; für den Druck bei voller Satzbreite '
            f'sind etwa {need} px gut (300 dpi).' for m in used if m.get('width_px') and m['width_px'] < need]


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
           footer_label='Probedruck'):
    """Setzt die Formate (pdf, pdf_print, cover, epub, docx) aus fertigem Markdown; gibt die Dateien zurück.
    Gemeinsam für Auflagen und den Sammelband (scripts/build_omnibus.py, #116)."""
    fonts = FONTS.get(ts['font'], FONTS['serif'])
    w, h = PAGE.get(ts['page_size'], PAGE['a5'])
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        def write(name, text):
            (tmp / name).write_text(text, encoding='utf-8')
            return tmp / name

        order = ['pdf', 'pdf_print', 'cover', 'epub', 'docx']
        wanted = [f.strip() for f in formats.split(',') if f.strip()]
        unknown = [f for f in wanted if f not in order]
        if unknown:
            raise SystemExit(f'Unbekannte Formate: {", ".join(unknown)} (möglich: {", ".join(order)})')
        fmts = sorted(set(wanted), key=order.index)
        if 'cover' in fmts and not {'pdf', 'pdf_print'} & set(fmts):
            fmts.insert(0, '_pdf')   # Innenteil nur zum Zählen der Seiten (Rückenbreite), nicht ausgeliefert
        interior = None
        for fmt in fmts:
            if fmt == 'cover':   # Umschlag (#68): braucht die Seitenzahl des Innenteils
                pages = pdf_pages(interior)
                target = out / f'{tag}-umschlag.pdf'
                dim = build_cover.build(base, config, pages, target, guides=proof)
                results.append(target)
                print(f'✓ {target} ({target.stat().st_size // 1024} KB) · {build_cover.summary(dim)}')
                for n in dim['notes']:
                    print(f'ⓘ {n}')
                continue
            hidden = fmt == '_pdf'
            kind = 'pdf' if fmt in ('pdf', 'pdf_print', '_pdf') else fmt
            target = (tmp / 'innenteil.pdf') if hidden else \
                out / (f'{tag}-druck.pdf' if fmt == 'pdf_print' else f'{tag}.{fmt}')
            cmd = ['pandoc', '--from', 'markdown+smart', '--lua-filter', str(BOOK / 'merkkasten.lua'),
                   f'--top-level-division={top_level}', '-o', str(target)]
            if ts.get('toc'):
                cmd += ['--toc', f'--toc-depth={int(ts.get("toc_depth", 1))}']
            # Glossar-Verweise (#107): Kennzeichnung; im Druck-PDF ohne Link
            cmd += ['-M', f'gw-glossary-marks={ts.get("glossary_marks", "arrow")}']
            if fmt == 'pdf_print':
                cmd += ['-M', 'gw-print=true']
            m = dict(common_meta)
            if kind == 'pdf':
                lines = '\\\\\n'.join(l.replace('&', '\\&').replace('%', '\\%').replace('#', '\\#') for l in imprint)
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
                layout = layout_tex(ts, meta)
                if layout:
                    extra_header.append(str(write('layout.tex', layout)))
                if series_line and ts.get('title_page'):   # Reihe über dem Titel (KOMA \subject)
                    extra_header.append(str(write('series.tex', '\\subject{' + series_line.replace('&', '\\&') + '}\n')))
                if proof:
                    note = ('\\ifoot*{\\footnotesize\\sffamily\\color{red!65!black}' + footer_label + ' ' + date[8:10] + '.'
                            + date[5:7] + '.' + date[:4] + ' – nicht zur Veröffentlichung}\n')
                    if 'scrlayer-scrpage' in layout:   # eigene Kopf-/Fußzeilen bleiben, nur der Vermerk kommt dazu
                        extra_header.append(str(write('proof.tex', note)))
                    else:
                        extra_header.append(str(write('proof.tex',
                            '\\usepackage{scrlayer-scrpage}\\pagestyle{scrheadings}\\clearpairofpagestyles\n'
                            '\\ofoot*{\\pagemark}' + note)))
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
                    pre = '# Impressum {.unnumbered .unlisted .impressum}\n\n' + '\n\n'.join(imprint) + '\n\n'
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
                    if config.get('cover') and shutil.which('pdftoppm'):   # EPUB-Cover = Vorderseite des Umschlags
                        front = tmp / 'cover-vorne.jpg'
                        build_cover.build(base, build_cover.front_only(config), pdf_pages(interior) if interior else 0,
                                          tmp / 'cover-epub.pdf', front_jpg=front)
                        cmd += ['--epub-cover-image', str(front)]
                elif fmt == 'docx':
                    ref = tmp / 'reference.docx'
                    make_reference_docx(ref, ts)
                    cmd += ['--reference-doc', str(ref)]
            src_path = write(f'book-{fmt}.md', '---\n' + yaml.safe_dump(m, allow_unicode=True, sort_keys=False) + '---\n\n' + src)
            run(cmd + [str(src_path)], cwd=tmp)
            if kind == 'pdf':
                interior = target
            if hidden:
                continue
            results.append(target)
            print(f'✓ {target} ({target.stat().st_size // 1024} KB)')

    return results


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('--edition', type=int)
    ap.add_argument('--proof', action='store_true', help='Probedruck des aktuellen Stands (keine Auflage)')
    ap.add_argument('--manuscript', action='store_true',
                    help='„Manuskript ausgeben“ (#260): PDF des Arbeitsstands, Geplantes in Stichworten')
    ap.add_argument('--chapter', help='mit --manuscript: nur dieses Kapitel (Nummer oder ID)')
    ap.add_argument('--out', default='build')
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--formats', help='Formate, Komma-getrennt; ohne Angabe typesetting.formats (Vorgabe pdf,docx,epub)')
    ap.add_argument('--commit', default='')
    ap.add_argument('--allow-markers', action='store_true')
    args = ap.parse_args(argv[1:])

    if args.chapter and not args.manuscript:
        ap.error('--chapter nur mit --manuscript')
    if args.manuscript:
        args.proof, args.formats = True, 'pdf'
    if not args.proof and args.edition is None:
        ap.error('--edition N, --proof oder --manuscript angeben')
    base, config = load(args.project)
    if args.proof:
        args.edition = config['project'].get('current_edition') or 0
    only = find_chapter(config, str(args.chapter))[0] if args.chapter else None
    parts = book_parts(base, config, proof=args.proof, plan=args.manuscript, only=only)
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
    elif args.proof:
        tag = f'{tag_slug(short)}-probedruck-{args.date}'
        release_name = f'{short} – Probedruck vom {args.date[8:10]}.{args.date[5:7]}.{args.date[:4]}'
        proof_note = (f'Probedruck vom {args.date[8:10]}.{args.date[5:7]}.{args.date[:4]} – nicht zur Veröffentlichung. '
                      'Enthält auch nicht freigegebene Abschnitte; offene Marker sind hervorgehoben.')
    out = Path(args.out).resolve()   # Pandoc läuft im Arbeitsordner, daher absolut
    out.mkdir(parents=True, exist_ok=True)
    disc = ai_disclosure.for_book(config)   # KI-Angabe (#78): (Ort, Wortlaut) oder None
    in_body = disc if disc and disc[0] != 'imprint' else None
    overview = manuscript_overview(base, config, only, args.date, args.commit)[0] + '\n' if args.manuscript else ''
    body, used_images = resolve_images(base, config, overview + book_body(parts, matter, in_body), args.proof)
    # PDF: Widmung vor dem Inhaltsverzeichnis (include-before), daher dort ohne Widmung im Text
    dedication = ''.join(m[2] for m in matter if m[1]['kind'] == 'dedication' and m[2])
    body_pdf = resolve_images(base, config, overview + book_body(parts, [m for m in matter if m[1]['kind'] != 'dedication'],
                                                                 in_body), args.proof)[0]
    for note in image_notes(used_images, ts):
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
        label = 'Manuskript' if args.manuscript else 'Probedruck'
        common_meta['date'] = f'{label} · {shown}'
        meta['edition_text'] = label
        imprint = [release_name, proof_note] + ([f'Commit {args.commit[:7]}'] if args.commit else [])
    imprint += disc_lines
    results = render(base, config, ts, meta, common_meta, imprint, body, body_pdf, dedication, out, tag, args.formats,
                     args.proof, proof_note, args.date, series_line, ser,
                     footer_label='Manuskript' if args.manuscript else 'Probedruck')

    (out / 'edition.yml').write_text(yaml.safe_dump({
        'edition': args.edition, 'name': release_name, 'tag': tag, 'date': args.date,
        'chapters': [p[0] for p in parts], 'matter': [m[1]['id'] for m in matter if m[2]],
        'files': [r.name for r in results]},
        allow_unicode=True, sort_keys=False), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
