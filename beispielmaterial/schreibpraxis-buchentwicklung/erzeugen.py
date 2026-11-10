"""Deutschen lokalen Entwurf der dritten Schreibpraxis-Folge erzeugen."""
from pathlib import Path
from html import escape
import shutil
import argparse
import content_en
from inhalt import PAGES as DE_PAGES, CONCEPT as DE_CONCEPT

ROOT = Path(__file__).resolve().parent
for name in ['logo.svg', 'stil.css']:
    shutil.copyfile(ROOT.parent/'schreiben-mit-ghostwriter'/name, ROOT/name)
CSS = '''
.episode-title{display:block;font:normal 25px/1.3 Georgia,serif;color:var(--ink);text-decoration:none;margin:0 0 24px;padding-bottom:18px;border-bottom:1px solid var(--line)}.simulation{margin:28px 0 0;padding:16px 20px;background:#fff0df;border-left:4px solid var(--orange);font-size:14px;line-height:1.65}.simulation strong{display:block;color:var(--accent);margin-bottom:5px}.conversation{margin:30px 0}.conversation .message{max-width:90%;margin-bottom:22px}.conversation .message p{font-size:18px}.editorial{padding:18px 22px;border-left:3px solid var(--line);font-size:15px;color:var(--muted);margin:28px 0}.editorial p{margin:0}table{width:100%;border-collapse:collapse;margin:30px 0;font-size:15px}caption{text-align:left;font:normal 28px/1.3 Georgia,serif;margin-bottom:18px}th,td{text-align:left;vertical-align:top;padding:14px 12px;border-bottom:1px solid var(--line)}th{width:32%;font-weight:650}tr:nth-child(odd){background:#fffefa}.status{text-align:right;font-size:14px}@media(max-width:760px){.conversation .message{max-width:100%}.conversation .message p{font-size:16px}th,td{padding:12px 8px;overflow-wrap:anywhere}}@media print{.message,.simulation{break-inside:avoid}}
'''
(ROOT/'folge.css').write_text(CSS.strip()+'\n',encoding='utf-8')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--publish', action='store_true', help='Statische Dateien in website/buchentwicklung/ vorbereiten, kein Upload')
args = parser.parse_args()
for language, PAGES, CONCEPT in [('de', DE_PAGES, DE_CONCEPT), ('en', content_en.PAGES, content_en.CONCEPT)]:
    for i,(filename,label,title,lead,dialogue,result_title,result,note) in enumerate(PAGES):
        en = language == 'en'
        counterpart = DE_PAGES[i][0] if en else content_en.PAGES[i][0]
        other_label = 'Deutsch' if en else 'English'
        other_lang = 'de' if en else 'en'
        series = 'Writing practice' if en else 'Schreibpraxis'
        episode = 'An idea becomes a crime novel' if en else 'Aus einer Idee wird ein Krimi'
        credit = 'Developed with support from' if en else 'Entwickelt mit Unterstützung von'
        kind = 'Book development' if en else 'Buchentwicklung'
        status = '' if args.publish else ('Local draft · ' if en else 'Lokaler Entwurf · ')
        local = '' if args.publish else (' · Local English draft' if en else ' · Lokale deutsche Arbeitsfassung')
        notice = 'The author, book idea, characters and all dialogue are fictional. The example illustrates one possible conversation; it is not an original conversation and does not create a real book.' if en else 'Autorenperson, Buchidee, Figuren und sämtliche Gesprächsbeiträge sind erfunden. Das Beispiel veranschaulicht eine mögliche Dialogführung; es ist kein Originalgespräch und legt kein echtes Buch an.'
        menu=''.join(f'<li><a href="{p[0]}"'+(' aria-current="page"' if j==i else '')+f'>{escape(p[1])}</a></li>' for j,p in enumerate(PAGES))
        messages=''.join(f'<div class="message {"author" if role in ("Autor", "Author") else "assistant"}"><strong>{role}</strong><p>{escape(words)}</p></div>' for role,words in dialogue)
        table=''
        if i==len(PAGES)-1:
            rows=''.join(f'<tr><th scope="row">{escape(k)}</th><td>{escape(v)}</td></tr>' for k,v in CONCEPT)
            table=f'<table><caption>{"Basic details from this conversation" if en else "Grundangaben aus diesem Gespräch"}</caption><tbody>{rows}</tbody></table>'
        previous=f'<a href="{PAGES[i-1][0]}" rel="prev">← {"Back" if en else "Zurück"}</a>' if i else '<span></span>'
        following=f'<a href="{PAGES[i+1][0]}" rel="next">{"Next" if en else "Weiter"}: {escape(PAGES[i+1][1])} →</a>' if i+1<len(PAGES) else f'<a href="{PAGES[0][0]}">{"Back to the beginning" if en else "Zum Anfang"} ↗</a>'
        html=f'''<!doctype html><html lang="{language}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · {kind}</title><link rel="stylesheet" href="stil.css"><link rel="stylesheet" href="folge.css"><link rel="alternate" hreflang="{other_lang}" href="{counterpart}"></head><body>
    <header><a class="brand" href="{PAGES[0][0]}"><img src="logo.svg" alt="" width="48" height="48"><span>GhostWriter<small>{series}</small></span></a><span class="status"><a href="{counterpart}" lang="{other_lang}">{other_label}</a> · {kind}<br>{status}{i+1} / {len(PAGES)}</span></header>
    <main class="layout"><nav aria-label="{"Stages in this episode" if en else "Stationen dieser Folge"}"><a class="episode-title" href="{PAGES[0][0]}">{episode}</a><ol>{menu}</ol><aside class="simulation"><strong>{"Entirely simulated dialogue" if en else "Vollständig simulierter Dialog"}</strong>{notice}</aside></nav><article><div class="eyebrow">{escape(label)}</div><h1>{escape(title)}</h1><p class="lead">{escape(lead)}</p><div class="conversation" aria-label="{"Simulated conversation" if en else "Simuliertes Gespräch"}">{messages}</div><aside class="result"><h2>{escape(result_title)}</h2><p>{escape(result)}</p></aside>{table}<aside class="editorial"><p>{escape(note)}</p></aside><div class="progress" aria-hidden="true"><span style="width:{(i+1)/len(PAGES)*100:.2f}%"></span></div><div class="pager">{previous}{following}</div></article></main>
    <footer><p><a href="../../website/schreibpraxis{".en" if en else ""}.html">{"To the overview" if en else "Zur Übersicht"}</a>{local} · {"10 November 2026" if en else "10. November 2026"}</p><p>{credit} Claude (Anthropic)<br>{credit} Codex (OpenAI)</p></footer></body></html>'''
        (ROOT/filename).write_text(html,encoding='utf-8')
if args.publish:
    destination = ROOT.parents[1]/'website'/'buchentwicklung'
    destination.mkdir(parents=True, exist_ok=True)
    for name in [p[0] for p in DE_PAGES + content_en.PAGES] + ['stil.css', 'folge.css', 'logo.svg']:
        if name.endswith('.html'):
            text = (ROOT/name).read_text(encoding='utf-8').replace('../../website/schreibpraxis', '../schreibpraxis')
            (destination/name).write_text(text,encoding='utf-8')
        else:
            shutil.copyfile(ROOT/name, destination/name)
print('Zwölf Seiten zur Buchentwicklung erzeugt; kein Upload.')
