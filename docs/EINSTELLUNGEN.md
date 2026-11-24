# Einstellungen und Ausgabe

Deutsch · [English](SETTINGS.en.md)

## Welches Formular brauche ich?

| Im Chat | Dafür ist es da |
|---|---|
| `Projektdaten` (Stift in der Projektübersicht) | Titel, Untertitel, Kurztitel, Autor, Beschreibungen sowie Sprache, Buchtyp, Zielgruppe und geplante Übersetzungen |
| `Einstellungen` | Projekteinstellungen, unter anderem Faktencheck, Updates, Übernahmeverhalten und Grenzen |
| `Analyse-Einstellungen` | Analysen im Hintergrund: Anbieter, Modelle, Preise, gleichzeitige Aufrufe, Sprachprüfung (eigene Wörter, abgeschaltete Regeln) |
| `Grundregeln` | Stufen für Faktentreue, Kreativität und Recherche sowie Freigaben; Lockern nur mit eigener Bestätigung ([Grundsätze](GRUNDSAETZE.md#projektregeln)) |
| `Profil` | Git-Benutzer, Autor als Vorbelegung und Standard-Erzählstimme |
| `KI-Dienste` | Vorhandene Dienste, Zugangsart und Zuständigkeit je Aufgabe |
| `Ausgabe` oder `Umschlag` | Satz, Schrift, Absätze, Titelei, Formate, Impressum, Druckprofil und Umschlag |
| `KI-Angabe` | Ob und wo im Buch eine bestätigte Angabe zur KI-Nutzung steht |
| `Daten` oder `Update` | Tatsächlichen Programm- und Update-Stand anzeigen |
| `Alle Einstellungen` | Übersicht aller rund 100 Einstellungen des Buchs: aktueller Wert, Herkunft (eigener Wert im Buch, aus der Bibliothek, Vorgabe, nicht gesetzt) und in welchem Formular man sie ändert; Abweichungen von der Vorgabe fett (#299) |

**Alle Einstellungen** (`render_view.py <buch> settings-overview [gruppe]`, auch `scripts/settings_overview.py`) ist nur lesend. In Claude kommt sie als Widget (ab UI 0.64.0) mit Filter „Nur eigene Werte“ und Suche, mit `--text` als Tabelle. Mit `bibliothek` zeigt sie das Profil (`assistant.yml`), mit `serie <ser-id>` bzw. `sammelband <ser-id>` die Angaben der Serie und die eigenen Satz- und Impressumsangaben des Sammelbands. Am Ende der Buchseite stehen Abschnitte, deren Faktencheck von der Vorgabe des Buchs abweicht (Kapitel haben keine eigenen Einstellungen). Die Liste entsteht aus dem Schema, neue Einstellungen erscheinen also von selbst; was in keinem Formular steht, heißt „nur in der Datei“ und wird in `ghostwriter.yml` bzw. im Chat geändert. Aus der Bibliothek (`assistant.yml`) kommen die Bediensprache und, solange das Buch kein eigenes Stilprofil hat, die Angaben der Standard-Erzählstimme.

Das Öffnen eines Formulars speichert nichts. Erst die jeweilige Speicheraktion ändert Einstellungen. [Speichern und Übernehmen](SPEICHERN.md) erklärt, wann Änderungen im Buchstand ankommen.

## Ausgabe praktisch prüfen

Öffne **Ausgabe**, ändere die benötigten Felder und speichere sie. Lass danach ausdrücklich einen **Probedruck** erstellen und prüfe Schrift, Ränder, Bilder und Umschlag. Ein Probedruck ist keine veröffentlichte Auflage. **Auflage** öffnet den gesonderten Ablauf für einen unveränderlichen Buchstand; Voraussetzungen und Freigaben stehen in der [Anleitung](ANLEITUNG.md).

## Dienste und Kosten

Beginne mit deinen vorhandenen Diensten. Die Zugangsart bestimmt, ob Arbeit im aktuellen Chat, per kopiertem Auftrag oder über eine API läuft. Schlüssel gehören in GitHub-Secrets, nie in den Chat oder eine Buchdatei. Siehe [KI-Dienste nutzen](DIENSTE-NUTZEN.md). Fehlende Kostendaten sind keine bestätigten Nullkosten.

## Grenzen und geplante Funktionen

Die [Medienplatzierung](MEDIENPLATZIERUNG.md) mit Position, Textumfluss und Breitenregler ist noch nicht umgesetzt. Einen Umschlag aus einer hochgeladenen Gestaltungsvorlage abzuleiten ist ebenfalls geplant; die vorhandenen Umschlagoptionen versprechen diese Ableitung nicht.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
