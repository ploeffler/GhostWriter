# Maschinenlesbares Workflow-Modell

## Zweck und Verbindlichkeit

`workflow.yml` ist die kanonische, maschinenlesbare Definition der GhostWriter-Arbeitsabläufe. Sie legt Zustände, erlaubte Übergänge, Voraussetzungen, unveränderliche Regeln, Historien und GitHub-Automatisierung fest. `ghostwriter.yml` bleibt für konkrete Buchmetadaten und die projektspezifische Konfiguration zuständig.

Die JSON-Schema-Datei unter `schemas/workflow.schema.json` beschreibt die Struktur und validiert zentrale Pflichtfelder und unveränderliche Sicherheitsregeln.

## Zustandsmodell

### Abschnitt

`planned → research → brainstorming → ready_to_write → writing → revision → [fact_check] → ready_for_approval → approved`

Recherche, Brainstorming, Revision und Faktenprüfung können mehrere Läufe bzw. Runden umfassen. Jeder Lauf wird als eigene Datei gespeichert. Faktenprüfung ist optional und verändert den Manuskripttext niemals automatisch.

Der Übergang zu `writing` verlangt eine ausdrückliche Schreibfreigabe. Der Übergang zu `approved` verlangt eine ausdrückliche Abschnittsfreigabe des Benutzers. Sie wird an den SHA-256-Fingerabdruck der von `section_file` gelesenen, außen getrimmten UTF-8-Fassung des Manuskripttexts gebunden (`approvals.yml` → `note: content_sha256=<sha256>`). Für Vor- und Nachspann gilt dieselbe Prüfung mit `kind: matter`. Ein freigegebener Text darf nicht bearbeitet werden. Zuerst muss die Freigabe ausdrücklich zurückgenommen werden (`approved → revision`); die Rücknahme wird als neuer, unveränderlicher Historieneintrag protokolliert. Der nächste Schreibvorgang benötigt anschließend eine neue Schreibfreigabe.

### Kapitel

`planned → in_progress → ready_for_assembly → assembly → review → ready_for_approval → approved`

Ein Kapitel kann erst zusammengeführt werden, wenn alle zugehörigen Abschnitte freigegeben sind. Die Kapitelgesamtfreigabe ist eine eigenständige Benutzerentscheidung und wird nicht aus Abschnittsfreigaben abgeleitet. Sie kann nur durch ausdrückliche Bestätigung zurückgenommen werden (`approved → in_progress`); betroffene Strukturänderungen invalidieren sie ebenfalls.

Die **Kapitelrecherche** (`runs.chapter_research`) recherchiert für das ganze Kapitel, wahlweise mit einer Aufgabe (Ziel recherchieren, Abschnitte erstellen, Kurzbeschreibung erstellen) und gewichtetem Zusammenhang mit dem vorherigen und nächsten Kapitel. Sie ändert keinen Status und keine Struktur; ihre Vorschläge wirken erst, wenn der Benutzer sie im Formular übernimmt. Neue Abschnitte aus Vorschlägen kommen ans Ende und setzen ein freigegebenes Kapitel auf `in_progress` zurück.

## GitHub-Aufgaben und Milestones

Issues sind optional und werden nur auf ausdrücklichen Benutzerwunsch oder bei ausdrücklich aktivierter Automatisierung angelegt; es gibt keine Pflicht zu einem Issue pro Arbeitseinheit. Wird ein Issue angelegt, enthält es mindestens Entitäts-ID, aktuellen und angestrebten Status, Aufgabentyp, einschlägige Anweisungen, Eingaben, Akzeptanzkriterien, betroffene Dateien und gegebenenfalls die Freigabeschranke. Milestones sind optionale Gruppierungen für Kapitel oder Projektphasen.

Milestones gruppieren Arbeit auf Kapitel- oder Projektebene. Das Schließen eines Issues oder das Abschließen eines Milestones ist niemals gleichbedeutend mit einer Benutzerfreigabe.

## Änderungsregeln

Stabile IDs werden unabhängig von sichtbaren Nummern geführt. Nummern werden aus der aktuellen Reihenfolge berechnet. Strukturänderungen bewahren Inhalte und Historie. Löschen und Aufteilen erfordern Bestätigung. Hinzufügen, Umbenennen, Neuordnen, Verschieben, Aufteilen oder Löschen setzt betroffene Kapitel aus jedem Prüf- oder Freigabestatus auf `in_progress` zurück und invalidiert deren Kapitel-Freigabe; nicht betroffene Abschnittsfreigaben bleiben nur erhalten, wenn ihr Manuskript unverändert ist.

## Schreib- und Auditregeln

- Keine Schreiboperation ohne die jeweils erforderliche ausdrückliche Freigabe.
- Vor jeder GitHub-Schreiboperation den erwarteten Head-SHA berücksichtigen.
- Mutationen mit Idempotency-Key absichern.
- Erfolg erst nach bestätigter GitHub-Antwort melden.
- Statuswechsel, Freigabeakteur, Zeitstempel und Commit-SHA dokumentieren.
- Globale KI-Qualitätsregeln dürfen lokal nur verschärft, niemals abgeschwächt werden.

## Verhältnis zu bestehenden Dateien

- `START.md`: Gesprächsführung und Onboarding.
- `ghostwriter.yml`: Metadaten und konkrete Buchkonfiguration.
- `workflow.yml`: kanonische Workflow- und Automatisierungsregeln.
- `schemas/workflow.schema.json`: strukturelle Validierung von `workflow.yml`.
- `docs/DATA-MODEL.md`: Dateistruktur und Datenkonventionen.

Die Workflow-Datei definiert das Soll-Verhalten. Sie bedeutet nicht, dass alle beschriebenen Automatisierungen bereits implementiert sind.


## Produkt-Roadmap

Die GhostWriter-Produktversion und die Ausgabeversion eines Buches sind getrennte Dinge.

- **GhostWriter v0.5** ist eine bereits nutzbare Basisversion mit diesem Funktionsumfang:
  - ein Projekt erstellen und einrichten,
  - Kapitel erstellen und einrichten,
  - Kapitel und Abschnitte bearbeiten,
  - eine Auflage erstellen und ihren Inhalt als PDF, DOCX und EPUB bereitstellen,
  - AI-Läufe (Recherche, Brainstorming, Schreiben) nur im Modus „Sofort“ direkt im Chat; der Modus „Zeitgesteuert“ über die Cloud-Warteschlange folgt nach v0.5.

  Erweiterte Automatisierung darf die Basisnutzung nicht blockieren.
- **GhostWriter v1.0** umfasst einen vollständigen Buchworkflow ohne Verbindungen zu KI-Anbieter-APIs: KI-Arbeit erfolgt im Chat oder über „Auftrag kopieren“ mit geprüfter Rückgabe. GitHub-Steuerung, Freigabe- und Auditmechanismen sowie Export und Veröffentlichung bleiben Teil des Ziels.
- Die Roadmap beschreibt den Zielumfang; Funktionen gelten erst nach Implementierung und Prüfung als umgesetzt.

### Stufen bis v0.5

Der Weg zu v0.5 ist in fünf Stufen geteilt. Jede endet mit einer Abnahme im Chat mit den Testdaten. Die Stufen sind als GitHub-Milestones `v0.1` bis `v0.5` angelegt, die Arbeitsaufträge als Issues; der ausführliche Plan steht in [GhostWriter v0.5 – Voraussetzungen und Arbeitsaufträge](https://claude.ai/artifact/Dx54iTWGE9nx9KgHUBdfPj).

| Stufe | Ziel | Abnahme |
|---|---|---|
| v0.1 | Datenmodell steht und wird geprüft | Prüf-Action läuft ohne Fehler über das leere Projekt und das ADHS-Projekt |
| v0.2 | Testprojekt lesen und anzeigen | Link zum Test-Repo zeigt Übersicht, Kapitel und Abschnitt mit richtigen Summen und Markern |
| v0.3 | Projekt und Kapitel einrichten und bearbeiten | Ersten Start auf einem kurzlebigen Branch vom Starter durchlaufen; im Testbuch anlegen, umordnen, speichern und mit Bestätigung freigeben; jede Änderung als Pull Request, Merge per Schaltfläche |
| v0.4 | AI-Läufe „Sofort“ | Recherche und Ghostwriting für einen ADHS-Abschnitt mit Lauf-Datei und Statuswechsel; Chat-Läufe über Abos ohne Kosteneintrag (#13) |
| v0.5 | Auflage und Export | Auflage 2 mit PDF, DOCX und EPUB; Auflage 1 unverändert; Testplan bestanden ([TESTPLAN-v0.5.md](TESTPLAN-v0.5.md)) |

### Nach v0.5

| Stufe | Ziel |
|---|---|
| v0.6 | Bibliothek: eine Installation, mehrere Bücher als Branches (#36–#41); automatische Migration der Datenstruktur (#59); README und Anleitung (#46); Programm-Repository öffentlich, Testbuch getrennt (#48); Abnahme nach [TESTPLAN-v0.6.md](TESTPLAN-v0.6.md) |
| v0.7 | Figuren auf Buch-Ebene (#53) und Bilderzeugung (#54) |
| v1.0 | Vollständiger Buchworkflow in ChatGPT, Codex, Claude und Open WebUI; Standabgleich, beschlossene Sitzungssicherung, Bilder/Referenzen/Bildrecherche, Import und Chat-Analysen, Deutsch/Englisch, Datenseite und vorhandener Profiler. Keine eigene Web-App, kein eigener Verwaltungsdienst, keine KI-Anbieter-API-Anbindungen. Maßgeblich: [Beschlüsse D01–D32](ENTSCHEIDUNGEN-v1.0.md). |
| v1.1 | Externe DOCX-Bearbeitung mit Checkout, Buchsperre und kontrollierter Rückführung (#209, D17) |
| v1.5 | Vorwort, Nachwort, Glossar (#58); Übersetzung des Buchs mit Auflagen je Sprache (#75) |

Jeder Schritt, der die Datenstruktur ändert, liefert eine Migration mit (#59); Doku und Programm prüft `scripts/check_docs.py` in `validate.yml`.

### Verbindliche Entscheidung: v1.0 ohne KI-Anbieter-APIs

**Entschieden am 08.11.2026:** Bis einschließlich v1.0 werden keine Verbindungen zu KI-Anbieter-APIs vorgesehen. Die v1.0-Abnahme setzt weder Anbieter-Schlüssel noch kostenpflichtige Modellaufrufe voraus. Diese Entscheidung ersetzt frühere v1.0-Zuordnungen der betroffenen API-Teile.

KI-Aufträge werden im Chat bearbeitet oder über „Auftrag kopieren“ an einen Dienst übergeben. Zurückgegebene Texte, Bilder und Analyseergebnisse werden geprüft und nur nach den bestehenden Speicher- und Freigaberegeln übernommen. Unbeaufsichtigte Ganzbuchläufe sind kein Ersatzversprechen dieses Wegs.

| Aufgabe | Bis v1.0 | Erst nach v1.0 |
|---|---|---|
| #54 Bilder | Auftrag, Hochladen, Zuordnung, Freigabe, Einfügen und Ausgabe | Direkte Bilddienstaufrufe samt Kostenprüfung |
| #143 Referenzbilder | Speicherung, Metadaten, Auswahl und Freigabe; manuelle Übergabe mit offen ausgewiesenem tatsächlichem Einsatz | Automatische Übergabe der Bildbytes an Anbieter |
| #123 / #124 Analysen und Import | Import ohne KI sowie Chat-/Kopieraufträge mit geprüfter Rückgabe | Anbieteraufrufe im Hintergrund und Abnahme mit echten API-Schlüsseln |
| #65 Warteschlange | Manuelle Auftragsverwaltung möglich | Zeitgesteuerte Anbieter-KI-Läufe |
| #66 / #62 / #71 Kosten und Limits | Vorhandene Aufzeichnungen und verfügbare Grenzen; unbekannte Werte klar kennzeichnen | Anbieter-Nutzungsimport, Kontingentabfragen und vollständige automatische Abrechnung |
| #19 / #35 / #61 | Bestehende Client-/GitHub-Wege nutzen; kein eigener Dienst | Eigener Verwaltungsdienst, eigene Web-App und Offline-Web-App |
| #75 Übersetzung | Bestehende Einordnung nach v1.0 bleibt; Chat-/Kopierweg möglich | Automatisierte Anbieterläufe |
| #204 Prompt-Tuning | Vorhandenen Profiler abnehmen und Anweisungen nachvollziehbar ordnen | Compiler, automatische Kürzung und neue Anbieteradapter |

Die spätere Entscheidung D06/D01 verschiebt zusätzlich die eigene GhostWriter-API (#19), Web-App (#35) und Offline-Web-App (#61) auf nach v1.0. Bestehende GitHub-Verbindungen der Clients und lokale Dateiverarbeitung bleiben zulässig. Bestehender optionaler Anbieter-Code und historische Kostenaufzeichnungen werden durch die Planänderung nicht gelöscht; sie sind kein v1.0-Liefer- oder Abnahmekriterium. Neue Anbieteranbindungen und deren Live-Abnahme werden nach v1.0 geplant, ohne hier eine spätere Versionsnummer festzulegen.

### Bestätigter Entwicklungsauftrag

Die [Beschlüsse D01–D32](ENTSCHEIDUNGEN-v1.0.md) ersetzen widersprechende ältere Planungen. Die [Arbeitsaufträge](AUFTRAEGE-v1.0.md) legen Lieferfolge, Nachweise und offene technische Voraussetzungen fest. Änderungen an Anzeigen sind in ChatGPT, Codex, Claude und Open WebUI zu prüfen; unbekannte oder nicht ausführbare Tests bleiben offen. Reale Datenübernahme beschränkt sich auf YAWA; weitere Versionsfälle werden mit Testdaten geprüft. Änderungen bestehender YAWA-Buchdaten brauchen eine gesonderte Freigabe. Beschluss ist kein Implementierungsnachweis.

### Buchübersetzung (geplant)

**Bestätigte Anforderungen vom 07.11.2026 zu #75; Umsetzung weiterhin für
v1.5 geplant.** Eine Übersetzung darf ausschließlich von einer bestehenden
**Auflage** ausgehen. Deren feststehender Buchstand ist die verbindliche
Quelle; ein laufender Arbeitsstand ist keine zulässige Übersetzungsbasis.

- **Ein Auftrag, ein Abschnitt:** Die Übersetzung ist pro Abschnitt im Chat
  abarbeitbar, kein einzelner Großauftrag für das ganze Buch. Sie lässt sich
  nach einem Abschnitt unterbrechen und später anhand des gespeicherten
  Fortschritts fortsetzen.
- **Im vorhandenen KI-Chat:** Der gewählte Chat-Dienst, beispielsweise Claude
  oder GPT, führt den Abschnittsauftrag aus. Dafür ist keine zusätzliche
  Übersetzungs-API erforderlich. Ein anderer Chat wird über Auftrag und
  Ergebnisrückgabe eingebunden; kein stiller Anbieterwechsel.
- **Kein Hintergrundlauf:** Der zuvor erwogene Übersetzungslauf über GitHub
  Actions ist durch die abschnittsweise Bearbeitung im Chat ersetzt. Allgemeine
  Pläne für zeitgesteuerte KI-Läufe bleiben davon unabhängig.
- **Gemeinsamer Kontext:** Jeder Auftrag erhält neben dem Originalabschnitt
  den erforderlichen Buch- und Kapitelkontext sowie einheitliche Vorgaben für
  Zielsprache, Erzählstimme, Namen und Terminologie.
- **Prüfung und Fortschritt:** Original und Übersetzung getrennt erhalten;
  Ausgangsauflage, Abschnitt, Zielsprache, verwendeten Dienst und Bearbeitungs-
  und Prüfstand nachvollziehbar zuordnen. Übersetzung prüfen und überarbeiten,
  bevor sie zur eigenen Freigabe vorgelegt wird. Eine erzeugte Übersetzung
  erhält keine automatische Freigabe. Vor Abschluss den vollständigen
  betroffenen Zusammenhang gemäß den Qualitätsregeln prüfen.
- **Sprachauflagen:** Die neue Sprachfassung bekommt ihre eigene Freigabe und
  Auflage. Eine spätere Originalauflage ersetzt weder die festgehaltene
  Übersetzungsbasis noch bereits freigegebene Übersetzungen automatisch.

Die konkrete Datenstruktur, Speicherung und Bedienung sind noch auszuarbeiten.
Diese Anforderungen sind keine bereits implementierte Übersetzungsfunktion.
Die davon getrennte Anbindung eines integrierten KI-Chats in der eigenen App
bleibt ein [offener Architekturpunkt](ARCHITECTURE.md#ki-anbindung-der-eigenen-app-planungsstand-07112026).

### Git als Produktvorteil

Die aus der Softwareentwicklung kommende Versionsverwaltung ist ein ausdrücklicher Produktvorteil: präzise gespeicherte Änderungsschritte, vergleichbare Fassungen, gezielte Wiederherstellung, getrennte Entwürfe und die eindeutige Zuordnung jeder Auflage zu ihrem Buchstand. README und Grundlagen erklären diese Vorteile in Autorensprache; fehlendes Git-Fachwissen ist eine Frage der einfachen Bedienung. Die Dokumentationsarbeit knüpft an [#46](https://github.com/ploeffler/GhostWriter/issues/46) an. Versioniert sind gespeicherte Änderungen, nicht jeder noch ungespeicherte Chatentwurf.

### Standabgleich zwischen Clients (geplant)

**Prioritärer Planungsauftrag [#179](https://github.com/ploeffler/GhostWriter/issues/179), im Zielumfang `cross_client_state_sync` für v1.0 erfasst; noch nicht umgesetzt.** Beim Wechsel zwischen Clients können Buchtext, Programm, Werkzeug, Anweisungen und lokale Kopien auf unterschiedlichen Ständen sein. GitHub bleibt die gemeinsame Quelle für gespeicherte Buchstände. Ein erfolgreich geladener Starttext ist ein Anweisungs-Snapshot und kein Nachweis, dass spätere Buchdaten aktuell sind.

**Vorhandene technische Teilprüfung:** `scripts/workflow_support.py ... guard <expected> <current> <paths...>` prüft unveränderte, nicht betroffene, betroffene sowie divergierte Git-Stände schreibfrei. Änderungen an `ghostwriter.yml`, `workflow.yml`, `assistant.yml`, Manifest oder Update-Stand verlangen unabhängig von der Zieldatei eine Kontextaktualisierung. Der Assistent muss aktuelle Remote-Refs bereitstellen und beim späteren Schreiben den aktuellen Head atomar prüfen. Es gibt dadurch weder einen Hintergrundabgleich noch einen zusätzlichen Dienst; vollständige Live-Client-Abnahme bleibt offen.

Für die Umsetzung untersuchen:

- **Leichten Abgleich:** Zu Beginn einer neuen Arbeitsaufgabe, bei Client-/Buchwechsel und vor Schreiben oder Freigaben Repository, Buch-/Lesebranch, Head-SHA und passenden offenen PR prüfen. Änderungen anhand von Commit-Beziehungen erkennen; Zeitstempel allein reichen nicht.
- **Getrennte Versionen:** Buch-Datenversion, Programmversion mit Upstream-Commit, Client-/Werkzeugversion, Anweisungs-/Profilstand sowie Index und Zusammenfassungen getrennt erfassen. Veraltete abgeleitete Daten nachladen oder ihre Originaldateien verwenden.
- **Ansichten und Eingaben:** Bei neuem Stand Ansichten und betroffenen Kontext aktualisieren. Nicht gespeicherte Eingaben erhalten, ihren Ausgangsstand mitführen und gegen die neue Basis abgleichen. Kollidiert dieselbe Datei, Schreiben stoppen und den konkreten Unterschied zeigen. Nicht kollidierende Änderungen auf aktueller Basis fortsetzen.
- **Startspeicher:** Den kurzen Instanz-Einstieg aus #178 wiederverwenden, aber eine leichte Aktualitätsprüfung und gezielte Invalidierung bei geändertem Programm, Profil oder Anweisungsstand vorsehen. Aktuelle Buchdaten weiterhin separat lesen. Bereits geöffnete Chats müssen ein Programmupdate erkennen können.
- **Gesprächsarbeit gegen Verlust sichern:** Der maßgebliche Fall ist ein längeres Arbeitsgespräch: Nach zwei Stunden fällt der Browser oder die App während einer kurzen Abwesenheit aus. Bereits erarbeitete Inhalte dürfen nicht ausschließlich im offenen Chat liegen. Dafür einen fortlaufend gesicherten Sitzungsstand planen: Gesprächsbeiträge und Entwürfe, Entscheidungen, offene Fragen, noch nicht übernommene Vorschläge sowie die aktuelle Aufgabe und ihre Buch-/Dateibasis. Ein neuer Chat muss daraus ohne den alten Browserzustand weiterarbeiten können. Eine Zusammenfassung dient als Einstieg, ersetzt aber nicht die Sicherung der eigentlichen Inhalte. Sicherungen bleiben von freigegebenem Manuskript und formalen Freigaben getrennt; vor Strukturfreigabe gelten weiterhin die bestehenden Grenzen für Repository-Schreibzugriffe. Sicherung nach Gesprächsschritten bzw. in kurzen Abständen untersuchen, bestätigten Sicherungsstand sichtbar machen und fehlgeschlagene Sicherungen melden. Noch nicht abgesendete Eingaben brauchen eine clientseitige Entwurfssicherung, soweit die Anbindung sie unterstützt; der Assistent kann ihm nicht übermittelte Eingaben nicht sichern. Nicht auf das Erkennen von Einschlafen oder Abwesenheit warten. Bereits an GitHub Actions übergebene Aufträge sind nicht der Schwerpunkt dieses Verlustfalls.
- **Rückkehr nach Inaktivität:** Verbindung, Sitzung, Daten- und Anweisungsstand vor der nächsten Schreibaktion oder Freigabe erneut prüfen; ohne Aufwecksignal spätestens bei der nächsten Eingabe oder Aktion. Gesicherte Eingaben wiederherstellen und unterbrochene Aufträge anhand ihres tatsächlichen Ausführungs- und Speicherstands abgleichen. Fehlendes Netz oder abgelaufene Anmeldung verständlich anzeigen.
- **Verständlichen Status:** Gelesenen Commit und nicht abgeglichene Bereiche benennen. Bei fehlendem Zugriff oder inkompatiblen Daten-/Clientversionen keine unbelegte Zusage „alles synchron“ und keine Schreiboperation auf ungeprüfter Basis.

Leseaktualisierung erteilt keine Übernahmefreigabe. Synchronisation darf weder Force-Push noch pauschales Zusammenführen oder Verwerfen eines Arbeitsbranches bedeuten. Die bestehenden Regeln für Text-, Kapitel- und Auflagenfreigaben bleiben erhalten.

**Abnahme für die spätere Umsetzung:** Client A speichert; Client B sieht den neuen Stand ohne neuen Chat. Ein altes Formular in B überschreibt A nicht. Merge und Branchwechsel werden trotz veraltetem Index erkannt. Programm- und Profiländerungen invalidieren betroffene Anweisungen. Nicht gespeicherte Eingaben bleiben erhalten. Neustart, gekürzter Kontext, Offline-/Netzfehler, kollidierende und nicht kollidierende Änderungen werden getestet. Bezug: #178, eigene Schnittstelle #19 und Offline-Arbeit #61.

**Zusätzlicher mobiler Abnahmetest:** Tablet oder Mobiltelefon während einer Eingabe oder eines laufenden Speicherauftrags sperren und liegen lassen; währenddessen auf einem anderen Gerät weiterarbeiten. Nach dem Entsperren denselben Chat wieder aufnehmen, auch nach Netzwechsel, abgelaufener Sitzung oder Neuladen der App. Vor der nächsten Änderung muss der aktuelle Stand geprüft sein; wiederherstellbare Eingaben bleiben erhalten, Konflikte werden angezeigt und bereits ausgeführte Aufträge nicht doppelt gestartet. Den Fall ohne Aufwecksignal sowie einen vom Betriebssystem beendeten Client ausdrücklich prüfen und etwaige Wiederherstellungsgrenzen sichtbar machen.

**Abnahme beim Einschlafen:** Den Client während Eingabe, laufender KI-Antwort, Werkzeugaufruf und Speicherung jeweils sperren oder ohne Vorwarnung anhalten/beenden. Bereits gesicherte Eingaben und Ergebnisse bleiben erhalten. Für jeden gestarteten Auftrag lässt sich feststellen, ob er weiterläuft, pausiert, abgeschlossen oder fehlgeschlagen ist; bei unklarem Ausgang wird dieser ausdrücklich angezeigt und vor einem erneuten Ausführen geklärt. Kein Test darf von einem zuverlässig zugestellten letzten Sperrsignal oder einem dauerhaft aktiven mobilen Chat ausgehen.

### Session sichern, laden und übernehmen

**Manueller, durch den Assistenten ausgeführter Sicherungsablauf implementiert (#179).** `Session sichern` (auch `Chat sichern`, `Chat speichern`) legt verfügbare Gesprächsbeiträge, Entscheidungen, Recherche, Brainstorming einschließlich Varianten und verworfener Ansätze, Entwürfe, Planung und offene Fragen dauerhaft ab. Ein Commit je geändertem zusammenhängendem Thema und ein gemeinsamer PR je Sitzung. Strukturierte Zusammenfassungen ersetzen nicht die eigentlichen Inhalte; Lücken und fehlende Anhänge bleiben sichtbar.

`Session laden` liest die Sicherung zum Weiterarbeiten. `Session übernehmen` umfasst Prüfung, automatische Fehleranalyse bei fehlgeschlagenen Checks oder Merge, einen sicheren technischen Reparaturversuch durch den Assistenten, erneute Prüfung und Merge des Sicherungs-PRs. Kein zusätzlicher Reparaturbefehl. Inhaltliche Konflikte und fehlende Rechte nicht umgehen. Sichern allein mergt nicht; auch `changes.auto_merge` hebt diese Trennung nicht auf. Manuskript und inhaltliche Freigaben bleiben unverändert.

Der ausführbare Git-/PR-Helfer `scripts/chat_backup.py` prüft konkurrierende Änderungen, Gesprächshistorie, Sicherungsdateien und Prüfstatus. Der Assistent übernimmt die inhaltliche Sichtung und gezielte Reparaturen nach [Session-Sicherung](SESSION-SICHERUNG.md). Authentifizierte Git-/GitHub-Werkzeuge sind erforderlich; keine zeitgesteuerte Hintergrundsicherung, kein vollständiger App-Export und keine autonomen Quellcode-Reparaturen durch das Hilfsprogramm. Nach Abschluss des Dialogs über offene Abschnittspunkte wird derselbe Sicherungsablauf automatisch ausgelöst: keine ausstehende Antwort, alle besprochenen Punkte beantwortet, entschieden oder ausdrücklich vertagt, Nachrichtenbelege vorhanden. `checkpoint` prüft diese Voraussetzungen; kein automatischer Merge oder Freigabe. Die weitergehende fortlaufende Absturzabsicherung aus #179 bleibt geplant. Maschinenlesbare Regeln: `workflow.yml` → `session_backup`.

### Extern in Word oder LibreOffice weiterarbeiten (geplant)

**Anforderung [#209](https://github.com/ploeffler/GhostWriter/issues/209), noch nicht umgesetzt; Versionszuordnung offen.** Ein Benutzer gibt eine DOCX-Arbeitskopie aus, arbeitet beispielsweise zwei Wochen außerhalb von GhostWriter und lädt die bearbeitete Datei im Chat hoch. Die Änderungen werden kontrolliert in dasselbe Buch zurückgeführt. Der bestehende Erstimport (#124) legt ein neues Buch an und ersetzt diesen Abgleich nicht.

- **Arbeitskopie:** Von Lesevorschau und veröffentlichter Auflage unterscheiden. Repository, Buch-/Lesebranch, Quellcommit, Exportkennung und tatsächlichen exportierten Ausgangstext zuordnen; beständige Kennungen für Kapitel und Abschnitte vorsehen und ihren Erhalt in den unterstützten Programmen prüfen. Unfertige Inhalte dürfen als erkennbarer Arbeitsstand enthalten sein.
- **Checkout und Bearbeitungssperre:** Zur externen Bearbeitung das gesamte Buch ausdrücklich auschecken. Sperre mit Buch, Checkout-/Exportkennung, Benutzer, Zeitpunkt und Ausgangscommit dauerhaft clientübergreifend speichern und als „Extern in Bearbeitung / ausgecheckt“ anzeigen. Lesen bleibt möglich; sämtliche regulären GhostWriter-Schreibwege einschließlich anderer Chats, Automatik, Metadaten-, Struktur-, Freigabe-, Update- und Auflagenänderungen am betroffenen Buch müssen die Sperre beachten. Andere Bücher bleiben bearbeitbar. Laufende Schreiber beim Checkout koordiniert abschließen oder stoppen; Arbeitskopie erst nach bestätigter Sperre auf feststehender Basis als geschützt ausgeben. Reine Lesevorschau sperrt nicht; keine zweite unabhängige Arbeitskopie während der Sperre, erneuter Download derselben Exportfassung bleibt möglich.
- **Rückgabe und Entsperren:** Upload, Zeitablauf, Chatende und Gerätewechsel heben die Sperre nicht auf. Nur der zugehörige ausdrücklich bestätigte Rückimport darf die erforderlichen Änderungen durchführen; erst nach vollständig erfolgreicher Übernahme und bestätigtem Abschluss entsperren. Fehler oder Konflikte erhalten die Sperre. Abbruch oder verlorene Datei erfordern eine gesonderte ausdrückliche Entsperrentscheidung mit Hinweis auf nicht zurückgeführte externe Änderungen; Exportbasis und Historie erhalten. Checkout und Entsperren sind keine inhaltlichen Freigaben. Eine Anwendungssperre verhindert direkte Änderungen durch fremde Git-Werkzeuge nicht; solche Umgehungen beim Rückimport erkennen und die Schutzgrenze offen benennen.
- **Vergleich:** Exportbasis, externe Fassung und aktuellen Buchstand vergleichen. Text- und Strukturänderungen einschließlich Ergänzungen, Löschungen, Umbenennungen, Verschiebungen, Aufteilungen und Zusammenführungen als Vorschlag anzeigen. Trotz Sperre außerhalb von GhostWriter entstandene Änderungen erhalten; Konflikte und unsichere Zuordnungen ausdrücklich klären. Fehlende Teile eines Teildokuments sind keine automatische Löschung.
- **Dokumentinhalte:** Änderungsverfolgung ist keine Voraussetzung; offene nachverfolgte Änderungen nicht still annehmen oder verwerfen. Kommentare separat behandeln. Inhalt und reine Gestaltung unterscheiden; Regeln für Hervorhebungen, Listen, Fußnoten, Tabellen, Bilder und Verweise festlegen. Konvertierungsverluste vor Übernahme melden. Original und Vergleichsbasis nach nachvollziehbarer Aufbewahrungsregel sichern.
- **Übernahme:** Erst nach ausdrücklicher Bestätigung ausgewählte Änderungen gegen den erneut geprüften aktuellen Buchstand übernehmen. Freigegebene Texte brauchen zuvor die ausdrückliche Freigaberücknahme; Struktur- und Löschschutz bleiben wirksam. Keine automatische Freigabe. IDs soweit möglich und sonstige Projektdaten erhalten; betroffene Zusammenfassungen aktualisieren oder als veraltet markieren und die vollständige betroffene Einheit nach `docs/QUALITAETSSICHERUNG.md` redigieren.
- **Robustheit:** Wiederholter Import erzeugt keine doppelten Inhalte. Fehlende Basis, falsches Buch, verlorene oder duplizierte Kennungen sowie nicht unterstützte Inhalte werden konkret gemeldet. Ganzbuchkonvertierung und Vergleich erfolgen als Datei-/Hintergrundverarbeitung; der Chat zeigt Berichte und gezielte Ausschnitte.

**Abnahme:** DOCX in Word und LibreOffice bearbeiten und in dasselbe Buch zurückführen; unveränderte Arbeitskopie ohne inhaltliche Änderungen. Parallele Änderungen, Konflikte, Strukturänderungen, Teildokumente, verlorene Kennungen, Kommentare, Änderungsverfolgung, Fußnoten, Bilder, Tabellen und reine Layoutänderungen prüfen. Fehlende Basis, Wiederholungsimport und eine Änderung des Buchstands zwischen Vorschau und Übernahme müssen sicher behandelt werden. Freigegebene Inhalte bleiben geschützt und sonstige Projektdaten erhalten. Bezug: #124, Ausgabeoptionen #68, Standabgleich #179.

**Checkout-Abnahme:** Alle regulären Schreibwege und Automatik beachten die Sperre über Neustart und Gerätewechsel hinweg; andere Bücher bleiben bearbeitbar. Konkurrierende Schreiber beim Checkout, Exportfehler, zweite Arbeitskopie, verlorene Datei und ausdrücklichen Abbruch testen. Upload allein entsperrt nicht; erfolgreicher bestätigter Rückimport entsperrt, Fehler erhalten die Sperre. Direkte externe Änderungen werden trotz Sperre erkannt. Reine Vorschau bleibt ohne Sperre.

## Buchausgaben als GitHub Releases

Jede veröffentlichte Ausgabe des Buches wird als eigener GitHub Release abgebildet. Ein Release ist ein unveränderlicher Snapshot eines konkreten Repository-Commits mit Release Notes und – soweit erzeugt – PDF-, EPUB- und DOCX-Dateien.

- Ausgaben heißen **Auflagen** und werden mit ganzen Zahlen ab 1 gezählt. Der Release-Name verbindet Kurztitel und Auflage, z. B. „ADHS im Erwachsenenleben – Auflage 1“.
- Der Tag ist daraus abgeleitet: Kurztitel in Kleinbuchstaben, Umlaute umgeschrieben, Leer- und Sonderzeichen als Bindestrich, z. B. `adhs-im-erwachsenenleben-auflage-1`.
- Eine neue Auflage entsteht nur auf ausdrücklichen Wunsch des Benutzers.
- Nur ausdrücklich freigegebene Manuskriptinhalte dürfen veröffentlicht werden.
- Release Notes dokumentieren Änderungen gegenüber der vorherigen Ausgabe.
- Korrekturen werden im Repository gesammelt und erscheinen mit der nächsten Auflage. Veröffentlichte Auflagen werden nicht verändert.
- GhostWriter-Produktversionen (v0.5/v1.0), technische Git-Tags und Buchausgaben sind getrennte Versionsräume.


## AI-Kosten und Nutzungsverbrauch

**Erfassungsbereich (entschieden am 31.10.2026, #13):** Erfasst werden zusätzliche, verbrauchsabhängige KI-API-Kosten aus GhostWriter-Backend-Aufrufen (`backend_api`) und aus GitHub Actions (`action_api`). Chat-Arbeit über bestehende Abos erzeugt keinen Kosteneintrag.

- Arbeit im Chat über bestehende Abos erzeugt **keinen** Kosteneintrag: keine geschätzten API-Kosten, kein `unavailable`-Eintrag.
- Reine Verwaltungsanfragen über das Backend (Projekt lesen, Dateien speichern, Übersichten laden) erzeugen keinen KI-Kosteneintrag.
- Betriebs- und Hostingkosten der GhostWriter-Infrastruktur sowie Chat-Abogebühren gehören nicht in diese Rechnung (Abos lassen sich im Formular „KI-Dienste“ zur Information notieren).
- Laufhistorie und Kosten sind getrennt: Auch Chat-Läufe ohne Kosten werden als Lauf-Datei dokumentiert.
- Einträge aus der Zeit vor v0.4 ohne Herkunft werden als `legacy_chat_estimate` gekennzeichnet und zählen nicht mit (`scripts/migrate_project.py`).

Jeder kostenpflichtige KI-API-Aufruf über das Backend wird als eigener, unveränderlicher Kosteneintrag erfasst und primär einem Abschnitt über dessen stabile ID zugeordnet. Projektweite Aktivitäten dürfen ohne `section_id` in `costs/project.yml` stehen; bei Abschnittsaktivitäten ist die stabile `section_id` Pflicht. Erfasst werden – soweit verfügbar – Anbieter, Modell, Aktivitätstyp, Zeitpunkt, Token-/Nutzungsmenge, Preisgrundlage, Preisquelle und Betrag. Nicht verfügbare Werte werden ausdrücklich als unbekannt markiert; manuelle Eingaben und Schätzungen bleiben als solche gekennzeichnet.

- **Abschnitt:** Summe aller zugeordneten AI-Aktivitäten.
- **Kapitel:** automatisch berechnete Summe der Abschnittssummen.
- **Projekt:** automatisch berechnete Summe aller Kapitelsummen zuzüglich separat ausgewiesener projektweiter Kosten.
- Tatsächliche und geschätzte Kosten werden getrennt ausgewiesen. Originalwährung und Originalbetrag bleiben erhalten; Umrechnungen speichern Wechselkurs und Datum.
- Summen werden aus Einzelbuchungen abgeleitet. Dieselbe Aktivität darf nicht zusätzlich auf Kapitel- oder Projektebene verbucht werden.
- Korrekturen erzeugen nachvollziehbare Gegen- oder Folgeeinträge; historische Buchungen werden nicht stillschweigend überschrieben.

### Ausbaustufen

**v0.5:** Kosteneinträge für KI-API-Aufrufe über eine implementierte GhostWriter-API, optionale Token-/Nutzungsdaten, Abschnittszuordnung, Kapitelzwischensummen und Projektgesamtbetrag; Kennzeichnung tatsächlicher und geschätzter Kosten. Kostenanzeigen sind keine Voraussetzung für die Arbeit im Chat; ohne Backend-Aufrufe zeigen sie „–“.

**v1.0:** vorhandene Kostenaufzeichnungen nachvollziehbar anzeigen, tatsächliche und geschätzte Werte unterscheiden und Budgetgrenzen nur aus verfügbaren Daten berechnen. Kein automatischer Import von Anbieter-Nutzungsdaten oder Kontingenten; diese Erweiterungen folgen erst nach v1.0.

Die Kostenfunktion muss auch dann nutzbar bleiben, wenn ein Anbieter keine Nutzungsdaten oder Rechnungswerte bereitstellt.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
