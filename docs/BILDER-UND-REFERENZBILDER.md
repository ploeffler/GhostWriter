# Bilder und visuelle Referenzen

[English](IMAGES-AND-REFERENCES.en.md) · Deutsch

**GhostWriter ist nicht für Bildbände oder Fotobücher gedacht. Eine Szene entspricht einem Abschnitt; je Abschnitt höchstens ein Medium.** Die sechs Positionen, Textumfluss und der Breiten-Schieberegler sind in [Medien im Abschnitt](MEDIENPLATZIERUNG.md) festgelegt. Diese neuen Layoutfunktionen und die technische Mengenbegrenzung sind noch nicht umgesetzt.

## Zweck und Geltungsbereich

Diese Anforderung gilt für **alle GhostWriter-Bücher** und alle Buchtypen. Sie ergänzt die bestehende Illustrationsfunktion (#54) um eine eigenständige Verwaltung hochgeladener Bilder, die als visuelle Referenzen in spätere Erstellungsaufträge einbezogen werden können.

Die Spezifikation beschreibt das gewünschte Produktverhalten. Sie behauptet nicht, dass der vollständige Referenzbild-Workflow bereits implementiert ist.

## Zwei getrennte Rollen

Ein Bild kann eine oder beide Rollen erhalten:

- **Buchbild / Illustration:** Das Bild ist für die Verwendung im Manuskript oder in einer Buchausgabe vorgesehen.
- **Visuelle Referenz:** Das Bild dient als Vorlage für einen späteren Erstellungsauftrag, etwa zur Wahrung des Aussehens einer Person oder Figur, eines Ortes, Gegenstands, Kostüms oder einer wiederkehrenden Szene.

Die Rollen sind unabhängig voneinander. Ein hochgeladenes Foto wird nicht automatisch zur Buchillustration und nicht automatisch zur Erstellungsreferenz. Die bestehende Illustrationsverwaltung und ihre Freigabe für die Buchausgabe bleiben davon unberührt.

## Nachträglicher Upload

Bilder müssen jederzeit nach der Einrichtung eines Buchprojekts hochgeladen werden können. Der Upload ist nicht auf den Wizard oder die Erstanlage des Buches beschränkt.

Beim Ablegen kann der Benutzer das Bild zuordnen zu:

- einer Person oder Figur,
- einem Ort,
- einem Gegenstand,
- einer Szene oder Situation,
- einem Kapitel oder Abschnitt,
- dem gesamten Buchprojekt,
- oder mehreren passenden Bezugspunkten.

Mehrere Bilder dürfen demselben Bezugspunkt zugeordnet werden. Bereits vorhandene Bilder müssen später ergänzt, ersetzt, deaktiviert oder neu zugeordnet werden können, ohne frühere Aufträge und deren Historie zu verändern.

## Metadaten und Freigabe

Zu einem Bild sollen mindestens nachvollziehbar gespeichert werden:

- stabile Bild-ID und Dateipfad,
- ursprünglicher Dateiname,
- zugeordnete Projektelemente,
- Rolle(n): Buchbild, visuelle Referenz oder beides,
- kurze Beschreibung des sichtbaren Inhalts und des beabsichtigten Referenzzwecks,
- Herkunft (z. B. eigenes Foto, bereitgestellte Datei, lizenzierte Quelle),
- bekannte Urheber-, Lizenz- und Einwilligungsinformationen,
- Upload-Zeitpunkt und Status.

Für visuelle Referenzen gelten getrennte, ausdrückliche Entscheidungen:

1. **Nur gespeichert:** Das Bild ist Material im Projekt, wird aber nicht automatisch verwendet.
2. **Als Referenz freigegeben:** Das Bild darf bei passenden Erstellungsaufträgen angeboten und nach Auswahl verwendet werden.
3. **Deaktiviert / zurückgezogen:** Das Bild bleibt in der Historie erhalten, darf aber nicht mehr in neue Aufträge einfließen.

Ein Upload allein ist niemals eine Freigabe. Bei Personenbildern sind insbesondere Einwilligung, Nutzungsrechte und der vom Benutzer angegebene Verwendungszweck zu beachten.

## Verwendung im Erstellungspfad

Vor einem passenden Erstellungsauftrag zeigt GhostWriter die verfügbaren, freigegebenen Referenzbilder an, die zum gewählten Bezugspunkt passen. Der Benutzer entscheidet ausdrücklich, welche davon für genau diesen Auftrag verwendet werden.

Der Ablauf:

1. Erstellungsauftrag und Bezugspunkt bestimmen, z. B. „Porträt von Figur X“ oder „Illustration für Abschnitt 3.2“.
2. Passende, freigegebene Referenzbilder anzeigen.
3. Auswahl durch den Benutzer ermöglichen; keine automatische Übernahme allein aufgrund einer Zuordnung.
4. Ausgewählte Referenzen zusammen mit dem Auftrag an den Bilddienst bzw. den Erstellungsprozess übergeben, soweit der Dienst Bildreferenzen unterstützt.
5. Im Auftragsprotokoll festhalten, welche Referenz-IDs tatsächlich verwendet wurden.
6. Ergebnis wie bisher prüfen und ausdrücklich freigeben, bevor es als Buchillustration in das Manuskript bzw. die Ausgabe übernommen wird.

**Übergabe über die Action „Bild erzeugen“ (#143):** `python3 scripts/image_service.py . services` zeigt die Fähigkeit je Bilddienst aus `providers.yml` (`image_services`: Referenzbilder ja/nein, Höchstzahl, Formate, Größe). `image_service.py plan --service google --references ref-img-…` prüft, was an den Dienst gehen würde (übergeben, übersprungen mit Grund, Betriebsart), ohne etwas zu senden. Die Action „Bild erzeugen“ (`image.yml`, nur mit eigenem Secret `GEMINI_API_KEY` und `consent`) schickt die freigegebenen Referenzen tatsächlich als Bild an Google Gemini und schreibt je Auftrag `bild.jpg` und `handover.yml` unter `quellen/bild-entwuerfe/` auf den Arbeits-Branch: Dienst, Modell, übergebene Referenz-IDs mit Bildversion (SHA-256 der Datei), Übersprungenes mit Grund; spätere Änderungen an einer Referenz ändern das Protokoll nicht. Das Ergebnis ist ein Entwurf, kein Buchbild. Heute übergibt GhostWriter nur an Google Gemini (bis zu 3 Bilder, PNG/JPEG, bis 7 MB je Bild); bei anderen Diensten meldet es ausdrücklich, dass nichts übergeben wird.

Wenn der verwendete Dienst keine Bildreferenzen unterstützt, muss GhostWriter dies offen anzeigen. Das Bild darf dann nicht als tatsächlich übermittelte Referenz ausgegeben werden. Eine textliche Beschreibung kann als Ersatz vorgeschlagen werden, muss aber als solche kenntlich sein.

## Wiederverwendbarkeit und Nachvollziehbarkeit

- Freigegebene Referenzen können bei späteren Aufträgen erneut ausgewählt werden, auch in anderen Kapiteln desselben Buches.
- Eine Zuordnung zu einer Figur oder einem anderen Projektelement macht das Bild auffindbar, bedeutet aber keine automatische Verwendung.
- Jeder Auftrag speichert seine konkrete Referenzauswahl. Änderungen an einer Bilddatei oder deren Freigabestatus verändern vergangene Auftragsprotokolle nicht.
- Bei mehreren Referenzen muss der Benutzer sie einzeln auswählen können; GhostWriter darf widersprüchliche oder veraltete Referenzen nicht stillschweigend priorisieren.
- Referenzbilder werden nicht automatisch in den Buchsatz oder eine veröffentlichte Ausgabe aufgenommen.

## Bilder recherchieren (#218)

Bilder sucht der Chat mit seinen vorhandenen Werkzeugen, oder du nennst selbst einen Link. GhostWriter bindet dafür keinen eigenen Such- oder KI-Dienst an. Jeder Fund wird zuerst ein **Kandidat** (`research/images/candidates.yml`, `scripts/image_research.py propose`) mit Titel, Bild-URL, Fundseite, Urheber, Lizenz und Zuordnung. Eine Bilddatei wird dabei nicht gespeichert.

- **Rechte:** Ein Kandidat gilt als *geklärt*, wenn Urheber **und** Lizenz angegeben sind, sonst als *ungeklärt*. „Geklärt“ heißt nur, dass die Angaben vorliegen, nicht, dass sie rechtlich geprüft sind. GhostWriter erfindet keine Nutzungserlaubnis.
- **Übernehmen:** Erst nach deiner ausdrücklichen Bestätigung (`adopt <cand-id> --file … --confirm`) wird der Kandidat ein **gespeichertes Bild** unter `reference-images/` (Status `stored`), mit Quelle, Urheber und Lizenz in den Metadaten. Ohne Bestätigung ändert sich nichts. Bei ungeklärten Rechten braucht es zusätzlich `--accept-unclear`, und die Herkunft bleibt `unknown`. Die Regeln für Größe und Originale (D13) gelten wie beim eigenen Upload.
- **Buchabbildung:** Ein gespeichertes Bild ist weder freigegebene Referenz noch Buchabbildung. Beides bleibt eine eigene Freigabe über die Bildverwaltung.
- **Verwerfen:** `reject <cand-id>` hält den Kandidaten mit Grund als verworfen fest.

## Fotos colorieren (#452)

Schwarz-Weiß-Fotos aus Familienbesitz lassen sich einfärben, ohne dass ein Bildmodell Gesichter oder Formen verändert. Das Modell liefert nur einen Farbvorschlag. Übernommen wird davon allein die Farbe (Kanäle a/b im Lab-Farbraum); die Helligkeit kommt Pixel für Pixel aus dem aufbereiteten Bild. Ablauf und Sperren stehen in `START.md`, „Fotos colorieren (#452)“, die Dateien im [Datenmodell](DATA-MODEL.md#bildordner-und-colorieren-452). **Material einbringen (#574):** Auch ein Materialordner `quellen/<Datum>-<Kurzname>/` lässt sich so einfärben (`python3 scripts/material.py . colorize <ordner> …`): Quelle ist `bearbeitet.jpg`, die Beschreibung steht in `material.yml`, das Ergebnis ist `coloriert.jpg`; Minderjährige und Dokumente bleiben gesperrt.

- **Mit eigenem Google-Gemini-Zugang:** Action „Bild colorieren“ (`.github/workflows/colorize.yml`) mit dem Secret `GEMINI_API_KEY`. Der Chat liest den Schlüssel nicht; die Action schickt das Bild an Google und legt das Ergebnis ins Änderungspaket. Jeder Start legt einen Auftrag in die Hintergrund-Warteschlange (#479): Zehn Fotos am Abend werden alle coloriert, nacheinander.
- **Mit einem anderen Bilddienst im Chat:** dessen Farbvorschlag mit `scripts/colorize.py --proposal` übernehmen.
- **Gesperrt:** Bilder mit Kindern oder Jugendlichen (`minderjaehrige` muss ausdrücklich `false` sein) und Dokumente (`art` nur `foto` oder `foto-vom-foto`). Diese Bilder gehen an keinen externen Dienst.
- **Ausnahme im Einzelfall:** Ein Bild mit Kindern (`minderjaehrige: true`) lässt sich nur mit ausdrücklicher Ausnahme colorieren (`--minors-exception`, Action-Eingabe `minors_exception`), wenn die Abgebildeten bzw. die Familie einverstanden sind. `bild.yml` bleibt unverändert; der Eintrag unter `bearbeitung` nennt die Ausnahme. Für Dokumente gibt es keine Ausnahme.
- **Bekannte Farben:** Was man sicher weiß (z. B. „Die Fahne ist rot-weiß-rot.“), geht als Hinweis an Gemini (`--hint`, Action-Eingabe `hint`, höchstens 300 Zeichen) und steht im Eintrag unter `bearbeitung`. Ohne Hinweis rät das Modell.
- **Geprüft wird:** gleiches Seitenverhältnis, gleicher Bildaufbau und eine mittlere Helligkeitsabweichung unter 1/255. Sonst wird nichts geschrieben.
- Ein coloriertes Bild wird im Buch als „nachträglich coloriert“ gekennzeichnet. Die Farben sind eine Annahme, kein Beleg.

## Abgrenzung zur bestehenden Illustrationsfunktion

Die bestehende Funktion #54 verwaltet erzeugte bzw. bereitgestellte Illustrationen abschnittsbezogen und kennt deren Entwurf- und Freigabestatus für die Buchausgabe. Die neue Referenzverwaltung ergänzt dies, ersetzt es aber nicht.

Insbesondere darf die technische Umsetzung nicht einfach jedes hochgeladene Referenzbild als Illustration behandeln oder ungeprüft in `chapters/<kapitel>/images/` ablegen. Die dauerhafte Ablage und Metadatenstruktur für Referenzmaterial ist im Rahmen der Umsetzung mit dem bestehenden Datenmodell abzustimmen. Bestehende Bilddateien und das aktuelle `schemas/image.schema.json` dürfen nicht rückwirkend inkompatibel werden.

## Abnahmekriterien

- [ ] Bilder können jederzeit nachträglich in jedes GhostWriter-Buch hochgeladen werden.
- [ ] Bilder können Personen/Figuren, Orten, Gegenständen, Szenen, Kapiteln, Abschnitten oder dem Gesamtprojekt zugeordnet werden.
- [ ] Buchbild und visuelle Referenz sind getrennte Rollen; beide können gleichzeitig gesetzt sein.
- [ ] Upload und Zuordnung aktivieren keine Referenz automatisch.
- [ ] Referenzfreigabe und Auswahl für einen konkreten Auftrag erfordern eine ausdrückliche Benutzerentscheidung.
- [ ] Der Erstellungspfad übergibt nur die für diesen Auftrag ausgewählten Referenzen.
- [ ] Nicht unterstützte Referenzübergabe durch einen Dienst wird transparent angezeigt.
- [ ] Verwendete Referenz-IDs werden im jeweiligen Auftragsprotokoll festgehalten.
- [ ] Zurückgezogene Referenzen werden nicht in neuen Aufträgen verwendet; die Historie bleibt erhalten.
- [ ] Referenzbilder gelangen nicht ohne separate Freigabe in Manuskript oder Buchausgabe.
- [ ] Die Funktion gilt einheitlich für alle Bücher und ist nicht an ein einzelnes Buchprojekt gebunden.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
