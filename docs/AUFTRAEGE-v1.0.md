# Ausführbare Arbeitsaufträge bis v1.0

Grundlage: [bestätigte Beschlüsse D01–D32](ENTSCHEIDUNGEN-v1.0.md), 08.11.2026. Diese Datei plant Umsetzung und Abnahme; sie erklärt keine Funktion allein durch ihre Aufnahme für fertig.

## Reihenfolge und Befugnisse

Bestandsabnahme → Standabgleich und Sicherung → Bilder und Import → Gesamtabschluss, ohne festen Termin (D02). Technische Abhängigkeiten innerhalb des Umfangs selbstständig lösen. Bestehende passende Issues fortführen, neue nur nach Überschneidungsprüfung. Fehlendes bestehendes Verhalten als Fehler, neues Verhalten als Feature-Request dokumentieren. Umsetzungen der hier beschlossenen Änderungen brauchen keine erneute Grundsatzfreigabe. Weiterer fachlicher Umfang braucht Zustimmung (D28).

GhostWriter und ghostwriter-ui dürfen geändert und in isolierten Testbranches geprüft werden. Vorhandene fremde Änderungen erhalten. Erfolgreich geprüfte beschlossene Änderungen dürfen selbstständig in main übernommen werden (D29/D30). Keine zusätzlichen produktiven Bereitstellungen oder Änderungen offizieller Update-Abläufe allein aufgrund dieser Vollmacht. Das Produktrelease v1.0 und Änderungen bestehender YAWA-Buchdaten benötigen eigene Zustimmung.

## A01 – Bestand und Abnahmebasis sichern

**Bezug:** #18, #41, #22, #74, #71. **Voraussetzung:** aktueller Programm-/UI-Stand und nur lesender YAWA-Abgleich.

- Vorhandene Implementierung, bereits belegte Tests und wirklich fehlende Arbeit je Akzeptanzkriterium inventarisieren. Alte ungeprüfte Checkboxen sind weder Beweis fehlender Implementierung noch bestandener Abnahme.
- Testdaten für leeres Projekt, Einzelbuch, Bibliothek und Freigaben verwenden. Reale Übernahme nur YAWA; dessen tatsächliche Version lesen, keinen veralteten Chatstand unterstellen.
- Erststart, Buch-/Abschnittsarbeit, atomare Speicherung, Übernahme, Freigaberücknahme, Probedruck, Auflage und unveränderliche Ausgabe gegen die bestehenden Testpläne prüfen.
- Deutsch/Englisch unabhängig von Buchsprache abnehmen; Datenseite zeigt nur nachgewiesene Daten. Chat-Abos erzeugen keine fiktiven API-Kosten.
- Die drei Clientgruppen sind GPT (ChatGPT und Codex), Claude, Open WebUI. Keine weitere Integration hinzufügen.

**Fertig:** Bericht mit Quellcommit, Testdaten, ausgeführten Fällen, Ergebnissen und offenen Prüfungen. Codefehler getrennt von fehlendem Clientzugang ausweisen. Nur belegte Akzeptanzkriterien schließen.

## A02 – Internes Branch-Modell und Rollen konsistent machen

**Bezug:** #169, D03/D04. **Abhängigkeit:** A01-Inventar.

- Gemeinsamen Arbeits-Branch erst bei tatsächlicher autorisierter Speicherung; unverändert keine neue Speicherung. Exakten Buch-/Arbeitsstand und passendes Änderungspaket prüfen.
- Branch-Erzeugung, atomare Mehrdatei-Commits, konkurrierende Ref-Änderung, fehlgeschlagenes Anlegen des Änderungspakets und Wiederanlauf ohne doppelte Inhalte absichern.
- Nach bestätigter Übernahme nur den vollständig übernommenen unveränderten Arbeitsstand entfernen. Keine verwaisten eigenen Commits ungeprüft löschen; kein Force-Push als Konfliktlösung.
- Branch-Namen und -Verwaltung intern halten. Benutzer sehen verständlich gespeichert/übernommen/freigegeben/fehlgeschlagen. Änderungen an tatsächlichen Anzeigen brauchen die unten festgelegte Vier-Client-Prüfung.
- Eigentümer/Bearbeiter/Leser anhand vorhandener GitHub-Rechte begrenzen; zusätzliche Freigabeberechtigung ausdrücklich zuordnen. Keine fehlende serverseitige Durchsetzung durch eine behauptete zentrale Rollenverwaltung ersetzen. Grenzen des jeweiligen Clients offenlegen.

**Fertig:** Lebenszyklus- und Konflikttests; Rollen-/Freigabeprüfung für die tatsächlich unterstützten Schreibwege; übereinstimmende Dokumentation. Ungeklärte technische Durchsetzbarkeit gemäß D32 melden, keine neue Verwaltungs-API einführen.

## A03 – Standabgleich und beschlossene Sicherung

**Bezug:** #179, D18/D20/D21. **Abhängigkeit:** A02-Speicherregeln.

- Bei neuer Aufgabe, Client-/Buchwechsel und vor Schreiben/Freigabe aktuellen Head und betroffene Dateien prüfen. Derselbe Chat kann nach Wiederaufnahme veraltet sein.
- Nicht kollidierende Änderungen auf aktueller Basis fortsetzen; Konflikte sichtbar klären und Eingaben erhalten. Unterbrochene Vorgänge vor Wiederholung auf tatsächliches Ergebnis prüfen.
- Manuelle Sicherungsbefehle und vorhandenen Abschnittsabschluss-Checkpoint testen. Umfang und Lücken nennen, erst bestätigten Push als gesichert melden. Getrennte Sitzungspakete und Freigaben erhalten.
- Keine zusätzliche Hintergrund-/Eingabeentwurfssicherung bis v1.0 versprechen. Inhalte behalten bis ausdrücklicher Löschauftrag; keine automatische Git-Historienumschreibung.

**Fertig:** Zwei-Client-Fälle, veraltetes Formular, unterbrochene Speicherung und Wiederherstellung mit Testdaten nachweisen. Nicht verfügbare Clients oder Ereignissignale als offene Pflichtfälle ausweisen.

## A04 – Bilder, Originale und Referenzen

**Bezug:** #54/#143, D13/D14. **Abhängigkeit:** Speicher- und Freigaberegeln.

- PNG/JPEG im Buchrepository, höchstens 20 MB pro Datei; weder neuer Speicherdienst noch Git LFS.
- Originaldatei unverändert erhalten. Buchfassung standardmäßig höchstens 3.000 Pixel längste Kante; Verkleinerung vorher bestätigen, eigene Datei statt stiller Ersetzung. Warnung bei unzureichender Druckauflösung.
- Bei 500 MB Bildbestand pro Buch warnen und weiteres Hochladen bestätigen lassen. Die Zählung reproduzierbar machen; Originale und Ableitungen nicht ausblenden, geteilte Dateien nicht doppelt zählen. Nicht vorhandenen Bestand nicht als null behaupten.
- Herkunft, Bildunterschrift, Alternativtext und Freigabestatus speichern. Figuren/Orte/Szenen/Abschnitte zuordnen. Upload aktiviert keine Referenz; Freigabe und Auswahl je Auftrag explizit.
- Keine automatische Anbieterübergabe oder Behauptung tatsächlicher externer Verwendung. Referenz ist keine automatische Buchabbildung.

**Aktualisierter Prüfstand vom 08.11.2026:** Originalschutz und ausdrücklich bestätigte Verkleinerung wurden lokal geprüft. Die frühere Aussage zur automatischen Verkleinerung ist überholt. Andere Medienlücken bleiben offen; siehe [Testbericht](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/tests/evidence/2026-11-08-bilder/TESTBERICHT.md). Eine vollständige Vier-Client-Abnahme liegt damit nicht vor.

**Fertig:** Grenzen, abgebrochene Bestätigung, unveränderte Originalbytes, getrennte Ableitung, Zuordnungen, Freigabe/Rücknahme und Bildausgabe testen; UI-Anteile in allen vier Clients abnehmen.

## A05 – Externe Bildrecherche ohne neue Anbieter-API

**Bezug:** D15; eigener Auftrag nach Überschneidungsprüfung, ergänzt #54/#143.

- Vorhandene Recherchewerkzeuge des jeweiligen Chats sowie eingereichte Bilder/Links nutzen. Keine neue Such-/KI-Anbieteranbindung.
- Quelle, Urheber und verfügbare Lizenzangaben dokumentieren. Fehlende Angaben als ungeklärt kennzeichnen; keine rechtliche Nutzungserlaubnis erfinden.
- Kandidat, gespeichertes Bild und freigegebene Buchabbildung unterscheiden. Einfügen ausdrücklich bestätigen; vorhandene Veröffentlichungsprüfungen erhalten.

**Fertig:** eigener Upload, recherchierter Kandidat mit Angaben, unklare Rechte und abgebrochene Übernahme geprüft. Keine automatischen Live-Rechtezusagen.

## A06 – Import und geprüfte Chat-Analysen

**Bezug:** #124/#123, D07/D16/D21/D22. **Abhängigkeit:** A03/A04 soweit Dateien betroffen.

- Import ohne KI erhalten. Rückgabeweg als Text und Datei mit Auftrag, benötigten Auszügen und Ausgangsstand; Format, Quellen und zwischenzeitliche Änderungen vor Speicherung prüfen.
- Arten: Figuren, Zusammenfassungen/Ziele, Stil, Orte, Zeitleiste, Kontinuität, Sprache, Sachbuch-Prüfstellen, Bildideen, Klappentext, Buchtyp/Zielgruppe, Serienabgleich. Glossar später.
- Vorschläge nicht automatisch ins Manuskript oder als Freigabe übernehmen; Originale behalten bis ausdrücklicher Löschauftrag. Bereits gespeicherte Fristen dürfen keine automatische Entfernung auslösen.
- Keine echte API-Abnahme verlangen; vorhandener optionaler Anbietercode bleibt außerhalb v1.0 erhalten. Ganze Bücher nicht im Chat ausgeben; bei Kapazitätsgrenzen Aufgaben nachvollziehbar in Einheiten teilen statt unbeaufsichtigte Ganzbuchanalyse zu versprechen.
- Altversionen v0.5/v0.6 mit Fixtures testen; keine allgemeine Fremdbestandsmigration beauftragen.

**Bekannte Abweichung vor Umsetzung:** `scripts/import_book.py` und Import-/Aufräumpfade enthalten Aufbewahrungsfristen und einen Entfernungspfad. Bestehende YAWA-Daten nicht ohne gesonderte Freigabe verändern.

**Fertig:** Import, korrupte Rückgabe, geänderte Basis, geprüfte Fundstellen, abgelehnte Vorschläge, wiederholter Auftrag und ausbleibende automatische Löschung getestet. Keine Schlüsselerfordernis im normalen v1.0-Weg.

## A07 – Profiler und Diagnose

**Bezug:** #204/#208, D24/D25/D27. **Abhängigkeit:** Bestandsinventar.

- Vorhandenen Profiler auf nachvollziehbare Herkunft, Geltung, Messmethode und Sichtbarkeitsgrenzen prüfen. Unbekannte Modell-/Plattformanteile nicht als gemessen ausgeben.
- Anweisungen nachvollziehbar ordnen, ohne Regeln still zu kürzen. Compiler und automatische Kürzung erst nach v1.0.
- Technische Fehlerberichte ohne Secrets, Buchtexte oder Gesprächsvolltexte; keine zusätzliche Telemetrie. Sitzungssicherungen getrennt behandeln.
- Vorhandene Kostenaufzeichnungen erhalten; tatsächlich/geschätzt/manuell/unbekannt unterscheiden; verfügbare GitHub-Limits zeigen, keine Anbieter-Kontingentabfrage.

**Fertig:** Diagnosefälle ohne zusätzliche Anbieteraufrufe; Datenschutztests mit synthetischen Markern; konkrete Integrationsfehler beheben statt Navigation aus Versionsvermutung abzuleiten.

## A08 – Abschluss und spätere Versionen

**Abhängigkeit:** A01–A07 und sämtliche anwendbaren Pflichtprüfungen.

- Offene Akzeptanzkriterien und vorhandene Implementierung je Aufgabe abgleichen; fehlende Prüfungen nicht durch geschlossene Issues verdecken.
- Gesamtabnahme mit vollständiger Testsuite, Schema/Workflow/Dokumentation und relevanten praktischen Abläufen.
- Produktrelease v1.0 erst nach eigener Schlussbestätigung. Keine zusätzliche produktive Bereitstellung.
- #209 ausdrücklich v1.1: Checkout, Sperre, kontrollierter DOCX-Rückimport. #19/#35/#61, Anbieterteile von #54/#143/#65/#66/#62/#71/#123/#124, Compiler #204 nach v1.0 ohne hier erfundene Folgeversion. Glossar/Übersetzung bestehende v1.5-Planung erhalten.

**Fertig:** geprüfter Abschlussbericht und konkrete Releasevorlage, keine unerfüllten Pflichtfälle als bestanden.

## A09 – Ergänzte Medien-, Umschlag- und Dokumentationsaufträge

- A04 um die [bestätigten Medienvorgaben](MEDIENPLATZIERUNG.md) und die offenen Befunde des [lokalen Bildtests](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/tests/evidence/2026-11-08-bilder/TESTBERICHT.md) ergänzen: Mengenbegrenzung, Grafikbeschriftung, Alternativtext, PDF-Zusammenhalt und Entwurfskennzeichnung. Sechs Positionen, Textumfluss und Breitenregler brauchen Umsetzung und getrennte Formatabnahme.
- Hochgeladenen Coverentwurf für v1.0 nach dem [ergänzten Entscheidungsauftrag](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/ENTSCHEIDUNGSAUFTRAG-v1.0.md#nachtrag-für-v10-umschlag-aus-hochgeladener-gestaltungsvorlage) verarbeiten: Analyse, Vorschlag, Vorschau, ausdrückliche Übernahme. Original erhalten und Unsicherheiten nennen.
- Das [Bedienglossar](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/UMSETZUNGSAUFTRAG-BEDIENGLOSSAR.md) als eigenen deutschen/englischen Dokumentationsblock umsetzen, vorhandene/geplante Funktionen klar unterscheiden.
- Die [zentrale Dokumentationswebsite](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/PLANUNGSNOTIZ-DOKUMENTATIONSWEBSITE.md) war v0.9.0 zugeordnet; ihre technische Umsetzung wurde am 9. November 2026 als lokal geprüfter gemeinsamer PR vorgezogen beauftragt. Quelldokumente und Sprachpaare unter docs/, sechs vorhandene Grafiken und öffentliche Beispielseiten nutzen. Manueller Veröffentlichungsweg standardmäßig ohne Dokumentationsaktivierung; Merge und Veröffentlichung nur nach gesonderter Freigabe. Pflege, Fachprüfung und Releasepflichten nach [Dokumentationspflege](DOKUMENTATION-PFLEGE.md).
- Die [vorgeschlagene Versionsfolge](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/PLAN-v1.0-ZWISCHENVERSIONEN.md) nicht automatisch als bestätigte Roadmap einsetzen. Buch-Overlays bleiben eine [Planungsnotiz](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/PLANUNGSNOTIZ-BUCH-OVERLAYS.md), DOCX-Metadaten gehören nach D17 zu v1.1.

**Fertig:** Je Block Implementierungs- und praktische Abnahmenachweise; Aufnahme in diese Liste allein erklärt keine Funktion für fertig.

## A10 – Vorhandene Skill-Unterstützung für v1.0 abgleichen

**Bezug:** bestätigter Skill-Beschluss vom 8. November 2026 im [Entscheidungsprotokoll](ENTSCHEIDUNGEN-v1.0.md#beschluss-vom-8-november-2026-skill-unterstützung).

- Vorhandene GhostWriter-Skills und Einstiegspfade für Claude und Codex inventarisieren und mit START.md, Buchprofil, Schreibablauf und Qualitätsprüfung abgleichen.
- Gemeinsame fachliche Quellen verwenden; widersprüchliche Parallelregeln beseitigen. Tatsächliche Ladewege und Werkzeuggrenzen je Client dokumentieren und prüfen.
- Mit synthetischen Buchdaten Einstieg, Profilübernahme, Schreiben/Überarbeiten und Qualitätsprüfung prüfen; ausdrückliche Buchfreigaben bleiben erforderlich.
- Eigenständige Buch-Skills ab v1.1 schrittweise ausbauen; einzelne Lieferumfänge gesondert festlegen. Entwicklungsskills nach lokalem Bedarf, ohne feste Produktversionszusage.

**Fertig:** Konsistente bestehende Unterstützung und dokumentierte praktische Nachweise für Claude und Codex; fehlende Clientprüfungen ausdrücklich offenhalten. Planungsaufnahme allein ist keine Implementierung.

## Verbindliche Testmatrix und noch offene Voraussetzungen

| Umgebung | Pflicht bei Anzeigenänderungen | Verfügbarkeit zu Beginn dieser Planung |
|---|---|---|
| ChatGPT | Darstellung, Verständlichkeit, Aktionen, Textalternative | Noch kein nachgewiesener vollständiger Testzugang |
| Codex | Unterstützte native/Text-Ausgaben, Verständlichkeit, Aktionen | Aktueller Dialog vorhanden; kein pauschaler Nachweis aller Anzeige-/Aktionsfälle |
| Claude | Unterstützte GhostWriter-Vorlagen und Rückfälle | Noch kein nachgewiesener Testzugang |
| Open WebUI | Tatsächliche Integration, Anzeigen und Werkzeugübergabe | Lokaler Code vorhanden; Live-Abnahme der Installation noch offen |

Diese Tabelle ist kein dauerhafter Berechtigungsnachweis; vor der jeweiligen Prüfung aktuelle Möglichkeiten feststellen. Ein Rendering- oder Unit-Test allein erfüllt keine praktische Pflichtprüfung in einem nicht erreichbaren Client. Vollständige autonome Fertigstellung ist solange eingeschränkt, wie ein betroffener Pflichtfall nicht ausführbar ist. Nach D32 nur betroffenen Teil zurückstellen, unabhängige Arbeit weiterführen.

Alle Ergebnisse nennen Commit/Version, Testart, Testdaten, Resultat und offene Grenzen. Weder Session-Sicherung noch dieses Planungsänderungspaket ändern selbst Anzeigen, Bilddaten oder bestehende YAWA-Bücher.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
