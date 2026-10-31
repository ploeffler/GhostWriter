# UI-Vorlagen für die Ausgabe im Chat

Diese Vorlagen sind HTML-Fragmente, die als Inline-Widget im Chat ausgegeben werden. Platzhalter in der Form `{{NAME}}` werden vor der Ausgabe durch Projektdaten ersetzt. Jede Datei beschreibt in einem Kommentar am Anfang Aufbau, Platzhalter und Verhalten.

## Begriffe

**Aktionspanel**: ein Widget, über das der Benutzer im Chat Aktionen auslöst. Ein Klick sendet eine Nachricht in den Chat. Ein Aktionspanel besteht aus:

- **Aktionskarten**: je eine Karte pro Aufgabe, mit Icon, Titel und Untertitel.
- **Optionsschaltflächen**: die Wahlmöglichkeiten innerhalb einer Aktionskarte; pro Karte wird genau eine gewählt.
- **Steuerleiste** (optional): schmale Karte am rechten Rand mit Umschaltknöpfen, etwa zum Sperren.

**Anzeige**: ein Widget, das nur Informationen zeigt und keine Aktionen auslöst.

**Symbolleiste**: eine Zeile quadratischer Symbol-Knöpfe innerhalb eines Widgets. Jeder Knopf zeigt seinen Namen beim Darüberfahren und sendet beim Klick eine Nachricht in den Chat.

## Vorhandene Vorlagen

Die **Hauptvorlage** ist die Projektübersicht: Sie wird ausgegeben, wenn das Buchprojekt als Ganzes im Chat gezeigt wird.


| Datei | Art | Zweck |
|---|---|---|
| `abschnittssteuerung.html` | Aktionspanel | Recherche und Ghostwriting eines Abschnitts zeitgesteuert oder sofort starten; Abschnitt sperren und entsperren |
| `projektuebersicht.html` | **Hauptvorlage**, Anzeige mit Symbolleiste | Titel, Kurztitel, Autor, bisherige Gesamtkosten, Kurzbeschreibung und Beschreibung des Buchprojekts sowie Links zu den Kapiteln mit Kapitelkosten und Status |
