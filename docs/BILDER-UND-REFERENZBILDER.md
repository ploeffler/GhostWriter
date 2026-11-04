# Bilder und visuelle Referenzen

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

Wenn der verwendete Dienst keine Bildreferenzen unterstützt, muss GhostWriter dies offen anzeigen. Das Bild darf dann nicht als tatsächlich übermittelte Referenz ausgegeben werden. Eine textliche Beschreibung kann als Ersatz vorgeschlagen werden, muss aber als solche kenntlich sein.

## Wiederverwendbarkeit und Nachvollziehbarkeit

- Freigegebene Referenzen können bei späteren Aufträgen erneut ausgewählt werden, auch in anderen Kapiteln desselben Buches.
- Eine Zuordnung zu einer Figur oder einem anderen Projektelement macht das Bild auffindbar, bedeutet aber keine automatische Verwendung.
- Jeder Auftrag speichert seine konkrete Referenzauswahl. Änderungen an einer Bilddatei oder deren Freigabestatus verändern vergangene Auftragsprotokolle nicht.
- Bei mehreren Referenzen muss der Benutzer sie einzeln auswählen können; GhostWriter darf widersprüchliche oder veraltete Referenzen nicht stillschweigend priorisieren.
- Referenzbilder werden nicht automatisch in den Buchsatz oder eine veröffentlichte Ausgabe aufgenommen.

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
