# Vorschlag für Zwischenversionen bis GhostWriter v1.0

Stand: 8. November 2026. **Analyse und Versionsvorschlag, noch keine beschlossene neue Roadmap und kein Auftrag zur Umsetzung oder Veröffentlichung.** Zur Übernahme vorbereitet. Die Zuordnung der zentralen Dokumentationswebsite einschließlich Aufbau und Veröffentlichung zu v0.9.0 wurde am 8. November 2026 bestätigt; am 9. November wurde ihre technische Umsetzung als geprüfter PR vorgezogen beauftragt. Übernahme und Veröffentlichung bleiben gesperrt bis zur ausdrücklichen Freigabe. Die übrige Lieferfolge bleibt ein Vorschlag.

## Ergebnis

GhostWriter besitzt bereits wesentliche Grundfunktionen. Der Weg zu v1.0 besteht aus einer Mischung aus Bestandsabnahme, Schließen konkreter Lücken und Umsetzung der neu bestätigten Medien- und Umschlagfunktionen. Eine reine Abschlussversion direkt nach v0.7 würde zu viele voneinander unabhängige Aufgaben bündeln.

Empfohlen werden zwei Stabilisierungsstufen, drei Medienstufen, zwei Import-/Analysestufen, eine Bedienungsstufe und ein Freigabekandidat. Jede Zwischenversion muss für sich nutzbar und geprüft sein. Die Nummerierung ist ein Vorschlag; die vorhandene Zuordnung von v0.7 zu Figuren und Bildern bleibt erkennbar.

## Grundlage und Grenzen der Analyse

- Der aktuelle GitHub-Hauptstand wurde lesend geprüft: `cf6ee98bb19c93f8ddc65d37523c0651488b9d1a`, Änderung #224. Die verteilte Programmversion im Manifest ist weiterhin `0.6.0`; Commitstand, Programmversion und Abnahmestand sind verschiedene Dinge.
- Die aktuelle Arbeitskopie enthält darüber hinaus lokale Änderungen. Sie sind nicht automatisch veröffentlicht, geprüft oder Bestandteil einer neuen Programmversion.
- Maßgeblich für den fachlichen Umfang sind die [bestätigten Beschlüsse D01–D32](docs/ENTSCHEIDUNGEN-v1.0.md), ergänzt um den dortigen v1.0-Nachtrag zur Umschlagvorlage und die bestätigten [Medienanforderungen](docs/MEDIENPLATZIERUNG.md).
- Code und Tests wurden zusätzlich in der separaten lokalen Kopie des Hauptstands untersucht. Die Kernfunktionen für Bilder, Import und Analysen wurden durch #224 nicht geändert.
- Vorliegende Nachweise: 380 Tests mit 68 übersprungenen Fällen beim vorigen Gesamtlauf; anschließend gezielte Bild-, Referenz-, Medien- und Exportprüfungen sowie der praktische Bildtest. Daraus folgt keine vollständige Abnahme aller Clients oder Ausgabevarianten. Bei der anschließenden Übertragungsvorbereitung: 381 Tests ohne Fehler, 68 übersprungen. Optionale und praktische Clientprüfungen bleiben gesondert auszuweisen.
- Einzelne in älteren Unterlagen genannte Änderungspakete #215 und #217 waren beim aktuellen Leseversuch nicht abrufbar. Daraus lässt sich weder ihr Nichtvorhandensein noch ein Merge-Status ableiten. Umsetzungsstand vor weiteren Arbeiten anhand von Code und erreichbarer Historie abgleichen.

## Was bereits vorhanden ist und was noch fehlt

| Bereich | Vorhandene Grundlage | Restarbeit bis v1.0 |
|---|---|---|
| Buchworkflow und Bibliothek | Buchanlage, Kapitel/Abschnitte, Freigabemodell, getrennte Arbeitsstände, Probedruck und Auflagenexport; zahlreiche Tests | Den vollständigen normalen Arbeitsweg praktisch abnehmen; technische Branch-Verwaltung aus der normalen Bedienung heraushalten; Rechte und gesonderte Freigaben nachweisen. |
| Standabgleich | `workflow_support.py` prüft veraltete Schreibgrundlagen, betroffene Dateien, geänderten Kontext und divergierte Stände; Open-WebUI-Navigation lädt Kontext neu | Die Prüfung in alle relevanten Schreib-, Freigabe- und Übernahmewege einbinden bzw. ihre Ausführung nachweisen; Eingaben bei Konflikten erhalten; Wiederaufnahme und Wechsel zwischen Clients praktisch testen. Kein neuer Synchronisationsserver. |
| Gesprächssicherung | `chat_backup.py` mit Sichern, Laden, Übernehmen und Abschnitts-Checkpoint, gespeicherten Beiträgen und ausgewiesenen Lücken | Echte Sicherung und Wiederaufnahme über die verfügbaren Werkzeuge der vier Clients abnehmen; Netzwerkfehler, doppelte Aufträge, geschlossene Sitzungen, Reparatur und Wiederherstellung prüfen. CLI-/Werkzeugverfügbarkeit pro Client nachweisen. Keine zusätzliche Hintergrundsicherung als Pflicht. |
| Figuren, Bilder und Referenzen | Verwaltung, Referenzauswahl und Dateifingerabdrücke; Uploadgrenzen, Originalschutz und bestätigte Verkleinerung; praktischer Bild-/Referenztest | Ein-Medium-Grenze technisch durchsetzen; Grafikprompt korrigieren; Alternativtexte bis in DOCX/EPUB erhalten; PDF-Zusammenhalt von Überschrift, Bild, Bildunterschrift und Entwurfsvermerk verbessern. |
| Medienlayout | Derzeit feste volle Satzbreite | Sechs Positionen mit Textumfluss, prozentualen Breitenregler, proportionale Höhe, Speicherung, Vorschau und zuverlässige Ausgabe ergänzen. Medienabschnitte ohne Fließtext einschließen. |
| Externe Bildrecherche | Vorhandene Chat-Werkzeuge und Metadaten für Herkunft/Rechte als Ansatz | Recherche, Quell-/Urheber-/Lizenzangaben, ungeklärte Rechte und ausdrücklich bestätigte Aufnahme als durchgängigen Ablauf prüfen und ergänzen; keine neue Suchanbieter-API. |
| Umschlag | Vorhandener Umschlagbau mit Vorlagen, Bild, Farben, Druckmaßen, Rücken und EPUB-Vorderseite | Hochgeladenen Entwurf analysieren; fertiges Coverbild und bearbeitbaren Nachbau unterscheiden; fehlende Einstellungen ergänzen; Vorschau und bestätigte Übernahme pro Buch. Das ist eine neue v1.0-Funktion, keine bloße Abnahme. |
| Manuskriptimport | Formatumwandlung, Gliederungsvorschau, bestätigtes Anlegen und Tests vorhanden | Den vollständigen Weg ohne KI-Anbieter-API abnehmen; Bildkandidaten kontrolliert in die Medienverwaltung überführen; Textverluste anzeigen; historische Aufbewahrungsanzeigen bereinigen. |
| Aufbewahrung | Automatisches Löschen im Import wurde bereits gesperrt: `expire` verlangt ausdrücklich `confirmed=True`; keine tägliche Löschplanung im geprüften Import-Workflow | Veraltete Beschreibungen, Fristwahl und Ablaufwarnungen an „Originale bleiben bis zum Löschauftrag erhalten“ angleichen; bewusste Löschung und Wiederherstellung mit Testdaten abnehmen. Die eigentliche Löschsperre nicht fälschlich als noch fehlend planen. |
| Analysen | Registrierte Arten für Figuren, Zusammenfassungen/Ziele, Stil, Orte, Zeitleiste, Kontinuität und Sprache; lokale sprachliche Prüfung; Fundstellenkontrollen | Chat-/Datei-/Kopierweg für die ausgewählten Arten vervollständigen. Mehrere bestehende KI-Läufe verlangen noch Anbieter-Schlüssel. Zusätzlich Sachbuch-Prüfstellen, Bildideen, Klappentext, Buchtyp/Zielgruppe und Serienabgleich konsistent anbieten und abnehmen. Ergebnisse bleiben Vorschläge. |
| Bedienung und Sprachen | Umfangreiche deutsche und englische Ansichten, Anleitungen, Hilfen; vorhandener Prompt-Profiler | Vier-Client-Abnahme, verbleibende Missverständnisse und veraltete Texte bereinigen, Bedienglossar umsetzen, zentrale deutsch-/englischsprachige Dokumentationswebsite aus docs/ aufbauen und geprüft veröffentlichen, Herkunft und Geltung von Anweisungen nachvollziehbar ordnen. Keine automatische Prompt-Kürzung. |
| Datenseite und Nutzung | Stand-/Kosten-/Limitdarstellung vorhanden | Tatsächlich verfügbare Angaben prüfen; unbekannt nicht als null ausgeben; keine fiktiven Kosten für Chat-Abos; vorhandene Historien erhalten. |
| Migration und Updates | Datenversionen, Migrationen und Bibliotheksumwandlung als Grundlage | Änderungen an Medien-/Umschlageinstellungen mit Migration und Rückweg liefern; Testdaten für alte Einzelbücher/Bibliotheken; YAWA-Ausgangsstand gesondert prüfen und sichern. Reale YAWA-Änderungen bleiben ausdrücklich freigabepflichtig. |

## Vorgeschlagene Lieferfolge

| Version | Lieferziel | Woran die Stufe abgenommen wird |
|---|---|---|
| **v0.6.1** | **Verlässlicher Grundablauf und konsistenter Produktumfang.** Beschlüsse in Roadmap/Anweisungen abgleichen; Buchanlage, Bearbeiten, Freigaben, gewöhnliches Speichern/Übernehmen und Eigentümer-/Bearbeiter-/Lesergrenzen prüfen. | Ein isoliertes Testbuch durchläuft Anlage bis Testauflage; unzulässige Schreib- oder Freigabeaktionen werden verhindert; die normale Bedienung verlangt keine Branch-Verwaltung. Verschobene Dienste stehen nicht mehr als v1.0-Pflicht in der aktiven Roadmap. |
| **v0.6.2** | **Standabgleich, Sitzungssicherung und Wiederaufnahme.** Bestehende Helfer in den praktischen Ablauf einbinden, Konflikte und Bestätigungen absichern, Sicherungen wieder laden und übernehmen. | Client A speichert, Client B erkennt den neuen Stand vor dem nächsten Schreiben; veraltete Eingaben überschreiben nichts. Sicherung, Wiederherstellung, doppelter Auftrag und fehlgeschlagene Übernahme sind mit erhaltenen Inhalten getestet. |
| **v0.7.0** | **Figuren, Bilder und Grafiken zuverlässig verwenden.** Bildtest-Lücken schließen, Referenzen und externe Bildrecherche abnehmen, maximal ein Medium je Abschnitt durchsetzen. | Illustration und beschriftetes Diagramm lassen sich mit Quellen-/Herkunftsangaben und getrennten Freigaben aufnehmen. Zweites Medium wird abgefangen; Alternativtexte kommen an; ein Medienabschnitt und Entwurfsvermerke bleiben im PDF zusammenhängend. |
| **v0.7.1** | **Medien im Text platzieren.** Sechs Positionen, Textumfluss und Breiten-Schieberegler mit Prozentanzeige, gespeicherte Werte und Vorschau pro Buchmedium. | Oben/unten × links/mittig/rechts und Größenänderungen funktionieren mit kurzen/längeren Abschnitten und Seitenwechseln. PDF, DOCX und EPUB werden getrennt geprüft; nicht darstellbare Fälle werden vor Übernahme sichtbar geklärt. |
| **v0.7.2** | **Umschlag aus hochgeladenem Entwurf.** Fertiges Coverbild übernehmen oder aus der Gestaltung bearbeitbare Umschlageinstellungen vorschlagen. | Ein Paint-ähnlicher Entwurf durchläuft Analyse, kontrollierte Texterkennung, Einstellungsvorschlag, Vorschau und Bestätigung. Original bleibt erhalten; Unsicherheiten werden genannt; keine doppelte Schrift über einem fertigen Coverbild; Druck-/EPUB-Ausgabe geprüft. |
| **v0.8.0** | **Manuskriptimport und Originalerhalt.** Umwandlung, Vorschau, Strukturübernahme, Bildkandidaten und Wiederherstellung ohne zusätzliche Anbieter-API abschließen. | Text-, DOCX- und weitere tatsächlich unterstützte Importwege sind mit Formatverlusten und fehlender Gliederung getestet. Buchdateien entstehen nur nach erforderlicher Bestätigung. Originale verschwinden nicht automatisch; alte Fristangaben erzeugen keine irreführende Löschzusage. |
| **v0.8.1** | **Alle vereinbarten Analysearten im Chat.** Einheitlicher Text-/Dateiauftrag und geprüfte Rückgabe, ergänzte Analysearten, nachvollziehbare Fundstellen und ausgewählte Übernahme. | Jede in D16 ausgewählte Analyse hat einen geprüften Weg ohne Anbieter-Schlüssel. Fehlerhafte Rückgaben und veraltete Ausgangsstände werden erkannt; kein Vorschlag verändert ungefragt Manuskript oder Freigaben. Umfang je Auftrag ist begrenzt bzw. aufteilbar und nachvollziehbar. |
| **v0.9.0** | **Verständliche Bedienung und zentrale Dokumentationswebsite.** Bedienglossar, Deutsch/Englisch, Datenseite, verfügbare Grenzen und Profiler; Website aus docs/ mit Navigation, Suche und Sprachwechsel, lokalem Aufbau, Prüfung und Veröffentlichungsweg. | Die Begriffe und Zustände werden gleich verwendet; keine unbekannten Daten als sichere Werte, keine behaupteten API-/Widgetfähigkeiten. Profiler und Herkunft der Anweisungen sind geprüft. Die letzten offenen Bedienfälle der vier Clients sind nachvollziehbar abgearbeitet. Die zentrale Website ist gerendert geprüft und ihre Veröffentlichung nachvollziehbar; keine Websites oder privaten Inhalte einzelner Buch-Repositories. |
| **v1.0.0-rc.1** | **Gesamtabnahme und Upgradeprobe.** Alle Lieferblöcke zusammen testen, Einzelbuch/Bibliothek und Datenmigrationen prüfen; YAWA-Übernahme vorbereiten und nur nach gesonderter Freigabe ausführen. | Abnahmematrix vollständig: vier Clients, zwei Bediensprachen, Erststart, Wiederaufnahme, Konflikt, Freigaberücknahme, Import, Medien, Probedruck, Auflage, Update und Wiederherstellung. Keine offenen Pflichtprüfungen oder blockierenden Fehler. |
| **v1.0.0** | **Ausdrücklich freigegebene Veröffentlichung.** Geprüften Kandidaten als Produktversion kennzeichnen, Release Notes und verbindlichen Funktionsumfang ausweisen. | Alle Pflichtnachweise liegen vor; der Auftraggeber bestätigt die endgültige Veröffentlichung gesondert. Kein automatisches Produktrelease allein durch einen grünen Testlauf. |

Die Aufgaben innerhalb einer Stufe können in mehrere zusammengehörige Änderungspakete aufgeteilt werden. Die Versionsnummer bezeichnet ein nutzbares und abgenommenes Ergebnis, nicht jeden einzelnen Commit. Für diese Planung werden keine Termine oder unbelegten Aufwandszahlen angenommen.

## Dokumentationsstand für v0.9.0

Die Aufnahme der zentralen Dokumentationswebsite samt Aufbau und Veröffentlichung in v0.9.0 ist am 8. November 2026 ausdrücklich bestätigt. Quelle bleibt `docs/` im Hauptrepository. Zu liefern sind Navigation, Suche, Sprachwechsel, lokale Vorschau und Prüfung sowie ein geeigneter Veröffentlichungsweg. Der vorbereitete Veröffentlichungsweg verwendet den vorhandenen ausschließlich manuellen Pages-Ablauf mit standardmäßig ausgeschaltetem Dokumentationsmodus; der Upload aktiviert nichts. Gemeint ist der Aufbau der Website aus vorhandenen Dokumenten, kein automatisches Neuschreiben der Anleitungen. Details: [Planungsnotiz zur Dokumentationswebsite](PLANUNGSNOTIZ-DOKUMENTATIONSWEBSITE.md).

Vorhandene Grundlagen und Restarbeiten:

- **Bereits eingespielt:** sechs deutsche/englische Grafiken für Buchablauf, Erstellungskreislauf und Speichern samt eigenen Seiten und Verweisen, Änderung #224. In der Website wiederverwenden, nicht als noch fehlende Neuerstellung planen.
- **Lokal umgesetzt und geprüft:** zusätzliche Codex-Zeile unter dem Claude-Hinweis, angepasste gemeinsame Fußzeilenvorgaben und Dokumentationsprüfung. Noch nicht zu GitHub übertragen; vor der Übernahme den aktuellen Hauptstand abgleichen.
- **Beauftragt, noch umzusetzen:** das Bedienglossar nach [Umsetzungsauftrag](UMSETZUNGSAUFTRAG-BEDIENGLOSSAR.md).
- **Vorgezogen beauftragt am 9. November 2026:** zentrale Website, technische Erstellung, lokale Prüfungen und vorbereiteter manueller Veröffentlichungsweg als ein PR. Sichtprüfung mit Browser und tatsächliche Veröffentlichung bleiben gesondert freizugeben. Keine eigenen Websites für Buch-Repositories; private Buchdaten und interne Planungsunterlagen nicht ungeprüft veröffentlichen.

Die Aufnahme der Veröffentlichung als Lieferziel ersetzt weder die Prüfung des konkreten öffentlichen Inhalts noch einen ausdrücklichen Übertragungsauftrag nach der lokalen Arbeitsregel. Hosting, öffentliche Adresse und etwaige Kosten bleiben vor einer tatsächlichen Bereitstellung zu klären.

## Abhängigkeiten und Querschnittsregeln

- **Stabilität vor neuen Medienfunktionen:** v0.6.1 und v0.6.2 sichern zuerst Speichern, Freigaben und aktuelle Arbeitsstände ab. Das folgt der bestätigten Reihenfolge D02.
- **Gemeinsame Medienbasis vor Layout und Umschlagableitung:** v0.7.0 sichert Dateien, Referenzen und Freigaben; v0.7.1 ergänzt Layout. v0.7.2 nutzt diese Grundlagen und das vorhandene Umschlagmodell. Vor dem Nachbau klären, ob eine Vorlage nur die Vorderseite oder einen vollständigen Druckumschlag beschreibt.
- **Import vor zusätzlichen Analysewegen:** v0.8.0 liefert eine saubere Text-/Strukturbasis; v0.8.1 verarbeitet darauf nachvollziehbare Vorschläge. Ein Teil der vorhandenen Analysen lässt sich bereits früher unabhängig abnehmen.
- **Bedienglossar kann früher beginnen:** Es ist ein eigener bereits beauftragter Dokumentationsblock und kann parallel zur fachlichen Entwicklung bearbeitet werden. Seine Definitionen müssen den tatsächlichen Funktionsstand markieren. Die Versionszuordnung zu v0.9.0 ist eine Empfehlung, keine neu bestätigte Frist.
- **Vier Clients ab jeder betroffenen Änderung:** Anzeigenänderungen jeder Zwischenversion brauchen die Abnahme in ChatGPT, Codex, Claude und Open WebUI. Diese Pflicht wird nicht bis v0.9 oder zum Freigabekandidaten aufgeschoben. Lokale Tests ersetzen sie nicht.
- **Jede Datenänderung mit Migration:** Neue Felder für Layout oder Umschlag brauchen Standards für bestehende Bücher, Datenversion, Prüfung und Rückweg. Inkompatible Daten dürfen nicht ungeprüft überschrieben werden.

## Was ausdrücklich nicht als zusätzliche v1.0-Pflicht einplanen

Nach den bestätigten Beschlüssen bleiben eigene Web-App, eigener Verwaltungsdienst, Offline-Web-App, neue KI-Anbieter-API-Anbindungen und Prompt-Compiler nach v1.0. Bestehender optionaler API-Code wird nicht ungefragt entfernt; historische Aufzeichnungen bleiben erhalten.

Zeitgesteuerte KI-Anbieterläufe, neue Warteschlangen-/Serverinfrastruktur und automatische Anbieter-Kostenabrechnung dürfen nicht aus dem veralteten Vollausbau-Text als zusätzliche v1.0-Pflicht abgeleitet werden. Falls davon ein Teil unabhängig von den verschobenen Diensten gewünscht wird, braucht er eine gesonderte Abgrenzung.

- **v1.1:** Externe Word-/LibreOffice-Arbeitskopie mit Buchsperre, Vergleich und kontrollierter Rückführung, wie in D17 festgelegt.
- **Nach v1.0, bisher v1.5 eingeordnet:** Buchglossar-Erweiterungen und Buchübersetzung. Vorhandene Funktionen werden dadurch nicht ausgebaut oder entfernt. Das neue **Bedienglossar** ist davon unabhängig.
- **Ohne Versionszusage:** [Buchbezogene Overlays](PLANUNGSNOTIZ-BUCH-OVERLAYS.md). Bislang nur vorgemerkt; keine Overlay-Architektur als Voraussetzung für v1.0 erfinden. Das besprochene Ausblenden von Abschnittsbezeichnungen war ein Beispiel und kein eigenständiger Implementierungsauftrag.

## Abnahmehindernisse, die lokal nicht allein gelöst werden können

1. Tatsächliche Zugänge und Werkzeuge der vier Clients müssen für die jeweiligen Praxisprüfungen verfügbar sein. Ein erfolgreiches Codex-Skript oder eine installierbare Open-WebUI-Datei belegt die anderen Umgebungen nicht.
2. Der aktuelle YAWA-Stand und erreichbare Repository-Rechte müssen lesend nachgewiesen werden. Falls eine Kontosperre den Zugriff verhindert, bleibt die reale YAWA-Abnahme offen; lokale Fixtures ersetzen diese Prüfung nicht.
3. An vorhandenen YAWA-Buchdaten darf erst nach gesonderter ausdrücklicher Freigabe etwas geändert werden.
4. Die endgültige v1.0-Veröffentlichung bleibt eine gesonderte Entscheidung, selbst wenn die Entwicklungsversionen bereits übernommen wurden.

## Nächster sinnvoller Schritt

Nach Bestätigung oder Änderung dieser Lieferfolge einen konkreten Auftrag für **v0.6.1** erstellen: aktuelle Hauptbasis gegen die lokalen Änderungen abgleichen, die beschlossenen Schutzregeln und den tatsächlichen Arbeitsweg erfassen, veraltete Roadmap-Pflichten korrigieren und die Abnahmematrix anlegen. Die vorliegende Analyse ändert weder `workflow.yml` noch die offizielle Versionsnummer und legt keine GitHub-Meilensteine an.


**Vorziehung, keine weitere Umplanung:** Der technische Dokumentationsblock wird vor v0.9.0 vorbereitet. Das ändert keine andere Versionsstufe, keine übrige Roadmap-Zusage und nicht die geltende Programmversion. Pflege-, Fachprüfungs- und Releasepflichten stehen in [Dokumentationspflege](docs/DOKUMENTATION-PFLEGE.md).
