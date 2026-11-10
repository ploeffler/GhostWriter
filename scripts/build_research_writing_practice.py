#!/usr/bin/env python3
"""Zwei zweisprachige Schreibpraxis-Folgen reproduzierbar lokal aufbauen; kein Upload."""
import argparse
from html import escape
import json
from pathlib import Path
import shutil
from string import Template

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = 'https://www.seismo.ethz.ch/de/knowledge/faq/can-earthquakes-be-predicted/'
EXTRA_CSS = '''
article{min-width:0}article p,td,a{overflow-wrap:anywhere}
.conversation{margin:28px 0}.message{margin-bottom:20px}.message p{font-size:18px}
.editorial{padding:20px 24px;border-left:3px solid var(--line);margin:28px 0;color:var(--muted);font-size:16px}
.editorial h2{font-size:16px}.editorial p,.result p{margin:0}
.table-wrap{overflow-x:auto;margin:32px 0}table{width:100%;border-collapse:collapse;font-size:16px}
caption{text-align:left;font:normal 25px/1.3 Georgia,serif;margin-bottom:16px}
th,td{text-align:left;vertical-align:top;padding:14px 12px;border-bottom:1px solid var(--line)}th{width:32%}
.source{border-top:1px solid var(--line);padding-top:20px;margin-top:36px;font-size:14px;color:var(--muted)}
.source h2{font-size:16px}.source p{margin:8px 0}.skip{position:absolute;left:-10000px}.skip:focus{left:20px;top:8px;background:var(--paper);padding:10px;z-index:2}
@media(max-width:760px){.message{max-width:100%}.message p{font-size:16px}th,td{padding:12px 8px}table{font-size:14px}.status{max-width:140px;text-align:right}.editorial,.result{padding:20px}}
@media print{.message,.result,.editorial{break-inside:avoid}}
'''


def content(block, published):
    kind = block['type']
    if kind == 'message':
        role = block['role']
        css = ' author' if role in ('Autor', 'Author') else ''
        return f'<div class="message{css}"><strong>{escape(role)}</strong><p>{escape(block["text"])}</p></div>'
    if kind in ('result', 'note'):
        css = 'result' if kind == 'result' else 'editorial'
        return f'<aside class="{css}"><h2>{escape(block["title"])}</h2><p>{escape(block["text"])}</p></aside>'
    if kind == 'table':
        rows = ''.join(f'<tr><th scope="row">{escape(k)}</th><td>{escape(v)}</td></tr>' for k,v in block['rows'])
        return f'<div class="table-wrap"><table><caption>{escape(block["title"])}</caption><tbody>{rows}</tbody></table></div>'
    if kind == 'link':
        url = block['url'] if published else block['url'].replace('../', '../schreibpraxis-', 1)
        return f'<p><a href="{escape(url, quote=True)}">{escape(block["label"])}</a></p>'
    raise ValueError(f'Unbekannter Inhaltsblock: {kind}')


def build(published=False):
    raw_template = (ROOT/'templates/schreibpraxis/folge.html').read_text()
    raw_template = raw_template.replace('<article>', '<article id="inhalt">')
    for slug in ('recherche', 'zitieren'):
        source = ROOT/'beispielmaterial'/f'schreibpraxis-{slug}'
        pair = {lang: json.loads((source/name).read_text()) for lang,name in [('de','inhalt.json'),('en','content.en.json')]}
        assert len(pair['de']['pages']) == len(pair['en']['pages'])
        destination = ROOT/'website'/slug if published else source
        destination.mkdir(parents=True, exist_ok=True)
        css = (ROOT/'templates/schreibpraxis/grundstil.css').read_text() + EXTRA_CSS
        (destination/'stil.css').write_text(css)
        shutil.copyfile(ROOT/'assets/logo.svg', destination/'logo.svg')
        for lang,data in pair.items():
            en = lang == 'en'
            suffix = '.en' if en else ''
            other_lang = 'de' if en else 'en'
            pages = data['pages']
            assert len({p['file'] for p in pages}) == len(pages)
            skip = 'Skip to content' if en else 'Zum Inhalt'
            template = Template(raw_template.replace('<body>', f'<body>\n  <a class="skip" href="#inhalt">{skip}</a>'))
            for i,page in enumerate(pages):
                counterpart = pair[other_lang]['pages'][i]['file']
                navigation = ''.join(f'<li><a href="{escape(p["file"])}"'+(' aria-current="page"' if j==i else '')+f'>{escape(p["label"])}</a></li>' for j,p in enumerate(pages))
                blocks = ''.join(content(b, published) for b in page['blocks'])
                label = 'Simulated conversation and commentary' if en else 'Simuliertes Gespräch und Einordnung'
                blocks = f'<div class="conversation" aria-label="{label}">'+blocks+'</div>'
                source_url = SOURCE_URL.replace('/de/','/en/') if en else SOURCE_URL
                if en:
                    source_html = f'<h2>Q1 · Expert source actually consulted</h2><p>Swiss Seismological Service (SED) at ETH Zurich: <a href="{source_url}">Can earthquakes be predicted?</a> In particular, the introduction and the “Earthquake early warning” section. No publication date displayed; accessed on 10 November 2026.</p><p>Institutional expert information, not an original research study. A factual check for this example, not a complete literature review.</p>'
                else:
                    source_html = f'<h2>Q1 · Tatsächlich gelesene Fachquelle</h2><p>Schweizerischer Erdbebendienst (SED) an der ETH Zürich: <a href="{source_url}">Können Erdbeben vorhergesagt werden?</a> Insbesondere Einleitung und Abschnitt „Erdbebenfrühwarnung“. Ohne ausgewiesenes Veröffentlichungsdatum; abgerufen am 10. November 2026.</p><p>Institutionelle Fachinformation, keine Originalstudie. Sachprüfung für dieses Beispiel; keine vollständige Literaturübersicht.</p>'
                blocks += '<aside class="source" id="quelle-q1">'+source_html+'</aside>'
                overview = ('../' if published else '../../website/')+'schreibpraxis'+suffix+'.html'
                back = 'Back' if en else 'Zurück'
                next_label = 'Next' if en else 'Weiter'
                start_label = 'Back to the beginning' if en else 'Zum Anfang'
                notice_title = 'Entirely simulated dialogue' if en else 'Vollständig simulierter Dialog'
                credit = 'Developed with support from' if en else 'Entwickelt mit Unterstützung von'
                values = dict(
                    LANG=lang, OTHER_LANG=other_lang, OTHER_URL=counterpart, OTHER_LABEL='Deutsch' if en else 'English',
                    PAGE_TITLE=escape(page['title']), EPISODE_TITLE=escape(data['title']), STYLE_URL='stil.css', LOGO_URL='logo.svg',
                    OVERVIEW_URL=overview, SERIES_LABEL='Writing practice' if en else 'Schreibpraxis', PAGE_POSITION=str(i+1), PAGE_COUNT=str(len(pages)),
                    NAV_LABEL='Stages in this episode' if en else 'Stationen dieser Folge', EPISODE_URL=pages[0]['file'], NAV_ITEMS_HTML=navigation,
                    SIMULATION_NOTICE_HTML=f'<aside class="simulation"><strong>{notice_title}</strong>{escape(data["notice"])}</aside>',
                    STAGE_LABEL=escape(page['label']), LEAD=escape(page['lead']), CONTENT_HTML=blocks, PROGRESS_PERCENT=f'{(i+1)/len(pages)*100:.2f}',
                    PREVIOUS_LINK_HTML=f'<a href="{pages[i-1]["file"]}" rel="prev">← {back}</a>' if i else '<span></span>',
                    NEXT_LINK_HTML=f'<a href="{pages[i+1]["file"]}" rel="next">{next_label}: {escape(pages[i+1]["label"])} →</a>' if i+1<len(pages) else f'<a href="{pages[0]["file"]}">{start_label} ↗</a>',
                    OVERVIEW_LABEL='To the overview' if en else 'Zur Übersicht', CLAUDE_CREDIT=credit+' Claude (Anthropic)', CODEX_CREDIT=credit+' Codex (OpenAI)')
                (destination/page['file']).write_text(template.substitute(values), encoding='utf-8')
            print(f'{len(pages)} Seiten ({lang}) lokal erzeugt: {destination.relative_to(ROOT)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true', help='Zusätzlich lokale Website-Ausgabe erzeugen; kein Upload oder Deploy')
    args = parser.parse_args()
    build()
    if args.publish:
        build(published=True)
