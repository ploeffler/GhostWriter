# Anleitung: vom leeren Repository zur ersten Auflage

Deutsch · [English](USER-GUIDE.en.md)

Diese Anleitung führt einmal durch den ganzen Weg. Du brauchst ein GitHub-Konto und einen KI-Chat-Assistenten, idealerweise mit GitHub-Verbindung und Internetrecherche. Git, die Versionsverwaltung aus der Softwareentwicklung, sichert die gespeicherten Buchstände und macht Änderungen vergleichbar und wiederherstellbar. Die Bedienung läuft im Chat; Git-Kenntnisse sind dafür nicht erforderlich.

Die drei grafischen Übersichten haben eigene Seiten:

- [Buchablauf](BUCHABLAUF.md): von **Neues Buch** über den wiederkehrenden Kapitelkreis zur fertigen Auflage.
- [Erstellungskreislauf](ERSTELLUNGSKREISLAUF.md): einen Abschnitt mit Recherche, Brainstorming, neuen Eingaben und Überarbeitungen entwickeln.
- [Speichern, Übernehmen und Abschließen](SPEICHERN.md): Buchänderungen und Gesprächssicherung, ihre Zustände und getrennten Bestätigungen.

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

Die Arbeit ist ein [Erstellungskreislauf](ERSTELLUNGSKREISLAUF.md): Du kannst jederzeit neue Ideen, Vorgaben und Material einbringen. Je nach Inhalt geht es zurück zu Recherche, Brainstorming oder Überarbeitung. Sind die Abschnitte abgeschlossen, folgen Prüfung und Abschluss des ganzen Kapitels; für weitere Kapitel wiederholt sich dieser [Kapitelkreis](BUCHABLAUF.md).

- **Recherche:** je Abschnitt („Recherche sofort“) oder für ein ganzes Kapitel (Lupe neben Ziel und Kurzbeschreibung). Ergebnisse kommen mit Quellen und als Vorschlag.
- **Figurengespräch:** Mit `Figurengespräch <Name>` sprichst du im Chat mit einer deiner Figuren. Der Assistent antwortet in ihrer Rolle, mit ihrer Sprechweise, ihren Eigenschaften und Beziehungen aus dem Figurenprofil. Was über Profil und Text hinausgeht, ist erfunden und kein Buchwissen. Während des Gesprächs wird nichts gespeichert. Mit `Gespräch beenden` verlässt der Assistent die Rolle und zeigt, was neu war, etwa eine Eigenschaft oder ein Stück Vorgeschichte; ins Figurenprofil kommt nur, was du auswählst, ins Manuskript nichts. Die Figur kennt den bisherigen Buchstand; eine genaue Begrenzung auf eine Stelle im Buch ist geplant (#430), eine eigene Gesprächsansicht für v1.5 (#431).
- **Als Figur sprechen:** Mit `Als <Name> sprechen` geht es umgekehrt: Du sprichst als die Figur, und der Assistent antwortet als Gesprächspartner. Bei Biografien und Familienbüchern kann sich auch die Person selbst hinsetzen und erzählen, etwa ein Elternteil, das mit Computern nichts anfangen kann. Vorher legst du fest, woraus der Assistent antwortet: **nur Buchwissen**, **nur Recherche/Hintergrund** (mit Quellen) oder **Buch + Recherche**. Kurz geht das mit `Als Vilmos sprechen: Buch + Recherche`. Spricht die Person selbst, fragt der Assistent dich vorher, ob sie einverstanden ist, dass ihre Aussagen ins Buchprojekt kommen, und ob nach jeder Antwort still gesichert werden soll. Am besten schaltest du den Sprachmodus der Chat-App ein. Die Person sieht dann nur das Gespräch: keine Befehle, keine Fachbegriffe, keine Meldungen. Was nicht zum Buch passt, wird nicht korrigiert; der Assistent fragt höchstens freundlich nach. Nach dem Ende (`Gespräch beenden` oder „danke, das reicht“) bekommst du die Auswertung: das Gespräch sichern, Neues für das Figurenprofil, Einträge für die Chronologie (Belegstand „Angabe“, mit dem Gespräch als Quelle) und die Widersprüche. Gespeichert wird nur, was du auswählst, ins Manuskript nichts.
- **Zeitleiste:** Mit `Zeitleiste` siehst du die Chronologie deines Buchs: was wann geschah, mit Quelle und Belegstand (belegt, Angabe, unsicher, Romanfreiheit), auch bevor Text da ist. Der Assistent schlägt Einträge aus Figuren, Orten, Recherche und gespeicherten Gesprächen vor; gespeichert wird nur, was du auswählst. Oben steht, wo die Daten nicht zusammenpassen, etwa zwei Daten für dasselbe Ereignis oder Lebensabschnitte, die sich überschneiden. Die Grafik zeigt je Figur eine Spur mit Lebensabschnitten und Ereignissen auf einer gemeinsamen Zeitachse, Farbe für den Ort, Form für den Belegstand; mit „von“ und „bis“ oder einem Klick auf eine Jahreszahl siehst du dichte Zeiträume genauer. Den Knopf dafür findest du auch in der Projektübersicht. Verknüpfst du eine Stelle der Text-Zeitleiste mit einem Eintrag, meldet GhostWriter, wenn Jahr oder Kapitel im Text nicht dazu passen. Die Analyse „Chronologie“ liest deine Unterlagen (Figuren, Orte, Quellen, Recherche, deine eigenen Beiträge in gesicherten Gesprächen), nie das Manuskript, und schlägt Einträge mit Zitat vor; ein Datum nur, wenn es dasteht, „belegt“ nur aus Quellen und Recherche. Für einen Roman ohne Kalenderjahr zählt die Chronologie in Tagen ab einem Bezugstag („Tag −3“, „Tag 0, 6:42“), ohne ein Jahr zu erfinden; eine vorhandene Tabelle in `story/chronologie.md` kann GhostWriter als Vorschlag einlesen. Zum Ausdrucken oder Weitergeben gibt es die Action „Zeitleiste ausgeben“: Sie legt die Zeitleiste als HTML, PDF und PNG unter `story/` ab; ins Buch kommt sie nie.
- **Schreiben:** Ein Abschnitt wird erst geschrieben, wenn du **Schreiben erlaubst**. Ein **abgeschlossener** Abschnitt ist gesperrt: Für eine Änderung öffnest du ihn ausdrücklich **wieder** und erlaubst das Schreiben erneut.
- **Vor- und Nachspann:** Widmung, Vorwort, Prolog, Epilog, Nachwort, Glossar und Danksagung legst du bei Bedarf an (`Vor- und Nachspann` bzw. `Widmung`, `Glossar` …). Sie werden abgeschlossen wie Abschnitte; Widmung und Danksagung schreibst du selbst. Ins Glossar kommen Begriffe einzeln (`+ Begriff: Erklärung`), im Buch alphabetisch.
- **KI-Angabe:** In jedem Buch steht als Mindestangabe der Satz „Bei der Entstehung dieses Buchs wurden Funktionen einer KI genutzt, etwa für Rechtschreibung, Grammatik, Zeichensetzung und Quellenrecherche. *Autor* hat alle Inhalte geprüft und trägt die Verantwortung für den Text.“ Er braucht keine Bestätigung; die Aufzählung kannst du anpassen. Dazu gehört verpflichtend das Kennzeichen „KI-unterstützt“ (bei englischen Büchern „AI assisted“) als kleines Logo bei der Angabe, in allen Formaten; es lässt sich nicht abwählen. Ob darüber hinaus etwas im Buch steht, legst du selbst fest (`KI-Angabe`). GhostWriter schlägt dafür einen Satz aus den tatsächlichen Läufen vor. Bestätigst du den angezeigten Wortlaut eindeutig im Chat oder im Formular mit **OK**, speichert der Assistent ihn anschließend unverändert über `scripts/ai_disclosure.py set --text "…"` in `ghostwriter.yml` und committet die Änderung als **KI-Angabe geändert**. Erst dieser erfolgreiche Speicherschritt protokolliert die Bestätigung im Projekt; ein zusätzlicher Eintrag in `approvals.yml` ist nicht nötig. Ändern sich Modus oder Dienste-Nennung, muss der Wortlaut erneut bestätigt werden.
- **Ausgabe:** Wie Auflagen aussehen (Ränder, Schrift, Zeilenabstand, Kolumnentitel, Initialen, Formate, ISBN und Verlag im Impressum), stellst du im Formular `Ausgabe` ein; der nächste Probedruck zeigt es. Für den Druck gibt es dort auch das Profil deines Anbieters (KDP, BoD) und den **Umschlag** mit Rückenbreite, Beschnitt, Klappentext und ISBN-Strichcode; das EPUB bekommt dessen Vorderseite als Cover. Der Probedruck zeigt die Vorderseite als erste Seite, auf Wunsch auch jede Auflage (Einstellung „Vorderseite im PDF“). Wer selbst druckt, wählt das Format **Broschüre**: Das PDF ordnet die Seiten so an, dass du die Blätter beidseitig (Wenden an der kurzen Kante) druckst, aufeinanderlegst und in der Mitte faltest – bei Seitenformat A5 entsteht so aus A4-Blättern ein A5-Heft. Der Druckertreiber braucht dafür keine Broschürenfunktion.
- **Speichern und übernehmen:** Jede Änderung wird zuerst gesammelt; mit **Buchänderungen übernehmen** steht sie im Buch (oder sofort, wenn du das eingeschaltet hast).
- **Befehle** gehen immer: `Start`, `Übersicht`, `Kapitel 3`, `Abschnitt 3.2`, `Neues Kapitel`, `Probedruck`, `Auflage`, `Hilfe`.

### Änderungspakete schnüren und übernehmen

Der [grafische Speicherablauf](SPEICHERN.md) zeigt die zwei Wege und die Zustände **vorbereitet**, **gespeichert**, **übernommen** und **abgeschlossen** (inhaltlich bestätigt). Sie bedeuten jeweils etwas anderes.

Zusammengehörige Änderungen werden zu einem **Änderungspaket** gebündelt. „Schnüren“ heißt, die Ergebnisse zu ordnen und dauerhaft als gemeinsames Paket zu speichern. „Übernehmen“ heißt, das geprüfte Paket in den vorgesehenen Projektstand einzufügen. Technisch heißen diese Schritte Pull Request (PR) und Merge; in Chat-Ausgaben verwenden wir Änderungspaket und übernehmen.

Für Gesprächsarbeit schreibst du **Session sichern**: Recherche, Brainstorming, Entscheidungen, Entwürfe und offene Punkte werden mit einem Änderungsschritt je geändertem Themengebiet in einem gemeinsamen Paket gesichert. Nach Abschluss des Dialogs über offene Punkte eines Abschnitts geschieht diese Sicherung automatisch. **Session laden** liest den gesicherten Gesprächsstand; **Session übernehmen** prüft das Paket, analysiert bei Fehlern die Ursache, versucht eine sichere technische Reparatur und übernimmt nach erneuter erfolgreicher Prüfung. Ein offenes Paket ist bereits gespeichert, aber noch nicht übernommen. Weder Speichern noch Übernehmen erteilen eine Text- oder Kapitelfreigabe.

Mit **Hilfe**, **Hilfe Befehle**, **Hilfe Änderungspakete** und **Hilfe Session** bekommst du passende Befehle und Beispielprompts. [Befehlsübersicht und Begriffe](HILFE.md) · [Bedienglossar](BEDIENGLOSSAR.md) · [Sicherung und Übernahme im Detail](SESSION-SICHERUNG.md).

## 7. Abschließen

- **Abschnitt abschließen** (🔒), wenn der Text steht. Danach ist er gesperrt; für Änderungen **wieder öffnen**. Offene Marker zeigt die Bestätigung als Warnung; in eine Auflage kommt der Abschnitt erst, wenn keine mehr offen sind.
- **Kapitel abschließen**, wenn alle seine Abschnitte abgeschlossen sind und das Kapitel zusammengeführt ist (Status „bereit zum Abschluss“).

Jedes Abschließen und Wiederöffnen ist eine eigene Bestätigung und wird protokolliert. Früher hieß das „freigeben“ bzw. „Freigabe zurücknehmen“; die Kürzel `FA`, `FS`, `FK` gehen weiterhin.

## 8. Probedruck

Im Formular **Neue Auflage** (oder mit `Probedruck`) entsteht ein PDF des aktuellen Stands zum Lesen oder Weitergeben, mit allen Kapiteln, offenen Markern hervorgehoben und dem Vermerk „Probedruck“. Es ist keine Auflage und ändert nichts.

Der Vermerk steht auf jeder Seite in einer eigenen roten Zeile unter der Seitenzahl und auf der Titelseite. Wie er auf der Titelseite aussieht, wählst du in den Ausgabeoptionen unter **Kennzeichnung im Probedruck**: rote Zeile, roter Rahmen mit Datum und Stand, oder zusätzlich ein Wasserzeichen „PROBEDRUCK“ auf der Titelseite bzw. auf allen Seiten. Unter **Gestaltung der Titelseite** gibt es neben „klassisch“ die Varianten „mit Linien“, „modern“, „gesperrt“ und „mit Querband“. Im Formular zeigt ein kleines Vorschaubild unter jeder Auswahl, wie die Titelseite bzw. der Vermerk aussieht; in der Textfassung geht es mit `Gestaltung der Titelseite: mit Linien`. Die Gestaltung gilt für PDF, EPUB und DOCX: Im EPUB übernimmt die Titelseite Ausrichtung, Schrift, Linien bzw. Band; Titel, Untertitel und Autor stehen dort aber immer in dieser Reihenfolge, und das Lesegerät kann einiges davon überschreiben. Im DOCX bekommen Titel, Untertitel und Autor Ausrichtung, Schrift, Linien bzw. Band; eine eigene Titelseite mit Seitenumbruch gibt es dort nicht. Die Kennzeichnung im Probedruck (Rahmen, Wasserzeichen) gibt es nur im PDF.

Enthalten ist der übernommene Buchstand. Noch offene Änderungen zuerst übernehmen, wenn sie im Probedruck erscheinen sollen.

**Vorabfassung:** Ist ein Stand fertig genug, um ihn festzuhalten (etwa für Testleser), aber noch nicht die Auflage, sag `Vorabfassung`. Sie entsteht wie ein Probedruck, trägt aber den Vermerk „Vorabfassung 1“ (2, 3 …) und bleibt dauerhaft als Vorab-Release (Pre-Release) mit eigenem Tag im Repository liegen, statt nach 14 Tagen zu verschwinden. Die Auflagennummer ändert sich nicht. Die Nummern zählen über alle Auflagen weiter. Vor dem Anlegen fragt der Assistent nach, weil ein Tag und ein Release entstehen. Im Formular „Neue Auflage“ gibt es dafür auch den Knopf „Vorabfassung“ neben „Probedruck“: Der erste Klick zeigt, welcher Tag entsteht, erst der zweite legt die Vorabfassung an. Die Projektübersicht zeigt danach die letzte Vorabfassung mit Datum und Link zum Release neben der Auflage.

**Lesefassung:** Beim Öffnen eines Kapitels oder Abschnitts kommt der Text als Markdown-Datei neben die Chatansicht – auch in ChatGPT Work und Codex mit den tatsächlich verfügbaren Dateiwerkzeugen. In Codex wird das Dateipanel verwendet; „zur Anzeige vorgemerkt“ bestätigt noch keine geöffnete Ansicht. Der vollständige Text wird nicht zusätzlich in den Chat kopiert. Nach Änderungen wird dieselbe Datei aktualisiert, auch für noch nicht ins Manuskript gespeicherte Vorschläge; diese sind als solche gekennzeichnet und erteilen keine Freigabe. `Lesefassung aus/an` gilt nur für diesen Chat, unabhängig von „Darstellung: erweitert“. Ohne passende Vorschau erhältst du die Datei oder einen Link mit einem Hinweis auf die Grenze. Ohne Skriptausführung bleibt die Action „Manuskript ausgeben“ (Format `md`) für gespeicherte Arbeitsstände der Ersatzweg. Einzelheiten: [Chat-Apps](CHAT-APPS.md#lesefassung-neben-der-ansicht-289).

**Manuskript ausgeben:** Mit `Manuskript ausgeben` (oder `Manuskript ausgeben Kapitel 3` für ein Kapitel) entsteht ein PDF des Arbeitsstands, das du direkt im Chat herunterladen kannst. Abschnitte mit Text stehen darin wie im Probedruck. Abschnitte ohne Text erscheinen als Kasten „Geplant“: Ziel und Inhalt in Stichworten, was schon erledigt ist (Recherche, Brainstorming) und was noch offen ist. Die Stichworte kommen unverändert aus deinen Angaben; die KI schreibt nichts dazu. Vorn steht eine Übersicht, wie viele Abschnitte Text haben und wie viele noch geplant sind. Kann dein Chat keine Dateien übergeben, bekommst du stattdessen den Link zum Download auf GitHub (14 Tage).

## 9. Erste Auflage

Sind die gewünschten Kapitel abgeschlossen, öffne **Neue Auflage**: Name, Erscheinungsdatum, Formate (PDF, Word, E-Book) und Release Notes. Mindestens ein Kapitel muss abgeschlossen sein; die enthaltenen Abschnitte müssen ebenfalls abgeschlossen und frei von offenen Markern sein. Offene Buchänderungen zuerst übernehmen.

Der Assistent zeigt die Release Notes zur Freigabe und bereitet ein eigenes Änderungspaket für die Auflage vor. Dessen Übernahme bestätigst du ausdrücklich, auch bei eingeschaltetem „sofort übernehmen“. Erst danach baut GitHub die Dateien und veröffentlicht das Release mit Tag. Ein fehlgeschlagener Aufbau ist noch keine fertige Auflage. Veröffentlichte Auflagen bleiben unverändert; Korrekturen kommen in die nächste. Den Gesamtweg zeigt der [Buchablauf](BUCHABLAUF.md).

## 10. Später weiterarbeiten

Den gesamten redaktionellen Kreislauf und die Git-Wege – einschließlich der Arbeit am PC mit oder ohne lokalem Clone – zeigt [Buchworkflow und Git-Wege](BUCH-WORKFLOW.md).

- **Neuer Chat:** In jedem Browser genügt der Link zu deinem Repository; ein Link auf ein Buch (`…/tree/buch/<kurztitel>`) öffnet direkt dessen Übersicht, ein Link auf eine Kapitel- oder Abschnittsdatei direkt diese Stelle. Lange Chats lieber neu beginnen; der gespeicherte Stand liegt im Repository.
- **Client wechseln:** Repository, ausgewähltes Buch und offene Änderungen gegen GitHub neu prüfen lassen. Ein alter Chat oder lokaler Stand ist kein Nachweis für den aktuellen Buchstand. Nicht gespeicherte Eingaben vor dem Wechsel sichern. Ein verbesserter automatischer Abgleich ist [geplant](WORKFLOW-MODEL.md#standabgleich-zwischen-clients-geplant).
- **Weitere Bücher:** jederzeit über **Neues Buch** im Bücherregal.
- **Profil:** Mit dem Befehl `Profil` hältst du fest, mit welchem Git-Benutzer der Assistent committet, welcher Autorenname vorbelegt ist und wie deine Standard-Erzählstimme klingt. Daraus entsteht ein Skill, den Claude beim nächsten Öffnen des Repositorys von selbst lädt; im Repository ändert er nur `assistant.yml` und `.claude/skills/` ([Chat-Apps](CHAT-APPS.md#automatisch-geladene-hinweise-136)).
- **Updates:** kommen automatisch, ändern nur Programmdateien und nie dein Buch ([Updates](UPDATES.md)).
- **Mit anderen am Buch arbeiten (#455):** Lade weitere Personen in GitHub als Collaborators ein (Repository → Settings → Collaborators; Leser mit „Read“, Bearbeiter mit „Write“). Im Buch legst du in `ghostwriter.yml` unter `team` fest, wer Eigentümer, Bearbeiter oder Leser ist und welcher Bearbeiter abschließen darf (`approve: true`); mit `name` und `email` erscheinen die Commits einer Person unter ihrem Namen statt unter deinem. Der Assistent nennt jedem seine Rolle und bietet nur erlaubte Aktionen an. Die GitHub-Rechte bleiben die eigentliche Grenze: Wer „Write“ hat, kann Dateien auch selbst ändern. Wer das ausschließen will, richtet zusätzlich eine Regel mit Pflicht-Review ein (Settings → Rules). Eine Prüfung im Änderungspaket, die Abschlüsse durch Unberechtigte ablehnt, ist [geplant](https://github.com/ploeffler/GhostWriter/issues/455).
- **Schon ein Buch aus v0.5?** Es läuft unverändert weiter. Wer mehrere Bücher möchte, wandelt das Repository einmal in eine Bibliothek um ([Updates → Von v0.5 auf v0.6](UPDATES.md#von-v05-auf-v06)).

## Grafische Cover gestalten

Sage im Chat beispielsweise: „Übernimm das Cremeweiß oben aus dem Coverbild für Rücken und Rückseite. Setze Titel, Untertitel und Autor in den freien oberen Bereich.“ Der Assistent zeigt den Farbwert, die betroffenen Flächen und einen Einstellungsvorschlag. Prüfe die Vorschau mit den aktuellen Buchtexten; erst nach deinem Speicherauftrag werden die Einstellungen für dieses Buch übernommen. Bildanalyse und Vorschau allein speichern nichts. Ein grafischer Verschiebeeditor ist nicht enthalten; die Textbereiche werden im Chat mit Zahlen eingestellt.

Titel, Untertitel und Autor bleiben mit den Projektdaten verbunden. Je Textteil sind Position, Breite, maximale Höhe, Ausrichtung, Schriftgröße, Serifenschrift/serifenlose Schrift, Fettdruck, Farbe, Umbruch und Sichtbarkeit einstellbar. Maße gelten in Millimetern ab der linken oberen Schnittkante der Vorderseite, Schriftgrößen in Punkt. Der Sicherheitsrand beträgt 10 mm. Nicht angepasste Textteile verwenden weiter die ausgewählte Vorlage. Ohne neue Angaben bleiben `classic`, `modern` und `plain` erhalten.

Die Farbauswahl kann eine Stelle im Originalbild oder Vorschlagsfarben einschließlich der Bildecken verwenden. Koordinaten der Bildstelle liegen zwischen 0 und 1, ab links oben, **vor dem automatischen Bildbeschnitt**. Der sichtbare Hex-Farbwert lässt sich korrigieren. Farben können je Fläche gesetzt werden; vorhandene Farben anderer Flächen bleiben erhalten. Transparente Bildstellen werden für die Farbauswahl auf Weiß dargestellt.

**Bereits fertig beschriftetes Bild:** Wähle `image_mode: finished`. Dann erscheint auf der Vorderseite keine zusätzliche Beschriftung; Rücken und Rückseite bleiben separat gesetzt. `motif` ist die Vorgabe für ein unbeschriftetes Motiv. Das Originalbild wird in beiden Fällen unverändert aufbewahrt. Eine automatische Erkennung vorhandener Schrift findet nicht statt.

**Klappentext auf der Rückseite:** Mit `back_blurb_position` steht der Klappentext oben (`top`, Vorgabe), in der Mitte (`middle`) oder unten (`bottom`). Unten endet er 8 mm über Autorentext und Autorenbild; Strichcode und Preis bleiben unten rechts. Sage zum Beispiel: „Setz den Klappentext auf der Rückseite nach unten.“ Ein sehr langer Klappentext kann unten bis an den oberen Rand reichen; prüfe deshalb die Vorschau.

**Fertige Vorderseite als Datei** (#324): Liegt die Vorderseite schon fertig gestaltet vor, etwa als `cover/vorderseite.pdf`, trägst du sie als `cover.front` ein (PDF, JPG oder PNG, im Buchformat, gern mit Beschnitt). Sie kommt unverändert ins Buch, ohne zusätzlichen Titel: als erste Seite im PDF und als Cover im EPUB. Ohne `cover.front` nimmt GhostWriter die Covervorlage. Im Probedruck steht die Vorderseite vorn, gefolgt von einer Leerseite, damit die Titelseite rechts bleibt („nie“ schaltet das ab); für Auflagen stellst du „Vorderseite im PDF“ auf „im Probedruck und in Auflagen“ (`typesetting.pdf_cover: always`). Der Vermerk „Probedruck – nicht zur Veröffentlichung“ steht weiter auf den Innenseiten, nicht auf der Vorderseite. Passt das Seitenverhältnis nicht zum Buchformat, wird nichts verzerrt: Die Auflage bricht mit einem Hinweis ab, der Probedruck entsteht ohne Vorderseite. Druck-PDF, Broschüre und Umschlag bleiben unverändert.

**Vorschau und Grenzen:** Vorderseitenvorschau, Druckumschlag und EPUB-Cover verwenden denselben Satzweg. Das Bild wird proportional füllend zugeschnitten; prüfe freie Flächen deshalb in der tatsächlichen Vorschau. Zu hohe Textblöcke und nicht passende Wörter stoppen die Ausgabe statt unbemerkt über den Textbereich zu laufen. Ohne eigene Textbereiche brechen Titel, Untertitel und Autor der Vorlagen am Wortende um; ist ein einzelnes Wort breiter als die Vorderseite, wird seine Schrift so weit verkleinert, dass es passt, und die Ausgabe nennt die neue Größe (#326). Verkleinere dann die Schrift oder ändere den Bereich. Kontrast, Motivüberlagerungen und die Eignung des Bildausschnitts prüfst du visuell. Die Vorschau ist ein JPEG mit 150 dpi ohne Beschnitt; Druckausgabe ist ein PDF mit Beschnitt. Die Rückenbreite braucht weiterhin korrekte Buch-/Druckdaten. Vorschau und Hilfslinien ersetzen keine Druckfreigabe. DOCX und das normale Innenteil-PDF erhalten durch diese Einstellungen kein Cover.

### Lokale Werkzeuge für die Covergestaltung

Die allgemeinen Werkzeuge benötigen kein eigenes Buchskript. Farbauswahl benötigt Pillow; Satz benötigt XeLaTeX mit TikZ/TeX Gyre, Rastervorschau außerdem Poppler (`pdftoppm`). Die Coverdaten liegen in `ghostwriter.yml`; `project.title`, `project.subtitle` und `project.author` bleiben die Textquellen.

```sh
# Nur lesen: Farben vorschlagen oder eine Bildstelle abfragen
python scripts/cover_design.py BUCH colors
python scripts/cover_design.py BUCH colors --point 0.5 0.1
python scripts/cover_design.py BUCH show
# Erst nach Speicherauftrag: nur die genannten Flächen ändern
python scripts/cover_design.py BUCH set '{"panel_backgrounds":{"spine":"#EEDDCB","back":"#EEDDCB"}}'
# Ungespeicherten Vorschlag prüfen; Originaleinstellungen bleiben erhalten
python scripts/cover_design.py BUCH preview '{"panel_backgrounds":{"back":"#EEDDCB"}}' --pages 200 --out /tmp/cover-preview.pdf --front-jpg /tmp/cover-preview.jpg
```

Ein vollständiges Beispiel für die drei Textbereiche (A5) steht unten. Der Assistent kann diese Angaben über `cover_design.py BUCH set` als JSON-Patch übernehmen. `preview` prüft einen ungespeicherten JSON-Vorschlag im Speicher; Vorschauausgaben außerhalb des Originalbilds ablegen. Keine Programmdateien für ein einzelnes Buch ändern.

```yaml
cover:
  image: cover/motiv.png
  image_mode: motif
  panel_backgrounds:
    spine: '#EEDDCB'
    back: '#EEDDCB'
  text_boxes:
    title: {x: 12, y: 12, width: 124, height: 24, font_size: 24, color: '#312A24', align: center, bold: true}
    subtitle: {x: 12, y: 39, width: 124, height: 12, font_size: 13, color: '#312A24'}
    author: {x: 12, y: 55, width: 124, height: 12, font_size: 14, color: '#312A24'}
```

`visible: false` blendet einen Textteil aus. `font: serif` oder `sans` wählt die Schriftgruppe. `break_after: [2]` erzwingt nach dem zweiten Wort einen Umbruch; passt die Position nach einer Textänderung nicht mehr, stoppt die Ausgabe mit einem Hinweis. Sonst erfolgt der Umbruch anhand der Breite. `background_targets` begrenzt die Verwendung von `background` auf `front`, `spine` und/oder `back`; ausdrücklich gespeicherte `panel_backgrounds` haben Vorrang. Nicht ausgewählte Flächen ohne eigenen Farbwert verwenden die Standardfarbe. Das Bild überdeckt weiterhin die Vorderseitenfarbe. Ein JSON-Patch ändert nur genannte Felder; Textbereiche und Flächenfarben werden einzeln zusammengeführt. `null` entfernt eine individuelle Angabe, etwa `{"text_boxes":{"title":null}}` für die Rückkehr zur Vorlage.


---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
