# Bestätigte Entscheidungen bis v1.0

Stand: 08.11.2026. Dieses Protokoll enthält die ausdrücklich bestätigten Beschlüsse aus dem Entscheidungsdialog. Es ersetzt die vorbereitenden Empfehlungen des Entscheidungsauftrags. Beschlossen bedeutet nicht implementiert oder abgenommen.

GitHub bleibt Projektspeicher. KI-Anbieter-APIs, eigener Verwaltungsdienst, eigene Web-App und deren Offline-Modus sind bis einschließlich v1.0 ausgeschlossen. Produktrelease v1.0 und Änderungen bestehender YAWA-Buchdaten bleiben gesondert zu bestätigen.

## D01 – Verbindlicher Umfang von v1.0

Beschluss D01 (bestätigt am 08.11.2026 durch „ja“):
- Bis v1.0: Buchworkflow, Bibliothek, Freigaben und Export vollständig abnehmen; ChatGPT, Codex, Claude und Open WebUI unterstützen und Anzeigenänderungen in allen vier Umgebungen testen.
- Standabgleich sowie die nach D20 beschlossene Sitzungssicherung; keine zusätzliche Hintergrund- oder Eingabeentwurfssicherung als Pflicht.
- Bilder, Referenzbilder und externe Bildrecherche nach D13–D15; Manuskriptimport und bestätigte Analysearten nach D16.
- Deutsch/Englisch, Datenseite mit tatsächlich verfügbaren Informationen und vorhandener Prompt-Profiler; kein Prompt-Compiler oder automatische Prompt-Kürzung bis v1.0.
- Reale Datenübernahme nur für YAWA; weitere Versionsfälle mit Testdaten nach D22.
- Technische Branch-Trennung bleibt für Benutzer unsichtbar gemäß D04.
- Nach v1.0: eigene Web-App, eigener Verwaltungsdienst, Offline-Web-App und KI-Anbieter-API-Anbindungen. Kein späterer Termin dafür festgelegt.
- Externe DOCX-Rückführung ausdrücklich v1.1. Glossar und Buchübersetzung bleiben nach v1.0; bisherige v1.5-Einordnung ohne gesonderte Änderung beibehalten.
- D02–D32 konkretisieren Umfang, Schutzregeln, Abnahme und Befugnisse. Frühere Empfehlungen und Tabellen gelten nur, soweit sie diesen bestätigten Beschlüssen nicht widersprechen.

## D02 – Prioritäten und Lieferreihenfolge

Beschluss D02 (bestätigt am 08.11.2026 durch „ja“):
- Reihenfolge: bestehende Funktionen abnehmen → Standabgleich und Sicherung → Bilder und Import ergänzen → abschließende v1.0-Abnahme.
- Kein fester Termin.
- Verschobene Web-App-, Verwaltungsdienst- und Anbieter-API-Arbeiten sind kein Teil dieser v1.0-Lieferfolge. Technische Abhängigkeiten innerhalb der bestätigten Aufgaben werden berücksichtigt.

## D03 – Nutzerkreis und Zusammenarbeit

Beschluss D03 (bestätigt am 08.11.2026 durch „übernehmen“):
- Nutzerkreis: Auftraggeber und ausdrücklich eingeladene Nutzer; keine öffentliche Registrierung.
- Rollen: Eigentümer, Bearbeiter und Leser. Tatsächliche GitHub-Rechte begrenzen den Zugriff; die Anwendung erweitert diese Rechte nicht.
- Zusammenarbeit: Mehrere Bearbeiter je Buch sind erlaubt.
- Gleichzeitiges Speichern: Schreibvorgänge werden nacheinander verarbeitet und gegen den aktuellen Stand geprüft. Konflikte werden angezeigt; Eingaben bleiben erhalten.
- Inhaltliche Freigaben: Nur der Eigentümer oder ausdrücklich benannte Freigabeberechtigte dürfen Abschnitte, Kapitel und Auflagen freigeben. Bestehende ausdrückliche Freigaben und Schutzregeln bleiben wirksam.

## D04 – Entscheidung #169 verbindlich machen

Beschluss D04 (bestätigt am 08.11.2026 durch „ja - für den benutzer ist diese trennung/unterteilung nicht sichtbar“):
- Je Buch bleibt ein gemeinsamer technischer Arbeits-Branch bestehen; erst bei autorisierter Speicherung anlegen und nach vollständiger Übernahme entfernen.
- Bestehende technische Namen und die Einstellung „sofort übernehmen“ bleiben erhalten.
- Die Trennung zwischen Buch- und Arbeits-Branch ist für Benutzer nicht sichtbar und verlangt keine Branch-Auswahl oder Branch-Verwaltung. Technische Zuordnung wird intern erledigt.
- Fachlich relevante Speicher-, Übernahme-, Fehler- und Freigabezustände bleiben verständlich erkennbar. Ein offener oder fehlgeschlagener Vorgang darf nicht als bereits übernommen oder freigegeben erscheinen.
- Technische Details können bei ausdrücklich angeforderter Diagnose erklärt werden; sie sind kein Bestandteil des normalen Bucharbeitsablaufs.
- Die Umsetzung und Dokumentation zu #169/#215 sind auf diese Bedienvorgabe abzustimmen. Dieser Beschluss erklärt bestehende Anzeigen nicht ungeprüft für konform.

## B. Oberfläche und KI-Arbeitsweise ohne Anbieter-API

## D05 – Verbindlich unterstützte Clients

Beschluss D05 (bestätigt am 08.11.2026):
- Verbindlich unterstützt werden genau die drei Clientgruppen GPT, Claude und Open WebUI.
- GPT umfasst ausdrücklich sowohl ChatGPT als auch Codex. Die konkrete Abnahmematrix hat deshalb vier Umgebungen: ChatGPT, Codex, Claude und Open WebUI.
- Jede Änderung an „pseudo grafischen“ bzw. grafisch aufbereiteten Anzeigen muss in allen vier Umgebungen geprüft werden. Das betrifft insbesondere Übersichten, Karten, Tabellen, Formulare, Menüs, Statusanzeigen und zugehörige Text-/Darstellungsrückfälle.
- Je Umgebung nur tatsächlich unterstützte Darstellung verwenden: für ChatGPT/Codex unterstützte native Chat-Ausgaben bzw. Text/Markdown, für Claude die dort unterstützten GhostWriter-Vorlagen, für Open WebUI dessen unterstützten Darstellungsweg. Keine fremden Widgets oder Bedienfunktionen als unterstützt voraussetzen.
- Die Prüfung umfasst Darstellung, Verständlichkeit, verfügbare Aktionen und deren unveränderte fachliche Bedeutung. Fehlende Testmöglichkeiten ausdrücklich als offen ausweisen; ein Test in einer Umgebung ersetzt keinen Test in einer anderen. Eine ungeprüfte Umgebung darf nicht als bestanden gemeldet werden.
- Weitere Clients erhalten bis v1.0 keine eigene Integrations- oder Supportzusage.
- Kein einzelner primärer Client wird durch diesen Beschluss festgelegt; die vier Umgebungen sind für Änderungen an diesen Anzeigen gleichwertige Pflichtprüfungen.

## D06 – Eigene Web-App ohne integrierten Modellaufruf

Beschluss D06 (bestätigt am 08.11.2026 durch „verschieben, weil api“):
- Eigene Web-App (#35) und eigener GhostWriter-Verwaltungsdienst (#19) werden auf nach v1.0 verschoben; keine spätere Versionsnummer festgelegt.
- Bis einschließlich v1.0 Arbeit ausschließlich über die in D05 festgelegten Clients und deren vorhandene GitHub-Anbindung bzw. dokumentierte Datei-/Kopierwege.
- Die vorhandene GitHub-Anbindung der Clients bleibt zulässig. Keine neue eigene Verwaltungs-API oder KI-Anbieter-API als Voraussetzung für v1.0.
- Web-App-abhängige Offline-Buchbearbeitung im Browser (#61) ist damit ebenfalls nach v1.0 verschoben. Dies verwirft weder bestehende lokale Arbeitskopien noch verfügbare Dateiverarbeitung.
- D01 muss den Lieferumfang entsprechend korrigieren. D09–D13 und D25–D27 sind nur hinsichtlich tatsächlich verbleibender Funktionen zu bearbeiten; verschobene Hosting-/Dienstfragen blockieren die v1.0-Entwicklung nicht.

## D07 – Übergabe und Rückgabe von KI-Ergebnissen

Beschluss D07 (bestätigt am 08.11.2026 durch „ja“):
- KI-Aufträge werden als kopierbarer Text oder als Datei bereitgestellt.
- Der Auftrag enthält die Aufgabe, die benötigten Buchauszüge und den zugrunde liegenden Buchstand.
- Ergebnisse können als Text oder Datei zurückgegeben werden.
- Vor dem Speichern werden Format, Quellen und zwischenzeitliche Änderungen am Buchstand geprüft. Nicht prüfbare Angaben werden ausdrücklich als solche gekennzeichnet.
- Vorgeschlagene Änderungen werden zur Sichtung gezeigt; bestehende Speicher- und Freigaberegeln bleiben wirksam. Die Rückgabe allein speichert oder genehmigt nichts.
- Der Wechsel zwischen den unterstützten Clients erfordert keine eigene KI-Anbieter-API.

## D08 – Bestehender optionaler Anbieter-Code

Beschluss D08 (bestätigt am 08.11.2026 durch „ja“):
- Bestehender optionaler KI-Anbieter-API-Code bleibt erhalten und wird klar als außerhalb des v1.0-Lieferumfangs gekennzeichnet.
- Die Nutzung und Abnahme von v1.0 setzt keine Einrichtung von KI-Anbieter-Schlüsseln voraus.
- Für v1.0 werden keine kostenpflichtigen Live-Tests gegen KI-Anbieter-APIs verlangt oder durch diesen Beschluss autorisiert.
- Historische Kosten-, Nutzungs- und Laufaufzeichnungen bleiben erhalten.
- Keine Entfernung oder Migration des vorhandenen Codes allein aufgrund dieser Planungsentscheidung.

## C. Verwaltungsdienst, Betrieb und Zugänge

D09–D13 und D25–D27 müssen konkret beantwortet werden, wenn ein gehosteter Dienst zu D01 gehört. Wird er verschoben, bleibt die Umsetzung über bestehende Werkzeuge der gewählten Clients maßgeblich.

## D09 – Hosting, Laufzeit und Betriebsbudget

Beschluss D09: Entfällt für v1.0 aufgrund D06 und abschließend D01; eigener Hosting-/Verwaltungsdienst nach v1.0.

## D10 – Anmeldeverfahren und GitHub-Verknüpfung

Beschluss D10: Eigene Dienstanmeldung/GitHub-App nach v1.0 gemäß D06/D01. Vorhandene GitHub-Anbindungen der gewählten Clients bleiben bestehen; Rechte nach D03.

## D11 – Domain, Umgebungen und Bereitstellung

Beschluss D11: Eigene Dienst-/Web-App-Domains und Bereitstellungsumgebungen nach v1.0 gemäß D06/D01. Entwicklungs- und Testbefugnisse nach D29/D30 bleiben wirksam.

## D12 – Zusätzliche Persistenz

Beschluss D12: Zusätzliche Verwaltungsdatenbank nach v1.0 gemäß D06/D01; keine neue Pflichtpersistenz für einen eigenen Dienst bis v1.0.

## D13 – Medienablage und Größenlimits

Beschluss D13 (bestätigt am 08.11.2026 durch „ja“):
- Bilder liegen im jeweiligen Buch-Repository; für v1.0 kein zusätzlicher Speicherdienst und kein Git LFS.
- Unterstützte Uploadformate: PNG und JPEG. Höchstens 20 MB pro Datei.
- Buchfassungen haben standardmäßig eine längste Kante von höchstens 3.000 Pixeln. Unzureichende Druckauflösung wird gemeldet.
- Originale bleiben unverändert erhalten. Verkleinerte Fassungen werden separat gespeichert; Verkleinerung nur nach vorheriger ausdrücklicher Bestätigung.
- Ab 500 MB Bildbestand je Buch erfolgt eine Warnung; weiteres Hochladen verlangt eine ausdrückliche Bestätigung. Dies ist eine Warnschwelle, keine pauschale Lösch- oder Verkleinerungsfreigabe.
- Herkunft, Bildunterschrift, Alternativtext und Freigabestatus werden zum Bild gespeichert.
- Die Grenzen sind Produktvorgaben, keine Behauptung technischer GitHub-Grenzen.

## D. Bilder, Import und externe Bearbeitung

## D14 – Referenzbilder ohne Anbieteranbindung

Beschluss D14 (bestätigt am 08.11.2026 durch „ja“):
- Referenzbilder können Figuren, Orten, Szenen oder Abschnitten zugeordnet werden.
- Hochladen allein aktiviert keine Verwendung als Referenz.
- Verwendung als Referenz erfordert eine ausdrückliche Freigabe und eine ausdrückliche Auswahl für jeden Bildauftrag.
- Bis einschließlich v1.0 keine automatische Übergabe an KI-Anbieter-APIs gemäß der bestehenden Versionsentscheidung.
- Die weiteren Empfehlungen dieses Abschnitts sind durch die verkürzte Auswahlfrage nicht zusätzlich als Einzelentscheidungen bestätigt.

## D15 – Externe Bildrecherche und Rechteangaben

Beschluss D15 (bestätigt am 08.11.2026 durch „ja“):
- Externe Bildrecherche gehört zum Umfang von v1.0.
- Bilder werden über die vorhandenen Chat-Werkzeuge recherchiert; eigene Bilder und Links können eingereicht werden. Keine neue Anbieter-API-Anbindung gemäß der bestehenden Versionsentscheidung.
- Quelle, Urheber und Lizenzangaben werden dokumentiert.
- Ungeklärte Rechte werden sichtbar als ungeklärt gekennzeichnet; keine automatische Behauptung einer geklärten Nutzungserlaubnis.
- Einfügen ins Buch nur nach ausdrücklicher Bestätigung; die bestehenden Bild- und Veröffentlichungsfreigaben bleiben wirksam.
- Weitergehende Empfehlungen des Abschnitts sind durch die verkürzte Auswahlfrage nicht zusätzlich als Einzelentscheidungen bestätigt.

## D16 – Import und Analyseumfang

Beschluss D16 (bestätigt am 08.11.2026 durch „ja“):
- v1.0 umfasst Manuskriptimport sowie Analysen zu Figuren, Zusammenfassungen und Zielen, Stil, Orten, Zeitleiste, Kontinuität, Sprache, Sachbuch-Prüfstellen, Bildideen, Klappentext, Buchtyp/Zielgruppe und Serienabgleich.
- KI-Analysen erfolgen im Chat oder über „Auftrag kopieren“; keine KI-Anbieter-API-Anbindung als Voraussetzung.
- Ergebnisse bleiben prüfbare Vorschläge und werden nicht automatisch in Buchtext oder Freigaben übernommen.
- Glossar bleibt nach v1.0.
- Ein maximaler Umfang je Analyseauftrag wurde noch nicht festgelegt; die verkürzte Auswahlfrage enthielt hierfür keinen Zahlenwert.

## D17 – Externe DOCX-Arbeitskopie (#209)

Beschluss D17 (bestätigt am 08.11.2026 durch „für version 1.1 vorsehen und übernehmen“):
- Externe DOCX-Bearbeitung mit kontrollierter Rückführung (#209) ist für Version 1.1 vorgesehen und keine v1.0-Abnahmevoraussetzung.
- Der geplante Umfang umfasst Bearbeitung in Word oder LibreOffice, Buchsperre/Checkout, Änderungsvergleich und ausdrücklich bestätigte Übernahme gemäß den bestehenden Anforderungen in #209.
- Konkrete Programmversionen und die detaillierte Format-Abnahmematrix werden für die Umsetzung von v1.1 festgelegt; sie blockieren v1.0 nicht.

Ergänzung vom 08.11.2026, ausdrücklich durch „nehmen wir dazu“ bestätigt:
- Die ausgegebene DOCX-Arbeitskopie erhält eigene Dokumenteigenschaften zur Rückzuordnung: Buchkennung, Export-/Checkout-Kennung, Ausgangscommit, Hash des Ausgangsmanuskripts und Version des Metadatenformats. Die genaue Feldstruktur wird bei der Umsetzung festgelegt.
- Der Hash ist ein Fingerabdruck und enthält nicht den Ausgangstext. Die zugehörige Ausgangsfassung bleibt im Repository erhalten. Der Hash bezieht sich auf eine festgelegte Manuskriptfassung, nicht auf die sich beim Speichern verändernden Bytes der gesamten DOCX-Datei. Hashverfahren und Normalisierung nachvollziehbar definieren.
- Beständige Kapitel- und Abschnittskennungen im Dokument ergänzen die Dokumenteigenschaften für die Zuordnung einzelner Änderungen. Die genaue technische Ablage ist noch zu bestimmen und auf Erhalt beim Bearbeiten zu prüfen.
- Dokumenteigenschaften sind veränderbare Zuordnungshilfen, kein alleiniger Echtheitsnachweis, keine Schreibberechtigung und keine Freigabe. Kennungen und Ausgangsstand beim Rückimport mit dem gespeicherten Checkout abgleichen.
- Rückführung weiterhin durch Vergleich von Ausgangsfassung, bearbeiteter DOCX-Datei und aktuellem Buchstand, anschließend Vorschau und ausdrückliche Übernahmebestätigung. Die bestehenden Checkout-, Sperr- und Freigaberegeln bleiben wirksam.
- Erhalt und Lesbarkeit der Eigenschaften und internen Kennungen nach Bearbeitung in Word und LibreOffice sowie nach „Speichern unter“ und relevanten Konvertierungen prüfen. Fehlende, beschädigte oder widersprüchliche Angaben verständlich melden; keine ungeprüfte Rückschreibung oder automatische Entsperrung.
- Diese Ergänzung gehört zu v1.1. Sie ist eine bestätigte Anforderung, noch keine implementierte Funktion.

## E. Standabgleich, Sicherung und Datenlebenszyklus

## D18 – Konfliktverhalten

Beschluss D18 (bestätigt am 08.11.2026 durch „ja“):
- Vor dem Speichern wird der aktuelle Stand geprüft.
- Zwischenzeitliche Änderungen werden erhalten; Konflikte werden sichtbar angezeigt und geklärt.
- Nichts wird still überschrieben oder verworfen. Benutzereingaben bleiben erhalten.
- Bestehende Schutz- und Freigaberegeln bleiben wirksam.

## D19 – Offline-Umfang und Geräte

Beschluss D19: Offline-Web-App nach v1.0 gemäß D06/D01. Vorhandene lokale Arbeitskopien und Dateiverarbeitung bleiben davon unberührt.

## D20 – Sicherung von Gesprächen und Entwürfen

Beschluss D20 (bestätigt am 08.11.2026 durch „ja“):
- Für v1.0 werden die vorhandenen manuellen Sitzungssicherungsbefehle und automatischen Sicherungen nach abgeschlossenen Abschnittsdialogen verwendet.
- Zusätzliche Hintergrundsicherung oder Sicherung noch nicht abgesendeter Eingabeentwürfe ist keine v1.0-Voraussetzung.
- Umfang und bekannte Lücken jeder Sicherung werden sichtbar angegeben.
- Bestehende Regeln für Ablage, Vertraulichkeit, bestätigte Speicherung und getrennte Übernahme der Sitzung bleiben wirksam. Die Sicherung erteilt keine Buchfreigabe.

## D21 – Aufbewahrung, Löschen und Wiederherstellung

Beschluss D21 (bestätigt am 08.11.2026 durch „ja“):
- Gesprächssicherungen und Originaldateien bleiben erhalten, bis der Auftraggeber ihre Löschung ausdrücklich beauftragt.
- Keine automatische Löschung dieser Inhalte und keine automatische Umschreibung der Git-Historie.
- Vor einer Löschung wird darauf hingewiesen, dass frühere Git-Versionen die Inhalte weiterhin enthalten können.
- Die Wiederherstellung wird mit Testdaten geprüft.
- Bereits vorhandene automatische Aufbewahrungs-/Löschpfade für Originaldateien müssen vor der v1.0-Abnahme auf diesen Beschluss abgestimmt werden; der Beschluss allein ändert deren Implementierung nicht.
- Für davon nicht erfasste Betriebslogs, Auditdaten oder Datenbanksicherungen werden keine Fristen unterstellt; eigene gehostete Dienste sind nach D06 ohnehin nach v1.0 verschoben.

## D22 – Datenmigration und Altprojekte

Beschluss D22 (bestätigt und eingegrenzt am 08.11.2026):
- Nach Angabe des Auftraggebers gibt es derzeit außer YAWA keine Benutzerbestände. Die reale Datenübernahme und deren Abnahme beziehen sich daher für v1.0 auf YAWA als bestehende Testinstanz/Testrepository; kein weiterer Clienttyp neben D05.
- Bestehende Einzelbücher und Bibliotheken bleiben grundsätzlich unterstützt. Nötige Umstellungen sind versioniert und ohne stillen Inhaltsverlust auszuführen.
- Bei inkompatiblen Daten wird Speichern gesperrt und der nächste sichere Schritt angezeigt.
- Die zuvor vorgeschlagenen Kompatibilitätstests mit einem v0.5-Projekt und einer v0.6-Bibliothek können mit Testdaten/Fixtures erfolgen. Es wird keine Migration weiterer realer Benutzerbestände als Voraussetzung verlangt.
- Den tatsächlich vorhandenen YAWA-Ausgangsstand vor jeder Umstellung prüfen und sichern; keine frühere Version oder Datenlage unterstellen. Dieser Planungsbeschluss allein autorisiert keine produktive Datenänderung, Löschung oder Buchfreigabe in YAWA.
- Eine allgemeine Übernahme aus beliebigen historischen oder fremden Beständen ist keine zusätzliche v1.0-Pflicht.

## F. Bedienung, Grenzen und Nachweise

## D23 – Sprachen und Barrierefreiheit

Beschluss D23 (bestätigt am 08.11.2026 durch „ja“):
- Deutsch und Englisch werden vollständig als Bediensprachen unterstützt.
- Die Buchsprache bleibt von der Bediensprache unabhängig.
- Verständliche Beschriftungen und Textalternativen werden in allen vier festgelegten Umgebungen geprüft: ChatGPT, Codex, Claude und Open WebUI.
- Nur tatsächlich unterstützte Darstellungsmöglichkeiten verwenden; fehlende Tests offen ausweisen gemäß D05.
- Ein formaler Barrierefreiheitsstandard oder eine Konformitätszusage wurde durch diese Auswahl nicht festgelegt.

## D24 – Prompt-Tuning (#204)

Beschluss D24 (bestätigt am 08.11.2026 durch „ja“):
- Für v1.0 wird der vorhandene Prompt-Profiler abgenommen.
- Anweisungen werden nachvollziehbar geordnet, mit erkennbarer Herkunft und Geltung.
- Automatische Prompt-Kürzung und Prompt-Compiler werden auf nach v1.0 verschoben; keine spätere Versionsnummer festgelegt.
- Maßgebliche Regeln bleiben unverändert; die Ordnung und Analyse erteilen keine Freigabe zu deren stiller Kürzung oder Entfernung.
- Bestehender Ausschluss neuer KI-Anbieter-API-Verbindungen bis einschließlich v1.0 bleibt wirksam.

## D25 – Kosten- und Nutzungsanzeige

Beschluss D25 (bestätigt am 08.11.2026 durch „ok“):
- Für Chat-Abos werden keine fiktiven API-Kosten verbucht.
- Vorhandene Kostenaufzeichnungen bleiben erhalten und werden klar als tatsächlich, geschätzt, manuell erfasst oder nicht verfügbar gekennzeichnet, soweit zutreffend.
- Verfügbare GitHub-Nutzungsgrenzen werden angezeigt; unbekannte Werte bleiben ausdrücklich unbekannt und werden nicht als null ausgegeben.
- KI-Anbieter-Kontingente und deren Abfrage gehören bis einschließlich v1.0 nicht zum Lieferumfang.
- Zusätzliche harte Betriebsgrenzen oder Zuständigkeiten wurden durch diese verkürzte Auswahlfrage nicht festgelegt; bestehende Schutzregeln bleiben wirksam.

## D26 – Betrieb, Ausfälle und Wartung

Beschluss D26 (bestätigt am 08.11.2026 durch „ja“):
- Für v1.0 ist kein eigener Serverbetrieb vorgesehen, entsprechend der Verschiebung des eigenen Verwaltungsdienstes in D06.
- Fehler werden über GitHub dokumentiert.
- Wiederherstellung wird mit Testdaten geprüft; Wartungsänderungen werden regulär getestet.
- Keine zusätzliche Überwachung und keine zusätzlichen Benachrichtigungsdienste einrichten. Vorhandene GitHub-Funktionen werden dadurch nicht als abgeschafft beschlossen.
- Eigene Server-Verfügbarkeitsziele und Wiederanlaufzeiten sind für v1.0 nicht erforderlich.

## D27 – Datenschutz und Protokollierung

Beschluss D27 (bestätigt am 08.11.2026 durch „ja“):
- Technische Fehlerprotokolle enthalten keine Secrets, Buchtexte oder Gesprächsvolltexte.
- Keine zusätzliche Telemetrie einrichten.
- Gesprächssicherungen sind von technischen Fehlerprotokollen getrennt und folgen den bestätigten Speicher-, Vertraulichkeits- und Aufbewahrungsregeln.
- Fehlerberichte enthalten ausschließlich nötige technische Angaben; vertrauliche Inhalte nicht als technische Diagnosedaten veröffentlichen.
- Eine rechtliche Konformitätszusage oder zusätzliche Verarbeitung personenbezogener Daten wird dadurch nicht beschlossen.

## G. Selbstständige Umsetzung, Prüfung und Abschluss

## D28 – Delegation technischer Einzelentscheidungen

Beschluss D28 (bestätigt am 08.11.2026 durch „ja“):
- Innerhalb eines beschlossenen Auftrags darf der Entwicklungsassistent die technische Umsetzung selbstständig wählen, unter Einhaltung des vereinbarten Umfangs und der Schutzregeln.
- Neue oder geänderte Abläufe und Funktionen von GhostWriter werden als Feature-Requests erfasst und mit den bestätigten Entscheidungen abgeglichen. Fehlerhaftes bestehendes Verhalten wird als Fehlerbericht behandelt. Vorhandene passende Aufgaben zuerst prüfen; keine Doppelaufträge anlegen.
- Bereits ausdrücklich beschlossene Änderungen dürfen ohne erneute Grundsatzfrage umgesetzt werden, soweit der Entwicklungsauftrag und die übrigen Befugnisse dies decken.
- Darüber hinausgehende Änderungen am fachlichen Umfang oder Verhalten brauchen vorherige Zustimmung des Auftraggebers. Das Dokumentieren eines Feature-Requests allein genehmigt nicht dessen Umsetzung.
- Buchtexte und Bilder unterliegen den gesonderten Bucharbeits- und Freigaberegeln; dieser Beschluss erteilt dafür keine Freigabe.
- Neue kostenpflichtige Dienste oder zusätzliche Plattformbindungen sind durch diese Delegation nicht pauschal autorisiert.

## D29 – Freigabe für Entwicklungsarbeit und Testaktionen

Beschluss D29 (bestätigt am 08.11.2026 durch „ja“):
- Beschlossene Aufgaben dürfen in GhostWriter und ghostwriter-ui selbstständig implementiert, getestet und als Änderungspakete vorbereitet werden.
- Testdaten und isolierte Testbranches sind dafür erlaubt.
- Vorhandene fremde Änderungen bleiben erhalten und werden nicht ungeprüft in eigene Änderungspakete aufgenommen.
- Änderungen an bestehenden YAWA-Buchdaten benötigen eine gesonderte Freigabe.
- Dieser Beschluss allein erlaubt keine Übernahme in main oder Veröffentlichung; diese Befugnisse werden in D30 getrennt festgelegt. Bestehende Buchfreigaben und D28 bleiben wirksam.

## D30 – Übernahme und Veröffentlichung

Beschluss D30.1 (bestätigt am 08.11.2026 durch „ja“):
Beschlossene Aufgaben dürfen nach erfolgreichen Pflichtprüfungen selbstständig in main übernommen werden. Die Vorabfreigabe gilt innerhalb des bestätigten Umfangs für GhostWriter und ghostwriter-ui gemäß D28/D29. Keine Umgehung fehlgeschlagener Prüfungen, Schutzregeln oder ungeklärter Konflikte. Buchfreigaben und Änderungen an bestehenden YAWA-Buchdaten bleiben gesondert freigabepflichtig.

Beschluss D30.2 (bestätigt am 08.11.2026 durch „ja“):
Bereitstellung nur in Testumgebungen. Bestehende offizielle Update-Abläufe bleiben unverändert. Keine zusätzliche produktive Bereitstellung oder Änderung von Update-Abläufen allein aufgrund dieser Vorabfreigabe.

Beschluss D30.3 (bestätigt am 08.11.2026 durch „ja“):
Die endgültige Veröffentlichung der Produktversion v1.0 erfordert eine eigene abschließende Bestätigung des Auftraggebers. Die selbstständige Übernahme von Entwicklungsänderungen ersetzt diese Bestätigung nicht.

## D31 – Verbindliche Abnahme und Fertigdefinition

Beschluss D31 (bestätigt am 08.11.2026 durch „ja“):
- Eine Aufgabe wird mit passenden automatisierten Tests, Schema-, Workflow- und Dokumentationsprüfungen sowie praktischen Tests der betroffenen Abläufe geprüft.
- Änderungen an Anzeigen müssen gemäß D05 in ChatGPT, Codex, Claude und Open WebUI geprüft werden; nur tatsächlich unterstützte Darstellungen verwenden.
- Fehlende oder nicht ausführbare Tests bleiben ausdrücklich offen und dürfen nicht als bestanden gelten. Ein erfolgreicher Test in einer Umgebung ersetzt keinen Test in einer anderen.
- Die Freigabe zur selbstständigen Übernahme in D30 gilt erst bei erfolgreichen erforderlichen Prüfungen. Nicht geprüfte Pflichtfälle rechtfertigen keine Fertigmeldung.
- Eine pauschale Toleranz für Restmängel oder ein Ersatz nicht durchführbarer praktischer Pflichtprüfungen durch Unit-Tests wurde nicht beschlossen.

## D32 – Eskalation bei neuen Erkenntnissen

Beschluss D32 (bestätigt am 08.11.2026 durch „ja“):
- Technische Probleme innerhalb des beschlossenen Auftrags werden selbstständig gelöst, unter Einhaltung der bestätigten Vorgaben und Schutzregeln.
- Bei neuen Funktionen, Kosten, fehlenden Rechten, widersprüchlichen Vorgaben oder Verlustgefahr wird der betroffene Teil gestoppt und der Auftraggeber gezielt gefragt.
- Unabhängige autorisierte Aufgaben werden währenddessen weiterbearbeitet.
- Keine stillschweigende Erweiterung des Funktionsumfangs, Umgehung von Berechtigungen oder Aufgabe von Schutzregeln.

## Anwendung und Entwicklungsbefugnisse

Die Umsetzung richtet sich nach [den Arbeitsaufträgen](AUFTRAEGE-v1.0.md). Technische Details innerhalb beschlossener Aufgaben dürfen selbstständig entschieden werden. Neue fachliche Abläufe außerhalb dieser Beschlüsse sind Feature-Requests und brauchen Zustimmung; Fehler bestehenden Verhaltens sind Fehlerberichte. Vorher passende Issues suchen. Geprüfte Änderungen dürfen nach D30 selbstständig übernommen werden; fehlende Pflichtprüfungen verhindern eine Fertigmeldung und Übernahme. Keine Buchfreigabe aus einer Entwicklungsfreigabe ableiten.

Dieses Protokoll erteilt keine pauschale Autorisierung zum Löschen alter Originale, Zugriff auf Geheimnisse, echten Anbieteraufrufen oder Verändern bestehender YAWA-Inhalte. Die technische Branch-Trennung bleibt in der normalen Bedienung intern; relevante Speicher-/Übernahme-/Fehlerzustände bleiben sichtbar.

## Ergänzungen aus dem Planungs- und Mediengespräch vom 08.11.2026

- **Medien:** Eine Szene entspricht einem Abschnitt; höchstens ein Medium pro Abschnitt. GhostWriter ist für textorientierte Bücher gedacht, nicht für Bildbände/Fotobücher. Sechs Positionen (oben/unten × links/mittig/rechts) mit Textumfluss im Abschnitt und ein prozentualer Breitenregler sind bestätigt. Ein Bild vor/nach einem Textabschnitt kann einen eigenen Medienabschnitt erhalten. Anforderungen, keine Implementierungszusage: [Medienplatzierung](MEDIENPLATZIERUNG.md).
- **Umschlag:** Für v1.0 vorgemerkt: hochgeladene Gestaltung analysieren und kontrolliert in buchbezogene Umschlageinstellungen umwandeln. Fertiges Coverbild und bearbeitbaren Nachbau unterscheiden; Vorschau und ausdrückliche Bestätigung bleiben nötig. Ausführlicher Umfang im [Entscheidungsauftrag](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/ENTSCHEIDUNGSAUFTRAG-v1.0.md#nachtrag-für-v10-umschlag-aus-hochgeladener-gestaltungsvorlage).
- **Bedienglossar:** Eigener Auftrag erteilt; kein Buchglossar. [Umsetzungsauftrag](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/UMSETZUNGSAUFTRAG-BEDIENGLOSSAR.md).
- **Dokumentationswebsite:** Eine zentrale deutsche/englische Programmwebsite aus docs/, keine Websites je Buchrepository. Zuordnung samt Aufbau und Veröffentlichung zu v0.9.0 bestätigt. Technische Umsetzung am 9. November 2026 als lokal geprüfter PR vorgezogen beauftragt; Merge, Browserabnahme und produktive Bereitstellung bleiben gesondert freizugeben: [Planungsnotiz](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/PLANUNGSNOTIZ-DOKUMENTATIONSWEBSITE.md).
- **Versionsfolge und Overlays:** Die [Zwischenversionen](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/PLAN-v1.0-ZWISCHENVERSIONEN.md) bleiben mit Ausnahme der Websitezuordnung ein Vorschlag. [Buch-Overlays](https://github.com/ploeffler/GhostWriter/blob/7ea6d6d941757214b12ef7cdf5b1146890c22135/PLANUNGSNOTIZ-BUCH-OVERLAYS.md) bleiben eine vorgemerkte Idee ohne Versionszusage.


## Beschluss vom 8. November 2026: Skill-Unterstützung

Vom Benutzer mit „so machen wir das“ bestätigt:

- **v1.0:** Die vorhandene GhostWriter-Skill-Unterstützung prüfen und für Claude und Codex konsistent nutzbar machen. Einstieg, Buchprofil, Schreibablauf und Qualitätsprüfung verwenden dieselben fachlichen Regeln. Clientabhängiges Laden und verfügbare Werkzeuge praktisch prüfen; Unterstützung nicht allein aus dem Dateiformat ableiten.
- **Ab v1.1:** Eigenständige Buch-Skills für Konzeption, Recherche, Schreiben/Überarbeiten, Kontinuität und Ausgabeprüfung schrittweise ausbauen. Einzelumfang und Abnahme je Skill festlegen; keine Zusage, alle Skills bereits mit v1.1 vollständig zu liefern.
- Entwicklungsskills können nach Bedarf lokal eingesetzt werden und sind kein an eine Produktversion gebundenes Liefermerkmal.
- Fachliche Regeln bleiben in einer gemeinsamen Quelle; Skill-Einstiege verweisen darauf. Buchinhalte und individuelle Vorgaben bleiben im Buchprojekt. Normale Buchaufträge sollen ohne Kenntnis von Skill-Namen funktionieren.

Bestätigte Planung, noch keine Umsetzung oder praktische Abnahme. Keine GitHub-Übertragung durch diesen Beschluss beauftragt.


---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
