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
- Aktuelle Freigaben, Speicherung, Übernahme und formelle Freigaben getrennt
  benennen. „Alles freigeben“ ist bei mehreren möglichen Arten keine eindeutige
  Auswahl. Fehler, offene Fragen und verbleibende Freigaben sichtbar lassen.
- Eine Bestätigung darf mehrere ausdrücklich benannte und überprüfbare Aktionen
  bündeln. Nicht ausgeführte Teilaktionen als solche melden. Änderungen eines
  zusammenhängenden Auftrags atomar im Arbeitsstand speichern.

## Externen KI-Dialog vorbereiten und zurückbringen

„Externen KI-Dialog für Abschnitt 2.3 vorbereiten“ oder „Externe Überarbeitung für Kapitel 2 vorbereiten“ lädt den [allgemeinen manuellen Ablauf](EXTERNER-KI-DIALOG.md). „Das ist die Rückgabe von Anbieter A zu Abschnitt 2.3“ startet den Abgleich mit Ausgangsauftrag und aktuellem Stand. Jede Auswertung endet mit einer begründeten Empfehlung. Vorbereitung und Rückgabe erteilen keine Freigabe und speichern nichts automatisch; keine Parseraktion vortäuschen.

## Abschnitt erstellen und speichern

1. Abschnittsstand, Schreibfreigabe, Buchprofil und vorhandene Unterlagen lesen.
   `python scripts/workflow_support.py <projekt> material <kapitel>` zeigt
   Kapiteldateien und mögliche Texttreffer; Treffer sind nur Hinweise und können
   unvollständig sein. Ergänzungen und offene Fragen im Gespräch sammeln.
2. Einen Entwurf im Chat zeigen. Die Schreibfreigabe nicht durch bloßes Ansehen
   oder Speichern unterstellen. Bei noch fehlender Freigabe kann eine einzige
   Bestätigung beide Aktionen ausdrücklich nennen: „Schreibfreigabe für Abschnitt
   X erteilen und diesen Entwurf speichern“. Nur nach dieser Bestätigung Freigabe
   und Entwurf gemeinsam und mit bestätigt-gelesenem Stand dokumentieren.
3. Die vollständige Abschnittsprüfung gemäß QUALITAETSSICHERUNG.md ausführen;
   Probleme und ungesicherte Angaben nennen. Endgültige Abschnittsfreigabe bleibt
   eine eigene Handlung. Bei Ablehnung oder Abbruch weder Freigabe erfinden noch
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
   beschreiben nur den Plan und sind keine Abschnittsfreigaben.
4. Bestätigte Änderungen mit bestehender Schreibfreigabe ausführen, betroffene
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

## Übernahme und formelle Freigabe

Zum Abschluss die tatsächlichen Dateien und Entscheidungen in Alltagssprache
zusammenfassen: gespeichert, noch offen oder bereits übernommen. Die Bestätigung
„Buchänderungen übernehmen“ übernimmt nur den gezeigten Stand. Abschnitts- und
Kapitelfreigaben erhalten eigene, eindeutig bezeichnete Bestätigungen samt
Prüfung ihrer Voraussetzungen und Freigabeprotokoll. Bei einem anderen
zwischenzeitlichen Stand erneut vergleichen; bei Konflikt nicht automatisch
übernehmen. Dieser Merge-Schritt erteilt keine Abschnitts- oder Kapitelfreigabe.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
