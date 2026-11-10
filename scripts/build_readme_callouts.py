#!/usr/bin/env python3
"""HTML-Hinweisboxen als verlinkte README-Grafiken lokal erzeugen; kein Upload.

Quelle: die beiden aside.outlook-Boxen in website/index[.en].html.
Pillow, fontconfig und fontTools dienen Textumbruch und festen Schriftkonturen. SVGs bleiben ohne externe Ressourcen.
"""
from pathlib import Path
from html import escape
import re
import subprocess
from PIL import ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://ploeffler.github.io/GhostWriter/'


def font(family, size):
    path = subprocess.check_output(['fc-match', '-f', '%{file}', family], text=True).strip()
    return ImageFont.truetype(path, size)


def lines(text, face, width):
    result = []
    for word in text.split():
        if result and face.getlength(result[-1]+' '+word) <= width:
            result[-1] += ' '+word
        else:
            result.append(word)
    return result


def text_path(text, family, size, x, y, color, underline=False):
    face=font(family,size)
    tt=TTFont(face.path)
    glyphs=tt.getGlyphSet()
    cmap=tt.getBestCmap()
    units=tt['head'].unitsPerEm
    pen=SVGPathPen(glyphs)
    for i,char in enumerate(text):
        offset=(face.getlength(text[:i+1])-face.getlength(char))*units/size
        glyphs[cmap[ord(char)]].draw(TransformPen(pen,(1,0,0,1,offset,0)))
    scale=size/units
    path=f'<path d="{pen.getCommands()}" transform="translate({x} {y}) scale({scale} {-scale})" fill="{color}" stroke="none"/>'
    if underline:
        path+=f'<path d="M{x} {y+4}h{face.getlength(text):.2f}" fill="none" stroke="{color}" stroke-width="1"/>'
    tt.close()
    return path


def graphic(title, description, note):
    width, x, available = 696, 28, 640
    title_lines = lines(title, font('Georgia',30), available)
    body_lines = lines(description, font('system-ui',16), available)
    note_lines = lines(note, font('system-ui',13), available)
    y = 53
    parts = []
    for text in title_lines:
        parts.append(text_path(text,'Georgia',30,x,y,'#376b4b',True))
        y += 36
    y += 8
    for text in body_lines:
        parts.append(text_path(text,'system-ui',16,x,y,'#20392e'))
        y += 27
    y += 9
    for text in note_lines:
        parts.append(text_path(text,'system-ui',13,x,y,'#616a62'))
        y += 21
    height = y+6
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
<title id="title">{escape(title)}</title><desc id="description">{escape(description+' '+note)}</desc>
<defs><clipPath id="box"><rect x="0.5" y="0.5" width="695" height="{height-1}" rx="18"/></clipPath></defs>
<rect x="0.5" y="0.5" width="695" height="{height-1}" rx="18" fill="#fffefa" stroke="#dedfd4"/>
<rect x="0" y="18" width="4" height="{height-36}" fill="#b9551d" stroke="none"/>
{''.join(parts)}
</svg>
'''


def build():
    for suffix in ('','.en'):
        soup = BeautifulSoup((ROOT/'website'/f'index{suffix}.html').read_text(), 'html.parser')
        boxes = soup.select('aside.outlook')
        assert len(boxes)==2
        cards=[]
        for name,box in zip(('schreibpraxis','ausblick'),boxes):
            title=box.h2.get_text(' ',strip=True)
            description=box.p.get_text(' ',strip=True)
            note=box.small.get_text(' ',strip=True)
            image=f'assets/readme/{name}{suffix}.svg'
            (ROOT/image).write_text(graphic(title,description,note))
            target=BASE+box.h2.a['href']
            alt=escape(title+'. '+description+' '+note,quote=True)
            cards.append(f'<p align="center"><a href="{target}"><img src="{image}" alt="{alt}" width="696"></a></p>')
        readme=ROOT/f'README{suffix}.md'
        text=readme.read_text()
        start=text.index('</table>')+len('</table>')
        end=text.index('\n---',start)
        navigation=re.search(r'<p align="center"><a href="README(?:\.en)?\.md">.*?</p>',text[start:end],flags=re.S)
        assert navigation,'README-Sprachnavigation fehlt'
        text=text[:start]+'\n\n'+'\n\n'.join(cards)+'\n\n'+navigation.group(0)+'\n'+text[end:]
        readme.write_text(text)
    print('Vier README-Hinweisgrafiken und beide README-Einbindungen aus den HTML-Startseiten erzeugt; kein Upload.')


if __name__=='__main__':
    build()
