#!/usr/bin/env python3
"""Setzt eine Auflage als PDF, DOCX und EPUB (#15).

Aufruf:
  python scripts/build_edition.py <projektordner> --edition N [--out ordner] [--date JJJJ-MM-TT]
                                   [--formats pdf,docx,epub] [--allow-markers]
  python scripts/build_edition.py <projektordner> --proof [--out ordner] [--formats pdf]

--proof baut einen Probedruck des aktuellen Stands: alle Kapitel und Abschnitte,
auch nicht freigegebene (mit Vermerk „Stand: Entwurf, nicht freigegeben“),
offene Marker farbig hervorgehoben, in der Fußzeile bzw. vorn der Hinweis
„Probedruck – nicht zur Veröffentlichung“. Kein Tag, kein Release; die Action
„Probedruck“ stellt die Dateien als Download bereit.

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
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / 'templates' / 'book'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from assemble import book_body, book_parts, matter_notes, matter_parts, metadata, problems  # noqa: E402
from render_view import load, tag_slug  # noqa: E402
import ai_disclosure  # noqa: E402

PAGE = {  # Breite, Höhe in mm
    'a5': (148, 210), '12x19': (120, 190), '13.5x21.5': (135, 215), 'a4': (210, 297)}
# Schrift → (PDF: TeX-Gyre-Schrift, DOCX: verbreitete Entsprechung, EPUB: Familie); nur freie Schriften (#68)
FONTS = {'serif': ('TeX Gyre Pagella', 'Palatino Linotype', 'serif'), 'sans': ('TeX Gyre Heros', 'Arial', 'sans-serif'),
         'pagella': ('TeX Gyre Pagella', 'Palatino Linotype', 'serif'), 'termes': ('TeX Gyre Termes', 'Times New Roman', 'serif'),
         'bonum': ('TeX Gyre Bonum', 'Bookman Old Style', 'serif'), 'schola': ('TeX Gyre Schola', 'Century Schoolbook', 'serif'),
         'heros': ('TeX Gyre Heros', 'Arial', 'sans-serif'), 'adventor': ('TeX Gyre Adventor', 'Century Gothic', 'sans-serif')}
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


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('--edition', type=int)
    ap.add_argument('--proof', action='store_true', help='Probedruck des aktuellen Stands (keine Auflage)')
    ap.add_argument('--out', default='build')
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--formats', help='Formate, Komma-getrennt; ohne Angabe typesetting.formats (Vorgabe pdf,docx,epub)')
    ap.add_argument('--commit', default='')
    ap.add_argument('--allow-markers', action='store_true')
    args = ap.parse_args(argv[1:])

    if not args.proof and args.edition is None:
        ap.error('--edition N oder --proof angeben')
    base, config = load(args.project)
    if args.proof:
        args.edition = config['project'].get('current_edition') or 0
    parts = book_parts(base, config, proof=args.proof)
    matter = matter_parts(base, config, proof=args.proof)
    found = [] if args.proof else problems(parts, config, matter)
    blocking = [p for p in found if not (args.allow_markers and p.startswith('Offener Marker'))]
    if args.proof and not parts:
        print('Probedruck: Das Buch hat noch keine Kapitel.')
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
    if args.proof:
        tag = f'{tag_slug(short)}-probedruck-{args.date}'
        release_name = f'{short} – Probedruck vom {args.date[8:10]}.{args.date[5:7]}.{args.date[:4]}'
        proof_note = (f'Probedruck vom {args.date[8:10]}.{args.date[5:7]}.{args.date[:4]} – nicht zur Veröffentlichung. '
                      'Enthält auch nicht freigegebene Abschnitte; offene Marker sind hervorgehoben.')
    out = Path(args.out).resolve()   # Pandoc läuft im Arbeitsordner, daher absolut
    out.mkdir(parents=True, exist_ok=True)
    disc = ai_disclosure.for_book(config)   # KI-Angabe (#78): (Ort, Wortlaut) oder None
    in_body = disc if disc and disc[0] != 'imprint' else None
    body = book_body(parts, matter, in_body)
    # PDF: Widmung vor dem Inhaltsverzeichnis (include-before), daher dort ohne Widmung im Text
    dedication = ''.join(m[2] for m in matter if m[1]['kind'] == 'dedication' and m[2])
    body_pdf = book_body(parts, [m for m in matter if m[1]['kind'] != 'dedication'], in_body)
    imprint = imprint_markdown(meta, release_name, args.commit, config.get('publication'))
    disc_lines = [re.sub(r'^\s*[-*]\s+', '– ', line) for line in disc[1].splitlines() if line.strip()] \
        if disc and disc[0] == 'imprint' else []
    fonts = FONTS.get(ts['font'], FONTS['serif'])
    w, h = PAGE.get(ts['page_size'], PAGE['a5'])
    months = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
    shown_date = f'{meta.get("edition_text", "")} · {months[int(meta["date"][5:7]) - 1]} {meta["date"][:4]}'.strip(' ·')
    common_meta = {k: meta[k] for k in ('title', 'subtitle', 'author', 'lang') if k in meta}
    common_meta['date'] = shown_date
    if args.proof:
        common_meta['date'] = f'Probedruck · {args.date[8:10]}.{args.date[5:7]}.{args.date[:4]}'
        meta['edition_text'] = 'Probedruck'
        imprint = [release_name, proof_note] + ([f'Commit {args.commit[:7]}'] if args.commit else [])
    imprint += disc_lines
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        def write(name, text):
            (tmp / name).write_text(text, encoding='utf-8')
            return tmp / name

        for fmt in [f.strip() for f in args.formats.split(',') if f.strip()]:
            target = out / f'{tag}.{fmt}'
            cmd = ['pandoc', '--from', 'markdown+smart', '--lua-filter', str(BOOK / 'merkkasten.lua'),
                   '--top-level-division=chapter', '-o', str(target)]
            if ts.get('toc'):
                cmd += ['--toc', f'--toc-depth={int(ts.get("toc_depth", 1))}']
            m = dict(common_meta)
            if fmt == 'pdf':
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
                if args.proof:
                    note = ('\\ifoot*{\\footnotesize\\sffamily\\color{red!65!black}Probedruck ' + args.date[8:10] + '.'
                            + args.date[5:7] + '.' + args.date[:4] + ' – nicht zur Veröffentlichung}\n')
                    if 'scrlayer-scrpage' in layout:   # eigene Kopf-/Fußzeilen bleiben, nur der Vermerk kommt dazu
                        extra_header.append(str(write('proof.tex', note)))
                    else:
                        extra_header.append(str(write('proof.tex',
                            '\\usepackage{scrlayer-scrpage}\\pagestyle{scrheadings}\\clearpairofpagestyles\n'
                            '\\ofoot*{\\pagemark}' + note)))
                for h in extra_header:
                    cmd += ['--include-in-header', h]
                src = body_pdf
            else:
                pre = ''
                if ts.get('imprint'):
                    pre = '# Impressum {.unnumbered .unlisted .impressum}\n\n' + '\n\n'.join(imprint) + '\n\n'
                if args.proof:
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
                    isbn = (config.get('publication') or {}).get('isbn_ebook')
                    if isbn:
                        m['identifier'] = [{'scheme': 'ISBN-13', 'text': 'urn:isbn:' + re.sub(r'[^0-9Xx]', '', isbn)}]
                elif fmt == 'docx':
                    ref = tmp / 'reference.docx'
                    make_reference_docx(ref, ts)
                    cmd += ['--reference-doc', str(ref)]
            src_path = write(f'book-{fmt}.md', '---\n' + yaml.safe_dump(m, allow_unicode=True, sort_keys=False) + '---\n\n' + src)
            run(cmd + [str(src_path)], cwd=tmp)
            results.append(target)
            print(f'✓ {target} ({target.stat().st_size // 1024} KB)')

    (out / 'edition.yml').write_text(yaml.safe_dump({
        'edition': args.edition, 'name': release_name, 'tag': tag, 'date': args.date,
        'chapters': [p[0] for p in parts], 'matter': [m[1]['id'] for m in matter if m[2]],
        'files': [r.name for r in results]},
        allow_unicode=True, sort_keys=False), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
