# Testplan v0.6

Abnahme von v0.6 „Bibliothek“ (#41): eine Installation, mehrere Bücher als
Branches. Geprüft wird in zwei Repositorys:

- **Fork:** `chillyconcane/GhostWriter` – Einzelbuch aus v0.5, bekommt v0.6 per Update (#64) und wird danach umgewandelt.
- **Testbuch:** neues privates Repository aus der Vorlage (#48) mit dem Testbuch „ADHS im Erwachsenenleben“ als `buch/adhs-im-erwachsenenleben`.

Automatische Tests: `python -m unittest discover -s tests -p "test_*.py"`
(läuft in `validate.yml`; u. a. Erkennungsregel, Bücherregal, Neues Buch,
Branch-Auswahl beim Update, Umwandlung mit Rückweg, Seite „Daten“). Alles
andere im Chat bzw. auf GitHub; Ergebnisse als Kommentar in #41.

Legende: ✅ bestanden · ⏳ offen · — nicht anwendbar

## 1. Update von v0.5 (#40, #64)

| Prüfung | Fork | Wo |
|---|---|---|
| Nächtliches bzw. von Hand gestartetes Update bringt 0.6.0; Buch unverändert | ⏳ | Actions → GhostWriter aktualisieren |
| Migration der Datenversion gemeldet (Commit-Nachricht, Hinweis im Chat) | ⏳ | Chat |
| Link auf das Repository zeigt weiter direkt die Projektübersicht (Einzelbuch) | ⏳ | Chat |
| Arbeits-Branch `ghostwriter/main` wird vom Update nicht angefasst | ⏳ | Actions-Zusammenfassung |

## 2. Umwandlung in eine Bibliothek (#40)

| Prüfung | Fork | Wo |
|---|---|---|
| Probelauf (ohne `UMWANDELN`) zeigt den Plan und ändert nichts | ⏳ | Actions → In Bibliothek umwandeln |
| Offene Änderungen blockieren mit Hinweis „Änderungen übernehmen“ | ⏳ | Actions |
| Umwandlung: `buch/<kurztitel>` mit voller Historie, `main` nur Programm, `library.json` | ⏳ | GitHub |
| Tags und Releases bleiben gültig | ⏳ | GitHub |
| Rückweg per Revert dokumentiert und verständlich | ⏳ | `docs/UPDATES.md` |

## 3. Bücherregal und neues Buch (#37, #38)

| Prüfung | Fork | Testbuch | Wo |
|---|---|---|---|
| Link auf das Repository zeigt das Bücherregal (bei einem Buch direkt dessen Übersicht) | ⏳ | ⏳ | Chat |
| „Neues Buch“: Vorschau des Branch-Namens, vergebener Kurztitel gesperrt | ⏳ | ⏳ | Chat |
| Anlegen: Branch `buch/<slug>` mit genau einem Commit, Einstiegsdialog läuft dort | ⏳ | ⏳ | Chat, GitHub |
| Auswahlkarten im Einstiegsdialog (Schritte 4, 5, 6, 12, 13), Textfassung `1b, 2a` | ⏳ | ⏳ | Chat (#81) |
| Buch „im Aufbau“ im Bücherregal; „Einrichtung fortsetzen“ | ⏳ | ⏳ | Chat |
| Zwei Bücher: Öffnen, Bearbeiten, Freigeben, Änderungen übernehmen je Buch getrennt | ⏳ | ⏳ | Chat |
| Projektübersicht ab zwei Büchern mit „Bücherregal“ (Kürzel `L`) | ⏳ | ⏳ | Chat |

## 4. Actions je Buch (#39)

| Prüfung | Fork | Testbuch | Wo |
|---|---|---|---|
| Probedruck je Buch auf dessen Branch | ⏳ | ⏳ | Actions → Probedruck |
| Auflage eines Buchs berührt das andere nicht; Tag mit Kurztitel | ⏳ | ⏳ | Releases |
| Keine Auflage auf dem Standard-Branch oder einem Arbeits-Branch | ⏳ | ⏳ | Actions |
| Nächtliches Update: Standard-Branch und alle Bücher, eine Zeile je Buch | ⏳ | ⏳ | Actions-Zusammenfassung |
| `library.json` nach Änderungen an einem Buch aktuell | ⏳ | ⏳ | Actions → Bücherregal aktualisieren |

## 5. Seite „Daten“ (#71, Teil 1)

| Prüfung | Fork | Testbuch | Wo |
|---|---|---|---|
| Programmstand, je Buch Stand, Auflage, Probedruck, Datenversion, Prüfung richtig (Abgleich mit GitHub von Hand) | ⏳ | ⏳ | Chat |
| Secrets nur mit Namen; nach Hinterlegen „hinterlegt“ | ⏳ | ⏳ | Chat |
| Ohne GitHub-Abfrage „unbekannt“ statt geratener Werte | ⏳ | ⏳ | Chat |
| Befehl `Daten` öffnet die Seite aus jeder Ansicht | ⏳ | ⏳ | Chat |
| Eigener, umbenannter Schlüssel-Name: „unbekannt“ statt „fehlt“ (#97) | ⏳ | ⏳ | Chat, KI-Dienste-Formular |

## 6. Programm-Repository und Doku (#46, #48)

| Prüfung | Ergebnis | Wo |
|---|---|---|
| README eine Bildschirmseite; Anleitung, Grundsätze, Dialoge verlinkt und richtig | ⏳ | GitHub |
| Testbuch läuft im eigenen privaten Repository und bekommt Updates | ⏳ | Testbuch-Repository |
| Hauptrepository ohne Buch-Branches, Auflagen-Tags und Releases; Prüfung ohne Hinweise | ⏳ | validate.yml |
| Läufe in öffentlichen Repositorys werden nicht angehalten (Secrets einzeln nach Namen, #97) | ⏳ | Actions → Übersichtsdatei / Bücherregal aktualisieren |
| „Projektdateien prüfen“ im Buch-Repository grün; Programm-Prüfungen dort übersprungen (#98) | ⏳ | Actions im Fork |

## 7. Funktionen vom 01.11.2026 (Nachträge aus #41)

| Prüfung | Fork | Testbuch | Wo |
|---|---|---|---|
| **Änderungen sofort übernehmen** (#50): Wizard-Schritt 12 fragt; mit Ja wird nach dem Speichern gemergt; Freigaben und Auflagen weiter mit eigener Bestätigung; Häkchen in den Projekteinstellungen | ⏳ | ⏳ | Chat |
| **Befehle** (#52): `Start`, `Übersicht`, `Kapitel 3`, `Abschnitt 3.2`, `Neues Kapitel`, `Probedruck`, `Auflage`, `Einstellungen`, `KI-Dienste`, `Update`, `Hilfe` in jeder Ansicht, auch in der Textfassung; Hinweis nach dem Anlegen der Buchstruktur | ⏳ | ⏳ | Chat |
| **Kapitelansicht** zeigt Ziel und Kurzbeschreibung, Knopf zur Kapitelrecherche (#55) | ⏳ | ⏳ | Chat |
| **Kapitelrecherche** (#55, #56): je Aufgabe Ziel, Kurzbeschreibung, Abschnitte; Gewichtung der Nachbarkapitel wirkt; Lauf-Datei korrekt | — | ⏳ | Chat, `research/` |
| Kapitelrecherche: „Vorschlag übernehmen“ und „Speichern“; „Ausgewählte Abschnitte anlegen“ hängt nur neue Abschnitte in einem Commit ans Ende, freigegebenes Kapitel wird `in_progress` | — | ⏳ | Chat, GitHub |
| **Doku-Prüfung** (#60) schlägt bei einer absichtlich fehlenden Doku-Zeile an | ⏳ | — | validate.yml (Probe-Branch) |
| **Erststart:** ein Commit, deutsche Nachrichten (#63) | ⏳ | — | Neues Repository aus der Vorlage |

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
