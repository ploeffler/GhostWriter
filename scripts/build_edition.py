#!/usr/bin/env python3
"""Setzt eine Auflage als PDF, DOCX und EPUB (#15).

Aufruf:
  python scripts/build_edition.py <projektordner> --edition N [--out ordner] [--date JJJJ-MM-TT]
                                   [--formats pdf,docx,epub] [--allow-markers]

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
texlive-fonts-recommended), python-docx, pyyaml.
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
from assemble import book_parts, metadata, problems  # noqa: E402
from render_view import load, tag_slug  # noqa: E402

PAGE = {  # Breite, Höhe in mm
    'a5': (148, 210), '12x19': (120, 190), '13.5x21.5': (135, 215), 'a4': (210, 297)}
FONTS = {'serif': ('TeX Gyre Pagella', 'Palatino Linotype'), 'sans': ('TeX Gyre Heros', 'Arial')}


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if r.returncode:
        raise SystemExit(f'Fehler bei {" ".join(map(str, cmd[:3]))} …:\n{r.stderr[-4000:]}')
    return r.stdout


def imprint_markdown(meta, release_name, commit):
    year = meta['date'][:4]
    lines = [f'{meta["title"]}' + (f' – {meta["subtitle"]}' if meta.get('subtitle') else ''),
             f'{meta.get("edition_text", "")}, {meta["date"][8:10]}.{meta["date"][5:7]}.{year}',
             f'© {year} {meta.get("author", "")}'.rstrip()]
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
    for name in ('Normal', 'Body Text', 'First Paragraph', 'Compact'):
        try:
            st = doc.styles[name]
        except KeyError:
            continue
        st.font.name = font
        st.font.size = Pt(float(ts['font_size']))
    from docx.shared import RGBColor
    for name in ('Heading 1', 'Heading 2', 'Heading 3', 'Heading 4', 'Title', 'Subtitle'):
        try:
            doc.styles[name].font.name = font
            doc.styles[name].font.color.rgb = RGBColor(0x22, 0x22, 0x22)
        except KeyError:
            pass
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
    ap.add_argument('--edition', type=int, required=True)
    ap.add_argument('--out', default='build')
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--formats', default='pdf,docx,epub')
    ap.add_argument('--commit', default='')
    ap.add_argument('--allow-markers', action='store_true')
    args = ap.parse_args(argv[1:])

    base, config = load(args.project)
    parts = book_parts(base, config)
    found = problems(parts, config)
    blocking = [p for p in found if not (args.allow_markers and p.startswith('Offener Marker'))]
    if blocking:
        print(f'Auflage {args.edition} kann nicht gebaut werden:')
        for p in blocking:
            print(f'  ✗ {p}')
        return 1

    meta = metadata(config, args.edition, args.date)
    ts = meta['typesetting']
    wf = yaml.safe_load((ROOT / 'workflow.yml').read_text(encoding='utf-8'))['book_releases']
    short = config['project'].get('title_short') or meta['title']
    release_name = wf['name_pattern'].format(title_short=short, edition=args.edition)
    tag = wf['tag_pattern'].format(title_short_slug=tag_slug(short), edition=args.edition)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    body = '\n'.join(p[2] for p in parts)
    imprint = imprint_markdown(meta, release_name, args.commit)
    fonts = FONTS.get(ts['font'], FONTS['serif'])
    w, h = PAGE.get(ts['page_size'], PAGE['a5'])
    months = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
    shown_date = f'{meta.get("edition_text", "")} · {months[int(meta["date"][5:7]) - 1]} {meta["date"][:4]}'.strip(' ·')
    common_meta = {k: meta[k] for k in ('title', 'subtitle', 'author', 'lang') if k in meta}
    common_meta['date'] = shown_date
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
                m.update({'documentclass': 'scrbook',
                          'classoption': [f'paper={w}mm:{h}mm', f'fontsize={ts["font_size"]}pt', 'DIV=calc', 'BCOR=8mm',
                                          'titlepage=' + ('true' if ts.get('title_page') else 'false'), 'open=any',
                                          'parskip=false'],
                          'mainfont': fonts[0], 'sansfont': 'TeX Gyre Heros', 'monofont': 'TeX Gyre Cursor',
                          'linestretch': 1.1, 'colorlinks': False, 'header-includes': '',
                          'include-before': imp})
                cmd += ['--pdf-engine=xelatex', '--include-in-header', str(BOOK / 'header.tex')]
                for h in extra_header:
                    cmd += ['--include-in-header', h]
                src = body
            else:
                pre = ''
                if ts.get('imprint'):
                    pre = '# Impressum {.unnumbered .unlisted .impressum}\n\n' + '\n\n'.join(imprint) + '\n\n'
                src = pre + body
                if fmt == 'epub':
                    cmd += ['--css', str(BOOK / 'epub.css'),
                            '--epub-title-page=' + ('true' if ts.get('title_page') else 'false')]
                    m['description'] = meta.get('description', '')
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
        'chapters': [p[0] for p in parts], 'files': [r.name for r in results]},
        allow_unicode=True, sort_keys=False), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
