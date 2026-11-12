#!/usr/bin/env python3
"""Manuskript als Buch importieren (#124), Teil ohne KI: umwandeln, Gliederung erkennen, Vorschau, anlegen.

Aufruf (im Buch-Branch eines neuen Buchs, noch ohne Kapitel):
  python scripts/import_book.py <buch> convert <datei> [--keep first_edition|30|90|forever]
  python scripts/import_book.py <buch> edit '<json-liste von änderungen>'
  python scripts/import_book.py <buch> outline [--plan] [--json]   KI-Vorschlag für eine Gliederung (nur ohne Gliederung)
  python scripts/import_book.py <buch> apply [--writing-approval]
  python scripts/import_book.py <buch> status [--json]          Stand des Imports (Aufbewahrung des Originals)
  python scripts/import_book.py <buch> expire [--today JJJJ-MM-TT]  Original nach Ablauf entfernen

convert: Original unverändert nach import/original/<datei>; Umwandlung mit Pandoc
(DOCX, ODT, EPUB, HTML, Markdown, Text) bzw. pdftotext (PDF, mit Warnung) nach
import/manuscript.md; Bilder nach import/media/. Danach die Gliederung:
  - Überschriften: die oberste Ebene, die mindestens zweimal vorkommt, sind Kapitel,
    die nächste Abschnitte; eine einzelne Überschrift darüber gilt als Buchtitel.
  - Ohne Überschriften: Zeilen „Kapitel N …“ / „Chapter N …“.
  - Kapitel ohne Abschnittsüberschriften: Abschnitte an Szenentrennern (***, * * *, ⁂),
    sonst ein Abschnitt.
  - Widmung, Vorwort, Prolog, Epilog, Nachwort, Danksagung, Glossar (auch englisch)
    werden Teile von Vor- bzw. Nachspann (#57); kurzer Text vor der ersten
    Überschrift (bis 40 Wörter) als Widmung.
  - Wortzahl je Teil gegen die Umwandlung (verlustfrei), Hinweise zu Tabellen,
    Fußnoten, Bildern und sehr langen Abschnitten (> 4000 Wörter).
Ergebnis: import/proposal.json (Vorschlag) und import/import.yml (Quelle, Format,
Aufbewahrung). Am Buch ändert sich noch nichts.

outline (nur wenn das Dokument keine Gliederung hat, Action „Manuskript
importieren“, step: outline): der Text in nummerierten Absätzen geht an die KI
(`analysis.merge_model`, Schlüssel wie bei scripts/analyze.py). Zurück kommen
nur Anfänge von Kapiteln und Abschnitten (Absatznummer und die ersten Wörter
des Absatzes, wörtlich), je mit Titel und Begründung. Prüfung ohne KI: Der
Anfang muss wörtlich am genannten Absatz stehen, die Reihenfolge stimmen;
ungültige Anfänge fallen weg. Getrennt wird nur an Absatzgrenzen, der Text
bleibt also vollständig. Ergebnis: import/outline.json (Vorschlag, am
Vorschlag der Gliederung ändert sich nichts); Kosten in costs/project.yml.
Übernommen wird mit edit {op: outline, chapters: [{title, start, sections:
[{title, start}]}]} (Absatznummern aus outline.json, ab 1), verworfen mit
{op: discard_outline}. --plan zeigt nur Umfang, Tokens und Kosten.

edit: Änderungen am Vorschlag, je {op, …} (Nummern ab 1): rename_chapter
{chapter, title} · rename_section {chapter, section, title} · split_scenes
{chapter, section} · merge_sections {chapter, section} (mit dem folgenden) ·
merge_chapters {chapter} (mit dem folgenden) · split_chapter {chapter, section}
(neues Kapitel ab diesem Abschnitt) · to_matter {chapter, kind} · to_chapter {part} ·
outline {chapters} (KI-Vorschlag übernehmen, siehe oben) · discard_outline.

apply: legt Kapitel, Abschnitte und Teile an (Status revision; Schreibfreigabe nur
mit --writing-approval, Abschnitts- und Kapitelfreigaben nie), trägt Titel und
Autor ein, wenn sie fehlen, und setzt workflow.current_phase auf writing. Bilder
aus dem Dokument kommen nicht in den Text, sondern als Kandidaten in import.yml
(images, für #54). Der Text der Abschnitte ist der umgewandelte Text des Originals.

Aufbewahrung des Originals (import.yml keep): first_edition (bis zur ersten
Auflage), 30 bzw. 90 (Tage), forever. expire entfernt import/original/ nach
Ablauf (Action „Manuskript importieren“, täglich); die Projektübersicht weist
7 Tage vorher darauf hin.
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from render_view import MATTER, tag_slug  # noqa: E402

FORMATS = {'.docx': 'docx', '.odt': 'odt', '.epub': 'epub', '.html': 'html', '.htm': 'html', '.md': 'markdown',
           '.markdown': 'markdown', '.txt': 'text', '.pdf': 'pdf'}
MATTER_NAMES = {
    'dedication': ['widmung', 'dedication'], 'foreword': ['vorwort', 'geleitwort', 'foreword', 'preface'],
    'prologue': ['prolog', 'prologue'], 'epilogue': ['epilog', 'epilogue'], 'afterword': ['nachwort', 'afterword'],
    'acknowledgments': ['danksagung', 'dank', 'acknowledgments', 'acknowledgements'], 'glossary': ['glossar', 'glossary']}
SCENE = re.compile(r'(?m)^(?:[ \t]*(?:\*[ \t]*\*[ \t]*\*|\\\*[ \t]*\\\*[ \t]*\\\*|⁂|\*{3,}|#)|-{3,}|_{3,})[ \t]*$')
HEADING = re.compile(r'(?m)^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*(?:\{[^}]*\})?[ \t]*$')
CHAPTER_LINE = re.compile(r'(?im)^[ \t]*((?:kapitel|chapter)[ \t]+[\w.]+.*)$')
LONG_WORDS = 4000
NO_STRUCTURE = ('Keine Gliederung erkannt: das Manuskript ist ein Kapitel. Kapitel lassen sich in der Vorschau teilen '
                'oder mit KI vorschlagen.')
# Aufbewahrung des Originals. Seit D21 gilt für neue Importe nur until_deleted; die übrigen
# Werte stehen noch in älteren import.yml und beschreiben frühere Fristen ohne Löschwirkung.
KEEP = {'until_deleted': 'bis zum ausdrücklichen Löschauftrag', 'first_edition': 'bis zur ersten Auflage', '30': '30 Tage', '90': '90 Tage', 'forever': 'dauerhaft'}
PDF_WARNING = ('PDF: Absätze, Hervorhebungen, Fußnoten und Bilder können verloren gehen; Kopf- und Fußzeilen, '
               'Seitenzahlen und Silbentrennung wurden entfernt, so gut es ging. DOCX oder ODT ist zuverlässiger.')


def words(text):
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?', ' ', text or '')
    text = HEADING.sub(' ', text)
    return len(re.findall(r'[\wÄÖÜäöüß]+(?:[-’\'][\wÄÖÜäöüß]+)*', text))


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f'Umwandlung fehlgeschlagen ({" ".join(map(str, cmd[:2]))}): {r.stderr.strip()[-600:]}')
    return r.stdout


# ---------- Umwandeln ----------

def pdf_text(path):
    """pdftotext mit Aufräumen: Seitenzahlen, wiederkehrende Kopf-/Fußzeilen, Silbentrennung, harte Umbrüche."""
    raw = run(['pdftotext', '-enc', 'UTF-8', str(path), '-'])
    pages = [p.split('\n') for p in raw.split('\f')]
    edge = {}
    for p in pages:
        lines = [l.strip() for l in p if l.strip()]
        for l in lines[:2] + lines[-2:]:
            k = re.sub(r'\d+', '#', l)
            edge[k] = edge.get(k, 0) + 1
    repeated = {k for k, n in edge.items() if len(pages) > 3 and n >= max(3, len(pages) * 0.3)}
    out = []
    for p in pages:
        for l in p:
            s = l.strip()
            if re.fullmatch(r'[-–— ]*\d{1,4}[-–— ]*', s) or (s and re.sub(r'\d+', '#', s) in repeated):
                continue
            out.append(l.rstrip())
        out.append('')
    text = '\n'.join(out)
    text = re.sub(r'(\w)-\n[ \t]*([a-zäöüß])', r'\1\2', text)                  # Silbentrennung
    paras = [re.sub(r'\s*\n\s*', ' ', p).strip() for p in re.split(r'\n[ \t]*\n', text)]
    return '\n\n'.join(p for p in paras if p) + '\n'


def convert(base, src, keep=None, today=None):
    """keep ist seit D21 ohne Wirkung (nur noch für ältere Aufrufe angenommen)."""
    base, src = Path(base), Path(src)
    fmt = FORMATS.get(src.suffix.lower())
    if not fmt:
        raise SystemExit(f'{src.name}: Format nicht unterstützt (DOCX, ODT, EPUB, HTML, Markdown, Text, PDF)')
    if keep and keep != 'until_deleted':
        print(f'Hinweis: Aufbewahrung „{keep}“ ist ohne Wirkung; das Original bleibt bis zum ausdrücklichen '
              'Löschauftrag (D21).', file=sys.stderr)
    imp = base / 'import'
    (imp / 'original').mkdir(parents=True, exist_ok=True)
    orig = imp / 'original' / src.name
    if src.resolve() != orig.resolve():
        shutil.copyfile(src, orig)
    meta, warnings = {}, []
    if fmt == 'pdf':
        md = pdf_text(orig)
        warnings.append(PDF_WARNING)
    elif fmt == 'text':
        md = orig.read_text(encoding='utf-8', errors='replace')
    else:
        media = imp / 'media'
        md = run(['pandoc', '--from', {'markdown': 'markdown', 'html': 'html'}.get(fmt, fmt), '--to', 'markdown-smart',
                  '--wrap=none', '--standalone', f'--extract-media={media}', str(orig)])
        m = re.match(r'\A---\n(.*?)\n---\n', md, re.S)
        if m:
            meta = yaml.safe_load(m.group(1)) or {}
            md = md[m.end():]
    md = md.replace(str(imp / 'media') + '/', 'import/media/')
    (imp / 'manuscript.md').write_text(md, encoding='utf-8')
    title = meta.get('title') if isinstance(meta.get('title'), str) else ''
    author = meta.get('author')
    author = ', '.join(author) if isinstance(author, list) else (author or '')
    proposal = detect(md, title, str(author), fmt)
    proposal['warnings'] = warnings + proposal['warnings']
    save_proposal(base, proposal)
    today = today or datetime.date.today()
    info = {'source': f'import/original/{src.name}', 'format': fmt, 'imported_at': today.isoformat(), 'keep': 'until_deleted',
            'words': proposal['stats']['words_original']}
    (imp / 'import.yml').write_text(yaml.safe_dump(info, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return proposal


# ---------- Gliederung ----------

def matter_kind(title):
    t = re.sub(r'[^a-zäöüß ]', '', (title or '').casefold()).strip()
    for kind, names in MATTER_NAMES.items():
        if t in names:
            return kind
    return None


def scenes(text):
    return [p.strip('\n') for p in SCENE.split(text or '')]


def section_from(title, text):
    return {'title': title, 'text': text.strip('\n') + '\n', 'words': words(text), 'scenes': len(scenes(text))}


def detect(md, title='', author='', fmt=''):
    warnings = []
    heads = [(len(m.group(1)), m.group(2).strip(), m.start(), m.end()) for m in HEADING.finditer(md)]
    if not heads:   # Klartext: Zeilen „Kapitel N …“ als Überschriften
        lines = [(1, m.group(1).strip(), m.start(), m.end()) for m in CHAPTER_LINE.finditer(md)]
        if len(lines) >= 2:
            heads = lines
    levels = sorted({h[0] for h in heads})
    chap_level = next((lv for lv in levels if sum(1 for h in heads if h[0] == lv) >= 2), levels[0] if levels else None)
    if chap_level and levels and levels[0] < chap_level:
        tops = [h for h in heads if h[0] < chap_level]
        if len(tops) == 1 and not title:
            title = tops[0][1]
    sec_level = next((lv for lv in levels if chap_level and lv > chap_level), None)
    parts, chapters = [], []
    chap_heads = [h for h in heads if h[0] == chap_level] if chap_level else []
    if not chap_heads:
        warnings.append(NO_STRUCTURE)
        chapters.append({'title': title or 'Kapitel 1', 'sections': [section_from(f'Abschnitt {i}', t) for i, t in
                                                                      enumerate(scenes(md), start=1) if t.strip()] or
                         [section_from('Abschnitt 1', md)]})
    else:
        pre = md[:chap_heads[0][2]]
        pre = HEADING.sub('', pre).strip()
        if pre:
            if words(pre) <= 40:
                parts.append({'kind': 'dedication', 'title': MATTER['dedication'][1], 'text': pre + '\n', 'words': words(pre)})
            else:
                chapters.append({'title': 'Einleitung', 'sections': [section_from('Einleitung', pre)]})
        for i, h in enumerate(chap_heads):
            end = chap_heads[i + 1][2] if i + 1 < len(chap_heads) else len(md)
            body = md[h[3]:end]
            kind = matter_kind(h[1])
            if kind and not any(p['kind'] == kind for p in parts):
                text = HEADING.sub(lambda m: m.group(0) if len(m.group(1)) > chap_level else '', body).strip()
                parts.append({'kind': kind, 'title': h[1], 'text': text + '\n', 'words': words(text),
                              'area': MATTER[kind][0], 'position': 'before' if not chapters else 'after'})
                continue
            ctitle = re.sub(r'(?i)^(kapitel|chapter)\s+\w+[.:]?\s*[-–:]?\s*', '', h[1]) or h[1]
            subs = [x for x in HEADING.finditer(body) if sec_level and len(x.group(1)) == sec_level]
            secs = []
            if subs:
                intro = body[:subs[0].start()].strip()
                if intro:
                    secs.append(section_from(ctitle, intro))
                for j, s in enumerate(subs):
                    e = subs[j + 1].start() if j + 1 < len(subs) else len(body)
                    secs.append(section_from(s.group(2).strip(), body[s.end():e]))
            else:
                sc = [t for t in scenes(body) if t.strip()]
                secs = [section_from(ctitle if len(sc) == 1 else f'{ctitle} ({k})', t) for k, t in enumerate(sc, start=1)] \
                    or [section_from(ctitle, body)]
            chapters.append({'title': ctitle, 'sections': secs})
    # Teile nach dem letzten Kapitel gehören in den Nachspann, auch wenn ihre Art eigentlich vorn steht
    for p in parts:
        p.setdefault('area', MATTER[p['kind']][0])
    tables = len(re.findall(r'(?m)^\|.*\|\s*$\n^\|[-:| ]+\|\s*$', md)) + len(re.findall(r'(?m)^\+[-=+:]+\+\s*\n(?!\|)', md)) // 2 \
        + len(re.findall(r'(?m)^[ \t]+-{3,}(?:[ \t]+-{3,})+[ \t]*$', md))
    notes = len(re.findall(r'(?m)^\[\^[^\]]+\]:', md))
    images = re.findall(r'!\[[^\]]*\]\(([^)\s]+)', md)
    if tables:
        warnings.append(f'{tables} Tabelle(n): als Markdown-Tabelle übernommen, bitte im Probedruck prüfen.')
    if notes:
        warnings.append(f'{notes} Fußnote(n): bleiben als Fußnoten im Text.')
    if images:
        warnings.append(f'{len(images)} Bild(er): nicht im Text, sondern als Kandidaten für Illustrationen (#54).')
    for ci, c in enumerate(chapters, start=1):
        for si, s in enumerate(c['sections'], start=1):
            if s['words'] > LONG_WORDS:
                warnings.append(f'Abschnitt {ci}.{si} ist sehr lang ({s["words"]} Wörter): teilen?'
                                + (f' ({s["scenes"]} Szenen)' if s['scenes'] > 1 else ''))
    p = {'title': title, 'author': author, 'format': fmt, 'parts': parts, 'chapters': chapters, 'warnings': warnings,
         'images': images, 'structure': 'headings' if chap_heads else 'none'}
    p['stats'] = stats(p, md)
    return p


def stats(p, md=None):
    total = sum(x['words'] for x in p['parts']) + sum(s['words'] for c in p['chapters'] for s in c['sections'])
    st = dict(p.get('stats') or {})
    if md is not None:
        st['words_original'] = words(md)
    st.update({'words_proposal': total, 'chapters': len(p['chapters']),
               'sections': sum(len(c['sections']) for c in p['chapters']), 'images': len(p.get('images') or [])})
    st['lossless'] = st['words_original'] == total
    return st


def proposal_path(base):
    return Path(base) / 'import' / 'proposal.json'


def load_proposal(base):
    p = proposal_path(base)
    if not p.is_file():
        raise SystemExit('Es gibt noch keinen Import-Vorschlag (zuerst convert)')
    return json.loads(p.read_text(encoding='utf-8'))


def save_proposal(base, p):
    p['stats'] = stats(p)
    proposal_path(base).parent.mkdir(parents=True, exist_ok=True)
    proposal_path(base).write_text(json.dumps(p, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


# ---------- KI-Vorschlag für die Gliederung ----------

OUTLINE_SYSTEM = """Du bekommst ein Manuskript ohne Gliederung, geteilt in nummerierte Absätze ("[P12] …"). Schlage eine
Gliederung in Kapitel und Abschnitte vor, nur aus dem Text: ein neues Kapitel, wo ein neuer Teil der Handlung bzw. ein
neues Thema beginnt; neue Abschnitte innerhalb eines Kapitels an Szenenwechseln bzw. Unterthemen. Regeln:
- Jedes Kapitel und jeder Abschnitt beginnt an einem Absatz: "start" = Nummer des Absatzes, "quote" = die ersten Wörter
  dieses Absatzes, wörtlich (höchstens 12 Wörter).
- Das erste Kapitel und sein erster Abschnitt beginnen bei Absatz 1. Reihenfolge wie im Text; nichts wird ausgelassen
  oder umgestellt.
- "title": kurzer Titel aus dem Inhalt, ohne "Kapitel N"; Wörter aus dem Text bevorzugen, nichts dazuerfinden.
- "reason": ein Satz, warum hier ein neues Kapitel bzw. ein neuer Abschnitt beginnt.
- Richtwert: Kapitel mit 2000 bis 6000 Wörtern, Abschnitte mit 500 bis 2500 Wörtern; ein kurzes Manuskript darf
  wenige Kapitel haben.
Antworte nur mit JSON: {"chapters": [{"title": "", "start": 1, "quote": "", "reason": "", "sections": [{"title": "",
"start": 1, "quote": "", "reason": ""}]}]}"""
OUTLINE_FULL_CHARS = 600000      # darüber je Absatz nur der Anfang
OUTLINE_HEAD_WORDS = 60


def outline_path(base):
    return Path(base) / 'import' / 'outline.json'


def paragraphs(p):
    """Absätze des Vorschlags in Buchreihenfolge (nur Kapitel, nicht Vor- und Nachspann)."""
    out = []
    for c in p['chapters']:
        for s in c['sections']:
            out += [x.strip('\n') for x in re.split(r'\n[ \t]*\n', s['text']) if x.strip()]
    return out


def para_fingerprint(paras):
    import hashlib
    return hashlib.sha256('\n\n'.join(paras).encode('utf-8')).hexdigest()


def outline_prompt(paras):
    full = sum(len(x) for x in paras) <= OUTLINE_FULL_CHARS
    rows = []
    for i, x in enumerate(paras, start=1):
        t = ' '.join(x.split())
        if not full:
            w = t.split()
            t = ' '.join(w[:OUTLINE_HEAD_WORDS]) + (' …' if len(w) > OUTLINE_HEAD_WORDS else '')
        rows.append(f'[P{i}] ({words(x)} Wörter) {t}')
    return f'{len(paras)} Absätze, {sum(words(x) for x in paras)} Wörter.\n\n' + '\n\n'.join(rows)


def starts_at(paras, n, quote):
    """Steht das Zitat wörtlich am Anfang (erste 40 Wörter) von Absatz n?"""
    import analyze
    if not isinstance(n, int) or not 1 <= n <= len(paras):
        return False
    q = analyze.norm(quote)
    return len(q) >= 3 and q in analyze.norm(' '.join(paras[n - 1].split()[:40]))


def verify_outline(answer, paras):
    """Gliederung ohne KI prüfen: Anfänge wörtlich am genannten Absatz, Reihenfolge aufsteigend; ungültige fallen weg.
    Das erste Kapitel beginnt immer bei Absatz 1, ein Kapitel immer mit einem Abschnitt an seinem Anfang.
    → (kapitel, verworfen)"""
    def num(x):
        try:
            return int(x)
        except (TypeError, ValueError):
            return None
    dropped, chapters = 0, []
    for c in (answer or {}).get('chapters') or []:
        n = num(c.get('start'))
        if not starts_at(paras, n, c.get('quote')) or (chapters and n <= chapters[-1]['start']):
            dropped += 1
            continue
        chapters.append({'title': ' '.join(str(c.get('title') or '').split()), 'start': n, 'quote': c.get('quote', '').strip(),
                         'reason': ' '.join(str(c.get('reason') or '').split()), 'raw_sections': c.get('sections') or []})
    if not chapters:
        return [], dropped
    if chapters[0]['start'] != 1:
        chapters[0]['start'] = 1
        chapters[0]['quote'] = ' '.join(paras[0].split()[:8])
    for k, c in enumerate(chapters):
        end = chapters[k + 1]['start'] if k + 1 < len(chapters) else len(paras) + 1
        secs = []
        for s in c.pop('raw_sections'):
            n = num(s.get('start'))
            if not (c['start'] <= (n or 0) < end) or not starts_at(paras, n, s.get('quote')) or (secs and n <= secs[-1]['start']):
                dropped += 1
                continue
            secs.append({'title': ' '.join(str(s.get('title') or '').split()), 'start': n, 'quote': s.get('quote', '').strip(),
                         'reason': ' '.join(str(s.get('reason') or '').split())})
        if not secs or secs[0]['start'] != c['start']:
            secs.insert(0, {'title': c['title'], 'start': c['start'], 'quote': c['quote'], 'reason': ''})
        for j, s in enumerate(secs):
            e = secs[j + 1]['start'] if j + 1 < len(secs) else end
            s['words'] = sum(words(x) for x in paras[s['start'] - 1:e - 1])
            s['title'] = s['title'] or f'Abschnitt {j + 1}'
        c['title'] = c['title'] or f'Kapitel {k + 1}'
        c['words'] = sum(s['words'] for s in secs)
        c['sections'] = secs
    return chapters, dropped


def outline_plan(base):
    import analyze
    p = load_proposal(base)
    if p.get('structure', 'headings') != 'none' and len(p['chapters']) > 1:
        raise SystemExit('Das Dokument hat schon eine Gliederung; ein KI-Vorschlag ist nur ohne Gliederung vorgesehen.')
    paras = paragraphs(p)
    _, config = analyze.load(base)
    s = analyze.settings(config)
    tin = int(len(outline_prompt(paras)) / analyze.CHARS_PER_TOKEN) + 800
    tout = 300 + 120 * max(1, sum(words(x) for x in paras) // 1500)
    cost = None
    if s.get('price_input_per_mtok') is not None and s.get('price_output_per_mtok') is not None:
        cost = round(tin / 1e6 * float(s['price_input_per_mtok']) + tout / 1e6 * float(s['price_output_per_mtok']), 2)
    return {'paragraphs': len(paras), 'words': sum(words(x) for x in paras), 'input_tokens': tin, 'output_tokens': tout,
            'cost_estimate': cost, 'full_text': sum(len(x) for x in paras) <= OUTLINE_FULL_CHARS}


def outline(base, now=None):
    """KI-Vorschlag für die Gliederung nach import/outline.json; Kosten nach costs/project.yml. → Vorschlag"""
    import analyze
    base = Path(base)
    plan = outline_plan(base)
    p = load_proposal(base)
    paras = paragraphs(p)
    _, config = analyze.load(base)
    s = analyze.settings(config)
    provider, key = analyze.pick_provider(s)
    model = s.get('merge_model') or analyze.PROVIDERS[provider]['merge_model']
    now = now or datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    text, tin, tout = analyze.call_llm(provider, key, model, OUTLINE_SYSTEM, outline_prompt(paras), 'outline')
    chapters, dropped = verify_outline(analyze.parse_json(text), paras)
    old = json.loads(outline_path(base).read_text(encoding='utf-8')) if outline_path(base).is_file() else {}
    run_id = f'outline-{int(old.get("run", "outline-000")[8:]) + 1:03d}'
    entry = analyze.cost_entry(s, provider, model, run_id, tin, tout, now, 1, 'Gliederung')
    entry['note'] = 'Gliederung beim Import (KI-Vorschlag)'
    result = {'run': run_id, 'created_at': now, 'provider': provider, 'model': model, 'paragraphs': len(paras),
              'fingerprint': para_fingerprint(paras), 'chapters': chapters, 'dropped': dropped,
              'input_tokens': tin, 'output_tokens': tout, 'cost': entry['cost_amount'], 'full_text': plan['full_text'],
              'status': 'open' if len(chapters) > 1 or (chapters and len(chapters[0]['sections']) > 1) else 'empty'}
    outline_path(base).write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    cpath = base / 'costs' / 'project.yml'
    cpath.parent.mkdir(exist_ok=True)
    data = (yaml.safe_load(cpath.read_text(encoding='utf-8')) or {}) if cpath.is_file() else {'scope': 'project'}
    data['entries'] = (data.get('entries') or []) + [entry]
    cpath.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')
    return result


def apply_outline(p, base, chapters):
    """Gliederung (vom Benutzer bestätigt, Absatznummern aus outline.json) auf den Vorschlag anwenden; getrennt wird
    nur an Absatzgrenzen, kein Wort geht verloren."""
    o = json.loads(outline_path(base).read_text(encoding='utf-8')) if outline_path(base).is_file() else None
    if not o or o.get('status') != 'open':
        raise SystemExit('Es gibt keinen offenen KI-Vorschlag für die Gliederung (zuerst outline)')
    paras = paragraphs(p)
    if para_fingerprint(paras) != o['fingerprint']:
        raise SystemExit('Die Gliederung wurde seit dem KI-Vorschlag geändert; bitte den Vorschlag neu erstellen.')
    flat = []
    for c in chapters or []:
        secs = c.get('sections') or [{'title': c.get('title'), 'start': c.get('start')}]
        if int(secs[0].get('start') or 0) != int(c.get('start') or 0):
            secs = [{'title': c.get('title'), 'start': c.get('start')}] + list(secs)
        for j, s in enumerate(secs):
            flat.append((j == 0, ' '.join(str(c.get('title') or '').split()), ' '.join(str(s.get('title') or '').split()),
                         int(s.get('start') or 0)))
    starts = [f[3] for f in flat]
    if not flat or starts[0] != 1 or any(b <= a for a, b in zip(starts, starts[1:])) or starts[-1] > len(paras):
        raise SystemExit('Gliederung ungültig: Anfänge aufsteigend ab Absatz 1 angeben')
    new = []
    for k, (first, ctitle, stitle, start) in enumerate(flat):
        end = flat[k + 1][3] if k + 1 < len(flat) else len(paras) + 1
        if first:
            new.append({'title': ctitle or f'Kapitel {len(new) + 1}', 'sections': []})
        sec = section_from(stitle or f'Abschnitt {len(new[-1]["sections"]) + 1}', '\n\n'.join(paras[start - 1:end - 1]))
        new[-1]['sections'].append(sec)
    p['chapters'] = new
    p['structure'] = 'ai'
    p['warnings'] = [w for w in p.get('warnings') or [] if w != NO_STRUCTURE]
    o['status'] = 'applied'
    outline_path(base).write_text(json.dumps(o, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def discard_outline(base):
    if outline_path(base).is_file():
        o = json.loads(outline_path(base).read_text(encoding='utf-8'))
        o['status'] = 'discarded'
        outline_path(base).write_text(json.dumps(o, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def open_outline(base):
    """Offener KI-Vorschlag für die Gliederung oder None."""
    if not outline_path(base).is_file():
        return None
    o = json.loads(outline_path(base).read_text(encoding='utf-8'))
    return o if o.get('status') == 'open' else None


# ---------- Änderungen am Vorschlag ----------

def edit(base, ops):
    p = load_proposal(base)
    ch = p['chapters']
    def c(i):
        if not 1 <= int(i) <= len(ch):
            raise SystemExit(f'Kapitel {i} gibt es im Vorschlag nicht')
        return ch[int(i) - 1]
    def s(i, j):
        secs = c(i)['sections']
        if not 1 <= int(j) <= len(secs):
            raise SystemExit(f'Abschnitt {i}.{j} gibt es im Vorschlag nicht')
        return secs, int(j) - 1
    for op in ops:
        kind = op.get('op')
        if kind == 'rename_chapter':
            c(op['chapter'])['title'] = op['title'].strip()
        elif kind == 'rename_section':
            secs, k = s(op['chapter'], op['section'])
            secs[k]['title'] = op['title'].strip()
        elif kind == 'split_scenes':
            secs, k = s(op['chapter'], op['section'])
            parts = [t for t in scenes(secs[k]['text']) if t.strip()]
            if len(parts) > 1:
                base_title = secs[k]['title']
                secs[k:k + 1] = [section_from(f'{base_title} ({n})', t) for n, t in enumerate(parts, start=1)]
        elif kind == 'merge_sections':
            secs, k = s(op['chapter'], op['section'])
            if k + 1 < len(secs):
                title = re.sub(r' \(\d+\)$', '', secs[k]['title'])
                secs[k:k + 2] = [section_from(title, secs[k]['text'].rstrip('\n') + '\n\n\\* \\* \\*\n\n' + secs[k + 1]['text'])]
        elif kind == 'merge_chapters':
            i = int(op['chapter'])
            if i < len(ch):
                c(i)['sections'] += ch[i]['sections']
                del ch[i]
        elif kind == 'split_chapter':
            secs, k = s(op['chapter'], op['section'])
            if k > 0:
                i = int(op['chapter'])
                ch.insert(i, {'title': op.get('title') or secs[k]['title'], 'sections': secs[k:]})
                del secs[k:]
        elif kind == 'to_matter':
            if op['kind'] not in MATTER or any(x['kind'] == op['kind'] for x in p['parts']):
                raise SystemExit(f'{op["kind"]}: unbekannt oder schon vorhanden')
            i = int(op['chapter'])
            cc = c(i)
            text = '\n\n'.join(x['text'].strip('\n') for x in cc['sections']) + '\n'
            p['parts'].append({'kind': op['kind'], 'title': MATTER[op['kind']][1], 'text': text, 'words': words(text),
                               'area': MATTER[op['kind']][0]})
            del ch[i - 1]
        elif kind == 'to_chapter':
            k = int(op['part']) - 1
            if not 0 <= k < len(p['parts']):
                raise SystemExit(f'Teil {op["part"]} gibt es im Vorschlag nicht')
            part = p['parts'].pop(k)
            sec = section_from(part['title'], part['text'])
            ch.insert(0 if part.get('area') == 'front' else len(ch), {'title': part['title'], 'sections': [sec]})
        elif kind == 'outline':
            apply_outline(p, base, op.get('chapters'))
            ch = p['chapters']
        elif kind == 'discard_outline':
            discard_outline(base)
        else:
            raise SystemExit(f'Unbekannte Änderung: {kind}')
    save_proposal(base, p)
    return p


# ---------- Anlegen ----------

def q(text):
    return yaml.safe_dump(text, allow_unicode=True, default_style='"', width=10**6).splitlines()[0]


def approval_entries(base, ids, by='chat', commit=None):
    """Schreibfreigabe beim Import im Freigabe-Protokoll festhalten (approvals.yml, START.md „Freigaben“)."""
    commit = commit or (subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=base, capture_output=True, text=True).stdout.strip())
    if not re.fullmatch(r'[0-9a-f]{7,40}', commit or ''):
        raise SystemExit('Schreibfreigabe beim Import braucht den bestätigten Stand (Commit); ohne Git --commit angeben')
    p = Path(base) / 'approvals.yml'
    data = (yaml.safe_load(p.read_text(encoding='utf-8')) or {}) if p.is_file() else {}
    at = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    data['entries'] = (data.get('entries') or []) + [
        {'kind': 'writing', 'id': i, 'action': 'granted', 'at': at, 'by': by, 'commit': commit,
         'note': 'beim Import erteilt (alle importierten Abschnitte und Teile)'} for i in ids]
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')


def apply(base, writing_approval=False, by='chat', commit=None):
    base = Path(base)
    import library
    import matter as matter_mod
    p = load_proposal(base)
    cfg_path = base / 'ghostwriter.yml'
    text = cfg_path.read_text(encoding='utf-8')
    cfg = yaml.safe_load(text)
    if (cfg.get('structure') or {}).get('chapters'):
        raise SystemExit('Das Buch hat schon Kapitel; ein Import ist nur in ein neues Buch möglich')
    if not p['chapters']:
        raise SystemExit('Der Vorschlag hat kein Kapitel')
    status = 'revision'
    sec_tpl = (ROOT / 'templates' / 'section.md').read_text(encoding='utf-8')
    entries = []
    for ci, c in enumerate(p['chapters'], start=1):
        cslug = tag_slug(c['title'])[:40].strip('-') or f'kapitel-{ci}'
        cpath = f'chapters/{ci:02d}-{cslug}'
        entry = {'id': f'ch-{ci:02d}-{cslug}', 'title': c['title'], 'path': cpath, 'status': 'in_progress', 'sections': []}
        rows = []
        for si, s in enumerate(c['sections'], start=1):
            sslug = tag_slug(s['title'])[:40].strip('-') or f'abschnitt-{si}'
            sid = f'sec-{ci:02d}-{si:02d}-{sslug}'
            spath = f'{cpath}/sections/{si:02d}-{sslug}.md'
            body = re.sub(r'!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?\n?', '', s['text']).strip()
            doc = (sec_tpl.replace('<STABILE-ID>', sid).replace('"<KAPITEL>.<ABSCHNITT>"', f'"{ci}.{si}"')
                   .replace('"<TITEL>"', q(s['title'])).replace('status: planned', f'status: {status}')
                   .replace('  writing: false', f'  writing: {"true" if writing_approval else "false"}')
                   .replace('# <NUMMER> <TITEL>', f'# {ci}.{si} {s["title"]}')
                   .replace('<Was soll dieser Abschnitt leisten?>', 'Offen.').replace('<Inhaltliche Zusammenfassung.>', 'Offen.')
                   .replace('## Manuskript\n\nNoch nicht begonnen.', f'## Manuskript\n\n{body or "Noch nicht begonnen."}'))
            (base / spath).parent.mkdir(parents=True, exist_ok=True)
            (base / spath).write_text(doc, encoding='utf-8')
            entry['sections'].append({'id': sid, 'title': s['title'], 'path': spath})
            rows.append(f'| {ci}.{si} | {s["title"]} | `{status}` |')
        readme = [f'# Kapitel {ci} – {c["title"]}', '', '## Kurzbeschreibung', '', 'Offen.', '', '## Ziel des Kapitels', '',
                  'Offen.', '', '## Abschnitte', '', '| Nummer | Abschnitt | Status |', '|---|---|---|'] + rows + \
                 ['', '## Kapitelstatus', '', '`in_progress`', '', '## Kapitelzusammenführung', '', 'Noch nicht begonnen.', '']
        (base / cpath / 'README.md').write_text('\n'.join(readme), encoding='utf-8')
        entries.append(entry)
    block = yaml.safe_dump({'chapters': entries}, allow_unicode=True, sort_keys=False, width=10**6)
    block = ''.join('  ' + l + '\n' for l in block.splitlines())
    if not re.search(r'(?m)^  chapters: \[\]\s*$', text):
        raise SystemExit('ghostwriter.yml: structure.chapters: [] nicht gefunden; bitte von Hand eintragen')
    text = re.sub(r'(?m)^  chapters: \[\]\s*\n', lambda m: block, text, count=1)
    proj = cfg.get('project') or {}
    fields = {}
    if p.get('title') and not (proj.get('title') or proj.get('working_title')):
        fields['working_title'] = p['title']
    if p.get('author') and not proj.get('author'):
        fields['author'] = p['author']
    if fields:
        text = library.set_project_fields(text, fields)
    text = re.sub(r'(?m)^(  current_phase: )"?wizard"?', r'\1"writing"', text, count=1)
    cfg_path.write_text(text, encoding='utf-8')
    if (yaml.safe_load(text)['structure']['chapters'] or []) != entries:
        raise SystemExit('ghostwriter.yml ließ sich nicht sicher ändern')
    for part in p['parts']:   # Vor- und Nachspann über matter.py (Reihenfolge, Vorlage)
        item = matter_mod.add(base, part['kind'], part['title'] if part['title'] != MATTER[part['kind']][1] else None)
        mp = base / item['path']
        t = mp.read_text(encoding='utf-8')
        t = re.sub(r'(?m)^status: planned', f'status: {status}', t, count=1)
        t = t.replace('  writing: false', f'  writing: {"true" if writing_approval else "false"}', 1)
        body = re.sub(r'!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?\n?', '', part['text']).strip()
        if part['kind'] == 'glossary':
            body = '\n'.join(re.sub(r'^\s*[-*]?\s*\**([^:*]+?)\**\s*[:–-]\s+', r'- \1: ', l) if l.strip() else l
                             for l in body.splitlines())
        head, _, _ = t.partition('\n## Manuskript\n')
        mp.write_text(head + '\n## Manuskript\n\n' + (body or 'Noch nicht begonnen.') + '\n', encoding='utf-8')
    if writing_approval:
        _, cfg2 = __import__('render_view').load(base)
        ids = [s['id'] for e in entries for s in e['sections']] + \
              [i['id'] for a in ('front_matter', 'back_matter') for i in (cfg2['structure'].get(a) or [])]
        approval_entries(base, ids, by, commit)
    info_p = base / 'import' / 'import.yml'
    info = yaml.safe_load(info_p.read_text(encoding='utf-8')) or {} if info_p.is_file() else {}
    info.update({'applied_at': datetime.date.today().isoformat(), 'chapters': len(entries),
                 'sections': sum(len(e['sections']) for e in entries), 'matter': [x['kind'] for x in p['parts']],
                 'writing_approval': bool(writing_approval), 'images': p.get('images') or []})
    info_p.write_text(yaml.safe_dump(info, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return info


# ---------- Aufbewahrung des Originals ----------

def status(base, today=None):
    """{source, keep, keep_text, expires (Datum|None), due (bool), soon (≤ 7 Tage), removed} oder None."""
    p = Path(base) / 'import' / 'import.yml'
    if not p.is_file():
        return None
    info = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    today = today or datetime.date.today()
    out = {'source': info.get('source'), 'keep': info.get('keep'), 'keep_text': KEEP.get(str(info.get('keep')), ''),
           'removed': bool(info.get('removed_at')), 'expires': None, 'due': False, 'soon': False}
    if out['removed'] or not (Path(base) / str(info.get('source', ''))).is_file():
        out['removed'] = True
        return out
    if info.get('keep_until'):
        exp = datetime.date.fromisoformat(str(info['keep_until']))
        out.update({'expires': exp.isoformat(), 'due': today >= exp, 'soon': 0 <= (exp - today).days <= 7})
    elif info.get('keep') == 'first_edition':
        cfg = yaml.safe_load((Path(base) / 'ghostwriter.yml').read_text(encoding='utf-8')) or {}
        out['due'] = bool((cfg.get('project') or {}).get('current_edition'))
    return out


def expire(base, today=None, *, confirmed=False):
    """Entfernt das Original nur auf ausdrücklichen Löschauftrag (D21).

    Der Aufruf darf erst nach Benutzerauftrag mit confirmed=True erfolgen; dann
    ist eine Frist weder nötig noch hinderlich. Fristen allein löschen nichts.
    Historische Aufbewahrungsangaben bleiben nachvollziehbar.
    """
    if not confirmed:
        return False
    st = status(base, today)
    if not st or st['removed']:
        return False
    base = Path(base)
    original = base / 'import' / 'original'
    if (base / 'import').is_symlink() or original.is_symlink():
        raise ValueError('Originalordner darf kein symbolischer Link sein')
    shutil.rmtree(original)
    p = base / 'import' / 'import.yml'
    info = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    info['removed_at'] = (today or datetime.date.today()).isoformat()
    p.write_text(yaml.safe_dump(info, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return True


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['convert', 'edit', 'outline', 'apply', 'status', 'expire'])
    ap.add_argument('--plan', action='store_true', help='bei outline: nur Umfang, Tokens und Kosten')
    ap.add_argument('args', nargs='*')
    ap.add_argument('--keep', help='veraltet, ohne Wirkung (D21): das Original bleibt bis zum Löschauftrag')
    ap.add_argument('--writing-approval', action='store_true')
    ap.add_argument('--by', default='chat', help='bei apply --writing-approval: GitHub-Login (sonst chat)')
    ap.add_argument('--commit', help='bei apply --writing-approval: bestätigter Stand (sonst HEAD)')
    ap.add_argument('--today')
    ap.add_argument('--confirmed', action='store_true', help='bei expire: ausdrücklichen Löschauftrag bestätigen')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv[1:])
    base = Path(a.project)
    today = datetime.date.fromisoformat(a.today) if a.today else None
    if a.cmd == 'convert':
        if not a.args:
            ap.error('convert braucht die Datei')
        p = convert(base, a.args[0], a.keep, today)
        st = p['stats']
        print(f'✓ Vorschlag: {st["chapters"]} Kapitel, {st["sections"]} Abschnitte, {len(p["parts"])} Teile von Vor- und '
              f'Nachspann · {st["words_proposal"]} von {st["words_original"]} Wörtern'
              + (' (vollständig)' if st['lossless'] else ' ⚠️ Abweichung'))
        for w in p['warnings']:
            print(f'ⓘ {w}')
        return 0
    if a.cmd == 'edit':
        if not a.args:
            ap.error('edit braucht die Änderungen als JSON')
        p = edit(base, json.loads(a.args[0]))
        print(f'✓ Vorschlag geändert: {p["stats"]["chapters"]} Kapitel, {p["stats"]["sections"]} Abschnitte')
        return 0
    if a.cmd == 'outline':
        if a.plan:
            pl = outline_plan(base)
            if a.json:
                print(json.dumps(pl, ensure_ascii=False))
                return 0
            cost = (f', geschätzt {pl["cost_estimate"]:.2f} €'.replace('.', ',')) if pl['cost_estimate'] is not None else ', Kosten ohne Preisangabe nicht schätzbar'
            print(f'Gliederung mit KI: {pl["paragraphs"]} Absätze, {pl["words"]} Wörter · etwa {pl["input_tokens"]} Tokens '
                  f'Eingabe, {pl["output_tokens"]} Ausgabe{cost}' + ('' if pl['full_text'] else ' · sehr lang: je Absatz nur der Anfang'))
            return 0
        o = outline(base)
        n = sum(len(c['sections']) for c in o['chapters'])
        print(f'✓ KI-Vorschlag für die Gliederung: {len(o["chapters"])} Kapitel, {n} Abschnitte · {o["dropped"]} Anfänge ohne '
              f'wörtliche Fundstelle verworfen' if o['status'] == 'open' else '✓ Die KI hat keine brauchbare Gliederung gefunden')
        print('Commit-Nachricht: Import: KI-Vorschlag für die Gliederung')
        return 0
    if a.cmd == 'apply':
        info = apply(base, a.writing_approval, a.by, a.commit)
        print(f'✓ Importiert: {info["chapters"]} Kapitel, {info["sections"]} Abschnitte'
              + (f', {", ".join(MATTER[k][1] for k in info["matter"])}' if info['matter'] else '')
              + (' · Schreibfreigabe erteilt' if info['writing_approval'] else ''))
        print('Commit-Nachricht: Manuskript importiert')
        return 0
    if a.cmd == 'status':
        st = status(base, today)
        print(json.dumps(st, ensure_ascii=False) if a.json else (st and json.dumps(st, ensure_ascii=False)) or 'kein Import')
        return 0
    print('✓ Original entfernt (ausdrücklicher Auftrag)' if expire(base, today, confirmed=a.confirmed) else 'nichts zu entfernen')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
