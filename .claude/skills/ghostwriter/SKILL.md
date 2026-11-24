---
name: ghostwriter
description: Wiedereinstieg in ein GhostWriter-Repository (Buch oder Bibliothek) – Repository und Schreibzugriff prüfen, Git-Benutzer setzen, Darstellungsmodus festlegen, Bücherregal bzw. Projektübersicht zeigen, Fehler ans Hauptrepository melden. Bei jedem ersten Aufruf eines GhostWriter-Buch- oder Bibliotheks-Repositorys verwenden; gibt es einen persönlichen Skill für dieses Repository, gilt er zusätzlich. Nicht für Programmarbeit am Hauptrepository.
---

# GhostWriter: Wiedereinstieg

Kurzfassung von `START.md`, Abschnitt 0. Bei Abweichungen gilt `START.md`. Die allgemeine Skill-Fassung liegt in `ghostwriter-skills`. Lies `START.md`, `assistant.yml`, `docs/`, `templates/` und `scripts/` im jeweils ausgewählten Buch- oder Programmrepo. Persönliche Angaben gehören in `assistant.yml` und den daraus erzeugten Skill des Buch- oder Bibliotheksrepos.

**Skillauswahl (#261):** Zu Beginn einer Aufgabe in einem Satz nennen, welcher Skill verwendet wird (oder dass keiner passt). Passen mehrere, den spezifischeren nehmen: den persönlichen Skill dieses Repositorys (`assistant.yml` → `skill`) vor `ghostwriter`; für Programmarbeit am Hauptrepository nicht `ghostwriter`. Bei echter Mehrdeutigkeit einmal kurz fragen. Einen Skill, dessen Anleitung im Gespräch noch vorliegt, nicht erneut laden; nur neu laden, wenn sie nach dem Zusammenfassen des Verlaufs fehlt, und das dann kurz sagen. Details: `docs/CHAT-APPS.md`, „Skills auswählen“.

**Auswahlfragen im Gespräch:** Bei passenden Entscheidungen wenige verständliche Optionen und eine eigene Antwort anbieten; dazwischen frei sprechen. Keine Durchklickstrecke. Unterstützte Frageelemente bzw. vorhandene Karten nutzen, sonst Text. Details: `docs/QUALITAETSSICHERUNG.md`, „Gezielte Auswahlfragen im Gespräch“. Freigaben und Speicheraufträge bleiben eigene Schritte; eine anstehende Freigabe wird aber als eigene Auswahl angeboten („Abschnitt 3.2 freigeben“, „Noch ändern“, „Später“) statt als „sag …“-Satz zum Abtippen. Der Klick ist die ausdrückliche Bestätigung (`START.md`, „Freigaben“, „Freigabe im Chat“).

## 1. Repository feststellen

- `owner/repo` aus dem Link des Benutzers bzw. `git remote get-url origin`; das ist der Wert für `--repo` bei jedem Aufruf von `scripts/render_view.py`.
- Ist `upstream.repo` in `ghostwriter-manifest.yml` dieses Repository selbst, ist es das Programm-Repository (Entwicklung, kein Buch; siehe `CLAUDE.md`).
- Bibliothek oder Einzelbuch: Hat der Standard-Branch Kapitel (`structure.chapters` in `ghostwriter.yml`), ist er selbst das Buch; sonst sind die Bücher die Branches `buch/*` (`library.json`).

## 2. Einrichten und Schreibzugriff prüfen (ohne etwas zu ändern)

In einer Claude-Sitzung mit Repository-Werkzeugen:

1. Repository einbinden: `add_repo` mit `owner`, `repo` und `access: push`. Ohne diesen Schritt liefern die GitHub-Werkzeuge bei privaten Repositorys 404.
2. Flach klonen, großzügiges Timeout: `git clone --depth 1 https://github.com/<owner>/<repo> /home/claude/<repo>`, danach `register_repo_root`.

Vor dem ersten Commit der Sitzung, ohne Rückfrage:

```bash
gh api user --jq .login                                   # erwarteter Login (Profil: git.name)
gh api repos/<owner>/<repo> --jq .permissions.push        # muss true sein
git push --dry-run origin HEAD:refs/heads/zz-schreibtest  # muss „[new branch]“ melden, legt nichts an
```

- Ergebnis in einem Satz nennen („✓ Schreibzugriff als <login> auf <owner>/<repo> geprüft.“).
- Schlägt eine Prüfung fehl: in einem Satz sagen, welche (falscher Login, kein Push-Recht, Push abgelehnt), und nichts committen. Ohne Schreibzugriff gilt `START.md`, Abschnitt 7 (Dateien im Chat ausgeben).
- Ohne Klon reicht die GitHub-Verbindung des Chats für die Prüfung von `permissions.push`.

## 3. Git-Benutzer setzen

Commits sollen dem Benutzer zugeordnet sein, nicht dem Assistenten:

- Mit Profil (`assistant.yml` → `git.name`, `git.email`): `git config user.name "<name>"` und `git config user.email "<email>"` im Klon.
- Ohne Profil: den GitHub-Login des Benutzers und die Adresse `<id>+<login>@users.noreply.github.com` (aus `gh api user --jq '.id, .login'`) vorschlagen und erst nach einem Ja verwenden.

## 4. Persönlichen Skill und Profil laden

- Gibt es `assistant.yml`, den persönlichen Skill `.claude/skills/<skill>/SKILL.md` lesen (Name in `assistant.yml` → `skill`). Er enthält Autor und Standard-Erzählstimme.
- `python scripts/assistant.py . check` meldet, ob der Skill zum Profil passt; sonst `python scripts/assistant.py . skill` und als Commit vorschlagen.
- Fehlt `assistant.yml`: einmal anbieten, ein Profil anzulegen (`START.md`, „Assistenten-Profil“), nicht drängen.
- Der persönliche Skill hängt von Benutzer und Repository ab und lebt **nur im Repository**, nicht als Skill im Claude-Konto. Ist im Chat ein Konto-Skill mit demselben Namen (oder fast derselben Beschreibung) gelistet, gilt die Fassung im Repository; einmal darauf hinweisen und vorschlagen, die Kopie in den Claude-Einstellungen unter „Skills“ zu entfernen. Eigenes gehört in den Bereich „Eigene Ergänzungen“ des erzeugten Skills.

## 5. Darstellungsmodus festlegen

Zuerst die Bediensprache nach `START.md` bestimmen. Bei Englisch Text oder unterstützte native Chat-Elemente verwenden; die Widgets sind noch nicht vollständig übersetzt. Bei Deutsch: Claude zeigt das **Widget** mit `render_view.py` ohne `--text`; Text, wenn das Widget nicht erscheint oder der Benutzer ihn verlangt. Der Modus gilt für den ganzen Chat.

## 6. Darstellungsmodus für ChatGPT und andere Chat-Clients

Der Darstellungsmodus ist unabhängig vom Antwortmodus (einfach/erweitert) und gilt für den laufenden Chat, bis der Benutzer ihn ändert.

- **ChatGPT:** Wenn der Chat-Client native strukturierte Ausgaben unterstützt, Informationen passend als übersichtliche Karten/Abschnitte, Tabellen, Statuskennzeichnungen, Fortschrittsanzeigen, Diagramme oder – wenn inhaltlich sinnvoll – Bilder und interaktive Bedienelemente darstellen. Nur Elemente verwenden, die der jeweilige Client tatsächlich unterstützt. Keine HTML- oder Claude-Widget-Ausgabe als in ChatGPT funktionsfähig voraussetzen und keine bloß vorgetäuschte Interaktion erzeugen.
- **Claude:** Bei Deutsch das GhostWriter-Widget über `scripts/render_view.py` ohne `--text` verwenden; bei Englisch die Sprachregel oben beachten. Text verwenden, wenn das Widget nicht erscheint oder der Benutzer ihn verlangt.
- **Andere Clients oder unklare Unterstützung:** Auf eine klare, gut gegliederte Textdarstellung zurückfallen. Keine technische Darstellung erzwingen, die der Client nicht zuverlässig anzeigen kann.

Der Benutzer kann den Modus umschalten:
- **„Darstellung: einfach“**: knapper Text, nur notwendige Struktur.
- **„Darstellung: übersichtlich“**: Standard für ChatGPT; passende Karten, Tabellen und Statusanzeigen, ohne unnötige Dekoration.
- **„Darstellung: erweitert“**: ausführlichere strukturierte Darstellung und – sofern unterstützt und hilfreich – Diagramme oder interaktive Elemente.
- **„Nur Text“**: ausschließlich Text und Markdown, keine zusätzlichen strukturierten oder interaktiven Elemente.

Die Darstellungswahl gilt bis zur nächsten Änderung im laufenden Chat. Sie ist keine dauerhaft gespeicherte Projekteinstellung, sofern eine solche nicht ausdrücklich implementiert ist.

## 7. Verständliche Chat-Ausgaben und Antwortmodus

GhostWriter verwendet standardmäßig den **einfachen Modus**. Die Chat-Ausgaben richten sich an Autorinnen und Autoren, nicht an Git- oder Softwareentwickler.

Im einfachen Modus:

- Ergebnisse in klarer Alltagssprache und kurz zusammenfassen.
- Git-Begriffe wie Branch, Commit, SHA, Merge, Pull Request oder Issue vermeiden, sofern sie für die Entscheidung des Benutzers nicht nötig sind.
- Technische Vorgänge in ihrer Bedeutung erklären, zum Beispiel „Änderungen sind gespeichert“, „Bitte prüfe und bestätige diese Fassung“ oder „Die Übernahme ist noch ausstehend“.
- Nur die für den nächsten Schritt nötigen Informationen nennen.
- Wichtige Einschränkungen, fehlende Berechtigungen, Fehler und ausstehende Freigaben trotzdem ausdrücklich mitteilen. Vereinfachung darf nichts verschleiern.

Der Benutzer kann den Antwortmodus jederzeit im Chat umschalten:

- **„Erweiterte Antworten an“** oder **„Debugger-Modus an“**: technische Details, Repository- und Dateipfade, Branches, Commits, Prüfmeldungen, Fehlerursachen und Statusinformationen ausführlicher darstellen.
- **„Erweiterte Antworten aus“**, **„Debugger-Modus aus“** oder **„Einfacher Modus“**: wieder zur verständlichen, knappen Darstellung wechseln.

Der gewählte Modus gilt für den laufenden Chat, bis der Benutzer ihn ändert. Nicht behaupten, die Einstellung sei dauerhaft gespeichert, sofern dafür keine ausdrücklich vorhandene Projekteinstellung genutzt wird.

## 8. Kurzbefehle

Die folgenden einzelnen Chat-Befehle sind feste Abkürzungen. Sie gelten für das aktuell bearbeitete GhostWriter-Repository und den dort maßgeblichen Arbeits-Branch. Wenn die Zuordnung nicht eindeutig ist, vor der Aktion nachfragen.

### „Speichern“

- Alle seit dem letzten Speichern bzw. Commit im aktuellen Arbeitsauftrag entstandenen, zusammengehörigen Änderungen prüfen und zu **einem gemeinsamen Commit** bündeln.
- Den Commit mit einer aussagekräftigen, den Gesamtauftrag beschreibenden Nachricht erstellen und in das zugehörige Repository übertragen.
- Vorher sicherstellen, dass nur die zum aktuellen Auftrag gehörenden Änderungen enthalten sind; fremde oder nicht zuordenbare Änderungen nicht stillschweigend einschließen.
- Den richtigen Repository- und Ziel-Branch prüfen. Keine Änderungen auf einen anderen Branch oder in ein anderes Repository übertragen.
- Gibt es keine neuen Änderungen, mitteilen, dass nichts zu speichern ist. Bei unklarer Zuordnung oder einem Konflikt nachfragen, statt zu raten.
- Anschließend kurz bestätigen, was gespeichert wurde und in welchem Repository/Branch.

### „Zusammenführen“

- Den passenden offenen Pull Request des aktuellen Arbeitsauftrags ermitteln und dessen Ziel-Branch prüfen.
- Den Pull Request über GitHub **mergen** („Merge pull request“), sofern er offen und mergebar ist und die erforderlichen Prüfungen/Freigaben erfüllt sind.
- Gibt es mehrere passende Pull Requests oder ist der gemeinte Pull Request nicht eindeutig, zuerst nachfragen.
- Ist kein passender offener Pull Request vorhanden, keinen neuen Pull Request erstellen und nichts direkt in einen Branch übertragen; stattdessen den fehlenden Pull Request melden.
- Nach dem Merge Ergebnis und Ziel-Branch kurz bestätigen. Bei Merge-Konflikten oder nicht erfüllten Schutzregeln nicht erzwingen, sondern den Hinderungsgrund nennen.

## 8a. Navigation

`Start` · `Übersicht` · `Buchansicht <Buch>` · `Kapitel 3` · `Abschnitt 3.2` · `Hilfe`

Die vollständige Befehlsliste steht in `START.md`, Abschnitt 0, „Befehle“.

- **`Buchansicht <Buch>`:** Projektübersicht eines bestimmten Buchs, ohne Umweg über das Bücherregal. `<Buch>` ist Nummer, Kurztitel (`buch/<kurztitel>`) oder Titel. Das Buch ausschließlich aus `library.json` bzw. den Branches `buch/*` bestimmen (Kurztitel zuerst, dann Titel), nie über eine Suche in Repositories, Dateien oder Pull Requests. Passen mehrere oder keines, die Treffer aus `library.json` zur Auswahl zeigen. Ohne Angabe wie `Übersicht` (Einzelbuch) bzw. Bücherregal (Bibliothek).

## 9. Erste Ansicht

- Bibliothek: `library.json` vom Standard-Branch lesen und `python scripts/render_view.py . library --library library.json --repo <owner>/<repo>`; bei genau einem Buch direkt dessen Projektübersicht.
- Einzelbuch bzw. Link auf einen Buch-Branch: Projektübersicht nach `START.md`, Abschnitt 0, Schritte 1–8.

**Wissensstand (#369):** Vor der ersten inhaltlichen Antwort im Buch `python scripts/wissensstand.py .` intern lesen. Vor neuen Figuren, Orten, Begriffen und Vorschlägen damit abgleichen; Bekanntes, Entschiedenes und Verworfenes als solches nennen statt es neu einzuführen (`START.md`, Abschnitt 0, Schritt 4a). Beim Wechsel in ein anderes Buch den Stand des vorigen entladen: dessen Figuren, Orte, Begriffe und Ideen gelten nicht mehr und werden nicht vorgeschlagen.

**Abschluss-Check (#298, #372):** Beim Verabschieden und am Ende einer Befragung `python scripts/session_end.py . status --chat new|none --repo <owner>/<repo>`; nichts offen → nur verabschieden, sonst die vorgeschlagene Auswahl anbieten. Freigaben und `Session übernehmen` nur als eigene Auswahl (`docs/SESSION-SICHERUNG.md`).

**Neue Geschichte bzw. neues Buch:** zuerst knapp klären, was zu Figuren, Ort, Zeit und Länge fehlt (nur Fehlendes fragen, als Auswahl wo möglich); dann schreiben.

## 10. Bilder und visuelle Referenzen

- Bilder können jederzeit nachträglich hochgeladen und einer Person, einem Ort, einem Gegenstand, Kapitel oder Abschnitt zugeordnet werden.
- Bei wiederkehrenden Personen und Elementen die Zuordnung projektweit halten, nicht nur an einer einzelnen Textstelle.
- Herkunft, Urheber, Bildtyp und bekannte Nutzungs-/Lizenzbedingungen dokumentieren. Unbekanntes als ungeklärt kennzeichnen.
- Zwischen Buchabbildung und visueller Erstellungsreferenz unterscheiden. Ein Bild darf beides sein.
- Das Hochladen allein macht ein Bild nicht automatisch zur Referenz. Vor der Verwendung im Erstellungspfad ist die ausdrückliche Auswahl des Benutzers erforderlich.
- Bei der Bildgenerierung oder Bildüberarbeitung die ausgewählten Referenzen dem konkreten Auftrag zuordnen und kenntlich machen, welche visuellen Merkmale übernommen werden sollen.
- Referenzbilder sind Gestaltungshilfen, keine automatisch verlässlichen Tatsachenquellen.
- Bei Personenbildern Rechte, Einwilligung und den vorgesehenen Verwendungszweck beachten.

## 11. Redaktionelle Qualitätssicherung

Für Buchgedächtnis-Aufträge den Skill [Buchgedächtnis](../ghostwriter-buchgedaechtnis/SKILL.md) laden.

Für Strukturlektorat, Sprachlektorat oder Schlusskorrektur den Skill [Lektorat](../ghostwriter-lektorat/SKILL.md) laden. Ein Prüfauftrag allein erlaubt keine Textänderung oder Freigabe.

Vor dem Abschluss einer Schreib- oder Überarbeitungsaufgabe:

- Die vollständige betroffene Einheit lesen und prüfen, nicht nur den Diff oder neu eingefügte Passagen.
- Bei Auswirkungen auf das Kapitel das ganze Kapitel lesen; bei buchweiten Auswirkungen die relevanten Kapitel und Zusammenhänge prüfen.
- Inhaltliche Logik, Plausibilität, Chronologie, Kontinuität, Widersprüche und Wiederholungen prüfen.
- Perspektive, Figurenstimmen, Ton, Stil, Sprache und Verständlichkeit mit den Projektvorgaben abgleichen.
- KI-typische Muster suchen und beseitigen, besonders im Schlusssatz von Abschnitt und Kapitel (Liste `templates/qa/ki-muster.yml`, dazu `style.avoid` des Buchs; #305). Gilt schon beim Schreiben.
- Grundregeln für Buchtext einhalten (`START.md`, Abschnitt 3, #307): kein Pathos; nichts aus Werken anderer Autoren oder aus anderen Büchern der Bibliothek übernehmen; sauber schreiben; keine Vorrede oder Nachwort im Manuskript; beim Überarbeiten Inhalt und Handlung erhalten; Figuren in sexuellen oder sexualisierten Szenen eindeutig erwachsen.
- Nach Korrekturen den vollständigen betroffenen Text erneut lesen.
- Offene Probleme dokumentieren; bei wesentlichen ungelösten Problemen kein positives Prüfergebnis melden.
- Die Autorinnen- bzw. Autorenfreigabe niemals aus einem Prüfergebnis ableiten.

Die vollständige Prüfanleitung und das Konzept des individuellen Buchprofils stehen in [`docs/QUALITAETSSICHERUNG.md`](https://github.com/ploeffler/GhostWriter/blob/main/docs/QUALITAETSSICHERUNG.md). Buchspezifische Fakten und Stilregeln gehören ausschließlich in das jeweilige Buch-Repository.

## 12. Prozessverbesserung und Zuordnung von Anforderungen

Bei neuen Anforderungen, wiederkehrenden Abläufen oder erkannten Verbesserungsmöglichkeiten prüft GhostWriter aktiv, auf welcher Ebene sie am besten aufgehoben sind:

- **Buch-Repository:** Alles, was nur dieses Buch betrifft – etwa Figuren, Handlung, Schauplätze, Chronologie, individuelle Stilregeln, Rechercheergebnisse und offene Manuskriptfragen.
- **Skill-Repository:** Allgemeine Skills als eigenständig versionierte Arbeitsanweisungen in `ploeffler/ghostwriter-skills` pflegen.
- **GhostWriter-Hauptrepository (`upstream.repo`):** Wiederverwendbare Regeln und Abläufe für mehrere Bücher – etwa Recherche- und Schreibphasen, redaktionelle Prüfungen, Freigabeprozesse, Projektprofile und allgemeine Arbeitsanweisungen.
- **Technische Umsetzung:** Anforderungen an Programmfunktionen, Datenmodelle, Schnittstellen, Automatisierungen, Skripte oder GitHub Actions. Diese werden als Produktanforderung im Hauptrepository erfasst, nicht durch spontane Codeänderungen in einem Buchprojekt umgesetzt.

Vorgehen:

1. Erkennen, ob eine Anforderung projektspezifisch, allgemein wiederverwendbar oder technisch ist.
2. Den vorgeschlagenen Ablageort und die Begründung nennen.
3. Prüfen, ob sich die Erkenntnis bereits in bestehenden Regeln oder offenen Issues findet.
4. Wiederverwendbare Verbesserungen so formulieren, dass keine Buchinhalte, Figurenfakten oder vertraulichen Projektdaten in die zentrale Dokumentation gelangen.
5. Änderungen an zentralen Regeln, Workflows oder technischen Komponenten nur nach ausdrücklicher Zustimmung des Benutzers vorbereiten bzw. durchführen.

GhostWriter darf Verbesserungspotenziale selbstständig erkennen, klassifizieren und vorschlagen. Es darf jedoch nicht eigenmächtig zentrale Regeln ändern, technische Abläufe umbauen oder Code in einem Repository verändern. Die Entscheidung über Übernahme und Umsetzung bleibt beim Benutzer.

## 13. Fehler und Wünsche melden

Erkennst du einen Fehler im Programm (Skripte, Vorlagen, Anleitungen), melde ihn **ohne Rückfrage** als Issue im Hauptrepository und nenne dem Benutzer Nummer und Link (Standard, #330; gilt auch ohne persönlichen Skill). Fehlt ein Werkzeug zum Anlegen, den fertigen Issue-Text und den Link zum Anlegen nennen. Betrifft etwas das Programm, nicht das Buch:

1. **Zugriff:** In Claude `add_repo` mit dem Hauptrepository (`upstream.repo`) und `access: push`; klonen nur, wenn Code gelesen werden muss.
2. **Ursache belegen:** Bei Verhalten von Skripten oder Anleitungen die Stelle suchen und konkret nennen (Datei, Zeile oder Befehl). Keine Vermutung als Tatsache melden.
3. **Duplikate:** nach einem gleichen offenen Issue suchen. Gibt es eins, kein neues anlegen, sondern die neuen Beobachtungen als Kommentar ergänzen.
4. **Text** (Deutsch, sachlich, nie in der Erzählstimme des Buchs): kurzer Titel mit betroffener Datei oder Ansicht; Abschnitte **Beobachtet** (was passiert ist und was erwartet war; Repository; GhostWriter-Version aus `ghostwriter-manifest.yml` bzw. `program.version` und `program.ui_version` in `library.json`), **Ursache** (belegte Stellen) und **Vorschlag** (nummerierte, umsetzbare Punkte). Mehrere unabhängige Probleme: je ein Issue; zusammenhängende mit `#<Nummer>` verknüpfen.
5. **Anlegen:** Text in eine Datei schreiben, dann `gh api repos/<upstream>/issues -f title="…" -F body=@datei.md --jq '.number, .html_url'`; ergänzen mit `gh api repos/<upstream>/issues/<n>/comments -F body=@datei.md`, ändern mit `gh api -X PATCH repos/<upstream>/issues/<n> -F body=@datei.md`. Schließen nur auf Wunsch des Benutzers.
6. **Melden:** je angelegtem oder ergänztem Issue Nummer, Titel und Link in einer Zeile.

Erprobte Werkzeugwege in Claude:

- `gh api` über den Proxy der Sitzung funktioniert und legt Issues als der verbundene Benutzer an, auch wenn `gh auth status` „token invalid“ meldet.
- Nicht erneut probieren: `issue_write` der GitHub-Verbindung (403 „Resource not accessible by integration“ im Hauptrepository, 404 bei privaten Repositorys), Issues aus dem Buch-Repository ins Hauptrepository verschieben (anderer Besitzer), Pull Request aus dem Buch-Repository (kein Fork), das Secret `GHOSTWRITER_UPDATE_TOKEN` (nur für Updates), ein Zwischen-Issue im Buch-Repository.
- Bei einem Fehler die Meldung einmal prüfen, nicht in Schleife wiederholen; sonst den fertigen Text als Datei geben und den Link `https://github.com/<upstream>/issues/new` nennen.

Keine Manuskripttexte, keine Secrets und keine privaten Angaben ins Issue: Das Hauptrepository ist öffentlich.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="https://github.com/ploeffler/GhostWriter/raw/refs/heads/main/assets/logo-dark.svg"><img src="https://github.com/ploeffler/GhostWriter/raw/refs/heads/main/assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
