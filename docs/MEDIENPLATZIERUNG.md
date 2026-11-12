# Medien im Abschnitt

Deutsch · [English](MEDIA-LAYOUT.en.md)

**GhostWriter ist für textorientierte Bücher gedacht, nicht für Bildbände oder Fotobücher. Eine Szene entspricht einem Abschnitt; ein Abschnitt enthält höchstens ein Medium, etwa eine Illustration oder eine Grafik.**

## Verbindliche Vorgaben

Die folgenden Vorgaben wurden am 8. November 2026 bestätigt. Sie beschreiben das gewünschte Produktverhalten. Die Begrenzung auf ein Medium ist umgesetzt; die Platzierung mit Textumfluss und der Breitenregler sind im aktuellen Programm noch nicht umgesetzt.

### Ein Medium je Abschnitt

Ein Abschnitt bildet eine Szene ab und kann ohne Medium auskommen oder genau ein Medium enthalten. Soll eine weitere Szene mit einem weiteren Medium ins Buch, wird dafür ein eigener Abschnitt angelegt. Auch das mehrfache Einfügen desselben Bildes zählt als mehrere Platzierungen und erfüllt die Begrenzung nicht.

Gespeicherte Varianten und reine Referenzbilder sind noch keine Platzierungen im Manuskript. Referenzfreigabe, Auswahl für einen Erstellungsauftrag und Freigabe zur Buchausgabe bleiben getrennte Entscheidungen. Siehe [Bilder und visuelle Referenzen](BILDER-UND-REFERENZBILDER.md).

**Ein Medium eigenständig vor oder nach einem Textabschnitt zeigen:** Dafür einen eigenen Abschnitt anlegen, der nur das Bild oder die Grafik enthält. Dieser Medienabschnitt wird in der Gliederung unmittelbar vor oder nach dem betreffenden Textabschnitt eingeordnet. Er zählt als eigener Abschnitt mit höchstens einem Medium; Bild- und Abschnittsfreigaben gelten weiterhin.

### Position und Textumfluss

Das Medium steht **im Abschnittstext mit Textumfluss**, nicht als eigenständiges Seitenlayout für einen Bildband. Die Platzierung bietet sechs Möglichkeiten:

| Vertikal | Links | Mittig | Rechts |
|---|---|---|---|
| Oben | oben links | oben mittig | oben rechts |
| Unten | unten links | unten mittig | unten rechts |

Die Auswahl beschreibt die Lage innerhalb des Abschnitts. Ein fester Platz am oberen oder unteren Seitenrand wurde nicht beauftragt. Wie der Text bei der gewählten Größe und Position um das Medium läuft, muss in den unterstützten Ausgabeformaten praktisch geprüft werden.

### Größe als Anteil der Seitenbreite

Ein **Schieberegler mit Prozentanzeige** stellt die Breite des Mediums als Anteil der nutzbaren Seitenbreite innerhalb der Ränder ein. Die Höhe folgt proportional; das Seitenverhältnis bleibt erhalten. Bei einer fließenden E-Book-Ausgabe ist die nutzbare Lesebreite die entsprechende Bezugsgröße.

Position und Breite bestimmen gemeinsam den Textumfluss. Fehlende Druckauflösung und unleserliche Grafikbeschriftungen müssen sichtbar gemeldet werden. Die Größenwahl ersetzt weder die Bildfreigabe noch eine ausdrücklich nötige Bestätigung zur Verkleinerung der gespeicherten Bilddatei; Layoutgröße und Originaldatei sind verschiedene Dinge.

## Stand nach dem lokalen Funktionstest

| Teil | Tatsächlicher Stand |
|---|---|
| Illustration und Referenzbild | Aufnahme, Auswahl, Referenzprotokoll und Freigabeschranken vorhanden. |
| Beschriftetes Diagramm | Separat erstellen und als PNG aufnehmen möglich; der allgemeine Bildprompt verbietet derzeit Schrift. |
| Höchstens ein Medium | Umgesetzt: Projektprüfung (`validate_project.py`) und Ausgabe (Probedruck, Auflage) melden mehr als ein Medium im Abschnitt und ein mehrfach eingefügtes Bild als Fehler. Nicht eingefügte Varianten und Referenzbilder zählen nicht. |
| Position und Textumfluss | Noch nicht umgesetzt; die Ausgabe setzt Bilder derzeit auf volle Satzbreite. |
| Breitenregler | Noch keine Auswahl im Bildformular; die Ausgabe verwendet fest `width=100%`. |
| Medienabschnitt im PDF | Inhalt wird ausgegeben; Überschrift und Grafik können auf verschiedene Seiten rutschen. Auch Entwurfsvermerke können sich vom Bild lösen. |
| Alternativtext | Gespeichert, aber bei DOCX und EPUB wird bisher die Bildunterschrift statt des ausführlichen Alternativtexts ausgegeben. |

Vor Abschluss der Umsetzung sind alle sechs Positionen, Größenänderungen, Seitenwechsel und Textumfluss in PDF, DOCX und EPUB zu prüfen. Nicht unterstützte Einstellungen müssen sichtbar gemeldet werden. Ein erfolgreiches Speichern allein ist kein Nachweis einer richtigen Platzierung.

[Buchablauf](BUCHABLAUF.md) · [Erstellungskreislauf](ERSTELLUNGSKREISLAUF.md) · [Speichern und Freigeben](SPEICHERN.md)

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
