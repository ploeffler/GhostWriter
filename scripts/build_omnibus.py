#!/usr/bin/env python3
"""Sammelband einer Serie: eine Auflage aus mehreren Bänden (#116, Stufe 4).

Aufruf (im Standard-Branch der Bibliothek, mit allen Branches und Tags):
  python scripts/build_omnibus.py <repo> <ser-id> --edition N [--out ordner] [--date JJJJ-MM-TT]
                                  [--formats pdf,epub,docx,pdf_print,cover] [--commit SHA] [--check]

Beschreibung des Sammelbands: series/<ser-id>/omnibus.yml (Schema
schemas/omnibus.schema.json): Titel, Untertitel, Bände (Buch-Branch, optional
Auflage; sonst die neueste), welche Teile von Vor- und Nachspann der Bände
bleiben (keep_matter, Vorgabe Prolog und Epilog), eigenes Vorwort und
Nachwort, Angaben im Impressum (publication), Satz (typesetting, sonst wie
Band 1), Formate, status (draft | approved).

Inhalt: je Band der Stand seiner Auflage (Tag <kurztitel-slug>-auflage-N),
also genau das, was schon erschienen ist. Aufbau: Titelei mit eigenem Titel und
Impressum (enthaltene Bandauflagen, ISBN, Reihe und ISSN), Gesamtinhalts-
verzeichnis, eigenes Vorwort, je Band ein Teil mit Zwischentitel „Band N: Titel“
und seinen Kapiteln, eigenes Nachwort, zusammengeführtes Glossar (Begriffe der
Serie in der Fassung der Serie; sonst die Fassung des ersten Bandes, Abweichungen
werden gemeldet). Umschlag, Druck-PDF und Rückenbreite wie bei einer Auflage
(Umschlag-Einstellungen und Bilder von Band 1).

Ohne status: approved baut das Skript nichts (außer mit --check: nur prüfen).
Tag des Sammelbands: <reihen-slug>-sammelband-auflage-N; edition.yml hält die
enthaltenen Bandauflagen fest.
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import library  # noqa: E402
import series  # noqa: E402
from assemble import (book_parts, glossary_ref_term, link_glossary, matter_parts, metadata,  # noqa: E402
                      problems, resolve_images, shift_headings)
from render_view import (GLOSSARY_REF, german_key, glossary_anchor, glossary_entries, load,  # noqa: E402
                         section_file)
import ai_disclosure  # noqa: E402
import build_edition  # noqa: E402

KEEP_DEFAULT = ['prologue', 'epilogue']


def omnibus_file(repo, sid):
    return Path(repo) / 'series' / sid / 'omnibus.yml'


def load_omnibus(repo, sid):
    p = omnibus_file(repo, sid)
    if not p.is_file():
        raise SystemExit(f'{p}: Es gibt noch keinen Sammelband dieser Serie')
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}


def volume_tags(repo, ser, om):
    """[(band, branch, tag, auflage)] der gewählten Bände in Bandreihenfolge; Fehlerliste."""
    order = series.volumes(ser)
    out, errors = [], []
    for v in om.get('volumes') or []:
        br = v['branch'] if isinstance(v, dict) else v
        if br not in order:
            errors.append(f'{br} ist kein Band der Serie')
            continue
        cfg = yaml.safe_load(series._branch_file(repo, br, 'ghostwriter.yml') or '') or {}
        short = (cfg.get('project') or {}).get('title_short') or ''
        slug = library.slug(short)
        want = v.get('edition') if isinstance(v, dict) else None
        if want:
            tag = f'{slug}-auflage-{int(want)}'
            if not series._git(repo, 'rev-parse', '-q', '--verify', f'refs/tags/{tag}'):
                errors.append(f'Band {order.index(br) + 1}: Auflage {want} gibt es nicht ({tag})')
                continue
            num = int(want)
        else:
            ed = library.last_edition(slug, repo)
            if not ed:
                errors.append(f'Band {order.index(br) + 1} ({br}) hat noch keine Auflage')
                continue
            tag, num = ed['tag'], ed['number']
        out.append((order.index(br) + 1, br, tag, num))
    if not out and not errors:
        errors.append('Keine Bände gewählt')
    return sorted(out), errors


def merged_glossary(repo, sid, vols):
    """[(begriff, erklärung)] aus den Glossaren der Bände und den Begriffen der Serie, dazu Hinweise."""
    series_terms = {series.term_key(x['term']): (x['term'], x['text']) for x in series.glossary(repo, sid)}
    merged, notes, refs = {}, [], set()
    for n, vbase, vcfg, vparts, vmatter in vols:
        for _, item in [(a, i) for a, i, *_ in vmatter if i['kind'] == 'glossary']:
            for term, text in glossary_entries(section_file(vbase, item)[3])[1]:
                k = series.term_key(term)
                if k in merged and merged[k][1].strip() != text.strip() and k not in series_terms:
                    notes.append(f'„{term}“: Band {n} erklärt anders als ein früherer Band; im Sammelband gilt die erste Fassung.')
                merged.setdefault(k, (term, text))
        for md in [p[2] for p in vparts] + [m[2] for m in vmatter if m[2]]:
            refs |= {glossary_ref_term(m).casefold() for m in GLOSSARY_REF.finditer(md)}
    for k, v in series_terms.items():   # Fassung der Serie gilt; verwiesene Begriffe der Serie kommen dazu
        if k in merged or k in refs:
            merged[k] = v
    return sorted(merged.values(), key=lambda e: german_key(e[0])), notes


def glossary_markdown(entries):
    if not entries:
        return ''
    dl = '\n'.join(f'[{t}]{{#{glossary_anchor(t)}}}\n:   {e}\n' for t, e in entries)
    return f'# Glossar {{.unnumbered .glossary epub:type=glossary}}\n\n{dl}'


def volume_markdown(n, title, vparts, vmatter, keep):
    """Ein Band als Teil: Zwischentitel, beibehaltene Teile von Vor- und Nachspann, Kapitel (eine Ebene tiefer)."""
    front = [m[2] for m in vmatter if m[0] == 'front' and m[2] and m[1]['kind'] in keep]
    back = [m[2] for m in vmatter if m[0] == 'back' and m[2] and m[1]['kind'] in keep]
    inner = '\n'.join(front + [p[2] for p in vparts] + back)
    return f'# Band {n}: {title} {{.band epub:type=part}}\n\n' + shift_headings(inner, 2) + '\n'


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('repo')
    ap.add_argument('series_id')
    ap.add_argument('--edition', type=int)
    ap.add_argument('--out', default='build')
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--formats')
    ap.add_argument('--commit', default='')
    ap.add_argument('--check', action='store_true', help='nur prüfen, nichts bauen')
    a = ap.parse_args(argv[1:])
    repo = Path(a.repo).resolve()
    ser, _ = series.get(repo, a.series_id)
    om = load_omnibus(repo, ser['id'])
    keep = om.get('keep_matter', KEEP_DEFAULT) or []
    picked, errors = volume_tags(repo, ser, om)
    if om.get('status') != 'approved' and not a.check:
        errors.append('Der Sammelband ist nicht freigegeben (status: approved, START.md „Serien“)')
    if a.edition is None and not a.check:
        a.edition = int(om.get('current_edition') or 0) or 1
    tmp = Path(tempfile.mkdtemp(prefix='gw-omnibus-'))
    trees, vols = [], []
    try:
        for n, br, tag, num in picked:
            wt = tmp / f'band-{n}'
            r = subprocess.run(['git', 'worktree', 'add', '-q', '--detach', str(wt), tag], cwd=repo, capture_output=True, text=True)
            if r.returncode:
                errors.append(f'Band {n}: {tag} lässt sich nicht auschecken ({r.stderr.strip()[:200]})')
                continue
            trees.append(wt)
            vbase, vcfg = load(wt)
            vparts, vmatter = book_parts(vbase, vcfg), matter_parts(vbase, vcfg)
            errors += [f'Band {n}: {p}' for p in problems(vparts, vcfg, vmatter, vbase) if not p.startswith('Glossar-Verweis')]
            vols.append((n, vbase, vcfg, vparts, vmatter))
        if errors:
            print(f'Sammelband „{om.get("title") or ser["title"]}“ kann nicht gebaut werden:')
            for e in errors:
                print(f'  ✗ {e}')
            return 1
        gloss, notes = merged_glossary(repo, ser['id'], vols)
        for note in notes:
            print(f'ⓘ {note}')
        if a.check:
            print(f'✓ Sammelband prüfbar: {len(vols)} Bände, {len(gloss)} Begriffe im Glossar')
            return 0
        terms = {t.casefold(): t for t, _ in gloss}
        first_base, first_cfg = vols[0][1], vols[0][2]
        parts_md, used = [], []
        if (om.get('foreword') or '').strip():
            parts_md.append(f'# Vorwort {{.unnumbered .foreword epub:type=foreword}}\n\n{om["foreword"].strip()}\n')
        contents = []
        for n, vbase, vcfg, vparts, vmatter in vols:
            p = vcfg['project']
            title = p.get('title') or p.get('working_title') or p.get('title_short')
            md, u = resolve_images(vbase, vcfg, volume_markdown(n, title, vparts, vmatter, keep))
            parts_md.append(md)
            used += u
            contents.append((n, title, next(x[3] for x in picked if x[0] == n)))
        if (om.get('afterword') or '').strip():
            parts_md.append(f'# Nachwort {{.unnumbered .afterword epub:type=afterword}}\n\n{om["afterword"].strip()}\n')
        g = glossary_markdown(gloss)
        if g:
            parts_md.append(g)
        body = link_glossary('\n'.join(parts_md), terms)

        config = json.loads(json.dumps(first_cfg, default=str))   # Kopie von Band 1 mit den Angaben des Sammelbands
        config['project'] = dict(config['project'], title=om.get('title') or f'{ser["title"]} – Sammelband',
                                 subtitle=om.get('subtitle') or '', title_short=om.get('title') or ser['title'])
        config['publication'] = om.get('publication') or {}
        config['typesetting'] = dict(config.get('typesetting') or {}, **(om.get('typesetting') or {}))
        config['_series'] = dict(ser, volume=None)
        meta = metadata(config, a.edition, a.date)
        meta['edition_text'] = f'Sammelband, Auflage {a.edition}'
        ts = meta['typesetting']
        ts['_explicit'] = set((config.get('typesetting') or {}).keys())
        formats = a.formats or ','.join(om.get('formats') or ts.get('formats') or ['pdf', 'docx', 'epub'])
        slug = library.slug(ser['title'])
        tag = f'{slug}-sammelband-auflage-{a.edition}'
        release = f'{om.get("title") or ser["title"]} – Sammelband, Auflage {a.edition}'
        imprint = build_edition.imprint_markdown(meta, release, a.commit, config['publication'])
        imprint[1:1] = ['Enthält: ' + '; '.join(f'Band {n} „{t}“ (Auflage {e})' for n, t, e in contents)] + \
            series.edition_lines(dict(ser, volume=1))[1:] + [f'Reihe „{ser["title"]}“']
        credit = build_edition.image_credit(used, config)
        if credit:
            imprint.append(credit)
        for _, _, vcfg, _, _ in vols:   # KI-Angaben der Bände (Impressum), ohne Doppelungen
            disc = ai_disclosure.for_book(vcfg)
            if disc and disc[0] == 'imprint':
                for line in disc[1].splitlines():
                    line = re.sub(r'^\s*[-*]\s+', '– ', line).strip()
                    if line and line not in imprint:
                        imprint.append(line)
        common = {k: meta[k] for k in ('title', 'subtitle', 'author', 'lang') if k in meta}
        common['date'] = f'{meta["edition_text"]} · {build_edition.MONTHS[int(a.date[5:7]) - 1]} {a.date[:4]}'
        out = Path(a.out).resolve()
        out.mkdir(parents=True, exist_ok=True)
        extra = '\\renewcommand*{\\partformat}{}\n'   # Zwischentitel „Band N: Titel“ ohne „Teil I“
        results = build_edition.render(first_base, config, ts, meta, common, imprint, body, body, '', out, tag, formats,
                                       date=a.date, series_line=f'{ser["title"]} · Sammelband', ser=config['_series'],
                                       extra_tex=extra, top_level='part')
        (out / 'edition.yml').write_text(yaml.safe_dump({
            'edition': a.edition, 'name': release, 'tag': tag, 'date': a.date, 'series': ser['id'],
            'volumes': [{'volume': n, 'branch': br, 'tag': t} for n, br, t, _ in picked],
            'files': [r.name for r in results]}, allow_unicode=True, sort_keys=False), encoding='utf-8')
        return 0
    finally:
        for wt in trees:
            subprocess.run(['git', 'worktree', 'remove', '--force', str(wt)], cwd=repo, capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
