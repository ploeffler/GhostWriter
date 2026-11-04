# Grundsätze

GhostWriter ist ein Werkzeug für Menschen, die ein Buch schreiben. Es nimmt dir Ordnung, Suche und Buchhaltung ab, damit du dich auf das Schreiben konzentrieren kannst. Was im Buch steht, entscheidest du.

## Was GhostWriter tut

- **Ordnen:** Aus deiner Idee wird im Gespräch eine Gliederung aus Kapiteln und Abschnitten. Sie bleibt jederzeit änderbar.
- **Mitrecherchieren:** Zu jedem Abschnitt und Kapitel kann recherchiert werden, mit Quellenangaben, die du nachprüfen kannst.
- **Vorschlagen:** Ziele, Kurzbeschreibungen, Abschnitte und Textentwürfe kommen als Vorschläge. Übernommen wird nur, was du übernimmst.
- **Festhalten:** Jeder Stand liegt in deinem eigenen GitHub-Repository, mit Verlauf. Nichts geht verloren, jede Änderung ist nachvollziehbar.
- **Setzen:** Aus den freigegebenen Kapiteln entsteht ein Probedruck oder eine Auflage als PDF, Word-Datei und E-Book.

## Was GhostWriter nicht tut

- **Kein Buch auf Knopfdruck.** Ohne deine Entscheidungen, deine Erfahrung und deine Stimme entsteht kein Buch.
- **Keine Freigabe ohne dich.** Ein Abschnitt wird erst geschrieben, wenn du das Schreiben freigibst, und kommt erst ins Buch, wenn du ihn freigibst. Ein Kapitel erst nach deiner Kapitelfreigabe, eine Auflage erst nach deiner Bestätigung.
- **Nichts Erfundenes als Tatsache.** Unsichere Aussagen werden markiert (`[QUELLE PRÜFEN …]` und ähnliche Marker); solange ein Marker offen ist, kann ein Abschnitt nicht in eine Auflage.
- **Keine stillen Änderungen.** Was gespeichert wird, siehst du vorher; übernommen wird erst nach deiner Bestätigung (außer du schaltest das für dein Repository bewusst ein).
- **Keine Bindung an einen Anbieter.** Du wählst, welcher KI-Dienst recherchiert, schreibt oder prüft, auch mehrere nebeneinander.

## Projektregeln

Die globalen KI-Einstellungen stehen in `ghostwriter.yml` und gelten für Recherche, Brainstorming, Schreiben, Überarbeiten und Faktencheck. Sie lassen sich nicht stillschweigend abschwächen:

| Regel | Wert | Bedeutung |
|---|---|---|
| Halluzinationsschutz | `strict` | nichts erfinden; Wissenslücken offen sagen |
| Quellen | `required` | Aussagen mit tatsächlich geprüften Quellen belegen |
| Unsicherheiten | `explicit` | unsichere Stellen sichtbar markieren |
| Kreativität | `balanced` | Beispiele und Bilder ja, aber keine verfälschten Fakten |
| Internetrecherche | `research` | bei Recherchen aktiv suchen; ohne Suche das ausdrücklich sagen |

Welcher KI-Dienst welche Aufgabe übernimmt, ist je Buch wählbar (`ghostwriter.yml` → `ai_providers`, Formular „KI-Dienste“). Die möglichen Dienste stehen in [`providers.yml`](../providers.yml) und [PROVIDERS.md](PROVIDERS.md); wie man sie nutzt, in [DIENSTE-NUTZEN.md](DIENSTE-NUTZEN.md).

## Bilder und visuelle Referenzen

Bilder gehören zum Buchmaterial und können jederzeit nachträglich hochgeladen werden. Sie lassen sich beispielsweise einer Person, einem Ort, einem Gegenstand, einem Kapitel oder einem Abschnitt zuordnen.

Dabei wird unterschieden zwischen:
- **Buchbild:** Das Bild soll im Buch bzw. in einer späteren Ausgabe erscheinen.
- **Erstellungsreferenz:** Das Bild soll bei späteren Bild-Erstellungen als visuelle Vorlage berücksichtigt werden.
- **Beides:** Das Bild wird gespeichert und zusätzlich als Referenz im Erstellungspfad verwendet.

Das Hochladen allein aktiviert keine Referenzfunktion. Die Autorin oder der Autor entscheidet ausdrücklich, ob und wofür ein Bild als Referenz dienen soll. Herkunft, Urheber und bekannte Nutzungsrechte werden mit dem Bild dokumentiert. Nur dauerhaft gespeicherte und ausdrücklich übernommene Bilder können zuverlässig in späteren Ausgaben verwendet werden.

## Grundprinzip

**Buch → Kapitel → Abschnitte → Recherche- und Brainstormingläufe → Manuskript → Abschnittsfreigabe → Kapitelzusammenführung → Kapitelfreigabe → Auflage.**

- Ein Abschnitt ist die kleinste Einheit für Recherche und Schreiben. Jedes Kapitel hat mindestens einen und beliebig viele Abschnitte.
- Kapitel und Abschnitte lassen sich jederzeit ergänzen, umbenennen und neu ordnen; ihre internen Kennungen bleiben stabil.
- Ein Kapitel kann erst zusammengeführt und freigegeben werden, wenn alle seine Abschnitte freigegeben sind.
- Mehrere Bücher können in einem Repository liegen, jedes auf einem eigenen Branch (Bibliothek, [DATA-MODEL.md](DATA-MODEL.md)).

## Zum Startprompt

Ein Link auf `START.md` in einem Chat lädt deren Inhalt nicht automatisch. Mit einer GitHub-Verbindung liest der Assistent die Datei selbst, sobald du den Link zu deinem Repository schickst; ohne Verbindung hängst du `START.md` an oder kopierst den Startprompt aus der Datei. Eine eigene GhostWriter-Schnittstelle, die das übernimmt, ist für später geplant.

## KI im Buch

GhostWriter wurde mit Unterstützung von Claude (Anthropic) entwickelt; dieser Hinweis steht in der Dokumentation, nie in deinem Buch. Ob und wie dein Buch die Mitarbeit von KI erwähnt, entscheidest du (geplant: eigene Angabe im Buch, #78).

## Unterlagen

- [Anleitung](ANLEITUNG.md): Schritt für Schritt vom leeren Repository zur ersten Auflage
- [So sieht es aus](DIALOGE.md): die Dialoge im Chat
- [Qualitätssicherung](QUALITAETSSICHERUNG.md): allgemeine redaktionelle Prüfung und individuelles Buchprofil
- [START.md](../START.md): verbindliche Arbeitsanweisung für den Assistenten
- [Automatische Updates](UPDATES.md), auch „Von v0.5 auf v0.6“
- [KI-Dienste nutzen](DIENSTE-NUTZEN.md) · [KI-Anbieter](PROVIDERS.md) · [Chat-Apps](CHAT-APPS.md) · [Connector einrichten](CONNECTOR-SETUP.md)
- [Datei- und Statusmodell](DATA-MODEL.md) · [Architektur](ARCHITECTURE.md) · [Workflow-Modell](WORKFLOW-MODEL.md) · [Integration](INTEGRATION.md) · [Buchkontext](CONTEXT.md)
- [Produktclip](../media/produktclip/README.md)

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
