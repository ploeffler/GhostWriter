#!/usr/bin/env python3
"""DOCX und PDF zum Gegenlesen mit QR-Kennung (#572, Teil 2).

  python3 scripts/checkout_files.py <buch> build <GW-XXXX> --out <ordner> [--repo owner/name] [--branch <name>]

Baut aus dem Arbeitsstand des ausgecheckten Bereichs (Kapitel, Kapitelfolge oder Buch; wie „Manuskript ausgeben“,
auch nicht abgeschlossene Abschnitte, Geplantes in Stichworten) eine DOCX und daraus per LibreOffice das PDF. Beide
tragen dieselbe Kennung, damit sie Änderungen in Word, einen Ausdruck und ein PDF überstehen:

- Titelblatt „Zum Gegenlesen“ mit Buch, Bereich, Gegenleser, Datum, Stand, Kennung, großem QR-Code und Hinweis.
- Fußzeile jeder Seite: kleiner QR-Code und „GW-7F3A · Kap. 3 · Stand 24.11.2026 · S. n“. Je Kapitel ein eigener
  Word-Abschnitt mit eigener Fußzeile, der QR-Code trägt Kennung und Kapitel (die Seitenzahl steht als Text daneben).
- Überschriften „3.2 Titel“ zeigen die Abschnittsnummer, damit ein Foto mitten aus dem Kapitel zuordenbar ist.
- DOCX maschinenlesbar (für #209/#573): benutzerdefinierte Dokumenteigenschaften `ghostwriter_checkout`,
  `ghostwriter_repo`, `ghostwriter_commit`, `ghostwriter_sections` und je Abschnitt eine Textmarke `gw_<abschnitts-id>`.

QR-Inhalt, kurz und ohne Geheimnis: `GW1|<owner>/<repo>|<buch-branch>|GW-7F3A` auf dem Titelblatt, in der Fußzeile
zusätzlich `|<kapitel-id>`. Werkzeuge: pandoc, python-docx, segno und LibreOffice (nur für das PDF).
"""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import checkout as co  # noqa: E402

CUSTOM_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties'
CUSTOM_TYPE = 'application/vnd.openxmlformats-officedocument.custom-properties+xml'
HINT = ('Änderungen direkt im Text vornehmen (am besten mit Änderungsnachverfolgung) oder als Kommentar; '
        'ausgedruckt gern am Rand. Bitte die Kennung und den QR-Code auf jeder Seite nicht entfernen. '
        'Die Datei danach unverändert zurückschicken.')


def payload(repo, branch, cid, chapter=None):
    return '|'.join(['GW1', repo, branch, cid] + ([chapter] if chapter else []))


def qr_png(text, target, scale=6):
    import segno
    segno.make(text, error='m').save(str(target), kind='png', scale=scale, border=2)
    return Path(target)


def tool(name):
    if not shutil.which(name):
        raise ValueError(f'{name} fehlt (für die Dateien zum Gegenlesen nötig)')
    return name


def scope_chapters(config, entry):
    """Kapitelnummern des Bereichs (alle bei `book`), ohne zurückgeholte Kapitel."""
    back = {c for r in entry.get('zurueckgeholt') or [] for c in r.get('chapters') or []}
    ids = co.chapter_ids(config)
    chosen = ids if entry['bereich'].get('book') else [c for c in entry['bereich'].get('chapters') or [] if c in ids]
    return [i + 1 for i, c in enumerate(ids) if c in chosen and c not in back]


def markdown(base, config, entry, date):
    """(Markdown, [(Kapitelnummer, Kapitel)]) des Bereichs aus dem Arbeitsstand, Überschriften mit Abschnittsnummer."""
    import assemble
    numbers = scope_chapters(config, entry)
    parts, chapters = [], []
    for n in numbers:
        ch = config['structure']['chapters'][n - 1]
        md, _, _ = assemble.chapter_markdown(base, ch, n, proof=True, plan=True, numbered=True)
        parts.append(md)
        chapters.append((n, ch))
    return '\n'.join(parts), chapters


def _field(paragraph, instr):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    run = paragraph.add_run()
    for kind, text in (('begin', None), (None, instr), ('separate', None), (None, '1'), ('end', None)):
        if kind:
            el = OxmlElement('w:fldChar')
            el.set(qn('w:fldCharType'), kind)
        elif text == instr:
            el = OxmlElement('w:instrText')
            el.set(qn('xml:space'), 'preserve')
            el.text = f' {instr} '
        else:
            el = OxmlElement('w:t')
            el.text = text
        run._r.append(el)
    return run


def _footer(section, png, text):
    from docx.shared import Cm, Pt
    section.footer.is_linked_to_previous = False
    footer = section.footer
    for p in footer.paragraphs[1:]:
        p._element.getparent().remove(p._element)
    p = footer.paragraphs[0]
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    p.add_run().add_picture(str(png), width=Cm(1.6))
    run = p.add_run('  ' + text + ' · S. ')
    run.font.size = Pt(8)
    _field(p, 'PAGE').font.size = Pt(8)


def _section_break_after(paragraph, template_sectpr):
    """Word-Abschnittsumbruch (nächste Seite) hinter dem Absatz einfügen; gibt das neue sectPr zurück."""
    import copy
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    ppr = paragraph._p.get_or_add_pPr()
    sect = copy.deepcopy(template_sectpr)
    for ref in sect.findall(qn('w:footerReference')) + sect.findall(qn('w:headerReference')):
        sect.remove(ref)
    kind = sect.find(qn('w:type'))
    if kind is None:
        kind = OxmlElement('w:type')
        sect.insert(0, kind)
    kind.set(qn('w:val'), 'nextPage')
    ppr.append(sect)
    return sect


def _bookmark(paragraph, name, ident):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    start, end = OxmlElement('w:bookmarkStart'), OxmlElement('w:bookmarkEnd')
    start.set(qn('w:id'), str(ident))
    start.set(qn('w:name'), name)
    end.set(qn('w:id'), str(ident))
    paragraph._p.insert(1 if paragraph._p.pPr is not None else 0, start)
    paragraph._p.append(end)


def bookmark_name(section_id):
    return ('gw_' + re.sub(r'[^A-Za-z0-9]', '_', section_id))[:40]


def _custom_properties(doc, props):
    """Benutzerdefinierte Dokumenteigenschaften setzen; eine vorhandene docProps/custom.xml (Pandoc legt eine an) wird ergänzt."""
    from docx.opc.packuri import PackURI
    from docx.opc.part import Part
    from lxml import etree
    ns = 'http://schemas.openxmlformats.org/officeDocument/2006/custom-properties'
    vt = 'http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'
    package = doc.part.package
    existing = next((rel.target_part for rel in package.rels.values() if rel.reltype == CUSTOM_REL), None)
    root = etree.fromstring(existing.blob) if existing is not None else etree.Element(f'{{{ns}}}Properties', nsmap={None: ns, 'vt': vt})
    taken = {int(e.get('pid', 0)) for e in root}
    for k, v in props.items():
        for e in [e for e in root if e.get('name') == k]:
            root.remove(e)
        pid = max(taken | {1}) + 1
        taken.add(pid)
        el = etree.SubElement(root, f'{{{ns}}}property', fmtid='{D5CDD505-2E9C-101B-9397-08002B2CF9AE}', pid=str(pid), name=k)
        etree.SubElement(el, f'{{{vt}}}lpwstr').text = str(v)
    blob = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    if existing is not None:
        existing._blob = blob
    else:
        package.relate_to(Part(PackURI('/docProps/custom.xml'), CUSTOM_TYPE, blob, package), CUSTOM_REL)


def decorate(docx_path, config, entry, chapters, repo, branch, commit, date, tmp):
    """DOCX nachbearbeiten: Titelblatt, Fußzeilen je Kapitel, Textmarken, Dokumenteigenschaften."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt
    cid = entry['id']
    doc = Document(str(docx_path))
    body_sect = doc.sections[-1]._sectPr
    short = (config.get('project') or {}).get('title_short') or (config.get('project') or {}).get('title') or ''
    shown = f'{date[8:10]}.{date[5:7]}.{date[:4]}'
    area = co.scope_text(config, entry)
    first = doc.paragraphs[0]

    # Titelblatt vor dem ersten Absatz
    lines = [('Zum Gegenlesen', 'Title'), (short, 'Subtitle')]
    facts = [('Bereich', area), ('Gegenleser', entry.get('gegenleser', '')), ('Datum', shown),
             ('Stand', commit[:7] or 'unbekannt'), ('Kennung', cid)]
    for text, style in lines:
        p = first.insert_paragraph_before(text, style=style)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for k, v in facts:
        first.insert_paragraph_before(f'{k}: {v}').alignment = WD_ALIGN_PARAGRAPH.CENTER
    big = qr_png(payload(repo, branch, cid), Path(tmp) / 'qr-titel.png', scale=10)
    pic = first.insert_paragraph_before()
    pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic.add_run().add_picture(str(big), width=Cm(5.5))
    cap = first.insert_paragraph_before(cid)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.runs[0].font.size = Pt(14)
    cap.runs[0].bold = True
    last = first.insert_paragraph_before(HINT)
    last.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in last.runs:
        run.font.size = Pt(9)
    title_sect = _section_break_after(last, body_sect)

    # Abschnittsumbruch vor jedem Kapitel (Überschrift 1) außer dem ersten: dort endet das Titelblatt
    heads = [p for p in doc.paragraphs if p.style.name == 'Heading 1']
    by_chapter = list(zip(chapters, heads))
    ends = []       # sectPr, das das Kapitel k beendet (letztes Kapitel: das Rumpf-sectPr)
    for i, (_, head) in enumerate(by_chapter):
        if i:
            ends.append(_section_break_after(head.insert_paragraph_before(), body_sect))
    ends.append(body_sect)
    from docx.section import Section
    ordered = [(title_sect, None, 'Titelblatt')] + [(sect, ch['id'], f'Kap. {n}')
                                                    for sect, ((n, ch), _) in zip(ends, by_chapter)]
    for sect, chapter_id, label in ordered:
        png = qr_png(payload(repo, branch, cid, chapter_id), Path(tmp) / f'qr-{chapter_id or "titel"}.png', scale=5)
        _footer(Section(sect, doc.part), png, f'{cid} · {label} · Stand {shown}')

    # Textmarken je Abschnitt: Überschrift „n.m Titel“
    names, ident = {}, 100
    for n, ch in chapters:
        for si, s in enumerate(ch['sections'], start=1):
            for p in doc.paragraphs:
                if p.style.name.startswith('Heading') and p.text.startswith(f'{n}.{si} '):
                    name = bookmark_name(s['id'])
                    _bookmark(p, name, ident)
                    names[name] = s['id']
                    ident += 1
                    break

    _custom_properties(doc, {'ghostwriter_checkout': cid, 'ghostwriter_repo': repo, 'ghostwriter_branch': branch,
                             'ghostwriter_commit': commit, 'ghostwriter_sections': json.dumps(names, ensure_ascii=False)})
    doc.core_properties.title = f'{short} – Zum Gegenlesen {cid}'
    doc.core_properties.subject = f'{cid} · {area}'
    doc.save(str(docx_path))
    return names


def slug(text):
    t = re.sub(r'[^A-Za-z0-9]+', '-', (text or 'buch').translate(str.maketrans('äöüÄÖÜß', 'aouAOUs'))).strip('-')
    return t or 'buch'


def build(base, config, entry, out, repo, branch, commit='', date=None, pdf=True):
    """DOCX (und PDF) für einen Checkout bauen; gibt die Dateinamen zurück. Fehler: ValueError, es bleibt nichts liegen."""
    tool('pandoc')
    date = date or datetime.date.today().isoformat()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    md, chapters = markdown(base, config, entry, date)
    if not chapters:
        raise ValueError('Der Bereich enthält keine Kapitel')
    short = (config.get('project') or {}).get('title_short') or (config.get('project') or {}).get('title') or 'buch'
    name = f'{slug(short)}-{entry["id"]}'
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = tmp / 'bereich.md'
        src.write_text(md, encoding='utf-8')
        docx = tmp / f'{name}.docx'
        r = subprocess.run(['pandoc', '--from', 'markdown+smart', '-o', str(docx), '--resource-path', str(base), str(src)],
                           capture_output=True, text=True, cwd=str(base))
        if r.returncode:
            raise ValueError('pandoc: ' + (r.stderr.strip()[:300] or 'Fehler'))
        decorate(docx, config, entry, chapters, repo, branch, commit, date, tmp)
        files = [docx]
        if pdf:
            tool('soffice')
            r = subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', str(tmp), str(docx)],
                               capture_output=True, text=True, timeout=300,
                               env={'HOME': str(tmp), 'PATH': '/usr/bin:/bin:/usr/local/bin'})
            if r.returncode or not (tmp / f'{name}.pdf').is_file():
                raise ValueError('LibreOffice: ' + (r.stderr.strip()[:300] or 'PDF nicht erzeugt'))
            files.append(tmp / f'{name}.pdf')
        for f in files:
            shutil.copyfile(f, out / f.name)
    return [f.name for f in files]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('id')
    b.add_argument('--out', required=True)
    b.add_argument('--repo', default='')
    b.add_argument('--branch', default='')
    b.add_argument('--no-pdf', action='store_true')
    args = ap.parse_args(argv)
    from render_view import load
    base, config = load(args.project)
    entry = next((e for e in co.load(base)['checkouts'] if e['id'] == args.id), None)
    if not entry:
        print(f'Checkout {args.id} nicht gefunden', file=sys.stderr)
        return 1
    repo, branch = args.repo or default_repo(base), args.branch or default_branch(base)
    try:
        files = build(base, config, entry, args.out, repo, branch, entry.get('commit', ''), pdf=not args.no_pdf)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    print('\n'.join(f'✓ {Path(args.out) / f}' for f in files))
    return 0


def _git(base, *args):
    r = subprocess.run(['git', '-C', str(base), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ''


def default_repo(base):
    import os
    if os.environ.get('GITHUB_REPOSITORY'):
        return os.environ['GITHUB_REPOSITORY']
    m = re.search(r'github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$', _git(base, 'remote', 'get-url', 'origin'))
    return m.group(1) if m else 'unbekannt'


def default_branch(base):
    import os
    return os.environ.get('GITHUB_REF_NAME') or _git(base, 'rev-parse', '--abbrev-ref', 'HEAD') or 'main'


if __name__ == '__main__':
    sys.exit(main())
