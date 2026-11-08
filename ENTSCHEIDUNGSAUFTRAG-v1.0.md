# Entscheidungsauftrag: GhostWriter bis v1.0

Stand: 08.11.2026. Status: D01–D32 entschieden oder aufgrund bestätigter Verschiebung für v1.0 nicht anwendbar. Empfehlungen sind nur im Umfang der ausdrücklich protokollierten Beschlüsse bestätigt. Implementierung und Abnahme stehen gesondert aus.

## Ziel

Alle fachlichen, betrieblichen und architektonischen Entscheidungen treffen, die für die vereinbarte Entwicklung bis v1.0 erforderlich sind. Danach darf der ausführende Entwicklungsassistent die Umsetzung planen, implementieren, testen und Änderungspakete vorbereiten, ohne für normale Implementierungsdetails erneut nachzufragen.

Dieser Auftrag beauftragt zunächst die Entscheidungsvorbereitung. Er erteilt noch keine Freigabe für kostenpflichtige Dienste, produktive Bereitstellung oder die Übernahme zukünftiger Änderungspakete. Umfang und spätere Vollmachten werden unten ausdrücklich gewählt.

## So wird der Auftrag bearbeitet

1. Die Entscheidungen D01–D32 der Reihe nach bearbeiten. Bei jeder Nummer eine Auswahl oder einen eigenen eindeutigen Beschluss eintragen. „Empfehlung übernehmen“ ist eine gültige ausdrückliche Antwort; ein leeres Feld ist keine Zustimmung.
2. Bei Freitextfragen die verlangten konkreten Angaben ergänzen. Keine Passwörter, Schlüssel oder Token eintragen; nur Dienstnamen, vorhandene Zugänge und Secret-Namen.
3. Falls Informationen fehlen, darf der Assistent Optionen recherchieren und einen begründeten Vorschlag vorbereiten. Preis-, Rechts- und Anbieterangaben müssen dann aktuell geprüft werden. Eine Empfehlung hier ist keine geprüfte Aussage über ein konkretes kommerzielles Angebot.
4. Nicht gewählte Funktionen ausdrücklich verschieben. „Später“ muss festhalten, ob der Punkt die v1.0-Abnahme blockiert.
5. Nach Abschluss Entscheidungen gegen bestehende Regeln und untereinander prüfen. Widersprüche vor Entwicklungsbeginn auflösen. Anschließend Roadmap, Aufgaben, Verträge und Abnahmekriterien gemeinsam aktualisieren.

Antwortformat: `D01: …`, `D02: …` usw. Bei abhängigen Fragen dürfen Werte entfallen, wenn die Funktion ausdrücklich verschoben wurde; dann `entfällt wegen Dxx` eintragen.

## Einordnung bei der Übertragungsvorbereitung

Dieser Fragen-/Antwortenkatalog bleibt als Gesprächsprotokoll erhalten. Für den aktuellen verbindlichen Stand gelten die [bestätigten Entscheidungen](docs/ENTSCHEIDUNGEN-v1.0.md) und [Arbeitsaufträge](docs/AUFTRAEGE-v1.0.md). Historische Statusangaben zu einzelnen Änderungspaketen unten sind kein aktueller Merge-Nachweis. Die ergänzten Medien-, Umschlag-, Website- und DOCX-Metadatenanforderungen wurden dort ebenfalls aufgenommen.

## Bereits verbindlich oder gesondert vorbereitet

- **Beschlossen und in main:** Bis einschließlich v1.0 keine Verbindungen zu KI-Anbieter-APIs (#214). KI-Arbeit im Chat oder über „Auftrag kopieren“ mit geprüfter Rückgabe. Keine echten Anbieteraufrufe oder Anbieter-Schlüssel als Abnahmevoraussetzung.
- GitHub bleibt die gemeinsame Quelle für gespeicherte Buchdaten; Manuskript, Vorschlag, Speicherung, technische Übernahme und inhaltliche Freigabe bleiben unterscheidbar.
- Struktur-, Schreib-, Abschnitts-, Kapitel- und Auflagenfreigaben behalten ihre bestehenden ausdrücklichen Bestätigungen. Ein Entwicklungsauftrag darf keine Buchfreigabe ersetzen.
- Keine Secrets im Chat, Repository oder Protokoll; kein stilles Überschreiben oder Verwerfen konkurrierender Arbeit.
- **Vorbereitet, noch nicht in main:** Arbeits-Branch je Buch bei Bedarf beibehalten (#169, Änderungspaket #215). D04 entscheidet die verbindliche Grundlage für die folgende Entwicklung.
- Auth0 und eine separate GitHub App sind im bisherigen Zielbild vorgesehen. Hosting, Laufzeit und produktiver Verwaltungsdienst sind noch offen. Diese Ausgangslage ist kein Nachweis bereits eingerichteter Dienste.

## A. Lieferumfang und Reihenfolge

### D01 – Verbindlicher Umfang von v1.0

Für jede Zeile `Pflicht`, `später` oder `bereits fertig, nur abnehmen` wählen. Eine Verschiebung ändert gegebenenfalls die bisherige Roadmap ausdrücklich.

| Bereich | Ausgangslage / Empfehlung |
|---|---|
| Stabiler Chat-Buchworkflow, Bibliothek, Freigaben, Export | Pflicht; bestehende Funktionen vollständig abnehmen (#18/#41/#22) |
| Clientübergreifender Standabgleich und Wiederaufnahme | Pflicht (#179) |
| Sitzungssicherung und Wiederherstellung | Pflicht; vorhandene Teilumsetzung vervollständigen und abnehmen (#179) |
| Eigene Verwaltungs-API, Anmeldung und Repository-Zugriff | Entscheidung nötig: Pflicht, falls die eigene Web-App v1.0-Pflicht bleibt (#19) |
| Installierbare Web-App | Bisher v1.0; beibehalten oder ausdrücklich verschieben (#35) |
| Offline-Buchbearbeitung | Bisher v1.0; bei Beibehaltung erheblicher eigener Lieferblock (#61) |
| Referenzbildverwaltung ohne Anbieteranbindung | Pflicht, wenn vollständiger Bildworkflow v1.0-Ziel bleibt (#143/#54) |
| Import sowie Chat-/Kopierweg für Analysen | Pflichtumfang nach D16 festlegen (#124) |
| Deutsch/Englisch | Pflicht, vorhandene Umsetzung vollständig abnehmen (#74) |
| Datenseite mit tatsächlich verfügbaren Informationen | Pflicht; Abgleichanzeige entsprechend gewähltem Clientumfang (#71) |
| Lokaler Prompt-Profiler | Empfehlung: vorhandenen Kern abnehmen; Compiler nur bei ausdrücklicher Aufnahme (#204) |
| Externe DOCX-Bearbeitung mit Checkout und Rückführung | Versionszuordnung offen; Empfehlung: eigener späterer Lieferblock (#209) |
| Externe Bildrecherche | Noch kein eigener abgegrenzter Auftrag; in D15 aufnehmen oder verschieben |
| Vorwort/Nachwort/Glossar und Buchübersetzungen | Bisher v1.5; ohne ausdrückliche Änderung dort belassen |

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

### D02 – Prioritäten und Lieferreihenfolge

Empfehlung: Bestandsabnahme → Standabgleich/Sicherung → gewählte Bild-/Importergänzungen → Verwaltungsdienst → Web-App → Offline-Modus. Architekturvorarbeiten dürfen vorgezogen werden, ohne andere Funktionen als fertig zu erklären.

Beschluss D02 (bestätigt am 08.11.2026 durch „ja“):
- Reihenfolge: bestehende Funktionen abnehmen → Standabgleich und Sicherung → Bilder und Import ergänzen → abschließende v1.0-Abnahme.
- Kein fester Termin.
- Verschobene Web-App-, Verwaltungsdienst- und Anbieter-API-Arbeiten sind kein Teil dieser v1.0-Lieferfolge. Technische Abhängigkeiten innerhalb der bestätigten Aufgaben werden berücksichtigt.

### D03 – Nutzerkreis und Zusammenarbeit

Wählen: nur eigene private Nutzung / mehrere eingeladene Nutzer / öffentlich nutzbares Produkt. Festlegen: mehrere Autoren je Buch ja/nein; Rollen nur Eigentümer oder zusätzlich Bearbeiter/Leser; gleichzeitiges Bearbeiten unterstützen oder Schreibzugriffe nacheinander abarbeiten.

Empfehlung: zunächst eingeladene Nutzer, keine öffentliche Registrierung; Eigentümer und berechtigte Bearbeiter anhand geprüfter Repository-Rechte; konkurrierende Schreibvorgänge nacheinander und mit Versionsprüfung.

Beschluss D03 (bestätigt am 08.11.2026 durch „übernehmen“):
- Nutzerkreis: Auftraggeber und ausdrücklich eingeladene Nutzer; keine öffentliche Registrierung.
- Rollen: Eigentümer, Bearbeiter und Leser. Tatsächliche GitHub-Rechte begrenzen den Zugriff; die Anwendung erweitert diese Rechte nicht.
- Zusammenarbeit: Mehrere Bearbeiter je Buch sind erlaubt.
- Gleichzeitiges Speichern: Schreibvorgänge werden nacheinander verarbeitet und gegen den aktuellen Stand geprüft. Konflikte werden angezeigt; Eingaben bleiben erhalten.
- Inhaltliche Freigaben: Nur der Eigentümer oder ausdrücklich benannte Freigabeberechtigte dürfen Abschnitte, Kapitel und Auflagen freigeben. Bestehende ausdrückliche Freigaben und Schutzregeln bleiben wirksam.

### D04 – Entscheidung #169 verbindlich machen

Empfehlung: #215 nach erfolgreicher Prüfung übernehmen. Ein gemeinsamer Arbeits-Branch je Buch, erst bei Speicherung erzeugen, nach vollständig übernommener unveränderter Spitze entfernen. Bestehende Namen und `changes.auto_merge` erhalten. Keine Migration zu direktem Schreiben.

Beschluss D04 (bestätigt am 08.11.2026 durch „ja - für den benutzer ist diese trennung/unterteilung nicht sichtbar“):
- Je Buch bleibt ein gemeinsamer technischer Arbeits-Branch bestehen; erst bei autorisierter Speicherung anlegen und nach vollständiger Übernahme entfernen.
- Bestehende technische Namen und die Einstellung „sofort übernehmen“ bleiben erhalten.
- Die Trennung zwischen Buch- und Arbeits-Branch ist für Benutzer nicht sichtbar und verlangt keine Branch-Auswahl oder Branch-Verwaltung. Technische Zuordnung wird intern erledigt.
- Fachlich relevante Speicher-, Übernahme-, Fehler- und Freigabezustände bleiben verständlich erkennbar. Ein offener oder fehlgeschlagener Vorgang darf nicht als bereits übernommen oder freigegeben erscheinen.
- Technische Details können bei ausdrücklich angeforderter Diagnose erklärt werden; sie sind kein Bestandteil des normalen Bucharbeitsablaufs.
- Die Umsetzung und Dokumentation zu #169/#215 sind auf diese Bedienvorgabe abzustimmen. Dieser Beschluss erklärt bestehende Anzeigen nicht ungeprüft für konform.

## B. Oberfläche und KI-Arbeitsweise ohne Anbieter-API

### D05 – Verbindlich unterstützte Clients

Namentlich auswählen: Open WebUI, Claude-Chat, ChatGPT-Chat, Codex, eigene Web-App, weitere. Je Client festlegen: verbindliche Unterstützung und Abnahme oder nur dokumentierter Rückfallweg. Nicht jede Umgebung besitzt dieselben Werkzeuge.

Empfehlung: eine primäre Umgebung mit echtem Schreibtest; andere mit klarer Fähigkeitsprüfung und Text-/Dateirückfallweg. Native Chat-Ausgaben nur, soweit tatsächlich unterstützt.

Beschluss D05 (bestätigt am 08.11.2026):
- Verbindlich unterstützt werden genau die drei Clientgruppen GPT, Claude und Open WebUI.
- GPT umfasst ausdrücklich sowohl ChatGPT als auch Codex. Die konkrete Abnahmematrix hat deshalb vier Umgebungen: ChatGPT, Codex, Claude und Open WebUI.
- Jede Änderung an „pseudo grafischen“ bzw. grafisch aufbereiteten Anzeigen muss in allen vier Umgebungen geprüft werden. Das betrifft insbesondere Übersichten, Karten, Tabellen, Formulare, Menüs, Statusanzeigen und zugehörige Text-/Darstellungsrückfälle.
- Je Umgebung nur tatsächlich unterstützte Darstellung verwenden: für ChatGPT/Codex unterstützte native Chat-Ausgaben bzw. Text/Markdown, für Claude die dort unterstützten GhostWriter-Vorlagen, für Open WebUI dessen unterstützten Darstellungsweg. Keine fremden Widgets oder Bedienfunktionen als unterstützt voraussetzen.
- Die Prüfung umfasst Darstellung, Verständlichkeit, verfügbare Aktionen und deren unveränderte fachliche Bedeutung. Fehlende Testmöglichkeiten ausdrücklich als offen ausweisen; ein Test in einer Umgebung ersetzt keinen Test in einer anderen. Eine ungeprüfte Umgebung darf nicht als bestanden gemeldet werden.
- Weitere Clients erhalten bis v1.0 keine eigene Integrations- oder Supportzusage.
- Kein einzelner primärer Client wird durch diesen Beschluss festgelegt; die vier Umgebungen sind für Änderungen an diesen Anzeigen gleichwertige Pflichtprüfungen.

### D06 – Eigene Web-App ohne integrierten Modellaufruf

Wenn D01 die Web-App enthält: Soll sie Buchverwaltung, Editor, Freigaben und Exporte vollständig ermöglichen und für KI-Arbeit kopierbare Aufträge/Dateien ausgeben? Oder nur Übersichten und Übergabe an den Chat?

Empfehlung: vollständige fachliche Verwaltung; KI-Auftrag mit Rückgabeimport, kein eingebauter KI-Chat und keine neuen Anbieteradapter.

Beschluss D06 (bestätigt am 08.11.2026 durch „verschieben, weil api“):
- Eigene Web-App (#35) und eigener GhostWriter-Verwaltungsdienst (#19) werden auf nach v1.0 verschoben; keine spätere Versionsnummer festgelegt.
- Bis einschließlich v1.0 Arbeit ausschließlich über die in D05 festgelegten Clients und deren vorhandene GitHub-Anbindung bzw. dokumentierte Datei-/Kopierwege.
- Die vorhandene GitHub-Anbindung der Clients bleibt zulässig. Keine neue eigene Verwaltungs-API oder KI-Anbieter-API als Voraussetzung für v1.0.
- Web-App-abhängige Offline-Buchbearbeitung im Browser (#61) ist damit ebenfalls nach v1.0 verschoben. Dies verwirft weder bestehende lokale Arbeitskopien noch verfügbare Dateiverarbeitung.
- D01 muss den Lieferumfang entsprechend korrigieren. D09–D13 und D25–D27 sind nur hinsichtlich tatsächlich verbleibender Funktionen zu bearbeiten; verschobene Hosting-/Dienstfragen blockieren die v1.0-Entwicklung nicht.

### D07 – Übergabe und Rückgabe von KI-Ergebnissen

Festlegen: Zwischenablage, herunterladbare Auftragsdatei oder beides; erlaubte Rückgaben als Text/Datei; Behandlung fehlender Quellen und fehlerhafter Formate; Übernahmevorschau.

Empfehlung: Text und Datei anbieten; Auftrag enthält Aufgabe, IDs, Ausgangscommit und benötigte Auszüge. Rückgaben sind unvertrauenswürdige Vorschläge; Format, Quellen und Basis prüfen, Änderungen zeigen, keine automatische Manuskript- oder Freigabeänderung.

Beschluss D07 (bestätigt am 08.11.2026 durch „ja“):
- KI-Aufträge werden als kopierbarer Text oder als Datei bereitgestellt.
- Der Auftrag enthält die Aufgabe, die benötigten Buchauszüge und den zugrunde liegenden Buchstand.
- Ergebnisse können als Text oder Datei zurückgegeben werden.
- Vor dem Speichern werden Format, Quellen und zwischenzeitliche Änderungen am Buchstand geprüft. Nicht prüfbare Angaben werden ausdrücklich als solche gekennzeichnet.
- Vorgeschlagene Änderungen werden zur Sichtung gezeigt; bestehende Speicher- und Freigaberegeln bleiben wirksam. Die Rückgabe allein speichert oder genehmigt nichts.
- Der Wechsel zwischen den unterstützten Clients erfordert keine eigene KI-Anbieter-API.

### D08 – Bestehender optionaler Anbieter-Code

Wählen: erhalten, aber deutlich als nicht zum v1.0-Lieferumfang gehörend markieren / zusätzlich in der Oberfläche ausblenden / entfernen als gesonderte Migration.

Empfehlung: erhalten und kennzeichnen; in v1.0 keine Schlüssel-Einrichtung als notwendigen Schritt anbieten. Keine kostenpflichtigen Live-Tests. Historische Aufzeichnungen erhalten.

Beschluss D08 (bestätigt am 08.11.2026 durch „ja“):
- Bestehender optionaler KI-Anbieter-API-Code bleibt erhalten und wird klar als außerhalb des v1.0-Lieferumfangs gekennzeichnet.
- Die Nutzung und Abnahme von v1.0 setzt keine Einrichtung von KI-Anbieter-Schlüsseln voraus.
- Für v1.0 werden keine kostenpflichtigen Live-Tests gegen KI-Anbieter-APIs verlangt oder durch diesen Beschluss autorisiert.
- Historische Kosten-, Nutzungs- und Laufaufzeichnungen bleiben erhalten.
- Keine Entfernung oder Migration des vorhandenen Codes allein aufgrund dieser Planungsentscheidung.

## C. Verwaltungsdienst, Betrieb und Zugänge

D09–D13 und D25–D27 müssen konkret beantwortet werden, wenn ein gehosteter Dienst zu D01 gehört. Wird er verschoben, bleibt die Umsetzung über bestehende Werkzeuge der gewählten Clients maßgeblich.

### D09 – Hosting, Laufzeit und Betriebsbudget

Festlegen: eigener Rechner/Server oder gehosteter Dienst; vorhandener Anbieter oder ausdrücklich delegierte Auswahl; Betriebsregion; monatliche Kostenobergrenze; wer Verträge abschließt und Rechnungen trägt. Cloudflare ist nicht als automatische Vorgabe zulässig.

Empfehlung: Dienst containerisierbar und anbieterunabhängig halten. Auswahl eines konkreten Hosts erst nach Prüfung von Kosten, persistentem Speicher, Backups und Betrieb. Bei Delegation Musskriterien und Kostenobergrenze verbindlich angeben.

Beschluss D09: Entfällt für v1.0 aufgrund D06 und abschließend D01; eigener Hosting-/Verwaltungsdienst nach v1.0.

### D10 – Anmeldeverfahren und GitHub-Verknüpfung

Wählen: bestehendes Zielbild Auth0 + separate GitHub App beibehalten / bewusst durch anderes Verfahren ersetzen. Festlegen: Nutzer dürfen nur ausdrücklich freigegebene Repositories verbinden; benötigte Rollen; Verhalten bei Rechteentzug.

Empfehlung: bestehendes Zielbild beibehalten, serverseitig jede Operation autorisieren; nur erforderliche Repository-Rechte. App-Registrierung und Secret-Hinterlegung erfolgen über sichere Verwaltungswege.

Beschluss D10: Eigene Dienstanmeldung/GitHub-App nach v1.0 gemäß D06/D01. Vorhandene GitHub-Anbindungen der gewählten Clients bleiben bestehen; Rechte nach D03.

### D11 – Domain, Umgebungen und Bereitstellung

Festlegen: Produktions- und Testadresse oder ausdrücklich delegierte Auswahl; vorhandene Domain; mindestens getrennte Test-/Produktivkonfiguration; Zugang zur Testumgebung; wer DNS und Anmeldungs-Callbacks einrichtet. Bei offenem Produktionszugang darf zunächst eine lokale und eine Testbereitstellung als Lieferziel gewählt werden.

Beschluss D11: Eigene Dienst-/Web-App-Domains und Bereitstellungsumgebungen nach v1.0 gemäß D06/D01. Entwicklungs- und Testbefugnisse nach D29/D30 bleiben wirksam.

### D12 – Zusätzliche Persistenz

GitHub bleibt Buchspeicher. Zusätzlich entscheiden: Wo liegen Benutzer-/Installationszuordnungen, Idempotenzdaten und koordinierte Schreibsperren? Datenbanktyp und Betriebsform selbst wählen oder innerhalb D09 delegieren. Keine privaten Schlüssel im Buchrepository.

Empfehlung: kleine transaktionale Verwaltungsdatenbank mit Migrationen; keine zweite maßgebliche Manuskriptkopie. Technologieauswahl durch Entwickler innerhalb der Hosting- und Backupvorgaben erlauben.

Beschluss D12: Zusätzliche Verwaltungsdatenbank nach v1.0 gemäß D06/D01; keine neue Pflichtpersistenz für einen eigenen Dienst bis v1.0.

### D13 – Medienablage und Größenlimits

Wählen: Bilder/Referenzen zunächst im Buchrepository / Git LFS / zusätzlicher Objektspeicher. Festlegen: Formate, maximale Dateigröße, Pixelgrenze, Gesamtbudget je Buch sowie Umgang mit Originalen und Konvertierungen.

Empfehlung: vorhandene Repository-Ablage bis zu ausdrücklich gewählten Grenzen; keine automatische externe Speicherung. Große Dateien vor Upload ablehnen oder nachvollziehbare Verkleinerung anbieten; Originale nicht still überschreiben.

Beschluss D13 (bestätigt am 08.11.2026 durch „ja“):
- Bilder liegen im jeweiligen Buch-Repository; für v1.0 kein zusätzlicher Speicherdienst und kein Git LFS.
- Unterstützte Uploadformate: PNG und JPEG. Höchstens 20 MB pro Datei.
- Buchfassungen haben standardmäßig eine längste Kante von höchstens 3.000 Pixeln. Unzureichende Druckauflösung wird gemeldet.
- Originale bleiben unverändert erhalten. Verkleinerte Fassungen werden separat gespeichert; Verkleinerung nur nach vorheriger ausdrücklicher Bestätigung.
- Ab 500 MB Bildbestand je Buch erfolgt eine Warnung; weiteres Hochladen verlangt eine ausdrückliche Bestätigung. Dies ist eine Warnschwelle, keine pauschale Lösch- oder Verkleinerungsfreigabe.
- Herkunft, Bildunterschrift, Alternativtext und Freigabestatus werden zum Bild gespeichert.
- Die Grenzen sind Produktvorgaben, keine Behauptung technischer GitHub-Grenzen.

## D. Bilder, Import und externe Bearbeitung

### D14 – Referenzbilder ohne Anbieteranbindung

Festlegen: Pflichtzuordnungen (Buch, Figur, Ort, Szene, Kapitel, Abschnitt), erlaubte Rollen, Freigabe-/Rücknahmeregeln, Oberfläche für Mehrfachauswahl und manuellen Export.

Empfehlung: vorhandenes Metadatenmodell weiterverwenden; Upload aktiviert nichts. Nur ausdrücklich freigegebene Referenzen auswählbar, konkrete Version je Auftrag protokollieren. Tatsächliche Nutzung beim externen Dienst nur als bestätigt ausweisen, wenn nachgewiesen oder ausdrücklich vom Benutzer gemeldet. Referenz wird nicht automatisch Buchabbildung.

Beschluss D14 (bestätigt am 08.11.2026 durch „ja“):
- Referenzbilder können Figuren, Orten, Szenen oder Abschnitten zugeordnet werden.
- Hochladen allein aktiviert keine Verwendung als Referenz.
- Verwendung als Referenz erfordert eine ausdrückliche Freigabe und eine ausdrückliche Auswahl für jeden Bildauftrag.
- Bis einschließlich v1.0 keine automatische Übergabe an KI-Anbieter-APIs gemäß der bestehenden Versionsentscheidung.
- Die weiteren Empfehlungen dieses Abschnitts sind durch die verkürzte Auswahlfrage nicht zusätzlich als Einzelentscheidungen bestätigt.

### D15 – Externe Bildrecherche und Rechteangaben

Wählen: v1.0-Pflicht / später. Bei Aufnahme: nur vom Benutzer gelieferte Links/Bilder oder zusätzlich Recherche im verbundenen Chat; erlaubte Quellen; benötigte Felder und Freigabekriterium.

Empfehlung: Recherche durch vorhandene Chat-Werkzeuge; keine neue Suchanbieter-API. Quelle, Urheber, Lizenzhinweis/-link, Abrufdatum und vorgesehene Nutzung speichern; unklare Angaben sichtbar offenlassen. Übernahme und Bildfreigabe ausdrücklich; keine automatische Behauptung geklärter Nutzungsrechte. Rechtliche Zweifelsfälle entscheidet der Rechteverantwortliche.

Beschluss D15 (bestätigt am 08.11.2026 durch „ja“):
- Externe Bildrecherche gehört zum Umfang von v1.0.
- Bilder werden über die vorhandenen Chat-Werkzeuge recherchiert; eigene Bilder und Links können eingereicht werden. Keine neue Anbieter-API-Anbindung gemäß der bestehenden Versionsentscheidung.
- Quelle, Urheber und Lizenzangaben werden dokumentiert.
- Ungeklärte Rechte werden sichtbar als ungeklärt gekennzeichnet; keine automatische Behauptung einer geklärten Nutzungserlaubnis.
- Einfügen ins Buch nur nach ausdrücklicher Bestätigung; die bestehenden Bild- und Veröffentlichungsfreigaben bleiben wirksam.
- Weitergehende Empfehlungen des Abschnitts sind durch die verkürzte Auswahlfrage nicht zusätzlich als Einzelentscheidungen bestätigt.

### D16 – Import und Analyseumfang

Für jede Art Pflicht oder später: Figuren; Kurzbeschreibungen/Ziele; Stilprofil; Orte; Zeitleiste; Kontinuität; sprachliche Hinweise; Sachbuch-Prüfstellen; Bildideen; Klappentext; Buchtyp/Zielgruppe; Serienabgleich; Glossar.

Empfehlung: bestehenden Import ohne KI erhalten; ausgewählte Analysen über D07, unveränderte Fundstellen skriptgestützt prüfen. Glossar wie bisher später. Keine automatische Ganzbuchauswertung versprechen. PDF-Verluste konkret anzeigen.

Beschluss D16 (bestätigt am 08.11.2026 durch „ja“):
- v1.0 umfasst Manuskriptimport sowie Analysen zu Figuren, Zusammenfassungen und Zielen, Stil, Orten, Zeitleiste, Kontinuität, Sprache, Sachbuch-Prüfstellen, Bildideen, Klappentext, Buchtyp/Zielgruppe und Serienabgleich.
- KI-Analysen erfolgen im Chat oder über „Auftrag kopieren“; keine KI-Anbieter-API-Anbindung als Voraussetzung.
- Ergebnisse bleiben prüfbare Vorschläge und werden nicht automatisch in Buchtext oder Freigaben übernommen.
- Glossar bleibt nach v1.0.
- Ein maximaler Umfang je Analyseauftrag wurde noch nicht festgelegt; die verkürzte Auswahlfrage enthielt hierfür keinen Zahlenwert.

### D17 – Externe DOCX-Arbeitskopie (#209)

Wählen: v1.0 / später. Bei Aufnahme bleibt die bestehende Anforderung maßgeblich: expliziter Checkout des ganzen Buchs, clientübergreifende Schreibsperre, Exportbasis, Dreifachvergleich, Vorschau und bestätigter Rückimport; kein Entsperren durch bloßen Upload.

Zusätzlich festlegen: Word/LibreOffice-Versionen für die Abnahme; Unterstützung von Fußnoten, Tabellen, Bildern, Kommentaren, Änderungsverfolgung; unklare Elemente ablehnen oder mit ausdrücklicher Verlustbestätigung importieren. Direktes GitHub-Schreiben kann eine Anwendungssperre umgehen und muss als Konflikt erkannt werden.

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
- Diese Ergänzung gehört zu v1.1. Sie ist eine bestätigte Anforderung, noch keine implementierte Funktion und kein Auftrag zur GitHub-Übertragung.

## E. Standabgleich, Sicherung und Datenlebenszyklus

### D18 – Konfliktverhalten

Empfehlung: vor Schreiben/Freigabe Stand prüfen; Änderungen in anderen Dateien auf aktueller Basis fortsetzen; gleichzeitige Änderungen an derselben Datei zunächst mit erhaltener Eingabe zeigen. Automatische inhaltliche Zusammenführung nur, wenn ausdrücklich als zusätzlicher Umfang beauftragt und geprüft. Kein letzter Schreiber gewinnt, kein Force-Push.

Beschluss D18 (bestätigt am 08.11.2026 durch „ja“):
- Vor dem Speichern wird der aktuelle Stand geprüft.
- Zwischenzeitliche Änderungen werden erhalten; Konflikte werden sichtbar angezeigt und geklärt.
- Nichts wird still überschrieben oder verworfen. Benutzereingaben bleiben erhalten.
- Bestehende Schutz- und Freigaberegeln bleiben wirksam.

### D19 – Offline-Umfang und Geräte

Wenn Offline-Arbeit Pflicht ist: unterstützte Browser/Geräte; Lesen oder auch Bearbeiten, Strukturänderungen und Freigaben; Medien offline vollständig oder nur gezielt; Verhalten bei vollen/gelöschten Browserspeichern.

Empfehlung: lokal gespeicherte Arbeitsstände mit explizitem Abgleichstatus; Freigaben nur für eindeutig zugeordneten lokalen Commit und nach erneuter Prüfung beim Abgleich. Keine Veröffentlichung ohne Verbindung. Browsermatrix und Offline-Medienbudget konkret festlegen.

Beschluss D19: Offline-Web-App nach v1.0 gemäß D06/D01. Vorhandene lokale Arbeitskopien und Dateiverarbeitung bleiben davon unberührt.

### D20 – Sicherung von Gesprächen und Entwürfen

Festlegen: manuelle und bereits implementierte Abschnitts-Checkpoints genügen / zusätzlich automatische Sicherung in der eigenen Oberfläche. Bei Automatik: Intervall und Ereignisse, Sicherung vor Buchanlage, maximale Datenmenge, private Ablage für Programmgespräche ohne Buch.

Empfehlung: übermittelte Beiträge nach bestätigtem Gesprächsschritt sichern; in eigener Oberfläche Eingabeentwürfe lokal laufend sichern. In fremden Clients nur tatsächlich verfügbare Beiträge sichern und Lücken anzeigen. Keine Erfassung verborgener Nachrichten oder unbekannter Anhänge behaupten.

Beschluss D20 (bestätigt am 08.11.2026 durch „ja“):
- Für v1.0 werden die vorhandenen manuellen Sitzungssicherungsbefehle und automatischen Sicherungen nach abgeschlossenen Abschnittsdialogen verwendet.
- Zusätzliche Hintergrundsicherung oder Sicherung noch nicht abgesendeter Eingabeentwürfe ist keine v1.0-Voraussetzung.
- Umfang und bekannte Lücken jeder Sicherung werden sichtbar angegeben.
- Bestehende Regeln für Ablage, Vertraulichkeit, bestätigte Speicherung und getrennte Übernahme der Sitzung bleiben wirksam. Die Sicherung erteilt keine Buchfreigabe.

### D21 – Aufbewahrung, Löschen und Wiederherstellung

Konkrete Fristen wählen für Gesprächssicherungen, Importoriginale, Medienoriginale, Betriebslogs, Auditdaten und Datenbanksicherungen. Festlegen: Löschungen aus aktuellem Stand oder zusätzlich bereinigte Git-Historie; Export vor Löschung; wer Wiederherstellung auslösen darf.

Empfehlung: keine automatische Umschreibung der Git-Historie; Grenzen der Löschung deutlich dokumentieren. Wiederherstellung mit Testdaten abnehmen. Fristen ausdrücklich setzen, nicht vom Entwickler erraten lassen.

Beschluss D21 (bestätigt am 08.11.2026 durch „ja“):
- Gesprächssicherungen und Originaldateien bleiben erhalten, bis der Auftraggeber ihre Löschung ausdrücklich beauftragt.
- Keine automatische Löschung dieser Inhalte und keine automatische Umschreibung der Git-Historie.
- Vor einer Löschung wird darauf hingewiesen, dass frühere Git-Versionen die Inhalte weiterhin enthalten können.
- Die Wiederherstellung wird mit Testdaten geprüft.
- Bereits vorhandene automatische Aufbewahrungs-/Löschpfade für Originaldateien müssen vor der v1.0-Abnahme auf diesen Beschluss abgestimmt werden; der Beschluss allein ändert deren Implementierung nicht.
- Für davon nicht erfasste Betriebslogs, Auditdaten oder Datenbanksicherungen werden keine Fristen unterstellt; eigene gehostete Dienste sind nach D06 ohnehin nach v1.0 verschoben.

### D22 – Datenmigration und Altprojekte

Empfehlung: vorhandene Einzelbücher und Bibliotheken weiter lesbar; strukturelle Migrationen versioniert, idempotent und ohne stillen Inhaltsverlust. Fehlende neue Angaben nicht erfinden. Bei inkompatibler Version Schreibzugriff sperren und sicheren nächsten Schritt zeigen. Mindestens eine definierte Altversion als Abnahmebasis auswählen.

Beschluss D22 (bestätigt und eingegrenzt am 08.11.2026):
- Nach Angabe des Auftraggebers gibt es derzeit außer YAWA keine Benutzerbestände. Die reale Datenübernahme und deren Abnahme beziehen sich daher für v1.0 auf YAWA als bestehende Testinstanz/Testrepository; kein weiterer Clienttyp neben D05.
- Bestehende Einzelbücher und Bibliotheken bleiben grundsätzlich unterstützt. Nötige Umstellungen sind versioniert und ohne stillen Inhaltsverlust auszuführen.
- Bei inkompatiblen Daten wird Speichern gesperrt und der nächste sichere Schritt angezeigt.
- Die zuvor vorgeschlagenen Kompatibilitätstests mit einem v0.5-Projekt und einer v0.6-Bibliothek können mit Testdaten/Fixtures erfolgen. Es wird keine Migration weiterer realer Benutzerbestände als Voraussetzung verlangt.
- Den tatsächlich vorhandenen YAWA-Ausgangsstand vor jeder Umstellung prüfen und sichern; keine frühere Version oder Datenlage unterstellen. Dieser Planungsbeschluss allein autorisiert keine produktive Datenänderung, Löschung oder Buchfreigabe in YAWA.
- Eine allgemeine Übernahme aus beliebigen historischen oder fremden Beständen ist keine zusätzliche v1.0-Pflicht.

## F. Bedienung, Grenzen und Nachweise

### D23 – Sprachen und Barrierefreiheit

Empfehlung: Deutsch und Englisch vollständig; Buchsprache davon getrennt. Tastaturbedienung, verständliche Fehlermeldungen, sinnvolle Beschriftungen und Textalternative als Pflicht. Weitere Sprachen später. Falls formale Barrierefreiheitskonformität verlangt wird, Zielstandard und Prüfumfang ausdrücklich festlegen.

Beschluss D23 (bestätigt am 08.11.2026 durch „ja“):
- Deutsch und Englisch werden vollständig als Bediensprachen unterstützt.
- Die Buchsprache bleibt von der Bediensprache unabhängig.
- Verständliche Beschriftungen und Textalternativen werden in allen vier festgelegten Umgebungen geprüft: ChatGPT, Codex, Claude und Open WebUI.
- Nur tatsächlich unterstützte Darstellungsmöglichkeiten verwenden; fehlende Tests offen ausweisen gemäß D05.
- Ein formaler Barrierefreiheitsstandard oder eine Konformitätszusage wurde durch diese Auswahl nicht festgelegt.

### D24 – Prompt-Tuning (#204)

Wählen: vorhandenen lokalen Profiler abnehmen / zusätzlich Anweisungskatalog / zusätzlich regelbasierten Compiler. Festlegen: darf der Compiler nur Vorschläge zeigen oder die erzeugte Prompt-Fassung automatisch verwenden?

Empfehlung: Profiler und nachvollziehbarer Katalog vor Compiler; Originalregeln erhalten, keine KI-Anbieteradapter bis v1.0. Compiler nur mit Vorher-/Nachhervergleich, Regel-Erhalt und Rückfall auf Original. Keine verborgenen Provider-Kontexte als bekannt darstellen.

Beschluss D24 (bestätigt am 08.11.2026 durch „ja“):
- Für v1.0 wird der vorhandene Prompt-Profiler abgenommen.
- Anweisungen werden nachvollziehbar geordnet, mit erkennbarer Herkunft und Geltung.
- Automatische Prompt-Kürzung und Prompt-Compiler werden auf nach v1.0 verschoben; keine spätere Versionsnummer festgelegt.
- Maßgebliche Regeln bleiben unverändert; die Ordnung und Analyse erteilen keine Freigabe zu deren stiller Kürzung oder Entfernung.
- Bestehender Ausschluss neuer KI-Anbieter-API-Verbindungen bis einschließlich v1.0 bleibt wirksam.

### D25 – Kosten- und Nutzungsanzeige

Empfehlung: Chat-Abos erzeugen keine fiktiven API-Kosteneinträge. Vorhandene historische/manuell dokumentierte API-Kosten erhalten und kennzeichnen; unbekannte Werte nicht null nennen. GitHub-Limits soweit verfügbar anzeigen; KI-Anbieter-Kontingente entfallen bis v1.0. Hostingkosten getrennt vom Buch-KI-Budget führen.

Zusätzlich festlegen: harte Betriebsgrenzen, Verhalten bei GitHub-Limit oder Speicherbudget, Kostenwarnung und Zuständigkeit.

Beschluss D25 (bestätigt am 08.11.2026 durch „ok“):
- Für Chat-Abos werden keine fiktiven API-Kosten verbucht.
- Vorhandene Kostenaufzeichnungen bleiben erhalten und werden klar als tatsächlich, geschätzt, manuell erfasst oder nicht verfügbar gekennzeichnet, soweit zutreffend.
- Verfügbare GitHub-Nutzungsgrenzen werden angezeigt; unbekannte Werte bleiben ausdrücklich unbekannt und werden nicht als null ausgegeben.
- KI-Anbieter-Kontingente und deren Abfrage gehören bis einschließlich v1.0 nicht zum Lieferumfang.
- Zusätzliche harte Betriebsgrenzen oder Zuständigkeiten wurden durch diese verkürzte Auswahlfrage nicht festgelegt; bestehende Schutzregeln bleiben wirksam.

### D26 – Betrieb, Ausfälle und Wartung

Konkrete Vorgaben: verantwortliche Person; Backuphäufigkeit; maximal tolerierter Datenverlust und Wiederherstellungsdauer; Benachrichtigungskanal bei Ausfall; Wartungsfenster; Zuständigkeit für Sicherheitsupdates. Benachrichtigungen erst nach ausdrücklicher Einrichtung versenden.

Empfehlung: für private Erprobung einfache dokumentierte Wiederherstellung und getestete Backups; keine nicht betreibbare Hochverfügbarkeitszusage. Entwickler darf technische Retry-/Timeoutwerte innerhalb dieser Ziele wählen.

Beschluss D26 (bestätigt am 08.11.2026 durch „ja“):
- Für v1.0 ist kein eigener Serverbetrieb vorgesehen, entsprechend der Verschiebung des eigenen Verwaltungsdienstes in D06.
- Fehler werden über GitHub dokumentiert.
- Wiederherstellung wird mit Testdaten geprüft; Wartungsänderungen werden regulär getestet.
- Keine zusätzliche Überwachung und keine zusätzlichen Benachrichtigungsdienste einrichten. Vorhandene GitHub-Funktionen werden dadurch nicht als abgeschafft beschlossen.
- Eigene Server-Verfügbarkeitsziele und Wiederanlaufzeiten sind für v1.0 nicht erforderlich.

### D27 – Datenschutz und Protokollierung

Festlegen: verarbeitete Daten, Verarbeitungsregion, Rollen des Betreibers, benötigte Datenschutz-/Nutzungstexte und verantwortliche Prüfung. Welche Metadaten dürfen Logs enthalten? Telemetrie ja/nein? Fehlerberichte nur manuell oder nach gesonderter Einwilligung?

Empfehlung: keine Manuskript-/Gesprächsvolltexte und keine Secrets in Betriebslogs; Telemetrie standardmäßig aus; Auditmetadaten getrennt mit D21-Fristen. Keine ungeprüfte rechtliche Konformitätszusage.

Beschluss D27 (bestätigt am 08.11.2026 durch „ja“):
- Technische Fehlerprotokolle enthalten keine Secrets, Buchtexte oder Gesprächsvolltexte.
- Keine zusätzliche Telemetrie einrichten.
- Gesprächssicherungen sind von technischen Fehlerprotokollen getrennt und folgen den bestätigten Speicher-, Vertraulichkeits- und Aufbewahrungsregeln.
- Fehlerberichte enthalten ausschließlich nötige technische Angaben; vertrauliche Inhalte nicht als technische Diagnosedaten veröffentlichen.
- Eine rechtliche Konformitätszusage oder zusätzliche Verarbeitung personenbezogener Daten wird dadurch nicht beschlossen.

## G. Selbstständige Umsetzung, Prüfung und Abschluss

### D28 – Delegation technischer Einzelentscheidungen

Empfehlung: Entwickler darf Bibliotheken, interne Struktur, Datenbankschema, Testaufteilung und technische Parameter selbst wählen, sofern D01–D27, bestehende Schutzregeln, ausgewählte Laufzeit und Kostenrahmen eingehalten werden. Entscheidungen kurz protokollieren. Keine neue kostenpflichtige Abhängigkeit, Plattformbindung oder fachliche Funktion ohne gedecktes Mandat.

Beschluss D28 (bestätigt am 08.11.2026 durch „ja“):
- Innerhalb eines beschlossenen Auftrags darf der Entwicklungsassistent die technische Umsetzung selbstständig wählen, unter Einhaltung des vereinbarten Umfangs und der Schutzregeln.
- Neue oder geänderte Abläufe und Funktionen von GhostWriter werden als Feature-Requests erfasst und mit den bestätigten Entscheidungen abgeglichen. Fehlerhaftes bestehendes Verhalten wird als Fehlerbericht behandelt. Vorhandene passende Aufgaben zuerst prüfen; keine Doppelaufträge anlegen.
- Bereits ausdrücklich beschlossene Änderungen dürfen ohne erneute Grundsatzfrage umgesetzt werden, soweit der Entwicklungsauftrag und die übrigen Befugnisse dies decken.
- Darüber hinausgehende Änderungen am fachlichen Umfang oder Verhalten brauchen vorherige Zustimmung des Auftraggebers. Das Dokumentieren eines Feature-Requests allein genehmigt nicht dessen Umsetzung.
- Buchtexte und Bilder unterliegen den gesonderten Bucharbeits- und Freigaberegeln; dieser Beschluss erteilt dafür keine Freigabe.
- Neue kostenpflichtige Dienste oder zusätzliche Plattformbindungen sind durch diese Delegation nicht pauschal autorisiert.

### D29 – Freigabe für Entwicklungsarbeit und Testaktionen

Festlegen: Implementierung, lokale Tests, GitHub-Tests und Änderungspakete sind vorab autorisiert? Auch Änderungen im UI-Repository? Welche Testrepositories und anonymisierten Testdaten dürfen verwendet werden? Dürfen Testbranches/-artefakte dort erzeugt und anschließend entfernt werden?

Empfehlung: alle nötigen Änderungen in GhostWriter und ghostwriter-ui samt Tests und Änderungspaketen autorisieren; vorhandene fremde Änderungen erhalten; nur ausdrücklich benannte Testrepositories. Keine produktiven Buchdaten verändern oder veröffentlichen.

Beschluss D29 (bestätigt am 08.11.2026 durch „ja“):
- Beschlossene Aufgaben dürfen in GhostWriter und ghostwriter-ui selbstständig implementiert, getestet und als Änderungspakete vorbereitet werden.
- Testdaten und isolierte Testbranches sind dafür erlaubt.
- Vorhandene fremde Änderungen bleiben erhalten und werden nicht ungeprüft in eigene Änderungspakete aufgenommen.
- Änderungen an bestehenden YAWA-Buchdaten benötigen eine gesonderte Freigabe.
- Dieser Beschluss allein erlaubt keine Übernahme in main oder Veröffentlichung; diese Befugnisse werden in D30 getrennt festgelegt. Bestehende Buchfreigaben und D28 bleiben wirksam.

### D30 – Übernahme und Veröffentlichung

Drei Vorgänge getrennt entscheiden:

1. **Entwicklungsänderungen in main:** jedes Änderungspaket einzeln bestätigen / nach grünen definierten Prüfungen vorab erlauben.
2. **Bereitstellung:** nur lokal/Test / auch automatisch produktiv innerhalb D09–D11.
3. **Produktrelease v1.0:** eigene abschließende Bestätigung / ausdrücklich vorab anhand D31 autorisieren.

Empfehlung: selbstständig implementieren und testen; Übernahme nach grünen Pflichtprüfungen nur bei ausdrücklich erteilter Vorabvollmacht; Produktrelease gesondert bestätigen. Wer wirklich keinerlei weitere technische Freigabe erteilen möchte, muss erlaubte Übernahmen und Bereitstellungen hier ausdrücklich konkret autorisieren. Buchfreigaben bleiben unabhängig davon beim Autor.

Beschluss D30.1 (bestätigt am 08.11.2026 durch „ja“):
Beschlossene Aufgaben dürfen nach erfolgreichen Pflichtprüfungen selbstständig in main übernommen werden. Die Vorabfreigabe gilt innerhalb des bestätigten Umfangs für GhostWriter und ghostwriter-ui gemäß D28/D29. Keine Umgehung fehlgeschlagener Prüfungen, Schutzregeln oder ungeklärter Konflikte. Buchfreigaben und Änderungen an bestehenden YAWA-Buchdaten bleiben gesondert freigabepflichtig.

Beschluss D30.2 (bestätigt am 08.11.2026 durch „ja“):
Bereitstellung nur in Testumgebungen. Bestehende offizielle Update-Abläufe bleiben unverändert. Keine zusätzliche produktive Bereitstellung oder Änderung von Update-Abläufen allein aufgrund dieser Vorabfreigabe.

Beschluss D30.3 (bestätigt am 08.11.2026 durch „ja“):
Die endgültige Veröffentlichung der Produktversion v1.0 erfordert eine eigene abschließende Bestätigung des Auftraggebers. Die selbstständige Übernahme von Entwicklungsänderungen ersetzt diese Bestätigung nicht.

### D31 – Verbindliche Abnahme und Fertigdefinition

Empfehlung: Pflichtprüfungen umfassen vollständige Unit-Tests, Workflow-/Schema-/Dokumentationsprüfung samt UI, Integrationstests im Testrepository und End-to-End-Tests der gewählten Clients. Zusätzlich Nachweise für Erststart, Altprojektmigration, Speichern, Konflikt, Freigaberücknahme, Probedruck/Auflage, Wiederaufnahme und Sicherungswiederherstellung; bei gewähltem Umfang auch Offline-/DOCX-/Medienpfade.

Entscheiden: Welche Tests darf der Assistent vollständig selbst abnehmen? Welche visuellen oder fachlichen Tests verlangen den Auftraggeber? Für Entwicklung ohne weiteres Zutun müssen geeignete Testdaten und objektive Prüfkriterien anstelle zwingender manueller Abnahmen vereinbart werden. Ungeprüfte Punkte bleiben offen; ein grüner Unit-Test ersetzt keinen realen Gerätetest.

Beschluss D31 (bestätigt am 08.11.2026 durch „ja“):
- Eine Aufgabe wird mit passenden automatisierten Tests, Schema-, Workflow- und Dokumentationsprüfungen sowie praktischen Tests der betroffenen Abläufe geprüft.
- Änderungen an Anzeigen müssen gemäß D05 in ChatGPT, Codex, Claude und Open WebUI geprüft werden; nur tatsächlich unterstützte Darstellungen verwenden.
- Fehlende oder nicht ausführbare Tests bleiben ausdrücklich offen und dürfen nicht als bestanden gelten. Ein erfolgreicher Test in einer Umgebung ersetzt keinen Test in einer anderen.
- Die Freigabe zur selbstständigen Übernahme in D30 gilt erst bei erfolgreichen erforderlichen Prüfungen. Nicht geprüfte Pflichtfälle rechtfertigen keine Fertigmeldung.
- Eine pauschale Toleranz für Restmängel oder ein Ersatz nicht durchführbarer praktischer Pflichtprüfungen durch Unit-Tests wurde nicht beschlossen.

### D32 – Eskalation bei neuen Erkenntnissen

Empfehlung: innerhalb des Umfangs selbstständig lösen und dokumentieren. Bei fehlenden Zugängen, überschrittenem Budget, Verlustgefahr, widersprüchlichen Vorgaben oder neuer grundlegender Produktentscheidung den betroffenen Teil pausieren und unabhängige Aufgaben fortsetzen. Keine Schutzregel oder Kostenobergrenze still umgehen. Optional kann für fachliche Randfragen der Standard „kleinere sichere Lösung, Zusatzfunktion später“ ausdrücklich gewählt werden.

Beschluss D32 (bestätigt am 08.11.2026 durch „ja“):
- Technische Probleme innerhalb des beschlossenen Auftrags werden selbstständig gelöst, unter Einhaltung der bestätigten Vorgaben und Schutzregeln.
- Bei neuen Funktionen, Kosten, fehlenden Rechten, widersprüchlichen Vorgaben oder Verlustgefahr wird der betroffene Teil gestoppt und der Auftraggeber gezielt gefragt.
- Unabhängige autorisierte Aufgaben werden währenddessen weiterbearbeitet.
- Keine stillschweigende Erweiterung des Funktionsumfangs, Umgehung von Berechtigungen oder Aufgabe von Schutzregeln.

## Abschlussauftrag an den Entwicklungsassistenten

Nach Beantwortung aller anwendbaren Punkte:

1. Antworten in ein verbindliches Entscheidungsprotokoll mit Datum, Herkunft und IDs übertragen. Empfehlungen ohne ausdrückliche Annahme bleiben Vorschläge.
2. Vollständigkeit, Abhängigkeiten und Widersprüche prüfen. Keine offenen Pflichtfelder als technische Details umdeuten. Voraussetzungen wie Zugangseinrichtung und Testgeräte gesondert als „bereit“ oder „fehlt“ erfassen, ohne Secrets zu lesen.
3. Roadmap, workflow.yml, Schema, Architektur, API-Vertrag, Startanweisungen und betroffene Issues konsistent aktualisieren. v1.0-Teile von späteren Anbieterfunktionen trennen; bereits implementierte Funktionen von fehlender Abnahme unterscheiden. Nicht ausgewählte Aufgaben verschieben, nicht als umgesetzt schließen.
4. Für jeden Lieferblock einen ausführbaren Auftrag mit Umfang, Abhängigkeiten, Nichtzielen, Tests und Fertigkriterium erstellen. Codearbeiten über Repositories hinweg passend bündeln.
5. Nach den ausdrücklich erteilten Vollmachten selbstständig implementieren, prüfen, Fehler beheben und Änderungspakete vorbereiten bzw. übernehmen. CI-Fehler nicht ignorieren. Keine KI-Anbieter-Verbindung für v1.0 entwickeln.
6. Fortschritt verständlich melden: vorbereitet, implementiert, geprüft, übernommen oder bereitgestellt. Offene externe Voraussetzungen und Einschränkungen sichtbar halten.

## Prüfliste: Darf die Umsetzung ohne weitere fachliche Rückfragen beginnen?

- [ ] D01 enthält für jeden Bereich ein eindeutiges Lieferziel.
- [ ] Alle anwendbaren Entscheidungen D02–D32 sind ausdrücklich beantwortet.
- [ ] Hostingkosten, Plattformwahl, Speicher- und Aufbewahrungsregeln sind gedeckt oder der Dienst ist ausdrücklich verschoben.
- [ ] Zugänge und Testumgebungen sind vorhanden oder fehlende Einrichtungsschritte konkret zugeordnet.
- [ ] Clients, Browser und Testgeräte sowie überprüfbare Abnahmekriterien sind benannt.
- [ ] Übernahme-, Bereitstellungs- und Releasevollmachten sind getrennt eindeutig festgelegt.
- [ ] Alle Widersprüche zu bestehenden Regeln sind ausdrücklich aufgelöst.
- [ ] Der ausführende Assistent hat die Umsetzungsvoraussetzungen geprüft und den Auftrag als ausführbar dokumentiert.

Dann sind die heute bekannten wesentlichen Entscheidungen abgedeckt. Unerwartete externe Hindernisse oder neue grundlegende Anforderungen können weiterhin eine Entscheidung erfordern; normale Implementierungsdetails sind durch D28 delegiert.

## Ergebnis des Entscheidungsdialogs vom 08.11.2026

D01–D32 sind im oben protokollierten Umfang geklärt. D09–D12 und D19 sind durch D06/D01 nach v1.0 verschoben. Die jeweils nach „Beschluss“ notierten bestätigten Angaben haben Vorrang vor den vorbereitenden Empfehlungen und ursprünglichen Umfangstabellen.

Die fachliche Entscheidungsliste ist damit abgeschlossen. Vor einer Aussage „vollständig autonom ausführbar“ bleiben tatsächliche technische Voraussetzungen zu prüfen: Testzugänge und Darstellungsmöglichkeiten für alle vier Umgebungen, Repository-Rechte sowie ein gegebenenfalls nötiger sicherer YAWA-Testweg. Fehlende praktische Pflichtprüfungen dürfen nach D31 nicht ersetzt oder als bestanden erklärt werden.

Der nächste autorisierte Schritt ist die konsistente Übertragung der Beschlüsse in Roadmap, Arbeitsanweisungen, Aufgaben und ausführbare Entwicklungsaufträge. Implementierung und selbstständige Übernahme sind nur innerhalb D28–D32 gedeckt. Endgültige Veröffentlichung von v1.0 und Änderungen an bestehenden YAWA-Buchdaten bleiben gesondert zu bestätigen.

## Nachtrag für v1.0: Umschlag aus hochgeladener Gestaltungsvorlage

Am 8. November 2026 vom Benutzer ausdrücklich für v1.0 vorgemerkt. Planungsaufnahme, noch keine implementierte oder abgenommene Funktion. Zunächst lokal; keine GitHub-Übertragung durch diese Vormerkung beauftragt.

Benutzer können einen beispielsweise mit Paint erstellten Coverentwurf im Chat hochladen. GhostWriter soll die Gestaltung analysieren und daraus einen überprüfbaren Vorschlag für die buchbezogenen Umschlageinstellungen ableiten.

Zwei Wege berücksichtigen:

1. **Als fertiges Coverbild verwenden:** Die Gestaltung einschließlich vorhandener Schrift bleibt im Bild enthalten. Nicht ungefragt zusätzliche Titel oder Autorennamen darüberlegen. Bildqualität und Eignung für das gewählte Ausgabeformat prüfen.
2. **Als bearbeitbare Gestaltung nachbauen:** Erkennbare Hintergrundfarben, Bildaufteilung, Textpositionen, Ausrichtung, ungefähre Schriftgrößen, Schriften und Abstände in unterstützte Umschlageinstellungen übersetzen. Nicht unterstützte Merkmale ausdrücklich benennen; keine exakte Nachbildung versprechen.

Vorgesehener Ablauf: Upload → Analyse → Einstellungsvorschlag → Vorschau → ausdrückliche Bestätigung → Speicherung für dieses Buch. Originaldatei erhalten. Das Hochladen oder Analysieren allein verändert keine Bucheinstellungen und erteilt keine Bild-, Text- oder Veröffentlichungsfreigabe.

Erkannte Titel, Untertitel und Autorennamen zur Kontrolle zeigen, nicht ungeprüft als Buchdaten übernehmen. Exakte Schriftart und Druckmaße lassen sich aus einem Bild nicht immer zuverlässig ermitteln; Annäherungen als solche kennzeichnen. Fehlende Angaben wie Endformat und Beschnitt klären. Rückenbreite aus den nötigen Buch- und Druckdaten berechnen, nicht aus der Bildansicht erraten.

Bei der weiteren Planung vorhandenes Umschlagmodell und Ausgabewege prüfen, erforderliche Erweiterungen abgrenzen und Abnahmekriterien formulieren. Die für v1.0 beschlossene Arbeit über vorhandene Chat-Werkzeuge ohne neue KI-Anbieter-API bleibt bestehen.


## Beschluss vom 8. November 2026: Skill-Unterstützung

Vom Benutzer mit „so machen wir das“ bestätigt:

- **v1.0:** Die vorhandene GhostWriter-Skill-Unterstützung prüfen und für Claude und Codex konsistent nutzbar machen. Einstieg, Buchprofil, Schreibablauf und Qualitätsprüfung verwenden dieselben fachlichen Regeln. Clientabhängiges Laden und verfügbare Werkzeuge praktisch prüfen; Unterstützung nicht allein aus dem Dateiformat ableiten.
- **Ab v1.1:** Eigenständige Buch-Skills für Konzeption, Recherche, Schreiben/Überarbeiten, Kontinuität und Ausgabeprüfung schrittweise ausbauen. Einzelumfang und Abnahme je Skill festlegen; keine Zusage, alle Skills bereits mit v1.1 vollständig zu liefern.
- Entwicklungsskills können nach Bedarf lokal eingesetzt werden und sind kein an eine Produktversion gebundenes Liefermerkmal.
- Fachliche Regeln bleiben in einer gemeinsamen Quelle; Skill-Einstiege verweisen darauf. Buchinhalte und individuelle Vorgaben bleiben im Buchprojekt. Normale Buchaufträge sollen ohne Kenntnis von Skill-Namen funktionieren.

Bestätigte Planung, noch keine Umsetzung oder praktische Abnahme. Keine GitHub-Übertragung durch diesen Beschluss beauftragt.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg"><img src="assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
