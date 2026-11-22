# Geführte Arbeitsabläufe für Bücher

Diese Dialoggerüste gelten für alle unterstützten Chat-Anbieter. Sie bündeln
vorhandene Schritte, ersetzen aber keine erforderliche Freigabe. Buchinhalte,
Erinnerungen und Quellen bleiben im jeweiligen Buchprojekt.

## Gesamtüberblick

Der redaktionelle Buchkreislauf und der technische Weg vom Chat bis zur Übernahme in den Buch-Branch sind mit Ablaufdiagrammen in [Buchworkflow und Git-Wege](BUCH-WORKFLOW.md) dargestellt. Dort werden auch GitHub-Arbeit, lokale Ordner und echte lokale Git-Clones voneinander abgegrenzt.

## Gemeinsame Regeln

- Vor jeder Änderung den Lese-Stand und einen offenen Arbeitsstand ermitteln.
  Nach `changes.auto_merge` handeln. Ein neuer Stand vor dem Schreiben erfordert
  erneuten Abgleich der betroffenen Dateien; vor Übernahme den bestätigten Head
  erneut prüfen. Nie einen älteren Stand ungeprüft über den Buchstand legen.
- Schreiberlaubnis, Speicherung, Übernahme und Abschließen getrennt
  benennen. „Alles freigeben“ ist bei mehreren möglichen Arten keine eindeutige
  Auswahl. Fehler, offene Fragen und verbleibende Freigaben sichtbar lassen.
- Eine Bestätigung darf mehrere ausdrücklich benannte und überprüfbare Aktionen
  bündeln. Nicht ausgeführte Teilaktionen als solche melden. Änderungen eines
  zusammenhängenden Auftrags atomar im Arbeitsstand speichern.

## Abschnitt erstellen und speichern

1. Abschnittsstand, Schreiberlaubnis, Buchprofil und vorhandene Unterlagen lesen.
   `python scripts/workflow_support.py <projekt> material <kapitel>` zeigt
   Kapiteldateien und mögliche Texttreffer; Treffer sind nur Hinweise und können
   unvollständig sein. Ergänzungen und offene Fragen im Gespräch sammeln.
2. Einen Entwurf im Chat zeigen. Die Schreiberlaubnis nicht durch bloßes Ansehen
   oder Speichern unterstellen. Ist das Schreiben noch nicht erlaubt, kann eine einzige
   Bestätigung beide Aktionen ausdrücklich nennen: „Schreiben für Abschnitt
   X erlauben und diesen Entwurf speichern“. Nur nach dieser Bestätigung Erlaubnis
   und Entwurf gemeinsam und mit bestätigt-gelesenem Stand dokumentieren.
3. Die vollständige Abschnittsprüfung gemäß QUALITAETSSICHERUNG.md ausführen;
   Probleme und ungesicherte Angaben nennen. Abschnitt abschließen bleibt
   eine eigene Handlung. Bei Ablehnung oder Abbruch weder Abschluss erfinden noch
   Manuskript speichern.

## Kapitel prüfen, planen und überarbeiten

1. Auf dem aktuellen Lese-Stand `python scripts/chapter_revision.py <projekt>
   <kapitel> --json` ausführen. Die Aktion erst bei `ready: true` anbieten und
   ausführen; bei `false` die fehlenden Voraussetzungen je Abschnitt nennen.
2. Das vollständige Kapitel, Profil und einschlägige Unterlagen lesen. Nach
   QUALITAETSSICHERUNG.md Befunde, Erweiterungsideen und offene Fragen mit
   Fundstellen sowie Priorität vorlegen. Keine historischen oder persönlichen
   Tatsachen erfinden und keine formelle Freigabe aus der Prüfung ableiten.
3. Die Auswahl des Autors einholen. Einen Arbeitsplan im Buchprojekt ablegen:
   geprüfter Stand, Fundstellen, Vorschlag, Status `offen`, `bestaetigt`,
   `umgesetzt` oder `zurueckgestellt`, offene Fragen und Ergebnis. Die Zustände
   beschreiben nur den Plan und schließen keinen Abschnitt ab.
4. Bestätigte Änderungen mit bestehender Schreiberlaubnis ausführen, betroffene
   Abschnitte und bei kapitelweiten Änderungen das gesamte Kapitel erneut lesen.
   Ergebnis, Änderungen und ungelöste Punkte dokumentieren. Die Übergabe des
   Arbeitsstands und eine endgültige Freigabe sind unterschiedliche Entscheidungen.

## Buchstand und Arbeitsstand abgleichen

`python scripts/workflow_support.py <projekt> compare <buch-ref> <arbeits-ref>`
vergleicht beide Stände mit ihrem gemeinsamen Vorfahren. `bereits_identisch` heißt,
dass eine Änderung bereits im Buchstand vorliegt; `nur_arbeitsfassung` bedeutet,
dass die Datei im Buch seit dem gemeinsamen Stand unverändert blieb;
`beide_geaendert` fordert eine manuelle Inhaltsprüfung. Löschungen sind gesondert
markiert. Ein gemeinsamer Vorfahr und beide Git-Referenzen müssen lokal vorhanden
sein; andernfalls den Abgleich als nicht möglich melden. Ähnlichkeit, Änderungen
in verschiedenen Dateien und Git-Mergekonflikte werden dadurch nicht abschließend
bewertet. Vor dem Übernehmen die aktuellen Köpfe und die gesamte Änderung prüfen.

## Historische Freigaben prüfen

`python scripts/workflow_support.py <projekt> historical-candidates` nennt nicht
mehr vorhandene Abschnitts- und Kapitel-IDs in Freigabe-Einträgen, die noch nicht
als historisch dokumentiert sind. Es ist nur ein Prüfhinweis: Die Historie und den
Sachverhalt untersuchen, keine automatische Zuordnung und keine neue Freigabe
ableiten. Nach dokumentierter Entscheidung kann der einzelne unveränderte Eintrag
nach dem Schema `historical_references` gekennzeichnet werden. Vor- und Nachspann
sowie Bilder werden von dieser begrenzten Kandidatensuche nicht beurteilt.

## Abschnitte zusammenlegen, entfernen oder verschieben

Für Änderungen an der Kapitelgliederung gibt es `scripts/sections.py` (#293):
`merge` legt Abschnitte zusammen, `remove` entfernt einen Abschnitt (Datei nach
`archiv/`), `move` verschiebt ihn in ein anderes Kapitel. Das Skript zieht
`ghostwriter.yml`, Nummern und Überschriften, die Abschnittslisten der
Kapitel-READMEs, Laufdateien, Kosten und Markdown-Verweise nach. Abgeschlossene
Abschnitte bleiben gesperrt, bis sie wieder geöffnet sind; ein Manuskript
wird nur nach ausdrücklicher Wahl angehängt, archiviert oder entfernt. Entfernte
IDs stehen in `structure.retired`, damit das Freigabe- und Prüfprotokoll
unverändert gültig bleibt. Übrige Verweise wie „Abschnitt 7.3“ im Fließtext meldet
das Skript zur Prüfung. Vor dem Ausführen zeigt der Assistent, was sich ändert,
und wartet auf die Bestätigung.

## Übernahme und Abschließen

Zum Abschluss die tatsächlichen Dateien und Entscheidungen in Alltagssprache
zusammenfassen: gespeichert, noch offen oder bereits übernommen. Die Bestätigung
„Buchänderungen übernehmen“ übernimmt nur den gezeigten Stand. Abschnitt abschließen und
Kapitel abschließen erhalten eigene, eindeutig bezeichnete Bestätigungen samt
Prüfung ihrer Voraussetzungen und Protokoll (`approvals`). Bei einem anderen
zwischenzeitlichen Stand erneut vergleichen; bei Konflikt nicht automatisch
übernehmen. Dieser Merge-Schritt schließt keinen Abschnitt und kein Kapitel ab.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
