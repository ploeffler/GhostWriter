"""Lokale Folge der Serie Schreibpraxis aus dem simulierten Drehbuch erzeugen."""
from pathlib import Path
from html import escape
import re
import shutil
import markdown
import argparse
from ui_en import TEXT

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent / 'schreiben-mit-ghostwriter'
SOURCE = ''

def md(text):
    return markdown.markdown(text.strip(), extensions=['fenced_code'])

def chapter(number):
    match = re.search(rf'^## {number}\. .*?\n(.*?)(?=^## |\Z)', SOURCE, re.M | re.S)
    return match.group(1).strip()

def message(role, text, author=False):
    return f'<div class="message {"author" if author else "assistant"}"><strong>{escape(role)}</strong>{md(text)}</div>'

def dialogue_page():
    text = chapter(3)
    intro = re.split(r'### (?:Runde|Round)', text)[0]
    blocks = []
    rounds = list(re.finditer(r'^### ((?:Runde|Round) .*?)\n(.*?)(?=^### |\Z)', text, re.M | re.S))
    assert len(rounds) == 5
    for match in rounds:
        heading, body = match.groups()
        exchanges = re.findall(r'^\*\*(.*?)\*\*\s*\n\s*> (.*?)(?=\n\n)', body+'\n\n', re.M | re.S)
        assert len(exchanges) == 4, heading
        questions = ''.join(message(role.rstrip(':'), answer) for role, answer in exchanges[:3])
        role, answer = exchanges[3]
        takeaway = re.split(r'\*\*(?:Was hinzugekommen ist|What we have learned):\*\*', body, maxsplit=1)[1].strip()
        blocks.append(f'<section class="round"><h2>{escape(heading)}</h2><div class="variants">{questions}</div>{message(role.rstrip(":"), answer, True)}<div class="takeaway"><strong>Was hinzugekommen ist</strong>{md(takeaway)}</div></section>')
    return md(intro) + ''.join(blocks)

def drafts_page():
    text = chapter(5)
    intro = text.split('### A.')[0]
    drafts = re.findall(r'^### ([ABC]\. .*?)\n(.*?)(?=^### |\Z)', text, re.M | re.S)
    assert len(drafts) == 3
    return '<details><summary>Der gemeinsame Ausarbeitungsauftrag</summary>'+md(chapter(4))+'</details>'+md(intro)+''.join(f'<section class="draft"><div class="eyebrow">Simulierter Entwurf</div><h2>{escape(h)}</h2>{md(t)}</section>' for h,t in drafts)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--publish', action='store_true', help='Beide Sprachen für website/augmentiert/ lokal vorbereiten; kein Upload')
args = parser.parse_args()
for language in ('de', 'en'):
    SOURCE = (ROOT / ('drehbuch.md' if language == 'de' else 'drehbuch.en.md')).read_text(encoding='utf-8')
    selection, final = re.split(r'### (?:Mögliche gemeinsam redigierte Fassung|A possible jointly edited version)', chapter(6), maxsplit=1)
    intro = '<section><h2>Eine kleine Alltagsszene</h2>'+md(chapter(1))+'</section><details><summary>Den gemeinsamen Startprompt lesen</summary>'+md(chapter(2))+'</details><aside class="result"><h2>Was „augmentiert“ hier bedeutet</h2><p>Der Mensch bringt Erfahrung, Antworten und Urteil ein. Die KI unterstützt beim Fragen, Ordnen und Formulieren. Wir zeigen, wie beides zusammenwirkt.</p></aside>'
    PAGES = [
        ('index.html', 'Ein Brief, drei Schreibdialoge', 'Augmentiert arbeiten', 'Ein Ausgangssatz. Drei mögliche Schreibdialoge. Und ein Mensch, der entscheidet, was daraus wird.', intro),
        ('01-dialoge.html', '01 · Die fünf Fragerunden', 'Aus einem Satz wird Material', 'Drei Fragevarianten pro Runde, eine gemeinsame Antwort: So bleibt die Informationsgrundlage für alle Entwürfe gleich.', dialogue_page()),
        ('02-entwuerfe.html', '02 · Drei Entwürfe', 'Dasselbe Material, andere Texte', 'Die Angaben bleiben gleich. Rhythmus, Bilder und Pointen verändern sich. Alle drei Texte sind für dieses Beispiel erfunden.', drafts_page()),
        ('03-auswahl.html', '03 · Der Mensch wählt', 'Was klingt nach mir?', 'Die Vorschläge liegen auf dem Tisch. Jetzt entscheidet die Beispielperson, welche Formulierungen passen und wo eine Zuspitzung zu weit geht.', '<section>'+md(selection)+'</section><aside class="result"><h2>Auch die Rückmeldung ist ein Beitrag</h2><p>Auswählen, verwerfen, Grenzen setzen: Die Person bestimmt die Stimme der nächsten Fassung. Ihre Ungewissheit bleibt ein Teil der Geschichte.</p></aside>'),
        ('04-fassung.html', '04 · Gemeinsam redigieren', 'Eine mögliche Fassung', 'Diese Fassung verbindet ausgewählte Formulierungen mit der Rückmeldung der erfundenen Beispielperson. Sie ist ein weiterer Vorschlag.', '<section class="draft final-draft"><div class="eyebrow">Simuliertes Redaktionsergebnis</div>'+md(final)+'</section><aside class="result"><h2>Das Ende bleibt offen</h2><p>Der Brief wurde noch nicht abgeschickt. Die Überarbeitung macht den Text stimmiger, ohne der Person einen Erfolg oder eine Erklärung zuzuschreiben.</p></aside>'),
        ('05-einordnung.html', '05 · Was zusammenwirkt', 'Erfahrung, Vorschlag und Urteil', 'Das Beispiel zeigt eine Arbeitsweise. Es bewertet keine Anbieter und behauptet keinen tatsächlichen Modellvergleich.', '<section>'+md(chapter(7))+'</section><aside class="result"><h2>Der gemeinsame Weg</h2><p>Ausgangssituation → Nachfragen → Antworten → Entwürfe → menschliche Auswahl → redigierte Fassung. An jedem Übergang kann der Mensch korrigieren und die Richtung ändern.</p></aside>'),
    ]

    shutil.copyfile(PREVIOUS/'stil.css', ROOT/'stil.css')
    shutil.copyfile(PREVIOUS/'logo.svg', ROOT/'logo.svg')
    EXTRA = '''
    .simulation{margin:28px 0 0;padding:16px 20px;background:#fff0df;border-left:4px solid var(--orange);font-size:14px;line-height:1.65}.simulation strong{display:block;color:var(--accent);margin-bottom:5px}.variants{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.variants .message{max-width:none;margin:0}.variants .message strong{line-height:1.5}.round .author{max-width:92%;margin:20px 0 20px auto}.takeaway{font-size:15px;color:var(--muted);padding:0 16px;border-left:2px solid var(--line)}.takeaway p{margin:6px 0}.round{margin-top:25px}.draft{background:#fffefa;border:1px solid var(--line);padding:26px;margin:24px 0;border-radius:8px}.draft p{margin:16px 0}.draft h2{margin-top:12px}.final-draft{font:21px/1.85 Georgia,serif}.final-draft .eyebrow{font-family:system-ui,sans-serif}.final-draft p:first-of-type{margin-top:20px}details{margin:24px 0;border:1px solid var(--line);border-radius:8px;padding:18px 22px;background:#fffefa}summary{cursor:pointer;font-weight:650;color:var(--accent)}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.7 ui-monospace,monospace;background:#f0f3f1;padding:20px;border-radius:6px}blockquote{margin:24px 0;padding:18px 24px;background:#fff0df;border-left:3px solid var(--orange);border-radius:0 8px 8px 0}blockquote p{margin:0}article>p{color:var(--muted)}section ul{padding-left:24px}section li{margin:12px 0}.episode-title{display:block;font:normal 25px/1.3 Georgia,serif;color:var(--ink);text-decoration:none;margin:0 0 24px;padding:0 0 18px;border-bottom:1px solid var(--line)}.status{text-align:right}@media(min-width:1100px){header,main,footer{max-width:1260px}.layout{grid-template-columns:210px 1fr;gap:48px}}@media(max-width:1050px){.variants{grid-template-columns:1fr}.variants .message{margin:5px 0}.round .author{max-width:100%}}@media print{.variants{grid-template-columns:1fr}.message,.simulation{break-inside:avoid}.draft{border:0}}
    '''
    (ROOT/'folge.css').write_text(EXTRA.strip() + '\n', encoding='utf-8')
    for i, (filename, label, title, lead, body) in enumerate(PAGES):
        menu = ''.join(f'<li><a href="{p[0]}"'+(' aria-current="page"' if j == i else '')+f'>{escape('Auftakt' if j == 0 else p[1])}</a></li>' for j,p in enumerate(PAGES))
        previous = f'<a href="{PAGES[i-1][0]}" rel="prev">← Zurück</a>' if i else '<span></span>'
        following = f'<a href="{PAGES[i+1][0]}" rel="next">Weiter: {escape(PAGES[i+1][1])} →</a>' if i+1<len(PAGES) else '<a href="index.html">Zum Anfang ↗</a>'
        page = f'''<!doctype html>
    <html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>{escape(title)} · Augmentiert arbeiten</title><link rel="stylesheet" href="stil.css"><link rel="stylesheet" href="folge.css"></head>
    <body><header><a class="brand" href="index.html"><img src="logo.svg" alt="" width="48" height="48"><span>GhostWriter<small>Schreibpraxis</small></span></a><span class="status">Augmentiert arbeiten<br>Lokaler Entwurf · {i+1} / {len(PAGES)}</span></header>
    <main class="layout"><nav aria-label="Stationen dieser Folge"><a class="episode-title" href="index.html">Ein Brief,<br>drei Schreibdialoge</a><ol>{menu}</ol><aside class="simulation"><strong>Vollständig simuliertes Beispiel</strong>Situation, Fragen, Antworten und Textfassungen sind erfunden. Die mit Gemini und Perplexity bezeichneten Varianten sind nachgestellt; es gab dafür keine Anbieteraufrufe. Auch die Variante des begleitenden Assistenten ist Teil der Simulation. Kein Leistungsvergleich.</aside></nav><article><div class="eyebrow">{escape(label)}</div><h1>{escape(title)}</h1><p class="lead">{escape(lead)}</p>{body}<div class="progress" aria-hidden="true"><span style="width:{(i+1)/len(PAGES)*100:.2f}%"></span></div><div class="pager">{previous}{following}</div></article></main>
    <footer><p>Augmentiert arbeiten · Lokale deutsche Arbeitsfassung · 10. November 2026</p><p>Entwickelt mit Unterstützung von Claude (Anthropic)<br>Entwickelt mit Unterstützung von Codex (OpenAI)</p></footer></body></html>'''
        counterpart = filename.replace('.html', '.en.html') if language == 'de' else filename
        if language == 'en':
            for original, translated in sorted(TEXT.items(), key=lambda item: -len(item[0])):
                page = page.replace(original, translated)
            page = page.replace('lang="de"', 'lang="en"').replace('.html', '.en.html')
            filename = filename.replace('.html', '.en.html')
        other_label = 'English' if language == 'de' else 'Deutsch'
        other_lang = 'en' if language == 'de' else 'de'
        page = page.replace('<span class="status">', f'<span class="status"><a href="{counterpart}" lang="{other_lang}">{other_label}</a> · ')
        page = page.replace('</head>', f'<link rel="alternate" hreflang="{other_lang}" href="{counterpart}"></head>')
        home = '../../website/index.html' if language == 'de' else '../../website/index.en.html'
        home_label = 'GhostWriter-Startseite' if language == 'de' else 'GhostWriter home'
        page = page.replace('<footer>', f'<footer><p><a href="{home}">{home_label}</a></p>')
        if args.publish:
            page = page.replace('<meta name="robots" content="noindex,nofollow">', '')
            page = page.replace('Lokaler Entwurf · ', '').replace('Local draft · ', '')
            page = page.replace(' · Lokale deutsche Arbeitsfassung', '').replace(' · Local English draft', '')
        (ROOT/filename).write_text(page, encoding='utf-8')
if args.publish:
    destination = ROOT.parents[1]/'website'/'augmentiert'
    destination.mkdir(parents=True, exist_ok=True)
    names = [p.name for p in ROOT.glob('*.html')] + ['stil.css', 'folge.css', 'logo.svg']
    for name in names:
        if name.endswith('.html'):
            content = (ROOT/name).read_text(encoding='utf-8').replace('../../website/index', '../index')
            (destination/name).write_text(content, encoding='utf-8')
        else:
            shutil.copyfile(ROOT/name, destination/name)
print('Zwölf Seiten in Deutsch und Englisch erzeugt. Kein Upload.')
