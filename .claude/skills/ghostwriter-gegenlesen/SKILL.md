---
name: ghostwriter-gegenlesen
description: Bereich eines GhostWriter-Buchs zum Gegenlesen auschecken (Kapitel 3–5 oder ganzes Buch, DOCX und PDF mit QR-Kennung, Bereich sperren) und die Rückgabe wieder einchecken (DOCX, PDF oder Foto der Ausdrucke); auch Checkout beenden und Checkouts auflisten. Befehle Auschecken, Einchecken, Checkout beenden, Checkouts, Check out, Check in, End checkout; Kürzel AC, EC, CB. Nicht für Lektorat oder allgemeines Material.
---

# GhostWriter-Gegenlesen

Arbeite im ausgewählten Buch nach dessen Repository-Regeln. Die Abläufe stehen
im Buchrepo und werden hier nicht wiederholt: `START.md`, Abschnitt „Ausgecheckte
Bereiche (#572)“ (mit Einchecken, #573), die Skripte `scripts/checkout.py` und
`scripts/checkin.py` sowie `templates/ui/BEFUELLUNG.md` (Aktionen
`checkout.start`, `checkout.return`, `checkout.end`). Fehlt die Datei im Buchrepo,
gilt die Fassung im Hauptrepo
[GhostWriter](https://github.com/ploeffler/GhostWriter). Fachbegriffe:
Bediensprache-Glossar (`docs/BEDIENGLOSSAR.md`, englisch `docs/USER-GLOSSARY.en.md`).

## Befehle

| Deutsch | English | Kürzel | Ablauf |
| --- | --- | --- | --- |
| `Auschecken Kapitel 3–5`, `Auschecken Buch` | `Check out chapters 3–5`, `Check out book` | **AC** | Bereich und Gegenleser klären, `checkout.py start`, DOCX und PDF mit QR-Kennung übergeben (#572) |
| `Einchecken` | `Check in` | **EC** | Rückgabe mit `checkin.py` zuordnen, Befunde in `editorial/rueckgabe-….yml` (#573) |
| `Checkout beenden` | `End checkout` | **CB** | `checkout.py end`, nur auf ausdrücklichen Wunsch |
| `Checkouts` | `Checkouts` | – | Liste mit `checkout.py status`, überfällige mit `overdue` |

## Regeln

- Ein Checkout sperrt den Bereich: lesen ja, schreiben nein. Vor jedem Schreiben
  im Bereich `checkout.py check` prüfen; bei Sperre Kennung und Gegenleser nennen
  und nichts ändern. Die Sperre ist keine Freigabe.
- Beenden, Abbrechen, Verlängern und Zurückholen nur als eigene Auswahl mit
  ausdrücklicher Bestätigung, nie durch Zeit oder Chatende. Einchecken beendet den
  Checkout nicht.
- Eine Rückgabe als Foto oder Scan wird wie Material behandelt: Ablage,
  Aufbereiten und Markieren stehen im Skill `ghostwriter-material`; hier nicht
  wiederholen.
- Handschrift selbst abschreiben, Unleserliches als Frage stellen, nie raten.
  Personen nie am Gesicht erkennen. Manuskriptseiten nie an externe Texterkennungs-
  oder Bilddienste geben.
- Ohne Skriptausführung die Action „Auschecken zum Gegenlesen“ starten. Fehlt ein
  Werkzeug, den Schritt nennen, der nicht geht, und einen manuellen Weg anbieten.
- Befunde sind Vorschläge; Übernehmen in den Text erst nach Hinweisdurchsicht und
  Bestätigung, abgeschlossene Abschnitte bleiben unverändert.

---
<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="https://github.com/ploeffler/GhostWriter/raw/refs/heads/main/assets/logo-dark.svg"><img src="https://github.com/ploeffler/GhostWriter/raw/refs/heads/main/assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
