# Anleitung: vom leeren Repository zur ersten Auflage

Diese Anleitung führt einmal durch den ganzen Weg. Du brauchst ein GitHub-Konto und einen KI-Chat-Assistenten, idealerweise mit GitHub-Verbindung und Internetrecherche. Git-Kenntnisse brauchst du nicht; alles Weitere läuft im Chat.

## 1. Repository anlegen

1. Öffne das [GhostWriter-Repository](https://github.com/ploeffler/GhostWriter) und wähle **Use this template → Create a new repository**.
2. Wähle einen Namen (z. B. `meine-buecher`) und **Private**: Ein Manuskript soll meist nicht öffentlich sein. (Ein Fork eines öffentlichen Repositorys ist immer öffentlich.)
3. Damit neue GhostWriter-Versionen automatisch ankommen, einmalig die Schritte unter [Updates → Eigenes Buch anlegen](UPDATES.md#eigenes-buch-anlegen) erledigen.

Dein Repository ist eine **Bibliothek**: Der Standard-Branch enthält das Programm, jedes Buch bekommt später einen eigenen Bereich (Branch `buch/<kurztitel>`). Du kannst also mehrere Bücher in einem Repository führen.

## 2. Chat mit GitHub verbinden

Verbinde deinen Chat-Assistenten mit GitHub und gib nur dieses Repository frei. Wie das in den gängigen Apps geht, steht in [Chat-Apps](CHAT-APPS.md) und [Connector einrichten](CONNECTOR-SETUP.md). Ohne GitHub-Verbindung geht es auch: Der Assistent gibt die Dateien dann im Chat aus, und du überträgst sie selbst.

## 3. Ersten Chat starten

Öffne einen neuen Chat und schicke den Link zu deinem Repository, z. B. `https://github.com/<du>/meine-buecher`. Der Assistent liest `START.md`, sagt dir, was er in dieser Umgebung kann (GitHub lesen und schreiben, Internetrecherche), und zeigt das **Bücherregal**. Ohne GitHub-Verbindung hängst du `START.md` an oder kopierst den Startprompt daraus ([Grundsätze → Zum Startprompt](GRUNDSAETZE.md#zum-startprompt)).

## 4. Neues Buch anlegen

Klicke im Bücherregal auf **Neues Buch** (oder schreib `Neues Buch: <Titel>`). Gib den Arbeitstitel ein, optional Kurztitel und Autor; das Formular zeigt dir den Namen des neuen Bereichs und warnt, wenn er schon vergeben ist. Nach **Anlegen** hat das Buch seinen eigenen Branch. Bilder dazu: [So sieht es aus](DIALOGE.md).

## 5. Einstiegsdialog bis zur Gliederung

Der Assistent führt dich durch die Fragen zu Thema, Ziel, Zielgruppe, Buchtyp, Sprache und Stil. Wo es feste Antwortmöglichkeiten gibt, erscheinen **Auswahlkarten** zum Anklicken; alles andere ist Gespräch. Gemeinsam entsteht die Gliederung: Kapitel, Abschnitte, ihre Ziele und Kurzbeschreibungen.

Bis du die Gliederung ausdrücklich freigibst, wird im Repository nichts weiter angelegt. Danach überträgt der Assistent die Struktur in **einem** Commit; dabei fragt er auch, ob gespeicherte Änderungen künftig sofort übernommen werden sollen (einfacher, wenn du allein schreibst).

## 6. Am Buch arbeiten

Die **Projektübersicht** zeigt alle Kapitel mit Status und Kosten; ein Klick öffnet die **Kapitelansicht** mit ihren Abschnitten, ein weiterer den **Abschnitt**.

- **Recherche:** je Abschnitt („Recherche sofort“) oder für ein ganzes Kapitel (Lupe neben Ziel und Kurzbeschreibung). Ergebnisse kommen mit Quellen und als Vorschlag.
- **Schreiben:** Ein Abschnitt wird erst geschrieben, wenn du das Schreiben freigibst. Den Text kannst du jederzeit selbst ändern.
- **Vor- und Nachspann:** Widmung, Prolog, Epilog und Danksagung legst du bei Bedarf an (`Vor- und Nachspann` bzw. `Widmung`, `Prolog` …). Sie werden freigegeben wie Abschnitte; Widmung und Danksagung schreibst du selbst.
- **Speichern und übernehmen:** Jede Änderung wird zuerst gesammelt; mit **Änderungen übernehmen** steht sie im Buch (oder sofort, wenn du das eingeschaltet hast).
- **Befehle** gehen immer: `Start`, `Übersicht`, `Kapitel 3`, `Abschnitt 3.2`, `Neues Kapitel`, `Probedruck`, `Auflage`, `Hilfe`.

## 7. Freigeben

- **Abschnitt freigeben**, wenn der Text steht. Offene Marker zeigt die Bestätigung als Warnung; in eine Auflage kommt der Abschnitt erst, wenn keine mehr offen sind.
- **Kapitel freigeben**, wenn alle seine Abschnitte freigegeben sind und das Kapitel zusammengeführt ist (Status „bereit zur Freigabe“).

Jede Freigabe ist eine eigene Bestätigung und wird protokolliert; zurücknehmen geht auch.

## 8. Probedruck

Im Formular **Neue Auflage** (oder mit `Probedruck`) entsteht ein PDF des aktuellen Stands zum Lesen oder Weitergeben, mit allen Kapiteln, offenen Markern hervorgehoben und dem Vermerk „Probedruck“. Es ist keine Auflage und ändert nichts.

## 9. Erste Auflage

Sind die gewünschten Kapitel freigegeben, öffne **Neue Auflage**: Name, Erscheinungsdatum, Formate (PDF, Word, E-Book) und Release Notes. Nach deiner Bestätigung baut GitHub die Auflage und legt sie als Release mit Tag ab. Veröffentlichte Auflagen bleiben unverändert; Korrekturen kommen in die nächste.

## 10. Später weiterarbeiten

- **Neuer Chat:** In jedem Browser genügt der Link zu deinem Repository; ein Link auf ein Buch (`…/tree/buch/<kurztitel>`) öffnet direkt dessen Übersicht, ein Link auf eine Kapitel- oder Abschnittsdatei direkt diese Stelle. Lange Chats lieber neu beginnen; der Stand liegt vollständig im Repository.
- **Weitere Bücher:** jederzeit über **Neues Buch** im Bücherregal.
- **Updates:** kommen automatisch, ändern nur Programmdateien und nie dein Buch ([Updates](UPDATES.md)).
- **Schon ein Buch aus v0.5?** Es läuft unverändert weiter. Wer mehrere Bücher möchte, wandelt das Repository einmal in eine Bibliothek um ([Updates → Von v0.5 auf v0.6](UPDATES.md#von-v05-auf-v06)).

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
