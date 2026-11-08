# Lokaler Test der Bild und Grafikfunktion

Datum: 8. November 2026. Ergebnis: **Grundablauf bestanden; Gesamtfunktion wegen der unten genannten Lücken noch nicht abgenommen.** Alles wurde lokal in synthetischen Testbüchern durchgeführt. Keine Veröffentlichung, kein GitHub-Upload und keine Freigabe eines echten Buchs.

## Geprüfter Stand und Umfang

Die Bildfunktionen stammen aus dem aktuellen Hauptstand `137465e927d647486bad08ce25eb93adb0982120` von `ploeffler/GhostWriter`. Die danach eingespielte Änderung #224 betrifft ausschließlich Dokumentation. Die hier neu bestätigten Medienanforderungen wurden lokal dokumentiert; die Bildfunktionen selbst wurden während dieser Prüfung nicht verändert.

Getestet wurden eine echte im verbundenen Chat erzeugte Illustration, ihr ausdrücklich ausgewähltes Referenzbild, ein deterministisch erstelltes beschriftetes Diagramm und ein eigener Abschnitt ohne Fließtext, der nur eine Grafik enthält. Das finale Testbuch hat drei Abschnitte mit jeweils genau einem Medium. Ein gesonderter Negativfall mit zwei Medien im selben Abschnitt bleibt als Beleg erhalten.

Synthetische Schreib-, Abschnitts-, Kapitel- und Bildfreigaben dienen ausschließlich dem Test. Sie sind keine Entscheidungen über reale Buchinhalte.

## Funktionierende Schritte

| Schritt | Ergebnis und Beleg |
|---|---|
| Referenzbild aufnehmen | PNG wird unverändert gespeichert. Der Zustand `stored` erlaubt noch keine Verwendung. |
| Referenz freigeben und auswählen | Die ausdrücklich simulierte Testfreigabe ermöglicht die Auswahl für genau den Bildauftrag. |
| Tatsächliche Übergabe | Die ausgewählte lokale Referenzdatei wurde über `referenced_image_paths` an die eingebaute Bildgenerierung übergeben. Das ist ein tatsächlich ausgeführter Werkzeugaufruf, keine bloße Erwähnung im Prompt. |
| Wiedererkennung | Weißes anatomisch rechtes Ohr, grünes Halsband und dreieckiger Anhänger sind in Referenz und neuer Szene erkennbar erhalten. Das ist eine Sichtprüfung dieses Beispiels, keine Garantie beliebiger weiterer Aufträge. |
| Illustration speichern | Bilddatei, Bildunterschrift, Alternativtext, Entwurfszustand und Laufprotokoll werden angelegt. Die Referenz-ID und der genaue SHA-256 der Referenzdatei stehen im Lauf. |
| Beschriftetes Diagramm | SVG wird nachvollziehbar als nicht unterstütztes Buchformat abgelehnt; die daraus gerenderte PNG-Fassung wird unverändert gespeichert. PNG/JPEG sind der bestätigte aktuelle Uploadumfang. |
| Bildfreigabeschranke | Nicht freigegebene Bilder verhindern die Testauflage. Nach simulierten Bildfreigaben ist sie baubar. |
| Referenz zurückziehen | Eine zurückgezogene Referenz wird bei neuen Auswahlen abgelehnt; der bereits angelegte Lauf bleibt unverändert. |
| Medienabschnitt | Ein Abschnitt, dessen Manuskript ausschließlich einen Bildverweis enthält, wird von Projekt- und Auflagenprüfung akzeptiert. Er wird in allen drei Formaten ausgegeben. |
| PDF | Die drei Bildplatzierungen und Bildunterschriften sind enthalten; Grafikbeschriftungen sind lesbar. Die Illustration erreicht im erzeugten Test-PDF etwa 355 dpi, das Diagramm etwa 554 dpi. |
| DOCX und EPUB | Je drei Bildplatzierungen. Die eingebetteten PNG-Dateien sind bytegleich mit den aufgenommenen Dateien. Das reine Referenzbild gelangt nicht automatisch in die Ausgabe. |
| Probedruck | Alle drei Entwurfsvermerke und der Hinweis „nicht zur Veröffentlichung“ sind vorhanden. Ihre räumliche Zuordnung hat allerdings einen Layoutmangel, siehe unten. |

Die EPUB-Inhalte wurden zusätzlich in einem separaten lokalen Chrome-Prozess gerendert. Alle drei Bilder laden vollständig. Das bestätigt diese HTML-Darstellung, ersetzt aber keine Abnahme auf unterschiedlichen E-Readern. DOCX wurde mit dem gebündelten LibreOffice-Renderer in Seitenbilder umgewandelt. PDF, DOCX und EPUB wurden visuell geprüft.

## Noch offene Punkte

| Priorität | Befund | Erwartetes Ergebnis |
|---|---|---|
| Hoch | Zwei Medien im selben Abschnitt wurden von Projektprüfung und Export akzeptiert. | Neue Regel technisch erzwingen: eine Szene entspricht einem Abschnitt, maximal ein Medium pro Abschnitt. Mehrfaches Einfügen desselben Mediums ebenfalls erkennen. Varianten und reine Referenzen nicht als Platzierungen zählen. |
| Hoch | Ausgabe nutzt fest volle Satzbreite (`width=100%`), ohne Position, Textumfluss oder Breitenregler. | Sechs Positionen oben/unten × links/mittig/rechts im Abschnittstext mit Textumfluss; Breiten-Schieberegler mit Prozentanzeige bezogen auf nutzbare Seitenbreite, Höhe proportional. Für jedes Ausgabeformat praktisch abnehmen. |
| Wesentlich | Der ausführliche gespeicherte Alternativtext geht in DOCX und EPUB verloren; als Alternativtext erscheint nur die Bildunterschrift. | Bildunterschrift und Alternativtext getrennt bis in die Ausgabe erhalten. Beleg: `exportpruefung.json`; Ursache im aktuellen `assemble.resolve_images`: es verwendet die Beschriftung und ignoriert das Metadatenfeld `alt`. |
| Wesentlich | Der allgemeine Bildauftrag hängt auch bei einem beschrifteten Diagramm „Ohne Schrift, Buchstaben oder Logos“ an. | Grafikaufträge von Illustrationsaufträgen unterscheiden; ausdrücklich gewünschte Beschriftungen zulassen. Der separat getestete SVG/PNG-Weg funktioniert bereits. |
| Wesentlich | Im PDF steht die Überschrift des reinen Medienabschnitts auf Druckseite 2, die Grafik erst auf Druckseite 3. | Überschrift, Medium und Bildunterschrift als zusammengehörigen Inhalt behandeln. Die Grafik darf nicht durch eine unkontrollierte Gleitplatzierung aus ihrem Abschnittszusammenhang geraten. |
| Wesentlich | Entwurfsvermerke im Probedruck können sich von ihrem Bild lösen. Beim dritten Bild steht der Vermerk auf der vorigen Seite. | Warnung eindeutig beim betreffenden Bild halten, auch bei Seitenwechseln und Gleitobjekten. |

Keine dieser Feststellungen wurde als behoben ausgegeben. Für Codeänderungen ist eine eigene Umsetzung mit passenden Tests erforderlich. Es wurden keine neuen Issues angelegt oder Nachrichten an Dritte gesendet.

## Bestätigte Produktvorgaben aus diesem Testgespräch

- GhostWriter dient textorientierten Büchern und ist nicht für Bildbände oder Fotobücher gedacht. Der Hinweis steht nun prominent in der lokalen Dokumentation.
- Eine Szene entspricht einem Abschnitt; je Abschnitt höchstens ein Medium.
- Ein eigenständiges Bild vor oder nach einem Textabschnitt bekommt einen eigenen Abschnitt, der nur dieses Medium enthält.
- Medien im Abschnittstext sollen mit Textumfluss platziert werden: oben/unten, jeweils links/mittig/rechts.
- Ein Schieberegler mit Prozentanzeige stellt die Breite relativ zur nutzbaren Seitenbreite ein. Die Höhe bleibt proportional.
- Diese neuen Layoutfunktionen und die Mengenbegrenzung sind Anforderungen und noch keine implementierten Funktionen.

Die Anforderungen stehen im Projekt unter `docs/MEDIENPLATZIERUNG.md` und `docs/MEDIA-LAYOUT.en.md`. Zusätzlich wurde der zuvor gewünschte Codex-Hinweis in einer eigenen Zeile unter dem Claude-Hinweis in der lokalen Programmdokumentation umgesetzt. Die dazugehörige Dokumentationsprüfung und sieben gezielte Tests bestehen. Die Hinweise gelangen nicht in die Buchvorlagen.

## Automatische Prüfungen

- 15 vorhandene Tests zu Bildern und Referenzbildern: 14 bestanden direkt; der vollständige Exporttest scheiterte zunächst am fehlenden deutschen LaTeX-Sprachpaket und bestand nach dessen rein lokaler Bereitstellung. Protokolle der ursprünglichen Suite und der erfolgreichen gezielten Wiederholung sind erhalten.
- 11 Tests für Dateigrenzen, Originalschutz, bestätigte Verkleinerung, Bestandswarnung und sichere Ablage: bestanden.
- Finale Projektprüfung, Auflagenprüfung, ZIP-/Bildintegritätsprüfung, Alternativtextprüfung und Probedruckprüfung: ausgeführt. Der Alternativtextvergleich dokumentiert bewusst die festgestellte Abweichung.
- `python3 scripts/check_docs.py`: bestanden.
- Sieben Tests für Dokumentationsprüfung, generierte Einstiege und die neue zweizeilige Fußzeile: bestanden.

Fehlende Exportabhängigkeiten wurden nur lokal bereitgestellt: temporäre Python-Abhängigkeiten, ein echtes aus dem vorhandenen XeTeX erzeugtes XeLaTeX-Format und das in einen temporären Ordner entpackte deutsche Sprachpaket. Keine Systeminstallation und keine Anbieter-API-Schlüssel waren nötig. Es fand kein Ersatz des PDF-Exports durch eine andere Ausgabe-Engine statt.

## Testbelege

- [Schrittprotokoll](pruefschritte.json)
- [Finaler Teststand mit einem Medium pro Abschnitt](teststand-ein-medium.json)
- [Nachweis der tatsächlichen Referenzübergabe](uebergabenachweis.json)
- [Prüfung der eingebetteten Dateien und Alternativtexte](exportpruefung.json)
- [EPUB im lokalen Browser](epub-browserpruefung.json)
Die Bilder wurden mit dem eingebauten Bildwerkzeug erstellt; ein Modellname wurde vom Werkzeug nicht ausgewiesen. Das Diagramm wurde als SVG programmiert und lokal gerendert. Es wurde keine externe Bildquelle recherchiert oder ein fremdes Nutzungsrecht als geklärt behauptet.

## Visuelle Belege und lokale Rohdaten

- [PDF-Seitenübersicht](pdf-ansicht-uebersicht.png)
- [Word-Seitenübersicht](docx-ansicht-uebersicht.png)
- [Probedruck-Seitenübersicht](probedruck-ansicht-uebersicht.png)

Die vollständigen lokalen Rohdaten (synthetische Testbücher, generierte Bilder, PDF/DOCX/EPUB, Prüfskripte und Protokolle) werden separat archiviert. Sie sind keine abgenommenen Vorlagen. Dieses Verzeichnis enthält den kompakten Prüfbericht, Messergebnisse und Ansichtsbelege; lokale absolute Dateipfade in JSON wurden durch relative Testlaufpfade ersetzt. Das belegt einen damaligen Testlauf und ist kein automatisch wiederholbarer Integrationstest.
