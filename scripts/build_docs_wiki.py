#!/usr/bin/env python3
"""Build GitHub Wiki pages from the website's explicit public source list. No upload."""
import argparse
import hashlib
import json
import re
import shutil
from urllib.parse import quote, unquote
from pathlib import Path

import yaml
from build_docs_site import ROOT, LANGS, config as site_config, parse_page, rewrite

SITE = 'https://ploeffler.github.io/GhostWriter/'
RAW = 'https://raw.githubusercontent.com/ploeffler/GhostWriter/main/'


def config(root=ROOT):
    cfg = site_config(root)
    # The already published wiki also includes the existing version outlook.
    if not any(p['id'] == 'road-to-1-0' for p in cfg['pages']):
        cfg['pages'].insert(1, {
            'id': 'road-to-1-0',
            'title': {'de': 'Ausblick bis 1.0', 'en': 'The road to 1.0'},
            'source': {'de': 'AUSBLICK-v1.0.md', 'en': 'LOOKING-AHEAD-v1.0.en.md'}})
    return cfg


def slug(page, lang):
    # GitHub derives its visible page title from the file name.
    title = page['title'][lang].replace('&', 'und' if lang == 'de' else 'and')
    title = re.sub(r'[^\w .()-]', '', title).strip()
    if page['id'] in ('updates', 'apps'):
        title += ' (Deutsch)' if lang == 'de' else ' (English)'
    return re.sub(r'\s+', '-', title)


def page_link(page, lang):
    return quote(slug(page, lang), safe='-._')


def footer(credit):
    return (credit['text_en'] + ' [↗](https://claude.ai "Claude")<br>\n'
            + credit['codex_text_en'] + ' [↗](https://openai.com/codex/ "Codex")')


def build(output, root=ROOT):
    root = root.resolve()
    output = output.resolve()
    # Never replace the older, independently generated version outlook or a checkout.
    if output == root or root.is_relative_to(output) or output.is_relative_to(root/'docs') or output.is_relative_to(root/'wiki'):
        raise ValueError('Eigenen Ausgabeordner verwenden, nicht docs/ oder wiki/')
    marker = output/'.ghostwriter-wiki'
    if output.exists() and any(output.iterdir()) and not marker.is_file():
        raise ValueError('Fremder Ausgabeordner wird nicht ersetzt')
    output.mkdir(parents=True, exist_ok=True)
    for child in output.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    marker.write_text('generated\n')
    cfg = config(root)
    version = str(yaml.safe_load((root/'ghostwriter-manifest.yml').read_text())['version'])
    credit = yaml.safe_load((root/'templates/branding.yml').read_text())['credit']
    names = [slug(p, lang).casefold() for p in cfg['pages'] for lang in LANGS]
    if len(names) != len(set(names)) or set(names) & {'home', '_sidebar', '_footer'}:
        raise ValueError('Wiki-Seitentitel sind nicht eindeutig')
    hashes = {}
    logo = f'<picture><source media="(prefers-color-scheme: dark)" srcset="{RAW}assets/logo-wortmarke-dark.svg"><img src="{RAW}assets/logo-wortmarke.svg" alt="GhostWriter" width="240"></picture>'
    for lang in LANGS:
        other = 'en' if lang == 'de' else 'de'
        for page in cfg['pages']:
            source = root/'docs'/page['source'][lang]
            text = source.read_text()
            hashes[str(source.relative_to(root))] = hashlib.sha256(source.read_bytes()).hexdigest()
            soup = parse_page(text)
            rewrite(soup, source, lang, cfg, output, root)
            for a in soup.find_all('a', href=True):
                value = a['href']
                if value.startswith('../assets/docs/bilder/'):
                    a['href'] = value.replace('../assets/', RAW, 1)
                match = re.fullmatch(r'../(de|en)/([a-z0-9-]+)\.html(.*)', value)
                if match:
                    target = next(p for p in cfg['pages'] if p['id'] == match[2])
                    a['href'] = page_link(target, match[1]) + match[3]
            for tag in soup.find_all(['img', 'source']):
                attr = 'srcset' if tag.name == 'source' else 'src'
                if tag.get(attr, '').startswith('../assets/docs/bilder/'):
                    tag[attr] = tag[attr].replace('../assets/', RAW, 1)
            # Explicit named anchors retain the website's checked fragment targets.
            for heading in soup.find_all(re.compile('^h[1-6]$'), id=True):
                anchor = soup.new_tag('a', attrs={'name': heading['id']})
                heading.insert_before(anchor)
                del heading['id']
            label = 'Programmversion' if lang == 'de' else 'Program version'
            web = 'Website mit Suche' if lang == 'de' else 'Website with search'
            nav = f'[Deutsch]({page_link(page, "de")}) · [English]({page_link(page, "en")}) · [{web}]({SITE}documentation/{lang}/{page["id"]}.html)'
            contents = '\n'.join(f'- [{p["title"][lang]}]({page_link(p, lang)})' for p in cfg['pages']) if page['id'] == 'index' else ''
            # Credits live only in GitHub's global footer box.
            last = next((tag for tag in reversed(soup.contents) if str(tag).strip()), None)
            if getattr(last, 'name', None) == 'hr':
                last.decompose()
            body = f'{logo}\n\n{nav}\n\n**{label} {version}**\n\n{soup}\n\n{contents}\n'
            (output/(slug(page,lang)+'.md')).write_text(body)
    index = next(p for p in cfg['pages'] if p['id'] == 'index')
    (output/'Home.md').write_text(f'{logo}\n\n# GhostWriter\n\n[Dokumentation auf Deutsch]({page_link(index, "de")}) · [Documentation in English]({page_link(index, "en")})\n\n[Website mit Suche / Website with search]({SITE}documentation/de/index.html)\n\n**Programmversion / Program version {version}**\n')
    sidebar = ['[GhostWriter](Home)', '', f'[Deutsch]({page_link(index, "de")}) · [English]({page_link(index, "en")})', '']
    for lang in LANGS:
        sidebar += ['### '+('Dokumentation' if lang == 'de' else 'Documentation'), '']
        sidebar += [f'- [{p["title"][lang]}]({page_link(p,lang)})' for p in cfg['pages']]
        sidebar += ['']
    (output/'_Sidebar.md').write_text('\n'.join(sidebar)+'\n')
    (output/'_Footer.md').write_text(f'GhostWriter · {version} · [Website]({SITE})\n\n{footer(credit)}\n')
    # Images are referenced from the same main-repository assets as the website.
    if (output/'assets').exists():
        shutil.rmtree(output/'assets')
    (output/'build-info.json').write_text(json.dumps({'version':version,'sources':hashes,
        'renames': {f'{lang}-{p["id"]}.md': slug(p, lang)+'.md' for p in cfg['pages'] for lang in LANGS}}, indent=2)+'\n')
    check(output, root)


def check(output, root=ROOT):
    cfg = config(root)
    expected = {slug(p,l)+'.md' for p in cfg['pages'] for l in LANGS} | {'Home.md','_Sidebar.md','_Footer.md'}
    if {p.name for p in output.glob('*.md')} != expected:
        raise ValueError('Wiki-Seitenauswahl unvollständig oder unerwartet')
    info = json.loads((output/'build-info.json').read_text())
    if info['version'] != str(yaml.safe_load((root/'ghostwriter-manifest.yml').read_text())['version']):
        raise ValueError('Veraltete Version')
    for name, digest in info['sources'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Veraltete Quelle: {name}')
    credit = yaml.safe_load((root/'templates/branding.yml').read_text())['credit']
    credits = [credit[k] for k in ('text', 'codex_text', 'text_en', 'codex_text_en')]
    from bs4 import BeautifulSoup
    for path in output.glob('*.md'):
        text = path.read_text()
        for notice in credits:
            expected_count = 1 if path.name == '_Footer.md' and notice in (credit['text_en'], credit['codex_text_en']) else 0
            if text.count(notice) != expected_count:
                raise ValueError(f'{path.name}: KI-Hinweis nur einmal in der globalen Fußzeile erlaubt')
        links = re.findall(r'\]\(([^)]+)\)', text)
        links += [a['href'] for a in BeautifulSoup(text,'html.parser').find_all('a',href=True)]
        for link in links:
            if re.match(r'^[a-z]+:',link):
                continue
            target, _, fragment = link.partition('#')
            dest = output/(unquote(target)+'.md') if target else path
            if not dest.is_file():
                raise ValueError(f'{path.name}: Ziel fehlt: {link}')
            if fragment:
                if not BeautifulSoup(dest.read_text(),'html.parser').find('a',attrs={'name':unquote(fragment)}):
                    raise ValueError(f'{path.name}: Anker fehlt: {link}')
    print(f'Wiki geprüft: {len(expected)} Seiten, Version {info["version"]}, {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/documentation-wiki')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check(args.output.resolve())
    else:
        build(args.output)
