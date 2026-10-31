# UI-Vorlagen für die Ausgabe im Chat

Diese Vorlagen sind HTML-Fragmente, die als Inline-Widget im Chat ausgegeben werden. Platzhalter in der Form `{{NAME}}` werden vor der Ausgabe durch Projektdaten ersetzt. Jede Datei beschreibt in einem Kommentar am Anfang Aufbau, Platzhalter und Verhalten.

## Begriffe

**Aktionspanel**: ein Widget, über das der Benutzer im Chat Aktionen auslöst. Ein Klick sendet eine Nachricht in den Chat. Ein Aktionspanel besteht aus:

- **Aktionskarten**: je eine Karte pro Aufgabe, mit Icon, Titel und Untertitel.
- **Optionsschaltflächen**: die Wahlmöglichkeiten innerhalb einer Aktionskarte; pro Karte wird genau eine gewählt.
- **Steuerleiste** (optional): schmale Karte am rechten Rand mit Umschaltknöpfen, etwa zum Sperren.

**Anzeige**: ein Widget, das nur Informationen zeigt und keine Aktionen auslöst.

## Vorhandene Vorlagen

| Datei | Art | Zweck |
|---|---|---|
| `abschnittssteuerung.html` | Aktionspanel | Recherche und Ghostwriting eines Abschnitts zeitgesteuert oder sofort starten; Abschnitt sperren und entsperren |
| `projektuebersicht.html` | Anzeige | Titel, Kurztitel, Autor, Kurzbeschreibung und Beschreibung des Buchprojekts |
