#!/usr/bin/env python3
"""Ausblick aus docs/ als HTML und lokale Wiki-Vorschau erzeugen; kein Upload."""
from pathlib import Path
import html
import re
import markdown

ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / 'templates/version-preview.css'


def main():
    wiki = ROOT / 'wiki'
    wiki.mkdir(parents=True, exist_ok=True)
    for lang, source, target, other in (
        ('de', 'AUSBLICK-v1.0.md', 'ausblick-1-0.html', 'ausblick-1-0.en.html'),
        ('en', 'LOOKING-AHEAD-v1.0.en.md', 'ausblick-1-0.en.html', 'ausblick-1-0.html'),
    ):
        text = (ROOT / 'docs' / source).read_text()
        # Wiki-Ausgabe wird stets aus derselben Markdown-Quelle erzeugt.
        wiki_text = text.replace('srcset="../assets/', 'srcset="https://raw.githubusercontent.com/ploeffler/GhostWriter/main/assets/').replace('src="../assets/', 'src="https://raw.githubusercontent.com/ploeffler/GhostWriter/main/assets/')
        (wiki / source).write_text(wiki_text)
        body = re.sub(r'\n---\n.*', '', text, flags=re.S)
        title, body = body.split('\n', 1)
        title = title.removeprefix('# ')
        lead, body = body.strip().split('\n\n', 1)
        lead = markdown.markdown(lead)
        content = markdown.markdown(body, extensions=['tables'])
        claude = 'Entwickelt mit Unterstützung von' if lang == 'de' else 'Developed with support from'
        page = f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · GhostWriter</title><style>{STYLE.read_text()}</style></head><body><div class="wrap"><header class="brand">GhostWriter<span class="badge">{'Ausblick' if lang == 'de' else 'Looking ahead'} · 1.0</span></header><nav class="languages"><a href="{other}">{'English' if lang == 'de' else 'Deutsch'}</a> · <a href="{'index.html' if lang == 'de' else 'index.en.html'}">{'Start' if lang == 'de' else 'Home'}</a></nav><main><section class="hero"><div class="eyebrow">{'Auf dem Weg zur 1.0' if lang == 'de' else 'On the road to 1.0'}</div><h1>{html.escape(title)}</h1>{lead}</section><div class="content"><section class="step">{content}</section></div></main><footer>{claude} Claude (Anthropic)<br>{claude} Codex (OpenAI)</footer></div></body></html>'''
        (ROOT / 'website' / target).write_text(page)
    print('HTML und Wiki-Vorschau aus docs/ erzeugt.')


if __name__ == '__main__':
    main()
