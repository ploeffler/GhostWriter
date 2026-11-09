#!/usr/bin/env python3
"""Build the explicitly selected public handbook. Never deploys or fetches URLs."""
import argparse
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import markdown
from bs4 import BeautifulSoup
import yaml

ROOT = Path(__file__).resolve().parent.parent
REPO = 'https://github.com/ploeffler/GhostWriter/blob/main/'
LANGS = ('de', 'en')
TEXT = {
 'de': {'name':'Dokumentation', 'skip':'Zum Inhalt', 'search':'Dokumentation durchsuchen',
        'hint':'Suchbegriff eingeben. Gesucht wird in der deutschen Dokumentation.',
        'none':'Keine Treffer.', 'results':'Treffer', 'toc':'Auf dieser Seite',
        'source':'Quelle in docs/', 'examples':'So einfach', 'version':'Programmversion',
        'note':'Vorhandene Funktionen und ausdrücklich gekennzeichnete Planungen.',
        'repo':'Repository', 'noscript':'Die Suche benötigt JavaScript. Alle Seiten sind über die Navigation erreichbar.'},
 'en': {'name':'Documentation', 'skip':'Skip to content', 'search':'Search documentation',
        'hint':'Enter a search term. Searches the English documentation.',
        'none':'No results.', 'results':'Results', 'toc':'On this page',
        'source':'Source in docs/', 'examples':'See how it works', 'version':'Program version',
        'note':'Existing features and explicitly marked plans.',
        'repo':'Repository', 'noscript':'Search requires JavaScript. All pages are available through navigation.'}}


def config(root=ROOT):
    cfg = json.loads((root / 'docs/site.json').read_text())
    ids, sources = set(), set()
    for page in cfg['pages']:
        if not re.fullmatch(r'[a-z][a-z0-9-]*', page['id']) or page['id'] in ids:
            raise ValueError('Ungültige oder doppelte Seitenkennung')
        ids.add(page['id'])
        if set(page['source']) != set(LANGS) or set(page['title']) != set(LANGS):
            raise ValueError(f"Sprachpaar fehlt: {page['id']}")
        for lang, source in page['source'].items():
            if Path(source).name != source or not source.endswith('.md') or source in sources:
                raise ValueError(f'Nicht eindeutige öffentliche Quelle: {source}')
            if lang == 'en' and not source.endswith('.en.md'):
                raise ValueError(f'Englische Sprachzuordnung falsch: {source}')
            if lang == 'de' and source.endswith('.en.md'):
                raise ValueError(f'Deutsche Sprachzuordnung falsch: {source}')
            if not (root / 'docs' / source).is_file():
                raise ValueError(f'Quelle fehlt: {source}')
            sources.add(source)
    if 'index' not in ids:
        raise ValueError('Startseite fehlt')
    return cfg


def parse_page(text):
    # Replace the Markdown footer with the same centralized, localized credits in the shell.
    text = re.sub(r'<p align="right"><sub>.*?</p>\s*$', '', text, flags=re.S)
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'sane_lists'],
                           extension_configs={'toc': {'permalink': False, 'slugify': lambda value, separator: re.sub(r'[^\w\s-]', '', value.lower()).strip().replace(' ', separator)}})
    return BeautifulSoup(md.convert(text), 'html.parser')


def target_path(source, value, root):
    split = urlsplit(value)
    path = (source.parent / unquote(split.path)).resolve() if split.path else source.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f'Link außerhalb des Repositorys: {value}')
    return path, split


def rewrite(soup, source, lang, cfg, output, root):
    mapping = {f"docs/{p['source'][l]}": f"{l}/{p['id']}.html" for p in cfg['pages'] for l in LANGS}
    for tag in soup.find_all(['a', 'img', 'source']):
        attr = 'href' if tag.name == 'a' else ('srcset' if tag.name == 'source' else 'src')
        value = tag.get(attr)
        if not value:
            continue
        split = urlsplit(value)
        if split.scheme or split.netloc:
            if split.scheme not in ('http', 'https', 'mailto'):
                raise ValueError(f'Nicht erlaubtes Linkprotokoll: {value}')
            if tag.name != 'a':
                raise ValueError(f'Externes Bild nicht freigegeben: {value}')
            continue
        path, split = target_path(source, value, root)
        rel = path.relative_to(root.resolve()).as_posix()
        suffix = ('#' + quote(unquote(split.fragment), safe='-._~')) if split.fragment else ''
        if rel in mapping:
            tag[attr] = '../' + mapping[rel] + suffix
            other = mapping[rel].split('/')[0]
            if tag.name == 'a' and other != lang:
                tag['hreflang'] = other
                tag['lang'] = other
            continue
        if rel in cfg['excluded_links']:
            if tag.name != 'a':
                raise ValueError('Interne Planungsdatei als Bild')
            tag.unwrap()  # Internal planning is neither copied nor linked from the public site.
            continue
        if tag.name == 'a' and rel in cfg['repository_links']:
            if not path.is_file():
                raise ValueError(f'Repository-Verweis fehlt: {rel}')
            tag[attr] = REPO + quote(rel) + suffix
            language = 'en' if '.en.' in path.name else 'de'
            tag['hreflang'] = language
            tag.append(f" ({TEXT[lang]['repo']}, {'English' if language == 'en' else 'Deutsch'})")
            continue
        if rel.startswith('docs/bilder/') and path.suffix.lower() in ('.svg', '.png', '.jpg', '.webp'):
            if not path.is_file():
                raise ValueError(f'Bild fehlt: {rel}')
            dest = output / 'assets' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
            tag[attr] = '../assets/' + rel + suffix
            continue
        raise ValueError(f'Nicht klassifizierter Verweis in {source.name}: {value}')


def shell(page, lang, soup, cfg, version, credit):
    t = TEXT[lang]
    other = 'en' if lang == 'de' else 'de'
    esc = html.escape
    nav = ''.join(f'<a href="{p["id"]}.html"' + (' aria-current="page"' if p['id'] == page['id'] else '') +
                  f'>{esc(p["title"][lang])}</a>' for p in cfg['pages'])
    toc = ''.join(f'<a href="#{esc(h["id"])}">{esc(h.get_text())}</a>' for h in soup.find_all('h2', id=True))
    examples = [('ghostwriter-startklar', 'Startklar' if lang == 'de' else 'Get ready'),
                ('so-einfach-gehts', 'Ein Buch erstellen' if lang == 'de' else 'Create a book'),
                ('programmieren-mit-ki', 'Programmieren mit KI' if lang == 'de' else 'Programming with AI')]
    example_nav = ' · '.join(f'<a href="../../{name}{".en" if lang == "en" else ""}.html">{label}</a>' for name, label in examples)
    notice = credit['text_en' if lang == 'en' else 'text']
    codex = credit['codex_text_en' if lang == 'en' else 'codex_text']
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(page['title'][lang])} · GhostWriter</title>
<link rel="alternate" hreflang="{other}" href="../{other}/{page['id']}.html">
<link rel="stylesheet" href="../assets/site.css"><script src="../assets/search.js" defer></script></head>
<body><a class="skip" href="#content">{t['skip']}</a>
<header><a class="brand" href="index.html"><img src="../assets/logo.svg" width="30" height="30" alt="">GhostWriter <span>{t['name']}</span></a>
<a class="language" href="../{other}/{page['id']}.html" lang="{other}" hreflang="{other}">{'English' if other == 'en' else 'Deutsch'}</a></header>
<div class="version">{t['version']} <strong>{esc(version)}</strong> · {t['note']}</div>
<div class="layout"><aside><form role="search"><label for="search">{t['search']}</label><input id="search" type="search" autocomplete="off" aria-controls="results" placeholder="{'Suchen …' if lang == 'de' else 'Search …'}"><button type="submit">{'Suchen' if lang == 'de' else 'Search'}</button></form>
<noscript>{t['noscript']}</noscript><p id="search-status" role="status" aria-live="polite"></p><ul id="results"></ul>
<nav aria-label="{t['name']}">{nav}</nav></aside>
<main id="content"><nav class="examples" aria-label="{t['examples']}"><strong>{t['examples']}</strong> · {example_nav}</nav>
<details class="toc"><summary>{t['toc']}</summary>{toc}</details><article>{soup}</article>
<p class="source"><a href="{REPO}docs/{quote(page['source'][lang])}">{t['source']}</a></p>
<footer>{esc(notice)}<br>{esc(codex)}</footer></main></div></body></html>'''


def build(output, root=ROOT):
    cfg = config(root)
    output = Path(output).resolve()
    # This tool may replace only a dedicated generated directory, never docs/ or live website/.
    if output == root.resolve() or output.is_relative_to(root / 'docs') or output == (root / 'website').resolve():
        raise ValueError('Ausgabe muss ein eigener erzeugter Ordner sein')
    if output.exists() and any(output.iterdir()) and not (output / '.ghostwriter-docsite').is_file():
        raise ValueError('Nichtleeres fremdes Ausgabeverzeichnis wird nicht ersetzt')
    output.mkdir(parents=True, exist_ok=True)
    (output / '.ghostwriter-docsite').write_text('generated\n')
    # Rebuild from scratch so removed pages and assets cannot remain publicly reachable.
    for child in output.iterdir():
        if child.name == '.ghostwriter-docsite':
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    version = str(yaml.safe_load((root / 'ghostwriter-manifest.yml').read_text())['version'])
    credit = yaml.safe_load((root / 'templates/branding.yml').read_text())['credit']
    assets = output / 'assets'
    assets.mkdir()
    for name in ('site.css', 'search.js'):
        shutil.copyfile(root / 'scripts/docsite' / name, assets / name)
    shutil.copyfile(root / 'assets/logo.svg', assets / 'logo.svg')
    hashes = {}
    for lang in LANGS:
        (output / lang).mkdir()
        index = []
        for page in cfg['pages']:
            source = root / 'docs' / page['source'][lang]
            text = source.read_text(encoding='utf-8')
            hashes[str(source.relative_to(root))] = hashlib.sha256(source.read_bytes()).hexdigest()
            soup = parse_page(text)
            rewrite(soup, source, lang, cfg, output, root)
            for table in soup.find_all('table'):
                wrapper = soup.new_tag('div', attrs={'class': 'table-wrap', 'tabindex': '0', 'role': 'region', 'aria-label': 'Tabelle' if lang == 'de' else 'Table'})
                table.wrap(wrapper)
            index.append({'title':page['title'][lang], 'url':page['id'] + '.html',
                          'text':soup.get_text(' ', strip=True)})
            (output / lang / (page['id'] + '.html')).write_text(shell(page, lang, soup, cfg, version, credit), encoding='utf-8')
        (output / lang / 'search-index.json').write_text(json.dumps(index, ensure_ascii=False), encoding='utf-8')
    (output / 'index.html').write_text('<!doctype html><html lang="de"><meta charset="utf-8"><title>GhostWriter Dokumentation</title><a href="de/index.html">Deutsch</a> · <a href="en/index.html">English</a></html>')
    (output / 'build-info.json').write_text(json.dumps({'version':version, 'sources':hashes}, indent=2)+'\n')
    check(output, root)
    return cfg


def check(output, root=ROOT):
    """Check all generated local targets and fragments, paired pages, credits and search data."""
    output = Path(output).resolve()
    cfg = config(root)
    info = json.loads((output/'build-info.json').read_text())
    current_version = str(yaml.safe_load((root/'ghostwriter-manifest.yml').read_text())['version'])
    if info['version'] != current_version:
        raise ValueError('Website verwendet eine veraltete Programmversion')
    for name, digest in info['sources'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Website ist veraltet: {name}')
    parsed = {p.resolve():BeautifulSoup(p.read_text(), 'html.parser') for p in output.rglob('*.html')}
    problems = []
    for path, soup in parsed.items():
        for tag in soup.find_all(['a', 'img', 'link', 'script', 'source']):
            value = tag.get('href') or tag.get('src') or tag.get('srcset')
            if not value or urlsplit(value).scheme or urlsplit(value).netloc:
                continue
            split = urlsplit(value)
            target = (path.parent / unquote(split.path)).resolve() if split.path else path
            # Example pages are deliberately retained in website/, outside generated documentation.
            if not target.is_relative_to(output):
                expected = root / 'website' / target.name
                if not expected.is_file() or target.name not in {
                    n + s + '.html' for n in ('ghostwriter-startklar','so-einfach-gehts','programmieren-mit-ki') for s in ('','.en')}:
                    problems.append(f'Nicht erlaubter externer Dateipfad: {value}')
                continue
            if not target.is_file():
                problems.append(f'{path.name}: Ziel fehlt: {value}')
            elif split.fragment and target in parsed and not parsed[target].find(id=unquote(split.fragment)):
                problems.append(f'{path.name}: Anker fehlt: {value}')
    credit = yaml.safe_load((root/'templates/branding.yml').read_text())['credit']
    for lang in LANGS:
        index = json.loads((output/lang/'search-index.json').read_text())
        if {e['url'] for e in index} != {p['id']+'.html' for p in cfg['pages']}:
            problems.append(f'Suchindex unvollständig: {lang}')
        for page in cfg['pages']:
            soup = parsed.get(output/lang/(page['id']+'.html'))
            if soup is None:
                problems.append(f'Seite fehlt: {lang}/{page["id"]}')
                continue
            if soup.html.get('lang') != lang:
                problems.append('HTML-Sprachzuordnung falsch')
            switch = soup.select_one('a.language')
            other = 'en' if lang == 'de' else 'de'
            if switch.get('href') != f'../{other}/{page["id"]}.html':
                problems.append('Sprachwechsel falsch')
            footer = soup.footer.get_text('|', strip=True)
            expected = credit['text_en' if lang == 'en' else 'text']+'|'+credit['codex_text_en' if lang == 'en' else 'codex_text']
            if footer != expected:
                problems.append('Gemeinsame Fußzeile falsch')
    if problems:
        raise ValueError('\n'.join(sorted(set(problems))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/documentation')
    parser.add_argument('--check', action='store_true', help='Vorhandenen Aufbau prüfen')
    args = parser.parse_args()
    try:
        if args.check:
            check(args.output)
        else:
            build(args.output)
        print(f'Dokumentationswebsite geprüft: {args.output}')
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
