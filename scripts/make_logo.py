#!/usr/bin/env python3
"""Erzeugt die GhostWriter-Logo-Dateien in assets/ (Feder, Orange/Grün/Grau).

Nur zur Entwicklung, nicht in Actions: braucht fontTools, rsvg-convert und
ImageMagick (convert) sowie die Schrift Inter SemiBold (SIL Open Font License),
aus der der Schriftzug als Pfade übernommen wird.
"""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import subprocess

OUT = Path(__file__).resolve().parent.parent / 'assets'
ORANGE, GREEN, GREEN_L, GRAY, GRAY_L, GRAY_D, LIGHT = '#F07F2E', '#4F9D69', '#6FBF8A', '#6B7280', '#D1D5DB', '#374151', '#F3F4F6'

def mark(vane_l, vane_r, nib, line, eyes, line_w=4.5):
    return (f'<path d="M70 12 C 48 18, 32 36, 28 62 L 34 64 C 40 44, 52 30, 70 12 Z" fill="{vane_l}"/>'
            f'<path d="M70 12 C 74 30, 64 48, 40 62 L 34 64 C 52 48, 62 32, 70 12 Z" fill="{vane_r}"/>'
            f'<path d="M28 62 L 22 80 L 34 64 Z" fill="{nib}"/>'
            f'<path d="M22 80 q 6 -6 12 0 t 12 0 t 12 0" fill="none" stroke="{line}" stroke-width="{line_w}" stroke-linecap="round"/>'
            f'<circle cx="52" cy="38" r="3" fill="{eyes}"/><circle cx="60" cy="30" r="3" fill="{eyes}"/>')

LIGHT_MARK = mark(GRAY, ORANGE, GRAY_D, GREEN, LIGHT)
DARK_MARK = mark(GRAY_L, ORANGE, LIGHT, GREEN_L, GRAY_D)

def svg(w, h, body, vb=None, title='GhostWriter'):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{vb or f"0 0 {w} {h}"}" role="img">'
            f'<title>{title}</title>{body}</svg>\n')

# Logo (nur Zeichen), hell und dunkel; Zeichen sitzt in 14..86 → viewBox zugeschnitten
(OUT / 'logo.svg').write_text(svg(96, 96, f'<g transform="translate(4 2)">{LIGHT_MARK}</g>'))
(OUT / 'logo-dark.svg').write_text(svg(96, 96, f'<g transform="translate(4 2)">{DARK_MARK}</g>', title='GhostWriter (dunkler Hintergrund)'))

# App-Symbol (Variante 2): dunkelgrauer Grund, farbige Feder
ICON = f'<rect width="96" height="96" rx="22" fill="{GRAY_D}"/><g transform="translate(0 -1)">{mark(GRAY_L, ORANGE, LIGHT, GREEN_L, GRAY_D, 5)}</g>'
(OUT / 'icon.svg').write_text(svg(96, 96, ICON, title='GhostWriter App-Symbol'))
# maskable: Vollfläche, Zeichen auf 70 % verkleinert (Sicherheitszone für runde Masken)
MASK = f'<rect width="96" height="96" fill="{GRAY_D}"/><g transform="translate(48 48) scale(0.7) translate(-48 -48) translate(0 -1)">{mark(GRAY_L, ORANGE, LIGHT, GREEN_L, GRAY_D, 5)}</g>'
(OUT / 'icon-maskable.svg').write_text(svg(96, 96, MASK, title='GhostWriter App-Symbol (maskable)'))

# Schriftzug „GhostWriter“ als Pfade aus Inter SemiBold (SIL OFL)
font = TTFont('/usr/share/fonts/opentype/inter/Inter-SemiBold.otf')
gs, cmap = font.getGlyphSet(), font.getBestCmap()
upm = font['head'].unitsPerEm
def text_paths(text, size, x0, baseline, fill):
    scale = size / upm
    x, out = 0, []
    hmtx = font['hmtx']
    for ch in text:
        g = cmap[ord(ch)]
        pen = SVGPathPen(gs)
        gs[g].draw(TransformPen(pen, (scale, 0, 0, -scale, x0 + x * scale, baseline)))
        out.append(f'<path d="{pen.getCommands()}" fill="{fill}"/>')
        x += hmtx[g][0] - 10   # leichtes Tracking
    return ''.join(out), x * scale
def wordmark(mark_body, c_ghost, c_writer, name, title):
    a, wa = text_paths('Ghost', 44, 94, 64, c_ghost)
    b, wb = text_paths('Writer', 44, 94 + wa + 1, 64, c_writer)
    w = int(94 + wa + wb + 12)
    (OUT / name).write_text(svg(w, 96, f'<g transform="translate(4 2)">{mark_body}</g>{a}{b}', title=title))
wordmark(LIGHT_MARK, GRAY_D, ORANGE, 'logo-wortmarke.svg', 'GhostWriter')
wordmark(DARK_MARK, LIGHT, ORANGE, 'logo-wortmarke-dark.svg', 'GhostWriter (dunkler Hintergrund)')

# PNG: Favicons und PWA-Symbole
for size in (16, 32, 48, 180, 192, 512):
    subprocess.run(['rsvg-convert', '-w', str(size), '-h', str(size), str(OUT / 'icon.svg'), '-o', str(OUT / f'icon-{size}.png')], check=True)
subprocess.run(['rsvg-convert', '-w', '512', '-h', '512', str(OUT / 'icon-maskable.svg'), '-o', str(OUT / 'icon-maskable-512.png')], check=True)
subprocess.run(['convert', str(OUT / 'icon-16.png'), str(OUT / 'icon-32.png'), str(OUT / 'icon-48.png'), str(OUT / 'favicon.ico')], check=True)
subprocess.run(['rsvg-convert', '-h', '192', str(OUT / 'logo-wortmarke.svg'), '-o', str(OUT / 'logo-wortmarke.png')], check=True)
print(sorted(p.name for p in OUT.iterdir()))
