# UI-Vorlagen für die Ausgabe im Chat

Die Chat-Vorlagen sind HTML-Fragmente, die als Inline-Widget im Chat erscheinen. Sie werden nur an einer Stelle gepflegt: im öffentlichen Repository [ploeffler/ghostwriter-ui](https://github.com/ploeffler/ghostwriter-ui), Ordner `templates/`. Jede Datei beschreibt dort in einem Kommentar am Anfang Aufbau, Platzhalter und Verhalten.

Dieser Ordner enthält:

- `ghostwriter-ui.yml`: der feste Commit von `ghostwriter-ui`, der verwendet wird
- `BEFUELLUNG.md`: wie der Assistent die Vorlagen mit Daten ausgibt, die Textfassung und das Nachrichtenformat
- diese Datei: Begriffe und Liste der Vorlagen

Eine Vorlage ändern: in `ghostwriter-ui` ändern, `python3 build.py` ausführen, committen und den neuen Commit in `ghostwriter-ui.yml` eintragen.

## Begriffe

**Aktionspanel**: ein Widget, über das der Benutzer im Chat Aktionen auslöst. Ein Klick sendet eine Nachricht in den Chat. Ein Aktionspanel besteht aus:

- **Aktionskarten**: je eine Karte pro Aufgabe, mit Icon, Titel und Untertitel.
- **Optionsschaltflächen**: die Wahlmöglichkeiten innerhalb einer Aktionskarte; pro Karte wird genau eine gewählt.
- **Steuerleiste** (optional): schmale Karte am rechten Rand mit Umschaltknöpfen, etwa zum Sperren.

**Anzeige**: ein Widget, das nur Informationen zeigt und keine Aktionen auslöst.

**Formular**: ein Widget mit Eingabefeldern. Speichern sendet alle Werte als Nachricht in den Chat, Verwerfen meldet nur den Abbruch; danach ist das Formular gesperrt.

**Symbolleiste**: eine Zeile quadratischer Symbol-Knöpfe innerhalb eines Widgets. Jeder Knopf zeigt seinen Namen beim Darüberfahren und sendet beim Klick eine Nachricht in den Chat.

## Vorhandene Vorlagen

Die **Hauptvorlage** ist die Projektübersicht: Sie wird ausgegeben, wenn das Buchprojekt als Ganzes im Chat gezeigt wird.


Dateien in `ghostwriter-ui/templates/`:

| Datei | Art | Zweck |
|---|---|---|
| `abschnittssteuerung.html` | Aktionspanel | Recherche und Ghostwriting eines Abschnitts zeitgesteuert oder sofort starten; Abschnitt sperren und entsperren |
| `projektuebersicht.html` | **Hauptvorlage**, Anzeige mit Symbolleiste | Titel, Kurztitel, Autor, bisherige Gesamtkosten, Kurzbeschreibung und Beschreibung des Buchprojekts sowie die Kapitel mit Kapitelkosten und Status; ein Klick öffnet die Kapitelansicht, der Stift je Kapitel das Formular „Kapitel bearbeiten“; bei offenen Änderungen ein Hinweis mit dem Knopf „Änderungen übernehmen“; Symbol-Knopf „Neue Auflage erzeugen“ |
| `abschnitt-bearbeiten.html` | Formular mit Symbolleiste, enthält die Abschnittssteuerung | Ziel, Kurzbeschreibung, offene Marker, Manuskript und Faktencheck eines Abschnitts bearbeiten; Freigaben nur anzeigen und über die Bestätigung erteilen oder zurücknehmen |
| `kapitelansicht.html` | Anzeige mit Symbolleiste | Alle Abschnitte eines Kapitels mit offenen Markern, Kosten und Status; ein Klick öffnet den Abschnitt zur Bearbeitung |
| `kapitel-anlegen.html` | Formular | Neues Kapitel mit Titel, Kurzbeschreibung, Ziel und Position anlegen |
| `projektdaten-bearbeiten.html` | Formular | Titel, Kurztitel, Autor, Kurzbeschreibung und Beschreibung des Buchprojekts bearbeiten |
| `kapitel-bearbeiten.html` | Formular | Titel, Untertitel, Kurzbeschreibung und Ziel eines Kapitels bearbeiten |
| `kapitelrecherche.html` | Formular | Ziel und Kurzbeschreibung eines Kapitels ändern, Recherche für das Kapitel mit Vorschlägen |
| `abschnitt-anlegen.html` | Formular | Neuen Abschnitt in einem Kapitel mit Titel, Ziel, Kurzbeschreibung, Faktencheck und Position anlegen |
| `reihenfolge.html` | Formular | Reihenfolge der Kapitel oder der Abschnitte eines Kapitels mit Pfeilen ändern |
| `projekteinstellungen.html` | Formular | Feste Regeln anzeigen; Faktencheck-Vorgabe und Buchsatz (Seitenformat, Schrift, Titelei, Inhaltsverzeichnis) bearbeiten |
| `ki-dienste.html` | Formular | Vorhandene KI-Dienste abhaken und Aufgaben zuteilen; weitere Dienste mit Link zur Anleitung bzw. Website hinzufügen |
| `freigabe-bestaetigen.html` | Bestätigung | Schreibfreigabe, Abschnitts- oder Kapitelfreigabe erteilen bzw. zurücknehmen; zeigt Prüfpunkte und sperrt bei Hindernissen |
| `aenderungen-uebernehmen.html` | Bestätigung | Offene Änderungen (Commits des Pull Requests aus dem Arbeits-Branch) auflisten und nach Bestätigung in den Buch-Branch übernehmen |
| `auflage-erzeugen.html` | Formular | Neue Auflage mit Erscheinungsdatum und Anmerkungen erzeugen; Name, Tag und Formate ergeben sich aus `workflow.yml` |

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../../assets/logo-dark.svg"><img src="../../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
