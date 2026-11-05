#!/usr/bin/env python3
"""Fügt freigegebene Abschnitte zu Kapiteln und zum Buch zusammen (#14).

Aufruf:
  python scripts/assemble.py <projektordner> chapter <nummer|kapitel-id> [-o datei.md]
  python scripts/assemble.py <projektordner> book [-o datei.md] [--edition N] [--date JJJJ-MM-TT]
  python scripts/assemble.py <projektordner> check [--edition N]

chapter  Ein Kapitel aus seinen freigegebenen Abschnitten (status approved), in
         der Reihenfolge aus ghostwriter.yml. Nicht freigegebene Abschnitte
         werden ausgelassen und gemeldet.
book     Das Buch für eine Auflage: nur freigegebene Kapitel (Kapitelstatus
         approved), darin nur freigegebene Abschnitte, dazu die Quellen je
         Kapitel. Vorn ein YAML-Block mit den Angaben für den Buchsatz
         (Titel, Autor, Auflage, typesetting aus ghostwriter.yml).
check    Prüft, ob eine Auflage gebaut werden kann: mindestens ein freigegebenes
         Kapitel und keine offenen Marker ([QUELLE PRÜFEN …] usw.) im
         freigegebenen Text. Exit-Code 1 mit Liste der Gründe, sonst 0.
         Nicht freigegebene Teile von Vor- und Nachspann werden als Hinweis
         genannt (ⓘ), verhindern die Auflage aber nicht; sie fehlen darin.

Was ins Buch kommt: je Kapitel Titel, Untertitel (erste kursive Zeile der
Kapitel-README), der Text unter „## Manuskript“ jeder freigegebenen
Abschnittsdatei mit dem Abschnittstitel als Überschrift, und der Abschnitt
„## Quellen“ der Kapitel-README. Nicht ins Buch kommen „Vorspann“,
„Kurzbeschreibung“, „Ziel“, „Prüfliste“ und alle Arbeitsdateien (Läufe,
Kosten). Die Ausgabe ist Markdown für Pandoc (scripts/build_edition.py).

Vor- und Nachspann (#57, #58, structure.front_matter/back_matter): nur freigegebene
Teile, der Text unter „## Manuskript“ der Datei in matter/. Vorwort und Nachwort
enden mit Verfasser und Ort/Datum, wenn im Kopf angegeben (byline, place_date;
Block `::: signatur`, rechtsbündig). Das Glossar wird zur Beschreibungsliste,
Einträge `- Begriff: Erklärung` alphabetisch nach DIN 5007-1 (ä wie a); ein
doppelter Begriff verhindert die Auflage. Verweise im Text (#107) – `[Begriff]{.glossar}`
bzw. `[Beugungsform]{.glossar term="Begriff"}` – werden zu Links auf den Eintrag
(Klasse glossar); ohne Glossar in der Ausgabe bleibt nur der Text, ein Begriff
ohne Eintrag verhindert die Auflage.

Illustrationen (#54): `![](bild:img-…)` wird zum Bild mit der Bildunterschrift
aus der Beschreibung (images/…/img-….yml), volle Satzbreite. In eine Auflage
kommen nur freigegebene Bilder; ein fehlendes oder nicht freigegebenes Bild in
freigegebenem Text verhindert sie. Der Probedruck zeigt alle mit Vermerk. Widmung als Block
`::: widmung` mit verborgener Überschrift (Klasse dedication, nicht im
Inhaltsverzeichnis); Prolog, Epilog und Danksagung als unnummerierte Kapitel mit
der Art als Klasse und als EPUB-Rolle (epub:type prologue, epilogue,
acknowledgments).
Vorspann vor Kapitel 1, Nachspann nach dem letzten Kapitel.

KI-Angabe (#78, ai_disclosure, scripts/ai_disclosure.py): der bestätigte Wortlaut
am Ende von Vorwort bzw. Nachwort (Block `::: ki-angabe`) oder als eigene,
unnummerierte Seite „Hinweis zur KI-Nutzung“ ganz am Ende; im Impressum setzt
ihn scripts/build_edition.py. Ist eine Angabe gewählt, aber ihr Wortlaut nicht
bestätigt oder ihr Ort nicht vorhanden, verhindert das die Auflage.

Dieses Skript läuft nur in GitHub Actions oder lokal; den zusammengeführten
Text gibt der Assistent nie im Chat aus (START.md, „Kein ganzes Buch im Chat“).
"""
import argparse
import datetime
import hashlib
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_disclosure  # noqa: E402
from render_view import (GLOSSARY_REF, MARKER_TEXT, MATTER, MATTER_SIGNED, TYPESETTING_DEFAULT,  # noqa: E402
                         german_key, glossary_anchor, glossary_entries, glossary_ref_term, load, matter_items,
                         section_file)


def readme_parts(base, chapter):
    path = base / chapter['path'] / 'README.md'
    text = path.read_text(encoding='utf-8') if path.is_file() else ''
    sub = re.search(r'(?m)^\*([^*].*)\*$', text)
    sources = re.search(r'(?ms)^## Quellen\n(.*?)(?=^## |\Z)', text)
    return (sub.group(1).strip() if sub else ''), (sources.group(1).strip() if sources else '')


def shift_headings(text, top):
    """Überschriften im Manuskript so verschieben, dass die oberste Ebene `top` ist
    (unter der Abschnittsüberschrift ##)."""
    levels = [len(m.group(1)) for m in re.finditer(r'(?m)^(#{1,6})\s', text)]
    if not levels:
        return text
    by = top - min(levels)
    def sub(m):
        level = max(1, min(len(m.group(1)) + by, 6))
        return '#' * level + m.group(2)
    return re.sub(r'(?m)^(#{1,6})(\s)', sub, text)


STATUS_DE = {'planned': 'geplant', 'research': 'Recherche', 'brainstorming': 'Ideensammlung',
             'ready_to_write': 'bereit zum Schreiben', 'writing': 'Entwurf', 'revision': 'Überarbeitung',
             'fact_check': 'Faktencheck', 'ready_for_approval': 'bereit zur Freigabe', 'approved': 'freigegeben'}


def latest_approval(base, kind, entity_id):
    """Letzter append-only Freigabeeintrag für eine Entität."""
    path = base / 'approvals.yml'
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    for entry in reversed(data.get('entries') or []):
        if entry.get('kind') == kind and entry.get('id') == entity_id:
            return entry
    return None


def mark_markers(text):
    """Probedruck: Marker als Pandoc-Span [ … ]{.gwmarker}, damit sie hervorgehoben werden."""
    return MARKER_TEXT.sub(lambda m: '[' + m.group(0).replace('[', '\\[').replace(']', '\\]') + ']{.gwmarker}', text)


def chapter_markdown(base, chapter, number, proof=False):
    """(Markdown, ausgelassene Abschnitte, Marker) eines Kapitels.
    proof=True (Probedruck): auch nicht freigegebene Abschnitte, mit Statusvermerk und hervorgehobenen Markern."""
    subtitle, sources = readme_parts(base, chapter)
    out = [f'# {chapter["title"]}', '']
    if subtitle:
        out += [f'*{subtitle}*', '']
    skipped, markers = [], []
    for si, s in enumerate(chapter['sections'], start=1):
        head, _, _, manuscript = section_file(base, s)
        approval = head.get('approvals') or {}
        digest = hashlib.sha256(manuscript.encode('utf-8')).hexdigest()
        record = latest_approval(base, 'section', s['id'])
        approved = (head.get('status') == 'approved'
                    and approval.get('section') is True
                    and approval.get('section_content_sha256') == digest
                    and record is not None
                    and record.get('action') == 'granted'
                    and record.get('content_sha256') == digest)
        if not approved:
            reason = ('Freigabe fehlt oder Manuskript seit Freigabe geändert'
                      if head.get('status') == 'approved' else str(head.get('status')))
            skipped.append(f'{number}.{si} {s["title"]} ({reason})')
            if not proof:
                continue
        text = shift_headings(manuscript.strip(), 3)
        if proof:
            text = mark_markers(text) or '*(noch kein Text)*'
            note = '' if approved else \
                (f'[Stand: Freigabe fehlt oder Manuskript geändert, nicht freigegeben]{{.gwstatus}}\n\n'
                 if head.get('status') == 'approved' else
                 f'[Stand: {STATUS_DE.get(head.get("status"), head.get("status"))}, nicht freigegeben]{{.gwstatus}}\n\n')
            text = note + text
        out += [f'## {s["title"]}', '', text, '']
        markers += [(f'{number}.{si}', m.group(0)) for m in MARKER_TEXT.finditer(manuscript)]
    if sources:
        clean = re.sub(r'(?m)^Status aller Einträge:.*\n?', '', sources).strip()
        if clean:
            out += ['## Quellen {.unnumbered .sources}', '', mark_markers(clean) if proof else clean, '']
            markers += [(f'{number} Quellen', m.group(0)) for m in MARKER_TEXT.finditer(clean)]
    return '\n'.join(out).rstrip() + '\n', skipped, markers


def series_glossary_extra(base, config, entries):
    """Begriffe der Serie (#116), die im Buch verwiesen werden ([…]{.glossar}), aber nicht im Glossar des Bandes
    stehen: gelten per Verweis und kommen mit der Erklärung der Serie ins Glossar."""
    ser = (config or {}).get('_series')
    if not ser:
        return []
    import series
    terms = series.glossary(base, ser['id'])
    if not terms:
        return []
    have = {t.casefold() for t, _ in entries}
    refs = set()
    paths = [s['path'] for ch in config['structure']['chapters'] for s in ch['sections']] + [i['path'] for _, i in matter_items(config)]
    for p in paths:
        if (base / p).is_file():
            refs |= {glossary_ref_term(m).casefold() for m in GLOSSARY_REF.finditer((base / p).read_text(encoding='utf-8'))}
    return [(x['term'], x['text']) for x in terms if x['term'].casefold() in refs and x['term'].casefold() not in have]


def matter_markdown(base, item, proof=False, config=None):
    """(Markdown, freigegeben, Marker) eines Teils von Vor- oder Nachspann (#57).
    Nicht freigegeben: leeres Markdown, außer im Probedruck (mit Statusvermerk)."""
    head, _, _, manuscript = section_file(base, item)
    approved = head.get('status') == 'approved'
    if not approved and not proof:
        return '', False, []
    text = manuscript.strip()
    if text == 'Noch nicht begonnen.':
        text = ''
    markers = [(item['title'], m.group(0)) for m in MARKER_TEXT.finditer(text)]
    kind = item['kind']
    if kind == 'glossary':   # Einträge alphabetisch (DIN 5007-1) als Beschreibungsliste
        intro, entries = glossary_entries(text)
        entries = list(entries) + series_glossary_extra(base, config, entries)
        dl = '\n'.join(f'[{term}]{{#{glossary_anchor(term)}}}\n:   {expl}\n'   # Anker für Verweise (#107)
                       for term, expl in sorted(entries, key=lambda e: german_key(e[0])))
        text = '\n\n'.join(x for x in (shift_headings(intro, 2), dl) if x)
    else:
        text = shift_headings(text, 2)
    if kind in MATTER_SIGNED and (head.get('byline') or head.get('place_date')):
        sign = [x.strip() for x in (head.get('byline'), head.get('place_date')) if x and x.strip()]
        text += '\n\n::: signatur\n' + '\n'.join(f'| {x}' for x in sign) + '\n:::'
    if proof:
        text = mark_markers(text) or '*(noch kein Text)*'
        if not approved:
            text = f'[Stand: {STATUS_DE.get(head.get("status"), head.get("status"))}, nicht freigegeben]{{.gwstatus}}\n\n' + text
    if kind == 'dedication':
        md = f'# {item["title"]} {{.unnumbered .unlisted .dedication epub:type=dedication}}\n\n::: widmung\n{text}\n:::\n'
    else:
        md = f'# {item["title"]} {{.unnumbered .{kind} epub:type={kind}}}\n\n{text}\n'
    return md, approved, markers


def matter_parts(base, config, proof=False):
    """Vor- und Nachspann in Buchreihenfolge: [(bereich, eintrag, markdown, freigegeben, marker)].
    Ohne proof fehlen nicht freigegebene Teile im Markdown (leer), stehen aber in der Liste."""
    return [(area, item, *matter_markdown(base, item, proof, config)) for area, item in matter_items(config)]


def with_disclosure(md, text):
    """KI-Angabe (#78) ans Ende eines Teils, vor Verfasser und Ort/Datum."""
    block = f'::: ki-angabe\n{text}\n:::\n'
    if '\n::: signatur\n' in md:
        head, _, tail = md.partition('\n::: signatur\n')
        return f'{head.rstrip()}\n\n{block}\n::: signatur\n{tail}'
    return md.rstrip('\n') + '\n\n' + block


def book_body(parts, matter, disclosure=None):
    """Markdown des Buchs: Vorspann, Kapitel, Nachspann; disclosure = (Ort, Wortlaut) der KI-Angabe
    (#78) für Vorwort, Nachwort oder eigene Seite; das Impressum setzt scripts/build_edition.py."""
    place, text = disclosure or (None, None)
    def md(m):
        return with_disclosure(m[2], text) if place == m[1]['kind'] else m[2]
    front = [md(m) for m in matter if m[0] == 'front' and m[2]]
    back = [md(m) for m in matter if m[0] == 'back' and m[2]]
    if place == 'page':
        back.append(f'# {ai_disclosure.PAGE_TITLE} {{.unnumbered .ki-angabe-seite}}\n\n{text}\n')
    terms = glossary_terms(matter)
    return link_glossary('\n'.join(front + [p[2] for p in parts] + back), terms)


def matter_notes(matter):
    """Hinweise (keine Hinderungsgründe): nicht freigegebene Teile fehlen in der Auflage."""
    return [f'{item["title"]} ist nicht freigegeben und fehlt in der Auflage.'
            for _, item, _, approved, _ in matter if not approved]


def find_chapter(config, key):
    chapters = config['structure']['chapters']
    if key.isdigit():
        n = int(key)
        return n, chapters[n - 1]
    for i, ch in enumerate(chapters, start=1):
        if ch['id'] == key:
            return i, ch
    raise SystemExit(f'Kapitel {key} nicht gefunden')


def book_parts(base, config, proof=False):
    """Freigegebene Kapitel: [(nummer, kapitel, markdown, ausgelassen, marker)].
    proof=True: alle Kapitel und Abschnitte (Probedruck)."""
    parts = []
    for i, ch in enumerate(config['structure']['chapters'], start=1):
        chapter_approval = latest_approval(base, 'chapter', ch['id'])
        chapter_approved = (ch.get('status') == 'approved'
                            and chapter_approval is not None
                            and chapter_approval.get('action') == 'granted')
        if not chapter_approved and not proof:
            continue
        md, skipped, markers = chapter_markdown(base, ch, i, proof)
        parts.append((i, ch, md, skipped, markers))
    return parts


def metadata(config, edition, date):
    p = config['project']
    ts = dict(TYPESETTING_DEFAULT)
    ts.update(config.get('typesetting') or {})
    title = p.get('title') or p.get('working_title') or 'Ohne Titel'
    meta = {'title': title, 'subtitle': p.get('subtitle') or '', 'author': p.get('author') or '',
            'lang': p.get('language') or 'de', 'date': date, 'edition': edition,
            'edition_text': f'{edition}. Auflage' if edition else '',
            'description': p.get('description_short') or '', 'typesetting': ts}
    return {k: v for k, v in meta.items() if v not in ('', None)}


def problems(parts, config, matter=(), base=None):
    out = []
    pr = config['project']
    if not (pr.get('title_short') or pr.get('title') or pr.get('working_title')):
        out.append('Das Buch hat noch keinen Titel; Name und Tag der Auflage entstehen aus dem (Kurz-)Titel.')
    if not parts:
        n = len(config['structure']['chapters'])
        out.append(f'Kein Kapitel ist freigegeben (0 von {n}); eine Auflage enthält nur freigegebene Kapitel.')
    for num, ch, _, skipped, markers in parts:
        if skipped:
            out.append(f'Kapitel {num} „{ch["title"]}“ ist freigegeben, enthält aber nicht freigegebene Abschnitte: '
                       + '; '.join(skipped))
        for where, marker in markers:
            out.append(f'Offener Marker in {where}: {marker}')
    for _, item, md, approved, markers in matter:
        if approved:
            out += [f'Offener Marker in {where}: {marker}' for where, marker in markers]
        if approved and item['kind'] == 'glossary':
            seen = {}
            for term in re.findall(r'(?m)^\[(.+?)\]\{#gl-[^}]*\}\n:   ', md):
                seen.setdefault(term.casefold(), []).append(term)
            out += [f'{item["title"]}: Begriff mehrfach eingetragen: {" / ".join(v)}' for v in seen.values() if len(v) > 1]
    out += ai_disclosure.problems(config, lambda kind: any(m[1]['kind'] == kind and m[3] for m in matter))
    if base is not None:
        out += image_problems(base, config, parts, matter)
    terms = glossary_terms(matter)
    if terms is not None:   # Verweise aufs Glossar (#107): jeder Begriff muss im freigegebenen Glossar stehen
        texts = [(f'Kapitel {num}', md) for num, _, md, _, _ in parts] + \
                [(item['title'], md) for _, item, md, approved, _ in matter if approved and item['kind'] != 'glossary']
        for where, md in texts:
            for m in GLOSSARY_REF.finditer(md):
                if glossary_ref_term(m).casefold() not in terms:
                    out.append(f'Glossar-Verweis ohne Eintrag in {where}: „{glossary_ref_term(m)}“')
    return out


def resolve_images(base, config, md, proof=False):
    """Bild-Verweise ![…](bild:img-…) auflösen (#54): (Markdown, [Beschreibungen der gesetzten Bilder]).
    Auflage: nur freigegebene Bilder; Probedruck: alle, nicht freigegebene mit Vermerk."""
    import images
    known = images.all_images(base, config)
    used = []
    def sub(m):
        alt, iid = m.group(1), m.group(2)
        hit = known.get(iid)
        if not hit or not hit[1].is_file():
            return f'[Bild {iid} fehlt]{{.gwmarker}}' if proof else ''
        meta, path = hit[0], hit[1]
        if meta.get('status') != 'approved' and not proof:
            return ''
        used.append(meta)
        caption = alt or meta.get('caption', '')
        note = '' if meta.get('status') == 'approved' else '\n\n[Bild: Entwurf, nicht freigegeben]{.gwstatus}'
        return f'![{caption}]({path.resolve().as_posix()}){{#{iid} width=100%}}{note}'
    return images.IMAGE_REF.sub(sub, md), used


def image_problems(base, config, parts, matter):
    """Bilder in freigegebenem Text: vorhanden und freigegeben (#54)."""
    import images
    known = images.all_images(base, config)
    out = []
    texts = [(f'Kapitel {num}', md) for num, _, md, _, _ in parts] + \
            [(item['title'], md) for _, item, md, approved, _ in matter if approved]
    for where, md in texts:
        for iid in images.refs_in(md):
            hit = known.get(iid)
            if not hit or not hit[1].is_file():
                out.append(f'Bild {iid} in {where} fehlt')
            elif hit[0].get('status') != 'approved':
                out.append(f'Bild „{hit[0].get("caption") or iid}“ in {where} ist nicht freigegeben')
    return out


def glossary_terms(matter):
    """{begriff.casefold(): begriff} des Glossars, das in die Ausgabe kommt; None ohne Glossar."""
    for _, item, md, _, _ in matter:
        if item['kind'] == 'glossary' and md:
            return {t.casefold(): t for t in re.findall(r'(?m)^\[(.+?)\]\{#gl-[^}]*\}\n:   ', md)}
    return None


def link_glossary(md, terms):
    """Verweise aufs Glossar zu Links machen; ohne Glossar bzw. bei unbekanntem Begriff bleibt nur der Text."""
    def sub(m):
        term = (terms or {}).get(glossary_ref_term(m).casefold())
        return f'[{m.group(1)}](#{glossary_anchor(term)}){{.glossar}}' if term else m.group(1)
    return GLOSSARY_REF.sub(sub, md)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('what', choices=['chapter', 'book', 'check'])
    ap.add_argument('key', nargs='?')
    ap.add_argument('-o', '--output')
    ap.add_argument('--edition', type=int)
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    args = ap.parse_args(argv[1:])
    base, config = load(args.project)
    edition = args.edition if args.edition is not None else (config['project'].get('current_edition') or 0)

    if args.what == 'chapter':
        if not args.key:
            ap.error('chapter braucht eine Kapitelnummer oder -ID')
        num, ch = find_chapter(config, args.key)
        md, skipped, markers = chapter_markdown(base, ch, num)
        for s in skipped:
            print(f'ausgelassen (nicht freigegeben): {s}', file=sys.stderr)
        if markers:
            print(f'{len(markers)} offene Marker im freigegebenen Text', file=sys.stderr)
    else:
        parts = book_parts(base, config)
        matter = matter_parts(base, config)
        if args.what == 'check':
            found = problems(parts, config, matter, base)
            for line in found:
                print(f'✗ {line}')
            for line in matter_notes(matter):
                print(f'ⓘ {line}')
            if not found:
                words = sum(len(re.findall(r'\w+', md)) for _, _, md, _, _ in parts) + \
                    sum(len(re.findall(r'\w+', m[2])) for m in matter)
                extra = sum(1 for m in matter if m[3])
                print(f'✓ Auflage {edition} kann gebaut werden: {len(parts)} Kapitel'
                      + (f', {extra} Teil{"e" if extra != 1 else ""} Vor-/Nachspann' if extra else '')
                      + f', etwa {words} Wörter')
            return 1 if found else 0
        meta = metadata(config, edition, args.date)
        disc = ai_disclosure.for_book(config)
        md = '---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + '---\n\n' + \
             resolve_images(base, config, book_body(parts, matter, disc if disc and disc[0] != 'imprint' else None))[0]
    if args.output:
        Path(args.output).write_text(md, encoding='utf-8')
        print(f'{args.output}: {len(md.split())} Wörter', file=sys.stderr)
    else:
        sys.stdout.write(md)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
