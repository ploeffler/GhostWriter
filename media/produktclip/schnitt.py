#!/usr/bin/env python3
"""Schneidet den GhostWriter-Clip (9:16) aus fünf Szenen, Texteinblendungen und Endkarte.

Aufruf: python3 schnitt.py [--musik datei.mp3] [--start 1.5,1.5,1.5,1.5,1.5] [--dauer 4.6]
Erwartet clips/szene1.* … clips/szene5.* (mp4, mov, webm). Ausgabe: build/ghostwriter-clip.mp4
"""
import argparse
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'  # Inter (SIL OFL)
TEXTS = ['Dein Buch.\nDeine Stimme.',
         'Von der Idee zu Kapiteln –\nim Gespräch.',
         'Recherche mit Quellen.\nDu prüfst.',
         'Schreiben –\nauch offline.',
         'Freigegeben von dir.\nGesetzt als Buch.']
W, H, FPS, FADE, END = 1080, 1920, 30, 0.4, 3.0


def clip(n):
    for ext in ('mp4', 'mov', 'webm', 'mkv'):
        p = HERE / 'clips' / f'szene{n}.{ext}'
        if p.is_file():
            return p
    raise SystemExit(f'clips/szene{n}.* fehlt')


def has_audio(p):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', str(p)],
                         capture_output=True, text=True).stdout
    return bool(out.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--musik')
    ap.add_argument('--start', default='1.5,1.5,1.5,1.5,1.5', help='Startsekunde je Szene')
    ap.add_argument('--dauer', type=float, default=4.6, help='Länge je Szene in Sekunden')
    ap.add_argument('--geraeusche', type=float, default=0.25, help='Lautstärke der Clip-Geräusche (0 = aus)')
    a = ap.parse_args()
    starts = [float(x) for x in a.start.split(',')]
    build = HERE / 'build'
    build.mkdir(exist_ok=True)
    inputs, filters = [], []
    for i in range(5):
        tf = build / f'text{i + 1}.txt'
        tf.write_text(TEXTS[i], encoding='utf-8')
        inputs += ['-ss', str(starts[i]), '-t', str(a.dauer), '-i', str(clip(i + 1))]
        filters.append(
            f'[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,format=yuv420p,'
            f"drawtext=fontfile={FONT}:textfile={tf}:fontsize=64:line_spacing=14:text_align=C:fontcolor=white:"
            f"x=(w-text_w)/2:y=h*0.70:box=1:boxcolor=0x374151@0.55:boxborderw=28:"
            f"alpha='if(lt(t,0.35),t/0.35,if(gt(t,{a.dauer - 0.6}),max(0,({a.dauer - 0.25}-t)/0.35),1))'[v{i}]")
    inputs += ['-loop', '1', '-t', str(END), '-i', str(build / 'endkarte.png')]
    filters.append(f'[5:v]scale={W}:{H},fps={FPS},setsar=1,format=yuv420p,fade=t=out:st={END - 0.6}:d=0.6[v5]')
    # Überblendungen
    last, offset = 'v0', a.dauer - FADE
    for i in range(1, 6):
        out = f'x{i}'
        filters.append(f'[{last}][v{i}]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[{out}]')
        last = out
        offset += (a.dauer if i < 5 else END) - FADE
    total = 5 * a.dauer + END - 5 * FADE
    # Ton: Clip-Geräusche leise, optional Musik
    audio = []
    for i in range(5):
        if a.geraeusche > 0 and has_audio(clip(i + 1)):
            audio.append(f'[{i}:a]aresample=48000,volume={a.geraeusche},apad=whole_dur={a.dauer},atrim=0:{a.dauer},'
                         f'afade=t=in:d={FADE},afade=t=out:st={a.dauer - FADE}:d={FADE}[a{i}]')
        else:
            audio.append(f'anullsrc=r=48000:cl=stereo,atrim=0:{a.dauer}[a{i}]')
    audio.append(f'anullsrc=r=48000:cl=stereo,atrim=0:{END}[a5]')
    alast = 'a0'
    for i in range(1, 6):
        audio.append(f'[{alast}][a{i}]acrossfade=d={FADE}[ax{i}]')
        alast = f'ax{i}'
    n = 6
    if a.musik:
        inputs += ['-i', a.musik]
        audio.append(f'[{n}:a]aresample=48000,atrim=0:{total:.3f},afade=t=in:d=1,afade=t=out:st={total - 2:.3f}:d=2,volume=0.8[m]')
        audio.append(f'[{alast}][m]amix=inputs=2:normalize=0[aout]')
    else:
        audio.append(f'[{alast}]anull[aout]')
    out = build / 'ghostwriter-clip.mp4'
    cmd = ['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(filters + audio),
           '-map', f'[{last}]', '-map', '[aout]', '-t', f'{total:.3f}',
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(out)]
    subprocess.run(cmd, check=True)
    print(f'{out} · {total:.1f} s')


if __name__ == '__main__':
    main()
