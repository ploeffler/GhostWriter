# Hilfe: Befehle und Beispielprompts

Deutsch · [English](HELP.en.md)

Schicke **Hilfe** im Chat. Du erhältst eine kurze Befehlsübersicht und die Kürzel der aktuellen Ansicht. Mit **Hilfe Änderungspakete**, **Hilfe Session** oder **Hilfe Befehle** kannst du gezielt nachlesen. Hilfe liest nur; sie speichert, übernimmt und bestätigt nichts. Der Assistent nennt offen, wenn ein Befehl in der verwendeten Umgebung mangels Werkzeugen nicht ausführbar ist. Was die Begriffe bedeuten, erklärt das [Bedienglossar](BEDIENGLOSSAR.md).

## Kurze Befehlsübersicht

| Du schreibst | Das passiert |
|---|---|
| `Start` oder `Bibliothek` | Bücher anzeigen |
| `Übersicht` | Aktuelles Buch anzeigen |
| `Buchansicht <Buch>` | Übersicht eines bestimmten Buchs, gefunden über Nummer, Kurztitel oder Titel |
| `Kapitel 2` oder `Abschnitt 2.3` | Gewünschte Stelle öffnen |
| `Neues Buch: Mein Titel` | Formular für ein neues Buch öffnen |
| `Neues Kapitel` | Formular für ein neues Kapitel öffnen |
| `Session sichern` | Gesprächsarbeit dauerhaft in einem Änderungspaket sichern |
| `Chat sichern` oder `Chat speichern` | Dasselbe wie „Session sichern“ |
| `Session laden` | Gesicherten Gesprächsstand zum Weiterarbeiten laden; nichts übernehmen |
| `Session übernehmen` | Änderungspaket zur Sitzung prüfen, bei Fehlern analysieren und sichere Reparatur versuchen, erneut prüfen und übernehmen |
| `Änderungen übernehmen` | Die Bestätigung für die gesammelten Buchänderungen öffnen; erst die eindeutige Bestätigung übernimmt das gezeigte Paket |
| `Figuren` oder `Figuren vorschlagen` | Figuren anzeigen oder Vorschläge aus dem Text erarbeiten |
| `Figurengespräch <Name>`, `Gespräch beenden` | Im Chat mit einer Figur sprechen; nichts wird gespeichert, Neues kommt nur auf deine Auswahl ins Figurenprofil |
| `Als <Name> sprechen` | Umgekehrt: du oder die Person selbst spricht als Figur, der Assistent antwortet aus Buchwissen, Recherche oder beidem; gespeichert wird nur, was du danach auswählst |
| `Zeitleiste` | Chronologie aus Unterlagen und Recherche, mit Hinweisen, wo Daten nicht zusammenpassen |
| `Bilder 2.3` | Bilder des Abschnitts verwalten |
| `Ausgabe` oder `Umschlag` | Ausgabeoptionen öffnen |
| `Probedruck` | Vorschau bauen lassen; keine veröffentlichte Auflage |
| `Vorabfassung` | Stand dauerhaft als Vorab-Release festhalten (Tag und Pre-Release, nach Rückfrage); keine Auflage |
| `Manuskript ausgeben` | PDF des Arbeitsstands zum Herunterladen; Geplantes in Stichworten |
| `Auflage` | Formular für eine neue Auflage öffnen |
| `Auschecken Kapitel 3–5` oder `Auschecken Buch` | Bereich zum Gegenlesen sperren und als DOCX und PDF mit QR-Kennung bereitstellen (Kürzel `AC`) |
| `Einchecken` | Rückgabe des Gegenlesers (DOCX, PDF oder Foto der Ausdrucke) einordnen und als Befunde einbringen (Kürzel `EC`); der Checkout bleibt bestehen |
| `Checkout beenden`, `Checkouts` | Sperre nach Bestätigung aufheben (Kürzel `CB`) bzw. alle Checkouts zeigen |
| `Material einbringen` | Foto, Dokument oder Rückgabe zum Buch ablegen, aufbereiten und markieren (Kürzel `ME`); startet auch bei einem Upload |
| `Nur Text` | Darstellung auf Text umstellen |
| `Einfacher Modus` | Knappe, verständliche Antworten |
| `Erweiterte Antworten an` | Technische Einzelheiten einschalten |

## Änderungspakete schnüren und übernehmen

Ein **Änderungspaket** bündelt zusammengehörige gespeicherte Änderungen. GitHub nennt es Pull Request oder PR. **Schnüren** heißt: Ergebnisse ordnen, die zugehörigen Dateien speichern und sie in einem gemeinsamen Paket zur Prüfung bereitstellen. Bei einer Sitzung erhält jedes geänderte zusammenhängende Themengebiet einen eigenen gespeicherten Änderungsschritt: Recherche, Brainstorming, Entscheidungen, Entwürfe, Planung und Gesprächsstand. Diese Schritte bilden gemeinsam ein Änderungspaket pro Sitzung; nicht für jede Nachricht ein neues Paket.

Mit **Session sichern** wird dieses Paket geschnürt bzw. ergänzt. Nach abgeschlossenem Dialog über offene Abschnittspunkte passiert die Sicherung auch automatisch. Eine offene Frage oder ausstehende Antwort verhindert diesen automatischen Auslöser; ausdrückliche Vertagungen werden mitgesichert. Mit **Session laden** liest du die Sicherung. Mit **Session übernehmen** lässt du das Paket prüfen und in den vorgesehenen Projektstand übernehmen. Details und technische Grenzen stehen in [Session-Sicherung](SESSION-SICHERUNG.md).

| Meldung | Bedeutung |
|---|---|
| Vorbereitet | Inhalte zusammengestellt, dauerhafte Speicherung noch nicht bestätigt |
| Im Repository gespeichert / Änderungspaket gespeichert | Benannte Inhalte erfolgreich übertragen und im Repository bestätigt; Paket kann noch offen sein |
| Geprüft | Die genannten Prüfungen sind erfolgt; noch keine Übernahme zugesichert |
| Übernommen | Das geprüfte Änderungspaket wurde erfolgreich in den vorgesehenen Projektstand übernommen (technisch: Merge) |
| [Abgeschlossen](BEDIENGLOSSAR.md#abgeschlossen) | Eigene ausdrückliche Entscheidung, dass ein Abschnitt, Teil oder Kapitel fertig ist; der Text ist danach gesperrt, bis du ihn wieder öffnest (früher „freigegeben“) |
| Freigegeben | Eigene ausdrückliche Entscheidung über ein Bild, einen Sammelband oder eine Auflage |
| Schreiben erlaubt | Der Assistent darf den Text dieses Abschnitts schreiben oder ändern |

Eine grüne Speichermeldung darf nur nach bestätigter Übertragung erscheinen und muss ihren Umfang nennen. „Abschnitt gespeichert“ bedeutet nicht automatisch „Gespräch gesichert“. Eine Sitzungssicherung speichert Gesprächsarbeit; sie ändert kein Manuskript. Eine Übernahme ersetzt keine inhaltliche Freigabe. Reguläre Buchänderungen können bei bewusst eingeschaltetem „sofort übernehmen“ direkt übernommen werden; Änderungspakete zu Sitzungen brauchen weiterhin **Session übernehmen**.

## Buchgedächtnis abgleichen

„Gleiche Kapitel 3 mit unserem Buchgedächtnis ab“ liefert einen
[lesenden Fakten- und Kontinuitätsabgleich](BUCHGEDAECHTNIS.md).
„Welche Fakten hat Abschnitt 2.3 geändert?“ benötigt einen benannten
Vergleichsstand. Keine automatische Änderung von Buchunterlagen oder Manuskript.

## Lektorat beauftragen

- „Strukturlektorat für Kapitel 3.“
- „Sprachlektorat für Abschnitt 2.3.“
- „Schlusskorrektur für Kapitel 4.“
- „Rundumprüfung Kapitel 3.“

Die [drei Prüfarten](LEKTORAT.md) liefern zunächst Befunde im Chat; sie ändern
kein Manuskript und erteilen keine Freigabe. Die Rundumprüfung („Rundumprüfung
Kapitel 3“) bündelt sie und setzt dabei um, was ohne Autor lösbar ist oder einen
eindeutigen Vorschlag hat.

## Beispielprompts zum Weiterarbeiten

Diese Beispiele sind normale Arbeitsaufträge, keine Abkürzungen, die Freigaben umgehen:

- „Welche Fragen sind in Abschnitt 2.3 noch offen?“
- „Recherchiere zu dieser Frage und nenne Quellen und Unsicherheiten.“
- „Sammeln wir drei mögliche Einstiege für Abschnitt 2.3.“
- „Zeige mir unsere Entscheidungen, verworfenen Ideen und offenen Punkte.“
- „Was ist bereits gespeichert und was liegt nur in diesem Gespräch?“
- „Welche Änderungen enthält dieses Änderungspaket?“
- „Einpflegen in Kapitel 2: <neue Notiz oder Material>“
- „Kapitel 2 nachziehen. Nur analysieren.“

Für Recherche und Schreiben gibt es im geöffneten Abschnitt die Kürzel **RS** (Recherche sofort) und **GS** (Ghostwriting sofort; Schreiben muss erlaubt sein). **M** öffnet in der Buchübersicht die Bestätigung für gesammelte Änderungen, wenn welche vorhanden sind. Kürzel gelten im Kontext der zuletzt angezeigten Ansicht; die vollständige Zuordnung steht in [Textfassung und Kürzel](../templates/ui/BEFUELLUNG.md#textfassung-ohne-widgets). Weitere Abläufe: [Einpflegen und Nachziehen](NACHZIEHEN.md), [Anleitung](ANLEITUNG.md).

## Ausgabe bei Hilfe im Chat

Der Assistent liest diese Hilfe und die aktuelle Ansicht. Bei **Hilfe** zunächst nur etwa acht bis zwölf passende Befehle mit knapper Wirkung und den Hinweis auf die drei Themenhilfen zeigen; nicht diese ganze Datei ausgeben. **Hilfe Befehle** zeigt die Befehlsübersicht, **Hilfe Änderungspakete** erklärt Schnüren, Speichern, Prüfen und Übernehmen mit den Statusunterschieden, **Hilfe Session** erklärt Sichern, automatischen Abschnittsabschluss, Laden und Übernehmen. Aktuelle Kürzel nur nennen, wenn die Ansicht bekannt ist. Hilfe kann ohne ausgewähltes Buch angezeigt werden; keinen Projektstand erfinden. Englische Eingaben `Help`, `Help commands`, `Help changes` und `Help sessions` sinngemäß behandeln und die Ausgabe in der gewählten Bediensprache formulieren.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
