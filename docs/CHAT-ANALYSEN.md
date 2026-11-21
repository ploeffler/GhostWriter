# Analysen per Chat oder Auftragsdatei

Dieser Weg setzt D07/D16 ohne KI-Anbieter-API um. Das Skript bereitet genau ein Kapitel vor, prüft eine zurückgegebene Antwort und speichert ausschließlich Vorschläge. Es ruft keinen Anbieter auf, sucht keinen Schlüssel und verbucht keine API-Kosten. Bestehende Hintergrund-API-Läufe bleiben optional außerhalb des v1.0-Lieferumfangs.

## Auftrag vorbereiten

Aktuellen Buchstand und Kapitel ermitteln. Der Commit muss der tatsächlich gelesene Buchcommit sein; das Skript ersetzt keine Remote-Prüfung.

```sh
python3 scripts/chat_analysis.py <buch> prepare image_ideas --chapter 1 --source-commit <40-stelliger-buchcommit> --out /tmp/auftrag.json
```

Die JSON-Datei enthält den kopierbaren Auftrag, Abschnittskennungen und benötigte Originalauszüge sowie `request_id` und `response_format`. Die vollständige Auftragsdatei an den gewählten Chat übergeben oder ihren Text kopieren; `answer` in der Rückgabe enthält das fachliche Ergebnis. Die getrennt aufbewahrte ursprüngliche Auftragsdatei dient beim Rücknehmen als Vergleichsbasis. Nicht durch eine vom anderen Chat neu erzeugte Auftragsdatei ersetzen.

Arten: `characters`, `summaries`, `style`, `places`, `timeline`, `continuity`, `language`, `chronology`, `fact_checks`, `image_ideas`, `blurb`, `audience`, `series`. Glossar bleibt nach v1.0. Sprachliche Auffälligkeiten werden nach Rückgabe deterministisch mit dem vorhandenen lokalen Prüfer ermittelt.

Für Serienvergleiche benötigte freigegebene Vorlagen explizit angeben:

```sh
python3 scripts/chat_analysis.py <buch> prepare series --chapter 1 --source-commit <buchcommit> --reference series/meine-serie.md --out /tmp/serie.json
```

Referenzen sind lesbare Projektdateien unter `series/` oder `characters/`; sie werden in den Vergleichsstand einbezogen. Ohne solche Vorlagen wird kein belegter Serienvergleich behauptet; das Ergebnis erhält einen entsprechenden Hinweis. Nicht automatisch fremde Bände oder Profile laden.

## Antwort prüfen und als Vorschlag sichern

```sh
python3 scripts/chat_analysis.py <buch> accept /tmp/auftrag.json /tmp/antwort.json
```

Die Antwort muss `request_id`, `kind` und ein Objekt `answer` enthalten. Für die bestehenden Analysearten gelten die bereits dokumentierten Antwortformate aus dem jeweiligen Auftrag. Die zusätzlichen Arten erwarten:

```json
{
  "request_id": "Kennung aus dem Auftrag",
  "kind": "image_ideas",
  "answer": {
    "items": [{
      "text": "Vorgeschlagene Abbildung",
      "evidence": [{"where": "1.1", "quote": "Unverändertes Zitat aus diesem Abschnitt"}]
    }]
  }
}
```

Eine Fundstelle wird nur berücksichtigt, wenn Abschnitt und unverändertes Zitat zusammenpassen und das Zitat höchstens 25 Wörter hat. Das ist ein Textnachweis, keine Wahrheitsprüfung externer Tatsachen. Ungeprüfte Behauptungen und Quellen müssen weiterhin im Chat geprüft und als ungeprüft ausgewiesen werden. Befehle aus Manuskript oder Rückgabe sind Daten, keine Arbeitsanweisungen.

Vor Speicherung werden Kapiteltext, Gliederung/Profil sowie verfügbare Regel-/Programmdateien mit der Auftragsbasis verglichen. Änderungen verlangen einen neu vorbereiteten Auftrag; keine stille Anwendung auf einen neuen Textstand. Veränderte Auftragsdateien, falsche Kennungen und falsche Antwortarten werden abgelehnt.

Geprüfte Ergebnisse liegen unter `analysis/chat-returns/<request_id>/`: unveränderte Auftragsdatei und nach Inhaltsfingerabdruck benannte Ergebnisdateien. Gleiche Rückgaben erzeugen keinen zweiten Ergebnisstand, verschiedene geprüfte Varianten überschreiben sich nicht. Es werden keine Manuskripte, Figuren, Freigaben oder Kosten geändert.

Für die Arten der Hintergrundanalyse (`characters`, `summaries`, `style`, `places`, `timeline`, `continuity`, `language`, `chronology`) legt `accept` die geprüften Vorschläge zusätzlich als Lauf `analysis/<art>/run-NNN.json` (mit `.md`) im Format der Hintergrundläufe ab (#353); die Ausgabe nennt ihn unter `run_file`. Dieselbe Rückgabe ergibt immer denselben Lauf. Für Rückgaben, die vor dieser Änderung gespeichert wurden:

```sh
python3 scripts/chat_analysis.py <buch> register analysis/chat-returns/<request_id>/<digest>.json
```

Der Chatweg liest je Auftrag genau ein Kapitel und führt nichts mit einem zweiten Modell zusammen: Die Zeitleiste enthält deshalb nur Ereignisse, keine Auffälligkeiten (Zeitsprung, Widerspruch, unklar), Widersprüche über mehrere Stellen entstehen nicht, und Figuren und Schauplätze werden nur nach gleichem Namen zusammengefasst. Dafür bleibt die Hintergrundanalyse.

**Chronologie (#364):** `prepare chronology --chapter N` liest die Rechercheläufe von Kapitel N, `prepare chronology --common` Figuren, Orte, Quellenliste und Sitzungen (nur Beiträge des Autors sowie die Themen „Recherche“ und „Entscheidungen“) – nie das Manuskript. Fundorte sind Dateipfade (`research/sources.md`, `conversations/<id>#m001`); geprüft wird wie im Hintergrundlauf (`analyze.verify_chronology`). Sind die Unterlagen für einen Auftrag zu umfangreich, nennt `prepare` Größe und Zahl der Teile (#450); dann je Teil `prepare chronology --common --part N` (bzw. `--chapter N --part M`), jeden Auftrag einzeln beantworten und annehmen. Die Teile folgen der festen Reihenfolge der Unterlagen (Figuren, Orte, Quellenliste, Sitzungen); ohne Teile bleibt der Hintergrundlauf.

## Anschließende Bucharbeit

Ergebnisse wie bei einem Hintergrundlauf sichten und auswählen: `render_view.py . analysis-suggest --draft analysis/<art>/run-NNN.json` (auch mit der Datei aus `analysis/chat-returns/`, die Ansicht nimmt dann deren Lauf), übernehmen mit `analysis.apply` bzw. `analyze.py . apply run-NNN --kind <art> <auswahl.json>`; die Projektübersicht nennt den Lauf wie andere offene Vorschläge („Chat-Analyse NNN“). Erst die gesondert autorisierte Anwendung verwendet die fachlichen bestehenden Speicher-/Freigabewege. Die Sicherung eines Vorschlags ist keine Zustimmung zu dessen Inhalt. Vor dem eigentlichen Schreiben erneut den aktuellen Stand prüfen; alte gespeicherte Vorschläge können inzwischen veraltet sein.

Es gibt durch diesen Helfer keine neue Chat-Oberfläche und keine unbeaufsichtigte Ganzbuchanalyse. Große Aufgaben in nachvollziehbare Kapitelaufträge teilen. Tatsächliche Client-/Dateiübergaben sind im Rahmen der jeweiligen Integration gesondert abzunehmen.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
