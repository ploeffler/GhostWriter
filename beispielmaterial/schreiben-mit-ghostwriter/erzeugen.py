"""Abstrahierten Ablauf zweisprachig erzeugen; --publish kopiert nur freigegebene Webdateien."""
from pathlib import Path
from html import escape
import argparse
import shutil
import english

ROOT = Path(__file__).parent
PAGES = [
    ('index.html', 'Vom Gespräch zum eigenen Text', 'Schreiben mit GhostWriter',
     'Ein Buch wächst im Austausch. Dieses Beispiel zeigt, wie Erinnerungen, ein zusätzlicher Text und die Rückmeldung des Autors zu einer überarbeiteten Erzählung werden.',
     [('Der Weg durch das Beispiel', 'Wir begleiten die Arbeit an einem ersten Kapitel und später an einem einzelnen Abschnitt. Dabei wird sichtbar, wie Material gesammelt, geschrieben und sprachlich weiterentwickelt wird.'),
      ('Aus einem echten Arbeitsverlauf', 'Die Schritte beruhen auf einem Buchprojekt. Persönliche Inhalte und Projektdaten wurden weggelassen oder abstrahiert. Die Darstellung ist verdichtet; sie bildet keinen wörtlichen Chat ab.')],
     ('Das Prinzip', 'Der Autor liefert Erfahrungen, entscheidet über die Richtung und beurteilt den Text. GhostWriter fragt nach, ordnet Material und erarbeitet Fassungen.')),
    ('01-kapitel.html', '01 · Das erste Kapitel', 'Aus Erinnerungen werden Szenen',
     'Am Anfang stehen Erlebnisse und Gedanken. Ein fertiger Text muss noch nicht vorhanden sein.',
     [('Erzählen und nachfragen', 'Der Autor berichtet von einer beruflichen Szene und einer Alltagserfahrung. Rückfragen klären die Reihenfolge, den erinnerten Wortlaut und das, was noch unsicher ist.'),
      ('Schreiben und konkretisieren', 'Nach der Schreibfreigabe entsteht eine erste Fassung aus drei Abschnitten. Beim Lesen zeigt sich: Eine allgemeine Erklärung bleibt zu fern. Sie wird durch eine konkrete Erinnerung ersetzt.'),
      ('Den Einstieg weiterentwickeln', 'Weitere Rückmeldungen verändern die Leseransprache und den Übergang zur ersten Szene. Das Kapitel entsteht in mehreren Überarbeitungen.')],
     ('Was sich verändert', 'Aus gesammelten Erinnerungen wird ein zusammenhängendes Kapitel. Die konkreten Erlebnisse tragen den Text.')),
    ('02-abschnitt.html', '02 · Ein späterer Abschnitt', 'Eine Stelle im Buch finden',
     'Nicht jedes neue Material gehört an dieselbe Stelle. Zuerst wird geklärt, was dieser Abschnitt erzählen soll.',
     [('Die Aufgabe abgrenzen', 'Ein späteres Kapitel soll zeigen, wie frühere Erfahrungen neu betrachtet werden. Andere Teile des Buchs vertiefen, was sich daraus für die Gegenwart ergibt.'),
      ('Vorhandenes Material nutzen', 'Bereits erzählte Erinnerungen und neue Antworten werden zusammengeführt. Offene Fragen bleiben sichtbar. Das Material dient als Grundlage für den Abschnitt.'),
      ('Vom Vorschlag zum Manuskript', 'Zunächst wird eine Fassung im Gespräch gezeigt. Nach dem Schreibauftrag wird sie als Manuskript gespeichert. Die übrigen Abschnitte des Kapitels sind dadurch noch nicht geschrieben.')],
     ('Was sich verändert', 'Der neue Abschnitt bekommt eine klare Aufgabe und einen Platz im Buch. Materialsammlung und Manuskript bleiben unterscheidbar.')),
    ('03-text.html', '03 · Ein weiterer Text', 'Vorhandene Arbeit mitbringen',
     'Auch ein Text, der in einem anderen KI-Dialog erarbeitet wurde, kann Ausgangsmaterial sein.',
     [('Den Text einbringen', 'Der Autor stellt eine bereits erarbeitete Fassung bereit. Sie ergänzt die Erinnerungen und Antworten aus dem laufenden Austausch.'),
      ('Bedeutung und Details klären', 'Der Autor präzisiert, welche Aussagen seiner Erfahrung entsprechen und wie eine Veränderung gemeint ist. Diese Klarstellungen bestimmen die weitere Fassung.'),
      ('Im Buchzusammenhang weiterarbeiten', 'Aus dem zusätzlichen Text und den bestätigten Angaben entsteht eine neue Erzählfassung. Übergänge und Verbindungen zu anderen Kapiteln werden mit angepasst.')],
     ('Was sich verändert', 'Die bisherige Arbeit geht in die Entwicklung ein. Der Autor kann weiterarbeiten, ohne jeden Gedanken erneut erzählen zu müssen.')),
    ('04-stimme.html', '04 · Die eigene Erzählstimme', 'Damit es nach dem Autor klingt',
     'Ein Text kann inhaltlich passen und trotzdem zu distanziert wirken. Dann wird an der Art des Erzählens gearbeitet.',
     [('Die Stimme beschreiben', 'Für das Buch wird der gewünschte Rhythmus präzisiert: klar geführte, mittellange und längere Erzählsätze; kurze Sätze gezielt für Dialog, Wendungen und Pointen.'),
      ('Am Abschnitt ausprobieren', 'Eine zusammenfassende Darstellung wird persönlicher und unmittelbarer. Konkrete Beobachtungen, natürlicher Sprechrhythmus und selbstironische Bilder prägen die neue Stilprobe.'),
      ('Gemeinsam verfeinern', 'Der Autor beurteilt die Probe und ergänzt eigene Bilder und Szenen. Daraus wächst die vollständige Fassung. Eine örtliche Stiländerung wird dabei nicht automatisch zur Vorgabe für das ganze Buch.')],
     ('Was sich verändert', 'Erzählabstand, Rhythmus und Szenengestaltung verändern die Wirkung. Die Stimme wird am konkreten Text erprobt und durch Rückmeldung weiterentwickelt.')),
    ('05-pruefen.html', '05 · Die Arbeitsfassung prüfen', 'Lesen, verbessern, entscheiden',
     'Nach den Ergänzungen wird der vollständige betroffene Abschnitt erneut geprüft.',
     [('Den Zusammenhang lesen', 'Passen Reihenfolge, Übergänge und Erzählstimme? Wiederholt der Abschnitt etwas aus einem anderen Kapitel? Bleiben berichtete Erinnerung und heutige Deutung unterscheidbar?'),
      ('Unsicherheit erhalten', 'Offene Zeitangaben werden benannt. Lücken werden nicht durch erfundene Ereignisse oder Reaktionen geschlossen.'),
      ('Den Stand richtig einordnen', 'Das Beispiel endet bei einer gespeicherten, überarbeiteten Arbeitsfassung. Eine Schreibfreigabe oder gespeicherte Änderung ersetzt nicht die endgültige Abnahme durch den Autor.')],
     ('Der Ablauf auf einen Blick', 'Erzählen → nachfragen → ordnen → schreiben → lesen → Stimme anpassen → prüfen. Zwischen diesen Schritten kann der Autor jederzeit ergänzen und die Richtung ändern.')),
]

DIALOGUES = {
    '01-kapitel.html': (0, 'Eine Erinnerung greifbar machen', [
        ('Autor', 'Ich hatte auf ein Problem hingewiesen. Hinterher ging es aber nur noch darum, wie ich es gesagt hatte.'),
        ('GhostWriter', 'Erinnerst du dich an eine konkrete Situation? Was hast du gesagt, und was kam als Antwort?'),
        ('Autor', 'Den genauen Wortlaut weiß ich nicht mehr. Aber die Reihenfolge kann ich dir erzählen.'),
        ('GhostWriter', 'Dann halten wir die Reihenfolge fest. Den unsicheren Wortlaut behandeln wir als sinngemäße Erinnerung.')]),
    '03-text.html': (1, 'Einen mitgebrachten Text weiterentwickeln', [
        ('Autor', 'Hier ist ein Text, den ich schon in einem anderen Chat erarbeitet habe. Der trifft einiges besser als unser erster Entwurf.'),
        ('GhostWriter', 'Der Text beschreibt, dass heute alles leichter ist. Meinst du die Aufgaben selbst oder deinen Blick auf dich?'),
        ('Autor', 'Eher meinen Blick auf mich. Die Aufgaben sind immer noch schwierig.'),
        ('GhostWriter', 'Dann arbeiten wir diesen Unterschied heraus: Der Alltag bleibt anstrengend, aber du beurteilst dich anders.')]),
    '04-stimme.html': (1, 'Die Stimme am Text ausprobieren', [
        ('Autor', 'Das klingt noch wie ein Bericht über mich. Ich erzähle eigentlich direkter. Und ein bisschen Selbstironie darf schon sein.'),
        ('GhostWriter', 'Ich probiere es an einer kurzen Stelle: „Mein Schreibtisch war bestens organisiert. Jedenfalls wusste jeder Papierstapel genau, wo er seit Monaten stand.“'),
        ('Autor', 'Ja, eher so. Aber nicht in jedem Absatz eine Pointe. Die Stelle danach soll ernst bleiben.'),
        ('GhostWriter', 'Dann bleibt das Bild an dieser Stelle. Den folgenden Gedanken erzähle ich ruhiger und in längeren Sätzen.')]),
}

CSS = '''
:root{color-scheme:light;--ink:#183438;--muted:#526a6d;--accent:#12675b;--line:#cedbd5;--paper:#fbfaf6}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:18px/1.7 system-ui,sans-serif}a{color:var(--accent);text-underline-offset:4px}a:focus-visible{outline:3px solid #b46e25;outline-offset:5px}header,main,footer{max-width:1120px;margin:auto;padding:24px 40px}header{display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);font-size:14px}.brand{font-weight:750;text-decoration:none;letter-spacing:.04em}.status{color:var(--muted)}.layout{display:grid;grid-template-columns:220px 1fr;gap:64px;padding-top:48px}nav ol{padding:0;list-style:none}nav li{margin:0 0 16px}nav a{display:block;font-size:14px;text-decoration:none;color:var(--muted);padding-left:12px;border-left:3px solid transparent}nav a[aria-current]{border-color:var(--accent);color:var(--accent);font-weight:750}.eyebrow{font-size:13px;text-transform:uppercase;letter-spacing:.12em;color:var(--accent);font-weight:750}h1{font:normal clamp(36px,4.3vw,58px)/1.12 Georgia,serif;margin:16px 0 24px;max-width:760px}h2{font-size:21px;line-height:1.35;margin:0 0 10px}.lead{font-size:21px;color:var(--muted);margin-bottom:40px}section{padding:24px 0;border-top:1px solid var(--line)}section p{margin:0}.result{background:#e8eee7;padding:26px 30px;margin:28px 0;border-radius:4px}.result h2{font-size:15px;color:var(--accent)}.pager{display:flex;justify-content:space-between;gap:20px;margin:40px 0 20px;font-size:16px}.pager a{font-weight:650}.progress{height:4px;background:#e0e6df;margin-top:28px}.progress span{display:block;height:100%;background:var(--accent)}footer{font-size:12px;color:var(--muted);border-top:1px solid var(--line);margin-top:40px}footer p{margin:6px 0}@media(max-width:760px){header,main,footer{padding:20px}.layout{display:block;padding-top:25px}nav ol{display:flex;overflow-x:auto;gap:16px;padding-bottom:12px}nav li{flex:0 0 145px;margin:0}h1{font-size:40px}.lead{font-size:19px}.pager{font-size:14px}}@media print{nav,.pager,header{display:none}.layout{display:block}footer{margin-top:20px}body{font-size:12pt}}
'''
CSS += '''
.dialogue{margin:28px 0 8px;padding:24px;background:#f0f3f1;border:1px solid var(--line);border-radius:8px}.dialogue h3{margin:0 0 6px;font-size:18px}.dialogue .fiction{font-size:13px;color:var(--muted);margin:0 0 22px}.message{max-width:94%;padding:14px 18px;margin:12px 0;background:white;border:1px solid var(--line);border-radius:12px 12px 12px 2px}.message.author{margin-left:auto;background:#e0ece5;border-color:#c4d7ca;border-radius:12px 12px 2px 12px}.message strong{display:block;font-size:12px;letter-spacing:.04em;color:var(--accent);margin-bottom:5px}.message p{margin:0;font-size:16px;line-height:1.65}@media(max-width:760px){.dialogue{padding:16px}.message{max-width:100%}}
'''
CSS += '''
:root{--accent:#b9551d;--orange:#f07f2e}.brand{display:flex;align-items:center;gap:12px;letter-spacing:.02em;color:var(--ink)}.brand img{width:48px;height:48px;flex:none}.brand small{display:block;font-size:12px;font-weight:500;letter-spacing:.04em;color:var(--muted)}header{align-items:center;border-bottom:3px solid var(--orange)}.result{background:#fff0df;border-left:4px solid var(--orange)}.progress span{background:var(--orange)}nav a[aria-current]{background:#fff0df;border-color:var(--orange);border-radius:0 5px 5px 0}.dialogue{border-top:3px solid var(--orange)}.message.author{background:#fff0df;border-color:#e8cdb7}.pager a:hover{color:#8a3c14}@media(max-width:760px){.brand img{width:40px;height:40px}.status{font-size:12px}}
'''
(ROOT/'stil.css').write_text(CSS, encoding='utf-8')
DE_PAGES = PAGES
DE_DIALOGUES = DIALOGUES
for lang, PAGES, DIALOGUES in [('de', DE_PAGES, DE_DIALOGUES), ('en', english.PAGES, english.DIALOGUES)]:
 for i, (filename, label, title, lead, sections, result) in enumerate(PAGES):
    en = lang == 'en'
    home = PAGES[0][0]
    counterpart = DE_PAGES[i][0] if en else english.PAGES[i][0]
    language_label = 'Deutsch' if en else 'English'
    site_home = '../../website/index.en.html' if en else '../../website/index.html'
    site_label = 'GhostWriter home' if en else 'GhostWriter-Startseite'
    fiction = 'Fictional dialogue example · Illustrates the process; these are not original quotes. The sample prose is fictional too.' if en else 'Erfundenes Dialogbeispiel · Zur Veranschaulichung des Ablaufs, kein Originalzitat. Auch die Textprobe ist erfunden.'
    credit = 'Developed with support from' if en else 'Entwickelt mit Unterstützung von'
    footer = 'Abstracted example based on a real writing process. Not a verbatim conversation. As of 9 November 2026.' if en else 'Abstrahiertes Fallbeispiel aus einem tatsächlichen Arbeitsverlauf. Keine wörtliche Gesprächswiedergabe. Stand: 9. November 2026.'
    subtitle = 'Writing practice' if en else 'Schreibpraxis'
    series = 'Writing with GhostWriter' if en else 'Schreiben mit GhostWriter'
    menu = ''.join(f'<li><a href="{escape(p[0])}"'+(' aria-current="page"' if j == i else '')+f'>{escape(p[1])}</a></li>' for j,p in enumerate(PAGES))
    parts = []
    for section_index, (h, t) in enumerate(sections):
        parts.append(f'<section><h2>{escape(h)}</h2><p>{escape(t)}</p></section>')
        if filename in DIALOGUES and section_index == DIALOGUES[filename][0]:
            _, heading, messages = DIALOGUES[filename]
            turns = ''.join(f'<div class="message {"author" if role in ("Autor", "Author") else "assistant"}"><strong>{escape(role)}</strong><p>{escape(words)}</p></div>' for role, words in messages)
            parts.append(f'<aside class="dialogue" aria-label="{"Fictional dialogue example" if en else "Erfundenes Dialogbeispiel"}"><h3>{escape(heading)}</h3><p class="fiction">{fiction}</p>{turns}</aside>')
    body = ''.join(parts)
    previous = f'<a href="{PAGES[i-1][0]}" rel="prev">← {"Back" if en else "Zurück"}</a>' if i else '<span></span>'
    following = f'<a href="{PAGES[i+1][0]}" rel="next">{"Next" if en else "Weiter"}: {escape(PAGES[i+1][1])} →</a>' if i+1<len(PAGES) else f'<a href="{home}">{"Back to the beginning" if en else "Zum Anfang"} ↗</a>'
    html = f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · {series}</title><link rel="stylesheet" href="stil.css"><link rel="alternate" hreflang="{'de' if en else 'en'}" href="{counterpart}"></head>
<body><header><a class="brand" href="{home}"><img src="logo.svg" alt="" width="48" height="48"><span>GhostWriter<small>{subtitle}</small></span></a><span class="status"><a href="{counterpart}" lang="{'de' if en else 'en'}">{language_label}</a> · {i+1} / {len(PAGES)}</span></header>
<main class="layout"><nav aria-label="{'Stages' if en else 'Stationen'}"><ol>{menu}</ol></nav><article><div class="eyebrow">{escape(label)}</div><h1>{escape(title)}</h1><p class="lead">{escape(lead)}</p>{body}<aside class="result"><h2>{escape(result[0])}</h2><p>{escape(result[1])}</p></aside><div class="progress" aria-hidden="true"><span style="width:{(i+1)/len(PAGES)*100:.2f}%"></span></div><div class="pager">{previous}{following}</div></article></main>
<footer><p><a href="{site_home}">{site_label}</a> · <a href="{counterpart}">{language_label}</a></p><p>{footer}</p><p>{credit} Claude (Anthropic)<br>{credit} Codex (OpenAI)</p></footer></body></html>'''
    (ROOT/filename).write_text(html, encoding='utf-8')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--publish', action='store_true', help='Statische Dateien unter website/schreibpraxis/ bereitstellen; kein Upload')
args = parser.parse_args()
if args.publish:
    destination = ROOT.parents[1]/'website'/'schreibpraxis'
    destination.mkdir(parents=True, exist_ok=True)
    for name in [p[0] for p in DE_PAGES + english.PAGES] + ['stil.css', 'logo.svg']:
        if name.endswith('.html'):
            text = (ROOT/name).read_text(encoding='utf-8').replace('../../website/index', '../index')
            (destination/name).write_text(text, encoding='utf-8')
        else:
            shutil.copyfile(ROOT/name, destination/name)
print('Zwölf HTML-Seiten und gemeinsames Stylesheet erzeugt; kein Upload.')
