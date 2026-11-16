# Buchgedächtnis: Fakten und Kontinuität abgleichen

Deutsch · [English](STORY-MEMORY.en.md)

Dieser optionale Chat-Arbeitsweg ergänzt [Lektorat](LEKTORAT.md) und
[Qualitätssicherung](QUALITAETSSICHERUNG.md). Er liest das ausgewählte Buch und
liefert Vorschläge im Chat. Er schreibt keine Fakten fest, verändert keine
Dateien oder Freigaben und startet keine Hintergrundanalyse.

## Aufträge

- „Gleiche Kapitel 3 mit unserem Buchgedächtnis ab.“
- „Welche neuen oder geänderten Fakten enthält Abschnitt 2.3?“
- „Prüfe, was die Figuren bis zum Ende von Kapitel 4 wissen können.“

Buch und Umfang aus der Anfrage beziehungsweise eindeutigen aktuellen Auswahl
übernehmen; bei fehlender Zuordnung nachfragen. Bei „neu/geändert“ den
Vergleichsstand benennen. Ohne zugängliche frühere Fassung nur Beobachtungen
und Abweichungen zu vorhandenen Referenzen berichten, keinen Versionsvergleich
behaupten. Keine anderen Bücher oder fremden Buch-Branches ungefragt einbeziehen.

## Vorhandene Quellen verwenden

| Quelle im ausgewählten Buch | Verwendung und Grenze |
|---|---|
| `ghostwriter.yml` und bestätigte Projektunterlagen | Buchvorgaben, Stil, Begriffe und ausdrückliche Entscheidungen; fehlende Bestätigungen offen nennen |
| Vollständige betroffene Manuskriptabschnitte und relevante Nachbartexte | Tatsächliche Textstellen, Verlauf und Wissensstände; Textstatus und Fassung festhalten |
| `characters/char-*.md` | Figurenmerkmale und Beziehungen; vorhandene IDs und Autorenangaben erhalten |
| `story/places.yml` | Namen, Aliase und Ortsbeschreibungen samt Abschnittsbezügen |
| `story/timeline.yml` | Ereignisse, wörtliche Zeitangaben und Chronologiehinweise; Buchreihenfolge ist nicht automatisch Ereignisreihenfolge |
| Vorhandenes Glossar und ausdrücklich zugängliche Serienreferenzen | Schreibweisen und Bedeutungen; Bandfassung und gemeinsame Serienfassung getrennt halten |
| Vorhandene Analyseläufe | Hinweise auf prüfbare Fundstellen; bei veraltetem oder unklarem Quellenstand erneut am aktuellen Text prüfen |

Eine vorhandene Datei beweist für sich keine Autorenbestätigung. Die bestehenden
Dateiformate speichern nicht für jede Aussage Bestätigungsstatus oder externe
Belegprüfung. Diese Angaben im Bericht nur mit nachgewiesener Herkunft nennen;
keine zusätzlichen Felder in YAML-Dateien erfinden. Fehlende Unterlagen nicht
anlegen und keine parallele `kb/`-Wissensablage einführen.

## Herkunft und Verbindlichkeit trennen

- **Textbeobachtung:** steht an der genannten Stelle der geprüften Fassung.
  Figurenrede, Vermutung, Traum, Erinnerung und unzuverlässige Erzählung als
  solche kennzeichnen; eine Behauptung der Figur ist keine objektive Buchwahrheit.
- **Vorläufig:** Entwurf, offene Variante oder KI-Vorschlag. Nicht automatisch
  zum verbindlichen Buchfakt erklären, auch wenn mehrfach wiederholt.
- **Autorentscheidung:** ausdrücklich bestätigte Entscheidung mit verfügbarer
  Quelle. Nicht aus einem allgemeinen „weiter“ oder einer anderen Freigabe ableiten.
- **Bestätigte Referenz:** für diesen Geltungsbereich nachweislich festgelegte
  Buchvorgabe. Abschnittsfreigabe und Sachbelegprüfung bleiben getrennte Angaben.

Diese Bezeichnungen gelten für den Bericht, sie sind keine neuen gespeicherten
Workflowzustände. Ein freigegebener Text kann Aussagen unzuverlässiger Figuren
enthalten. Bei Sachbüchern ist auch eine vom Autor bestätigte Aussage erst mit
passendem Nachweis extern belegt. Kein externer Faktencheck ohne entsprechenden
Auftrag; offene Belegfragen ausdrücklich benennen.

## Lesender Abgleich

Den vollständigen gewählten Umfang und die tatsächlich benötigten Referenzen
lesen. Zugängliche frühere Fassung für einen beauftragten Versionsvergleich
hinzunehmen. Nicht gelesene oder fehlende Teile nennen; bei Lücken keine
vollständige Buchprüfung behaupten.

Erfassen, soweit für spätere Abschnitte relevant:

- Eigenschaften, Zustand, Aufenthaltsort, Beziehungen und Wissensstand von Figuren;
- Ereignisse mit der Zeitangabe aus dem Text, ausdrücklich gesetzte Rückblenden
  und mögliche zeitliche Konflikte; ungenaue Angaben nicht zu Daten präzisieren;
- Ortsmerkmale, Regeln der erzählten Welt, wiederkehrende Gegenstände und Begriffe;
- Enthüllungen getrennt nach Leserwissen und Wissen jeder betroffenen Figur;
- bei Sachbüchern zentrale Aussagen, Definitionen, Zahlen und Belegfragen;
- wiederkehrende Kontinuitätsprobleme mit Belegen aus den betroffenen Einheiten.

Für jede relevante Beobachtung Vergleichsquelle und Fundstelle nennen. Unterschiede
als **neu beobachtet**, **verändert**, **möglicher Widerspruch** oder **unklar**
ordnen. Eine Zustandsänderung zwischen zwei Zeiten ist kein Widerspruch.
Eine nicht mehr erwähnte Eigenschaft ist nicht automatisch zurückgenommen.
Gleicher Name beweist keine Identität; Aliase und bestehende IDs prüfen.
Bei einem Konflikt beide Seiten belegen und deren Geltungsbereich und
Verbindlichkeit vergleichen. Widersprüche nie durch erfundene Übergänge,
Motive, neue Ereignisse oder stilles Überschreiben lösen. Bei unklarer
Verbindlichkeit die Autorenentscheidung offenlassen.

## Bericht

Zuerst Buch, Umfang, aktuelle Textfassung, Vergleichsstand und tatsächlich gelesene
Referenzen nennen. Beobachtungen und Konflikte kompakt aufführen:

| Gegenstand / vorhandene ID | Beobachtung mit Fundstelle | Vergleich mit Quelle | Herkunft / Verbindlichkeit | Einordnung und offene Entscheidung |
|---|---|---|---|---|
| Fiktive Figur `char-mara` | In Abschnitt 3.2 am Hafen | In Abschnitt 3.1 noch im Bahnhof | Zwei Textbeobachtungen | Ortswechsel, für sich kein Widerspruch; nur bei fehlender nötiger Reisezeit klären |

Bei Änderungen beide Fassungen belegen. Kurze Zitate mit Abschnitts-ID und Absatz
auffindbar halten. Wiederkehrende Probleme zusammenführen, vorhandene Hinweise
referenzieren. Ohne Konflikt nur „im gelesenen Umfang keine Abweichung gefunden“
melden. Offene Probleme nach den Schweregraden der Qualitätssicherung bewerten;
unzureichendes Material als **nicht vollständig prüfbar** ausweisen. Das Ergebnis
ändert keinen Status und ersetzt keine Autorenfreigabe.

Falls hilfreich, einen passenden **möglichen Zielort** für spätere Pflege nennen,
etwa Figurenunterlage oder Zeitleiste. Vorschlag, Autorenentscheidung und
Dateiänderung bleiben getrennt. Die Rücknahme eines Widerspruchsbefunds braucht
geprüfte Belege, nicht nur eine beruhigende Zusammenfassung.

## Abgrenzung zur bestehenden Analyse

Die [Analyse im Hintergrund](DATA-MODEL.md#analyse-im-hintergrund-123) hat bereits
Arten für Figuren, Schauplätze, Zeitleiste und Widersprüche. Ihre Läufe,
Zwischenspeicher und mögliche API-Kosten gehören zu diesem eigenen Arbeitsweg.
`analyze.py apply` kann Buchdateien ändern; bei `continuity` setzt die Übernahme
gewählte Marker ins Manuskript. Der lesende Abgleich startet weder diesen Lauf
noch dessen Übernahme. Ein gesonderter Pflege-/Speicherauftrag muss den konkreten
Umfang und den zulässigen bestehenden Schreibweg klären. Dieser Leitfaden
implementiert keine automatische Übernahme oder dauerhafte Faktenhistorie.

## Einbindung und Prüfgrenze

Der Repository-Skill `ghostwriter-buchgedaechtnis` lädt diese Anleitung auf einen
passenden Auftrag hin; Assistenten ohne native Skills verwenden die Verweise in
den Repository-Regeln. Programmupdates verteilen Anleitung und Skill. Tatsächliche
Aktivierung und Befolgung hängen vom Client ab. Es gibt keine globale Installation,
kein dauerhaftes Chatgedächtnis und keine automatische Überwachung nach jedem Kapitel.

Die eigenständig formulierte Methode greift Anregungen aus
[story-memory](https://github.com/haowjy/creative-writing-skills/tree/main/skills/story-memory)
auf. Kein fremdes Skillpaket wurde installiert.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
