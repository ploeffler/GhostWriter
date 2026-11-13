# Anleitung: vom leeren Repository zur ersten Auflage

Deutsch · [English](USER-GUIDE.en.md)

Diese Anleitung führt einmal durch den ganzen Weg. Du brauchst ein GitHub-Konto und einen KI-Chat-Assistenten, idealerweise mit GitHub-Verbindung und Internetrecherche. Git, die Versionsverwaltung aus der Softwareentwicklung, sichert die gespeicherten Buchstände und macht Änderungen vergleichbar und wiederherstellbar. Die Bedienung läuft im Chat; Git-Kenntnisse sind dafür nicht erforderlich.

Die drei grafischen Übersichten haben eigene Seiten:

- [Buchablauf](BUCHABLAUF.md): von **Neues Buch** über den wiederkehrenden Kapitelkreis zur fertigen Auflage.
- [Erstellungskreislauf](ERSTELLUNGSKREISLAUF.md): einen Abschnitt mit Recherche, Brainstorming, neuen Eingaben und Überarbeitungen entwickeln.
- [Speichern, Übernehmen und Freigeben](SPEICHERN.md): Buchänderungen und Gesprächssicherung, ihre Zustände und getrennten Bestätigungen.

**Für textorientierte Bücher, nicht für Bildbände oder Fotobücher:** Eine Szene entspricht einem Abschnitt; pro Abschnitt höchstens ein Medium. Die geplanten Positionen, Textumfluss und Größenwahl erklärt [Medien im Abschnitt](MEDIENPLATZIERUNG.md).

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

Bis du die Gliederung ausdrücklich freigibst, werden keine weiteren Buchdateien angelegt. Eine ausdrücklich beauftragte Sitzungssicherung wird getrennt vom Manuskript gespeichert. Danach überträgt der Assistent die Struktur in **einem** Commit; dabei fragt er auch, ob gespeicherte Änderungen künftig sofort übernommen werden sollen (einfacher, wenn du allein schreibst).

## 6. Am Buch arbeiten

Die **Projektübersicht** zeigt alle Kapitel mit Status und Kosten; ein Klick öffnet die **Kapitelansicht** mit ihren Abschnitten, ein weiterer den **Abschnitt**.

Die Arbeit ist ein [Erstellungskreislauf](ERSTELLUNGSKREISLAUF.md): Du kannst jederzeit neue Ideen, Vorgaben und Material einbringen. Je nach Inhalt geht es zurück zu Recherche, Brainstorming oder Überarbeitung. Nach den Abschnittsfreigaben folgt die Prüfung und Freigabe des ganzen Kapitels; für weitere Kapitel wiederholt sich dieser [Kapitelkreis](BUCHABLAUF.md).

- **Recherche:** je Abschnitt („Recherche sofort“) oder für ein ganzes Kapitel (Lupe neben Ziel und Kurzbeschreibung). Ergebnisse kommen mit Quellen und als Vorschlag.
- **Schreiben:** Ein Abschnitt wird erst geschrieben, wenn du das Schreiben freigibst. Bereits freigegebener Text bleibt geschützt: vor einer Änderung die Abschnittsfreigabe ausdrücklich zurücknehmen und eine neue Schreibfreigabe erteilen.
- **Vor- und Nachspann:** Widmung, Vorwort, Prolog, Epilog, Nachwort, Glossar und Danksagung legst du bei Bedarf an (`Vor- und Nachspann` bzw. `Widmung`, `Glossar` …). Sie werden freigegeben wie Abschnitte; Widmung und Danksagung schreibst du selbst. Ins Glossar kommen Begriffe einzeln (`+ Begriff: Erklärung`), im Buch alphabetisch.
- **KI-Angabe:** Ob im Buch steht, wie du KI genutzt hast, legst du selbst fest (`KI-Angabe`). GhostWriter schlägt einen Satz aus den tatsächlichen Läufen vor. Bestätigst du den angezeigten Wortlaut eindeutig im Chat oder im Formular mit **OK**, speichert der Assistent ihn anschließend unverändert über `scripts/ai_disclosure.py set --text "…"` in `ghostwriter.yml` und committet die Änderung als **KI-Angabe geändert**. Erst dieser erfolgreiche Speicherschritt protokolliert die Bestätigung im Projekt; ein zusätzlicher Eintrag in `approvals.yml` ist nicht nötig. Ändern sich Modus oder Dienste-Nennung, muss der Wortlaut erneut bestätigt werden.
- **Ausgabe:** Wie Auflagen aussehen (Ränder, Schrift, Zeilenabstand, Kolumnentitel, Initialen, Formate, ISBN und Verlag im Impressum), stellst du im Formular `Ausgabe` ein; der nächste Probedruck zeigt es. Für den Druck gibt es dort auch das Profil deines Anbieters (KDP, BoD) und den **Umschlag** mit Rückenbreite, Beschnitt, Klappentext und ISBN-Strichcode; das EPUB bekommt dessen Vorderseite als Cover.
- **Speichern und übernehmen:** Jede Änderung wird zuerst gesammelt; mit **Buchänderungen übernehmen** steht sie im Buch (oder sofort, wenn du das eingeschaltet hast).
- **Befehle** gehen immer: `Start`, `Übersicht`, `Kapitel 3`, `Abschnitt 3.2`, `Neues Kapitel`, `Probedruck`, `Auflage`, `Hilfe`.

### Änderungspakete schnüren und übernehmen

Der [grafische Speicherablauf](SPEICHERN.md) zeigt die zwei Wege und die Zustände **vorbereitet**, **gespeichert**, **übernommen** und **inhaltlich freigegeben**. Sie bedeuten jeweils etwas anderes.

Zusammengehörige Änderungen werden zu einem **Änderungspaket** gebündelt. „Schnüren“ heißt, die Ergebnisse zu ordnen und dauerhaft als gemeinsames Paket zu speichern. „Übernehmen“ heißt, das geprüfte Paket in den vorgesehenen Projektstand einzufügen. Technisch heißen diese Schritte Pull Request (PR) und Merge; in Chat-Ausgaben verwenden wir Änderungspaket und übernehmen.

Für Gesprächsarbeit schreibst du **Session sichern**: Recherche, Brainstorming, Entscheidungen, Entwürfe und offene Punkte werden mit einem Änderungsschritt je geändertem Themengebiet in einem gemeinsamen Paket gesichert. Nach Abschluss des Dialogs über offene Punkte eines Abschnitts geschieht diese Sicherung automatisch. **Session laden** liest den gesicherten Gesprächsstand; **Session übernehmen** prüft das Paket, analysiert bei Fehlern die Ursache, versucht eine sichere technische Reparatur und übernimmt nach erneuter erfolgreicher Prüfung. Ein offenes Paket ist bereits gespeichert, aber noch nicht übernommen. Weder Speichern noch Übernehmen erteilen eine Text- oder Kapitelfreigabe.

Mit **Hilfe**, **Hilfe Befehle**, **Hilfe Änderungspakete** und **Hilfe Session** bekommst du passende Befehle und Beispielprompts. [Befehlsübersicht und Begriffe](HILFE.md) · [Sicherung und Übernahme im Detail](SESSION-SICHERUNG.md).

## 7. Freigeben

- **Abschnitt freigeben**, wenn der Text steht. Offene Marker zeigt die Bestätigung als Warnung; in eine Auflage kommt der Abschnitt erst, wenn keine mehr offen sind.
- **Kapitel freigeben**, wenn alle seine Abschnitte freigegeben sind und das Kapitel zusammengeführt ist (Status „bereit zur Freigabe“).

Jede Freigabe ist eine eigene Bestätigung und wird protokolliert; zurücknehmen geht auch.

## 8. Probedruck

Im Formular **Neue Auflage** (oder mit `Probedruck`) entsteht ein PDF des aktuellen Stands zum Lesen oder Weitergeben, mit allen Kapiteln, offenen Markern hervorgehoben und dem Vermerk „Probedruck“. Es ist keine Auflage und ändert nichts.

Enthalten ist der übernommene Buchstand. Noch offene Änderungen zuerst übernehmen, wenn sie im Probedruck erscheinen sollen.

**Lesefassung:** Öffnest du ein Kapitel oder einen Abschnitt, legt der Assistent den Text als Datei daneben, in Claude in der Seitenansicht. So liest du mit, während du im Chat änderst und freigibst; nach jeder Änderung kommt die Datei neu. Sie zeigt auch nicht freigegebenen Text mit Stand und hebt offene Marker hervor. `Lesefassung aus` schaltet sie ab, `Lesefassung an` wieder ein. In ChatGPT und Open WebUI entsteht sie über die Action „Manuskript ausgeben“ (Format `md`) und muss nach Änderungen neu gestartet werden; dieser Weg ist noch nicht praktisch geprüft.

**Manuskript ausgeben:** Mit `Manuskript ausgeben` (oder `Manuskript ausgeben Kapitel 3` für ein Kapitel) entsteht ein PDF des Arbeitsstands, das du direkt im Chat herunterladen kannst. Abschnitte mit Text stehen darin wie im Probedruck. Abschnitte ohne Text erscheinen als Kasten „Geplant“: Ziel und Inhalt in Stichworten, was schon erledigt ist (Recherche, Brainstorming) und was noch offen ist. Die Stichworte kommen unverändert aus deinen Angaben; die KI schreibt nichts dazu. Vorn steht eine Übersicht, wie viele Abschnitte Text haben und wie viele noch geplant sind. Kann dein Chat keine Dateien übergeben, bekommst du stattdessen den Link zum Download auf GitHub (14 Tage).

## 9. Erste Auflage

Sind die gewünschten Kapitel freigegeben, öffne **Neue Auflage**: Name, Erscheinungsdatum, Formate (PDF, Word, E-Book) und Release Notes. Mindestens ein Kapitel muss freigegeben sein; die enthaltenen Abschnitte müssen ebenfalls freigegeben und frei von offenen Markern sein. Offene Buchänderungen zuerst übernehmen.

Der Assistent zeigt die Release Notes zur Freigabe und bereitet ein eigenes Änderungspaket für die Auflage vor. Dessen Übernahme bestätigst du ausdrücklich, auch bei eingeschaltetem „sofort übernehmen“. Erst danach baut GitHub die Dateien und veröffentlicht das Release mit Tag. Ein fehlgeschlagener Aufbau ist noch keine fertige Auflage. Veröffentlichte Auflagen bleiben unverändert; Korrekturen kommen in die nächste. Den Gesamtweg zeigt der [Buchablauf](BUCHABLAUF.md).

## 10. Später weiterarbeiten

Den gesamten redaktionellen Kreislauf und die Git-Wege – einschließlich der Arbeit am PC mit oder ohne lokalem Clone – zeigt [Buchworkflow und Git-Wege](BUCH-WORKFLOW.md).

- **Neuer Chat:** In jedem Browser genügt der Link zu deinem Repository; ein Link auf ein Buch (`…/tree/buch/<kurztitel>`) öffnet direkt dessen Übersicht, ein Link auf eine Kapitel- oder Abschnittsdatei direkt diese Stelle. Lange Chats lieber neu beginnen; der gespeicherte Stand liegt im Repository.
- **Client wechseln:** Repository, ausgewähltes Buch und offene Änderungen gegen GitHub neu prüfen lassen. Ein alter Chat oder lokaler Stand ist kein Nachweis für den aktuellen Buchstand. Nicht gespeicherte Eingaben vor dem Wechsel sichern. Ein verbesserter automatischer Abgleich ist [geplant](WORKFLOW-MODEL.md#standabgleich-zwischen-clients-geplant).
- **Weitere Bücher:** jederzeit über **Neues Buch** im Bücherregal.
- **Profil:** Mit dem Befehl `Profil` hältst du fest, mit welchem Git-Benutzer der Assistent committet, welcher Autorenname vorbelegt ist und wie deine Standard-Erzählstimme klingt. Daraus entsteht ein Skill, den Claude beim nächsten Öffnen des Repositorys von selbst lädt; im Repository ändert er nur `assistant.yml` und `.claude/skills/` ([Chat-Apps](CHAT-APPS.md#automatisch-geladene-hinweise-136)).
- **Updates:** kommen automatisch, ändern nur Programmdateien und nie dein Buch ([Updates](UPDATES.md)).
- **Schon ein Buch aus v0.5?** Es läuft unverändert weiter. Wer mehrere Bücher möchte, wandelt das Repository einmal in eine Bibliothek um ([Updates → Von v0.5 auf v0.6](UPDATES.md#von-v05-auf-v06)).

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
