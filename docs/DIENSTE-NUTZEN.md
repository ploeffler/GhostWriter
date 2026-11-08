# KI-Dienste mit GhostWriter nutzen

Diese Anleitung zeigt, wie du einen KI-Dienst, den du schon hast, für eine Aufgabe in GhostWriter einsetzt. Welche Dienste du hast und wer welche Aufgabe übernimmt, legst du im Formular **KI-Dienste** fest (Projektübersicht, Roboter-Symbol; in der Textfassung `D`).

> **Grundsatz:** Fang mit dem an, was du schon hast. Für GhostWriter brauchst du kein neues Abo. Weitere Dienste kannst du jederzeit später ergänzen.

**Stand:** 01.11.2026. Menüs und Funktionen der Anbieter ändern sich oft. Diese Anleitung beschreibt deshalb den Ablauf, nicht jeden Knopf beim Anbieter.

## Welcher Weg passt zu deinem Dienst?

| Dein Dienst | Weg | Aufwand |
|---|---|---|
| Der Chat, in dem du mit GhostWriter arbeitest | [Weg 1](#weg-1-der-chat-in-dem-du-arbeitest) | keiner |
| Ein anderer Chat-Dienst mit App oder Website (z. B. ChatGPT, Gemini, Perplexity, Le Chat, Copilot, Grok) | [Weg 2](#weg-2-ein-anderer-chat-dienst-auftrag-kopieren) | pro Auftrag einmal kopieren und einfügen |
| Ein Modell auf deinem eigenen Rechner (Ollama, LM Studio) | [Weg 3](#weg-3-lokale-modelle-auf-deinem-rechner) | wie Weg 2, aber ohne Internetrecherche |
| Ein Dienst nur mit API-Schlüssel (z. B. Cohere, OpenRouter, Amazon Bedrock, Azure, Vertex AI) | [Weg 4](#weg-4-dienste-nur-mit-api-schlüssel) | technisch; Schlüssel als [GitHub-Secret](#api-schlüssel-als-github-secret), vorerst nicht direkt aus dem Chat |
| Eine Recherchequelle (z. B. Semantic Scholar, OpenAlex, Brave Search) | [Recherchequellen](#recherchequellen) | je nach Quelle |
| Ein Agent für die Aufgaben-Warteschlange (z. B. GitHub Copilot, Claude Code, Codex, Jules) | [Agenten](#agenten-für-die-aufgaben-warteschlange) | Einrichtung in GitHub |

## Weg 1: Der Chat, in dem du arbeitest

Steht bei einer Aufgabe **Aktueller Chat** (oder **wie Standard**, und der Standard ist der aktuelle Chat), erledigt GhostWriter sie direkt im Gespräch. Du klickst zum Beispiel im Abschnitt auf **Recherche · Sofort**, und das Ergebnis wird gespeichert.

Damit GhostWriter speichern kann, braucht der Chat Schreibzugriff auf GitHub; siehe [CONNECTOR-SETUP.md](CONNECTOR-SETUP.md).

## Weg 2: Ein anderer Chat-Dienst: Auftrag kopieren

Beispiel: Du schreibst mit Claude, hast aber auch Perplexity und möchtest die Recherche dort machen. Dann trägst du im Formular **KI-Dienste** Perplexity als deinen Dienst ein und wählst ihn bei **Recherche** aus.

So läuft eine Aufgabe dann ab:

1. **Starten:** Im GhostWriter-Chat öffnest du den Abschnitt und klickst auf **Recherche · Sofort** (Textfassung `RS`).
2. **Auftrag bekommen:** GhostWriter sagt, dass die Recherche bei Perplexity läuft, und gibt einen fertigen **Auftrag** in einem grauen Kasten aus. Er enthält alles Nötige: Thema des Abschnitts, die Regeln (nichts erfinden, Quellen mit Link, Unsicherheiten kennzeichnen) und das gewünschte Antwortformat.
3. **Kopieren:** Klick auf das Kopier-Symbol am Kasten (oder markieren und kopieren).
4. **Beim anderen Dienst einfügen:** Öffne beim anderen Dienst einen **neuen** Chat, füge den Auftrag ein und schick ihn ab. Bietet der Dienst eine Websuche an, schalte sie für Recherche und Faktencheck ein.
5. **Antwort zurückgeben:** Kopier die **ganze** Antwort und füge sie im GhostWriter-Chat ein. Schreib darüber eine Zeile wie „Ergebnis von Perplexity“ und, wenn du es weißt, das Modell.
6. **Prüfen und speichern:** GhostWriter prüft das Ergebnis (Format, Quellen mit Link, Stichproben der Links), zeigt dir kurz, was drinsteht, und speichert es wie gewohnt in den Arbeits-Branch. Im Lauf steht der Dienst, den du benutzt hast.

Was je Aufgabe zurückkommt:

| Aufgabe | Was der andere Dienst liefert | Was GhostWriter daraus macht |
|---|---|---|
| Recherche | Ergebnisse mit Quellen | Recherchelauf (`research/…/run-NNN.md`) |
| Brainstorming | Ideen, Gliederungsvorschläge | Brainstorminglauf |
| Schreiben | Manuskripttext für **einen** Abschnitt | Text im Abschnittsformular; gespeichert erst nach deiner Prüfung (Schreibfreigabe nötig) |
| Überarbeiten | überarbeiteter Text eines Abschnitts | wie Schreiben; Änderungen werden dir gezeigt |
| Faktencheck | Prüfbericht | Prüfbericht; das Manuskript wird nicht automatisch geändert |

Gut zu wissen:

- **Ein Auftrag, ein Abschnitt.** Mische keine Abschnitte in einem Auftrag.
- **Kosten:** Arbeit in Chat-Diensten über dein Abo erzeugt in GhostWriter keinen Kosteneintrag; GhostWriter erfasst nur zusätzliche KI-API-Kosten, die über das eigene Backend entstehen (ab Weg B). Was dich dein Abo kostet, kannst du im Formular **KI-Dienste** unter „Kosten pro Monat“ notieren.
- **Keine stille Vertretung:** Ist Perplexity für die Recherche gewählt, recherchiert GhostWriter nicht heimlich selbst. Willst du es ausnahmsweise im aktuellen Chat machen, sag das ausdrücklich.
- **Datenschutz:** Der Auftrag enthält Teile deines Buchs. Prüf bei Diensten mit unklarer Datenverarbeitung (Hinweis im Formular), ob du das möchtest.

## Weg 3: Lokale Modelle auf deinem Rechner

Ollama und LM Studio laufen auf deinem eigenen Computer: ohne laufende Kosten, ohne dass Text das Haus verlässt, aber **ohne Internetrecherche**. Der Ablauf ist derselbe wie bei [Weg 2](#weg-2-ein-anderer-chat-dienst-auftrag-kopieren): Auftrag kopieren, im lokalen Programm einfügen, Antwort zurückgeben.

Geeignet für Brainstorming, Schreiben und Überarbeiten. Für Recherche und Faktencheck nicht, weil Quellen nicht im Netz geprüft werden können; Aussagen daraus würden als „ungeprüft“ markiert.

## Weg 4: Dienste nur mit API-Schlüssel

Manche Dienste haben keine Chat-Oberfläche, sondern nur eine Programmierschnittstelle (API) mit Schlüssel, oder sie sind Plattformen für viele Modelle. Der Chat kann sie in dieser Version nicht selbst aufrufen, und einen API-Schlüssel solltest du nie in einen Chat einfügen.

Möglichkeiten:

- Viele dieser Anbieter haben zusätzlich eine Test- oder Chat-Seite („Playground“). Dort kannst du wie bei [Weg 2](#weg-2-ein-anderer-chat-dienst-auftrag-kopieren) einen Auftrag einfügen.
- Den Schlüssel kannst du schon jetzt sicher als [GitHub-Secret](#api-schlüssel-als-github-secret) hinterlegen. Die direkte Anbindung aus dem Chat ist für eine spätere Version mit eigener GhostWriter-Schnittstelle vorgesehen (Issue #19).

Für den Einstieg empfehlen wir diese Dienste nicht.

## API-Schlüssel als GitHub-Secret

Für die Arbeit im Chat brauchst du **keinen** API-Schlüssel: ChatGPT und Claude laufen über dein Konto bzw. Abo in der App. Ein Schlüssel ist nur nötig, wenn ein Dienst **ohne dich** arbeiten soll, etwa ein Agent in GitHub Actions, der Aufgaben aus der Warteschlange abarbeitet, oder eine Such-API.

**Grundregel:** Ein API-Schlüssel gehört **nie** in einen Chat, in ein Formular, in eine Datei oder in einen Commit. Chats werden gespeichert, Repositorys geteilt. Der Schlüssel liegt ausschließlich als verschlüsseltes **Secret** in deinem GitHub-Repository. GhostWriter speichert nur den **Namen** des Secrets (`api_key_secret`), nie den Wert.

So legst du ihn an:

1. **Zugang wählen:** Im Formular **KI-Dienste** beim Dienst auf **Einstellungen** (direkt neben dem Namen) und als Zugang **API-Schlüssel** wählen. Darunter steht der Name des Secrets, z. B. `OPENAI_API_KEY`; meist passt der Vorschlag.
2. **Schlüssel erstellen:** Link **„1. Schlüssel beim Anbieter erstellen“** öffnen, dort einen neuen Schlüssel anlegen und kopieren. Viele Anbieter zeigen ihn nur einmal an. Lege nach Möglichkeit ein Ausgabenlimit fest.
3. **In GitHub hinterlegen:** Link **„2. In GitHub als Secret hinterlegen“** öffnen (Repository → *Settings → Secrets and variables → Actions → New repository secret*). Als **Name** genau den Namen aus dem Formular eintragen, als **Secret** den Schlüssel einfügen, **Add secret**. Dafür brauchst du Admin-Rechte am Repository.
4. **Speichern:** Im Formular **Speichern**. Die Action „Übersichtsdatei aktualisieren“ prüft danach, ob das Secret vorhanden ist; das Formular zeigt **hinterlegt** oder **fehlt in GitHub**. Sie liest dafür nur die Namen der Secrets, nie die Werte. Hast du das Secret erst nach dem Speichern angelegt, startest du die Prüfung unter *Actions → Übersichtsdatei aktualisieren → Run workflow* oder speicherst das Formular erneut.

Gut zu wissen:

- **Versehentlich in den Chat kopiert?** Den Schlüssel beim Anbieter sofort löschen und einen neuen erstellen. GhostWriter speichert ihn nicht, aber er steht im Verlauf.
- **Wer nutzt das Secret?** Nur GitHub Actions bzw. Agenten in deinem Repository. Der Chat kann Secrets weder lesen noch anlegen.
- **Abo statt Schlüssel bei Claude Code:** Mit einem Claude-Pro- oder -Max-Abo kannst du statt `ANTHROPIC_API_KEY` ein Token anlegen: auf deinem Rechner `claude setup-token` ausführen und das Ergebnis als Secret `CLAUDE_CODE_OAUTH_TOKEN` hinterlegen. Eines der beiden genügt.
- **OpenAI Codex:** Die Codex-Action in GitHub braucht einen API-Schlüssel (`OPENAI_API_KEY`). Codex in ChatGPT (Cloud) arbeitet dagegen über dein ChatGPT-Abo und die Verbindung zu GitHub, ohne Schlüssel.
- **Plattformen** wie Amazon Bedrock, Azure oder Vertex AI brauchen oft mehrere Zugangsdaten (z. B. Endpunkt und Region); trag den Hauptschlüssel ein und notiere den Rest in der **Notiz** (ohne geheime Werte).

## Recherchequellen

Recherchequellen liefern Treffer und Belege, schreiben aber keine Texte. Sie ergänzen den Dienst, der die Recherche macht.

- **Kostenlose Kataloge wissenschaftlicher Literatur** (Semantic Scholar, OpenAlex): Hakst du sie an, nennt GhostWriter sie im Rechercheauftrag, und der Recherche-Dienst durchsucht sie über seine Websuche. Kein Konto nötig.
- **Such-APIs mit Schlüssel** (Brave Search, Tavily, Exa, Parallel, Perplexity Sonar, SerpAPI): brauchen einen API-Schlüssel und lassen sich erst mit der eigenen Schnittstelle nutzen ([Weg 4](#weg-4-dienste-nur-mit-api-schlüssel)). Du kannst sie schon eintragen und den Schlüssel als [GitHub-Secret](#api-schlüssel-als-github-secret) hinterlegen, damit sie später verwendet werden.

## Agenten für die Aufgaben-Warteschlange

Die Warteschlange sind Aufgaben als Issues in GitHub (z. B. „Quelle in Abschnitt 2.3 prüfen“). Ein Agent kann ein Issue übernehmen, die Dateien bearbeiten und einen Pull Request anlegen. Standard ist **manuell**: Du arbeitest die Aufgaben im Chat ab.

Wenn du einen Agenten schon nutzt (zum Beispiel über ein GitHub-Copilot-Abo):

1. Trag ihn im Formular **KI-Dienste** ein und wähl ihn bei **Aufgaben-Warteschlange** aus.
2. Die Einrichtung passiert beim Anbieter und in GitHub; folge dem Link **Website** im Formular. Meist weist man dem Agenten danach ein Issue in GitHub zu. Läuft der Agent als GitHub Action (z. B. Claude Code, Codex-Action, Gemini CLI), wähl unter **Einstellungen** den Zugang **API-Schlüssel** und hinterleg den Schlüssel als [GitHub-Secret](#api-schlüssel-als-github-secret). Agenten, die du in GitHub direkt zuweist (Copilot, Partner-Agenten), brauchen keinen eigenen Schlüssel.
3. Was der Agent ändert, kommt als Pull Request. **Freigaben bleiben immer bei dir im Chat**; ein Agent kann nichts freigeben, und ein geschlossenes Issue ist keine Freigabe.

## Einen Dienst später hinzufügen

1. Projektübersicht → Roboter-Symbol **KI-Dienste**.
2. **Weitere Dienste hinzufügen** aufklappen und den Dienst abhaken. Daneben führt **Anleitung** hierher (oder zur passenden Einrichtung) und **Website** zum Anbieter.
3. Unter **Einstellungen** (neben dem Namen des Dienstes) festhalten, wie du ihn nutzt: **Zugang** (Chat-App oder Website, API-Schlüssel, auf meinem Rechner …; bei API-Schlüssel der Name des [GitHub-Secrets](#api-schlüssel-als-github-secret)), **Modell** (leer = Standard), **Mit GitHub verbunden** (nur wenn du für diese App die [Verbindung](CONNECTOR-SETUP.md) eingerichtet hast), **Tarif**, **Kosten pro Monat** und eine **Notiz**. Aus dem Zugang ergibt sich, welcher Weg oben gilt.
4. Bei den Aufgaben auswählen, was der neue Dienst übernehmen soll.
5. **Speichern.** Die Änderung kommt wie jede andere in den Arbeits-Branch und gilt nach „Änderungen übernehmen“.

Einen Dienst nicht mehr nutzen: Haken entfernen und speichern. Aufgaben, die er hatte, fallen auf **wie Standard** zurück.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
