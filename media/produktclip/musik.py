#!/usr/bin/env python3
"""Erzeugt eine ruhige Klavier-Streicher-Musik (D-Dur, 114 BPM halbes Tempo) für den Produktclip.

Rein synthetisch (numpy/scipy), keine fremden Samples: frei verwendbar.
Ein Takt = 240/114 s ≈ 2,105 s; zwei Takte = 4,21 s ≈ ein Szenenwechsel.
Ausgabe: build/musik.wav (26 s, 48 kHz, Stereo)
"""
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
BPM = 114
BEAT = 60 / BPM
BAR = 4 * BEAT
DUR = 26.0
N = int(SR * DUR)
rng = np.random.default_rng(7)


def hz(note):
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    n, o = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o + 1) - 69) / 12)


def piano(f, length, vel=0.6):
    t = np.arange(int(SR * length)) / SR
    out = np.zeros_like(t)
    for k in range(1, 6):
        fk = f * k * np.sqrt(1 + 0.0003 * k * k)          # leichte Inharmonizität
        amp = vel / (k ** 2.6)
        decay = np.exp(-t * (0.8 + 1.4 * k))
        out += amp * decay * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28))
    attack = np.minimum(1, t / 0.012)              # weicher Anschlag (gedämpft)
    hammer = 0 * t
    return out * attack + hammer


def pad(freqs, length, level=0.12):
    t = np.arange(int(SR * length)) / SR
    out = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):
            ff = f * 2 ** (det / 12)
            for k, a in ((1, 1.0), (2, 0.35), (3, 0.18), (4, 0.08)):
                out += a * np.sin(2 * np.pi * ff * k * t + rng.uniform(0, 6.28) + 0.3 * np.sin(2 * np.pi * 5.2 * t))
    env = np.minimum(1, t / 1.2) * np.minimum(1, (length - t) / 0.8).clip(0, 1)
    return level * out * env / (len(freqs) * 3)


def guitar(f, length, vel=0.25):
    t = np.arange(int(SR * length)) / SR
    out = np.zeros_like(t)
    for k in range(1, 7):
        out += (vel / k ** 2.2) * np.exp(-t * (2.2 + 1.6 * k)) * np.sin(2 * np.pi * f * k * t)
    return out * np.minimum(1, t / 0.002)


def place(buf, sig, start, ch_gain=(1.0, 1.0)):
    i = int(start * SR)
    j = min(N, i + sig.size)
    if i >= N:
        return
    buf[0, i:j] += sig[:j - i] * ch_gain[0]
    buf[1, i:j] += sig[:j - i] * ch_gain[1]


# Akkorde je zwei Takte (ein Szenenwechsel), D-Dur
chords = [
    (['D3', 'A3', 'D4', 'F#4'], 'D2'),     # 0–4,2 s   Idee
    (['C#3', 'A3', 'E4', 'A4'], 'A1'),     # 4,2–8,4   Struktur  (A/C#)
    (['B2', 'F#3', 'D4', 'B4'], 'B1'),     # 8,4–12,6  Recherche (Bm)
    (['G2', 'D3', 'B3', 'G4'], 'G1'),      # 12,6–16,8 unterwegs (G)
    (['D3', 'A3', 'F#4', 'D5'], 'D2'),     # 16,8–21   das Buch (D, voller)
    (['G2', 'D3', 'A3', 'E4'], 'G1'),      # 21–23,1   Endkarte Gsus2 …
    (['D3', 'A3', 'D4', 'F#4'], 'D2'),     # … löst nach D auf, klingt aus
]
starts = [0, 2 * BAR, 4 * BAR, 6 * BAR, 8 * BAR, 10 * BAR, 11 * BAR]

L = np.zeros((2, N))
P = np.zeros((2, N))   # Klavier-Bus, wird gedämpft (Tiefpass)
for idx, ((notes, bass), st) in enumerate(zip(chords, starts)):
    length = (starts[idx + 1] - st) if idx + 1 < len(starts) else DUR - st
    fuller = 1.6 if idx == 4 else (0.0 if idx == 0 else 1.0)
    if fuller:
        place(L, pad([hz(n) for n in notes[:3]], length + 0.6, 0.10 * fuller), st, (0.85, 1.0))
        place(L, pad([hz(bass)], length + 0.6, 0.08 * fuller), st, (1.0, 0.9))
    # Klavier: gebrochener Akkord auf jedem Schlag, ruhiges Achtel-Muster
    beats = int(round(length / BEAT))
    pattern = [0, 2, 1, 3]
    for b in range(beats):
        n = notes[pattern[b % 4]]
        v = 0.42 if b % 4 == 0 else 0.30
        place(P, piano(hz(n), 3.0, v * 0.8), st + b * BEAT, (1.0, 0.8))
    place(P, piano(hz(bass) * 2, 4.0, 0.5), st, (0.9, 0.9))
    if idx >= 1:   # Gitarre ab Szene 2, leise Off-Beats
        for b in range(beats):
            place(L, guitar(hz(notes[(b + 1) % 4]) * 2, 1.2, 0.12), st + b * BEAT + BEAT / 2, (0.7, 1.0))

# Melodie: peppiger, Achtel und Synkopen, eine Oktave tiefer notiert gespielt (/2)
melody = [  # (Note, Start in Schlägen, Länge in Schlägen)
    # Szene 1 – D
    ('F#5', 0, .5), ('A5', .5, .5), ('B5', 1, .5), ('A5', 1.5, 1), ('F#5', 2.5, .5), ('E5', 3, 1),
    ('D5', 4, .5), ('E5', 4.5, .5), ('F#5', 5, 1.5), ('A5', 6.5, .5), ('F#5', 7, 1),
    # Szene 2 – A/C#
    ('E5', 8, .5), ('F#5', 8.5, .5), ('A5', 9, 1), ('E5', 10, .5), ('C#5', 10.5, .5), ('E5', 11, 1.5),
    ('A4', 12.5, .5), ('C#5', 13, .5), ('E5', 13.5, 1), ('D5', 14.5, .5), ('C#5', 15, 1),
    # Szene 3 – Bm
    ('D5', 16, .5), ('F#5', 16.5, .5), ('B5', 17, 1), ('A5', 18, .5), ('F#5', 18.5, 1), ('D5', 19.5, .5),
    ('F#5', 20, .5), ('E5', 20.5, .5), ('D5', 21, 1), ('B4', 22, .5), ('D5', 22.5, .5), ('F#5', 23, 1),
    # Szene 4 – G
    ('G5', 24, .5), ('F#5', 24.5, .5), ('D5', 25, 1), ('B4', 26, .5), ('D5', 26.5, .5), ('G5', 27, 1.5),
    ('A5', 28.5, .5), ('B5', 29, 1), ('A5', 30, .5), ('G5', 30.5, .5), ('F#5', 31, 1),
    # Szene 5 – D, Höhepunkt
    ('A5', 32, .5), ('B5', 32.5, .5), ('D6', 33, 1), ('B5', 34, .5), ('A5', 34.5, 1), ('F#5', 35.5, .5),
    ('A5', 36, .5), ('B5', 36.5, .5), ('A5', 37, 1), ('F#5', 38, .5), ('E5', 38.5, .5), ('D5', 39, 1),
    # Endkarte – Gsus2 → D
    ('E5', 40, 1), ('D5', 41, .5), ('E5', 41.5, .5), ('A5', 42, 2),
    ('F#5', 44, .5), ('E5', 44.5, .5), ('D5', 45, 4),
]
M = np.zeros((2, N))
for note, sb, lb in melody:
    accent = 0.34 if float(sb).is_integer() else 0.27      # Schlag betont, Offbeat leichter
    place(M, piano(hz(note) / 2, max(1.2, lb * BEAT + 0.8), accent), sb * BEAT, (0.95, 1.0))
M = sosfilt(butter(2, 2600, 'low', fs=SR, output='sos'), M)   # Melodie etwas klarer als die Begleitung
L += M

# Klavier dämpfen (wie Moderator-Filz) und dazumischen
P = sosfilt(butter(2, 1600, 'low', fs=SR, output='sos'), P)
L += P

# Hall: Faltung mit abklingendem Rauschen
ir_len = int(SR * 2.4)
t = np.arange(ir_len) / SR
ir = rng.normal(0, 1, (2, ir_len)) * np.exp(-t * 2.6)
ir = sosfilt(butter(2, 6000, 'low', fs=SR, output='sos'), ir)
ir[:, :int(0.02 * SR)] = 0
wet = np.stack([fftconvolve(L[c], ir[c])[:N] for c in range(2)])
mix = 0.75 * L + 0.18 * wet / np.max(np.abs(wet))*np.max(np.abs(L))
mix = sosfilt(butter(2, 5000, 'low', fs=SR, output='sos'), mix)
mix = sosfilt(butter(1, 45, 'high', fs=SR, output='sos'), mix)
# sanftes Ein- und Ausblenden, normalisieren
tt = np.arange(N) / SR
mix *= np.minimum(1, tt / 0.15) * np.clip((DUR - tt) / 2.5, 0, 1)
mix = mix / np.max(np.abs(mix)) * 0.89
wavfile.write('build/musik.wav', SR, (mix.T * 32767).astype(np.int16))
print('build/musik.wav', DUR, 's')
