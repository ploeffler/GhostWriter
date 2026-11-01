# Produktclip

[<img src="vorschau.jpg" alt="Standbild aus dem GhostWriter-Produktclip" width="270" align="right">](ghostwriter-clip.mp4)

Kurzer Social-Clip zu GhostWriter **Version 1.0 (in Entwicklung)**: [ghostwriter-clip.mp4](ghostwriter-clip.mp4), 24 Sekunden, Hochformat 9:16 (1080×1920), mit Musik und leisen Geräuschen aus den Szenen, Lautheit −14 LUFS.

Der Clip zeigt Funktionen, die es zum Teil erst mit v1.0 gibt (z. B. Offline-Arbeit, #61); die Endkarte sagt deshalb „Version 1.0 – in Entwicklung“.

## Aufbau

| Zeit | Szene | Einblendung |
|---|---|---|
| 0–4 s | Idee am Küchentisch | Dein Buch. Deine Stimme. |
| 4–8 s | Struktur am Laptop | Von der Idee zu Kapiteln – im Gespräch. |
| 8–13 s | Recherche mit Textmarker | Recherche mit Quellen. Du prüfst. |
| 13–17 s | Schreiben im Zug | Schreiben – auch offline. |
| 17–21 s | Das gedruckte Buch | Freigegeben von dir. Gesetzt als Buch. |
| 21–24 s | Endkarte ([endkarte.png](endkarte.png)) | Du schreibst. GhostWriter hilft. · Version 1.0 – in Entwicklung |

## Wie er entstanden ist (01.11.2026)

- **Startbild** der Hauptfigur: ImagineArt (Seedream V5 Lite), 9:16. Die Figur ist erfunden.
- **Szenen**: Google Flow, Veo 3.1 Lite, 720p, je 8 Sekunden; Szene 1 aus dem Startbild als erstem Bild, Szenen 2–5 mit dem Startbild als Bildelement (Vorlage für die Person).
- **Musik**: [musik.py](musik.py), rein synthetisch erzeugt (Klavier, Streicherfläche, Gitarre; D-Dur, 114 BPM im halben Tempo, Szenenwechsel auf Taktbeginn, Aufbau zum Buch bei 17 s, Schlussakkord zur Endkarte). Keine fremden Samples, frei verwendbar.
- **Schnitt**: [schnitt.py](schnitt.py) mit ffmpeg: Zuschnitt auf 1080×1920, je 4,6 Sekunden ab gewählter Stelle (`--start 1.3,2.5,2.5,2.8,3.2`), Überblendungen, Texteinblendungen in Inter (SIL OFL), Endkarte mit der Wortmarke aus `assets/`; Musik mit `--musik build/musik.wav --geraeusche 0.5`, Lautheit normalisiert auf −14 LUFS.

Die Szenen-Prompts (englisch) und die Stilentscheidungen: ruhig, warm, Realfilm-Anmutung, kein lesbarer Text im Bild, Logo-Farben nur als Gegenstände (orange Tasse, grüne Pflanze, grauer Pullover).

## Nutzung

Vor einer öffentlichen oder werblichen Nutzung die Nutzungsbedingungen der verwendeten Generatoren (Google Flow, ImagineArt) für das jeweilige Konto prüfen; Gratis-Konten erlauben kommerzielle Nutzung oft nicht.

Dieser Ordner gehört nur zum Hauptrepository (nicht in `ghostwriter-manifest.yml` → `managed`) und wird nicht in Buch-Repositorys verteilt.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../../assets/logo-dark.svg"><img src="../../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
