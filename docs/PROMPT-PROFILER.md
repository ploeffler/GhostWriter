# Prompt-Profiler: Bestandsaufnahme und erster Baustein

Bezug: [Issue #204](https://github.com/ploeffler/GhostWriter/issues/204).
Bestandsaufnahme des Hauptstands `df49fbd`; keine zusätzliche Plattformunterstützung zugesagt.

## Vorhandene Modellwege und Prompt-Bestandteile

| Weg | Zusammenstellung und Reihenfolge | Sichtbarkeit und Messung |
|---|---|---|
| Hintergrundanalysen, `scripts/analyze.py`, `run`/`call_llm` | Je Art Systemkonstante aus `KINDS`, dann Benutzertext mit Block-ID, Manuskript und gegebenenfalls bekanntem Figurenkontext; Zusammenführung mit eigener Systemkonstante und geprüften Ergebnissen | OpenAI Chat Completions: system/user in messages; Anthropic Messages: separates system, dann user. Provider liefert Eingabe-/Ausgabetokens. Der optionale Profiler erfasst Cache-Tokens separat aus der Antwort; die bisherige Rückgabe von `call_llm` bleibt unverändert. Preise aus Projekteinstellungen ergeben geschätzte Kosten. |
| Import-Gliederung, `scripts/import_book.py`, `outline` | `OUTLINE_SYSTEM`, dann `outline_prompt`: nummerierte Manuskriptabsätze | Nutzt dieselbe Funktion `analyze.call_llm`; keine zusätzliche Providerimplementierung. |
| Open-WebUI-Pipe, `integrations/openwebui/ghostwriter_direct.py`, `pipe`/`_forward` | Vorhandener Verlauf; Startanweisungen am Anfang, falls nicht bereits identisch enthalten; aktueller Buchkontext mit Verhaltensregeln unmittelbar vor letzter Benutzernachricht, bei Abschnittsauswahl zusätzlich Abschnittsansicht | `_prepare_forward` entfernt Toolaufrufe und Navigationsmarker und setzt Modell/Optionen. `_forward` übergibt an `generate_chat_completion`. Das ist eine Plattformgrenze, kein nachgewiesener Provider-Request. Titel-/Folgefragenaufträge verwenden ihren eigenen Pfad. Direkte Navigation erzeugt keinen Modellaufruf. |
| GitHub-Werkzeug, `integrations/openwebui/ghostwriter_github.py` | Liefert Startdatei, Ansichten und Gesprächskontext; enthält Repository-Lese-/Schreibzugriffe | Kein eigener Modellaufruf. Der Startcache verhindert erneutes Laden, belegt aber keine beim Modell eingesparten Tokens. |
| Chat-Arbeit und „Auftrag kopieren“, `START.md`, Aufgaben-Vorlagen unter `templates/` | Startregeln, Profil, Buchregeln/Stil, ausgewählte Quellen und Kontext, Aufgabenauftrag sowie Verlauf; konkrete Auswahl durch den Assistenten | Kein zentraler Request-Builder im Repository. Der tatsächlich übertragene App-/Web-Request und verborgene Plattformregeln bleiben unbekannt. Das gilt auch für Recherche, Brainstorming, Schreiben, Redaktion und Fact-Checking im Chat. |
| Bildauftrag, `scripts/images.py`, `build_prompt` | Bildstil, Szene, Figurenmerkmale, explizite Referenzbeschreibungen, Schrift-/Formatvorgabe | Erzeugt Text und Referenz-IDs; kein automatischer Bildprovider-Aufruf. Tatsächliche Übertragung der Bildbytes ist damit nicht belegt. |

Actions `analyse.yml` und `import.yml` starten die genannten Python-Wege. Die anderen
Actions führen keine weiteren Modell-HTTP-Aufrufe aus. `scripts/make_logo.py`
erzeugt SVG lokal. GitHub-HTTP-Zugriffe und Recherchelinks sind keine Modellaufrufe.
`providers.yml` beschreibt mögliche Dienste, implementiert aber keine weiteren Adapter.

## Cache und wiederholte Übertragung

Der Analysecache unter `analysis/cache/` vermeidet bei passendem Fingerabdruck
komplette neue Analyseaufrufe. Das ist vom Provider-Prompt-Cache zu unterscheiden.
Nicht gecachte Blöcke senden ihre Systemanweisung jeweils erneut. Die Pipe übernimmt
den gelieferten Verlauf und fügt frischen Kontext ein; frühere Kontextnachrichten
können darin weiter enthalten sein. Ein Startcache begrenzt diesen Verlauf nicht.
Ohne aufeinanderfolgende tatsächliche Requests und Provider-Usage ist kein messbarer
Cache-Effekt oder Einsparbetrag nachgewiesen.

## Jetzt verfügbar: lesender Snapshot-Profiler

`scripts/prompt_profiler.py` nimmt einen explizit bereitgestellten JSON-Request über
Standardeingabe entgegen und schreibt ausschließlich einen Metadatenreport nach
Standardausgabe. Unterstützte Snapshot-Formate sind `openai-chat` und
`anthropic-messages`. Der CLI-Modus verarbeitet Offline-Snapshots. Zusätzlich können die bestehenden direkten API-Wege ausdrücklich während eines regulären Modelllaufs erfasst werden (siehe unten).
Nur den Request-Body übergeben, niemals Header oder Zugangsdaten. Keine echten
Manuskripte als Testdateien ins Repository aufnehmen.

```sh
python scripts/prompt_profiler.py --adapter openai-chat < /tmp/request.json
```

Der temporäre Plan hält Herkunft, Typ, Geltungsbereich, Priorität,
Aktivierungsbedingung und Position. Ohne belegte Herkunft bleiben Priorität und
Core-Zuordnung unbekannt. Der Report enthält Prüfsummen, Zeichenumfang und exakt
identische Bestandteile mit Fundstellen. Er trifft keine Löschentscheidung.

Tokens werden ausdrücklich nur mit Zeichen/3,5 geschätzt. Die Gesamtzahl bezieht
sich auf kanonisch serialisiertes JSON einschließlich sonstiger Request-Felder;
sie ist weder eine modellspezifische Tokenzählung noch die Summe der Inhaltszeilen.
Modell-Framing und Bild-/Audio-Tokens sind unbekannt. Provider-Usage, Cache-Nutzung
und Kosten werden nicht erfunden. Volltexte und frei übergebene Zusatzfelder
werden nicht in den Report übernommen; Fingerprints können dennoch Rückschlüsse
auf bekannte Inhalte ermöglichen. Reports entsprechend vertraulich behandeln.
Der Snapshot-Profiler sendet keine Anfrage und schreibt keine Datei.

## Erfassung an den vorhandenen API-Wegen

`GHOSTWRITER_PROMPT_PROFILE=1` aktiviert die Metadatenausgabe für die vorhandenen
OpenAI-/Anthropic-Aufrufe von `scripts/analyze.py` und dadurch auch die
KI-Gliederung in `scripts/import_book.py`. Ohne dieses exakte Opt-in wird kein
Report erstellt. Die Testabkürzung `GHOSTWRITER_FAKE_LLM` erzeugt keine angeblich
gemessenen Providerberichte.

Der reguläre Modelllauf bleibt kostenpflichtig wie bisher; der Profiler ruft
kein zusätzliches Modell auf. Beispiel für einen ohnehin beauftragten Analyselauf:

```sh
GHOSTWRITER_PROMPT_PROFILE=1 python3 scripts/analyze.py /pfad/zum/buch run --kind summaries
```

In GitHub Actions gibt es dafür bei **Analyse im Hintergrund** und
**Manuskript importieren** das standardmäßig ausgeschaltete Feld
**Prompt-Profil erstellen** (`prompt_profile`). Nach dem offiziellen
GhostWriter-Update im eigenen Repository den Lauf auf dem gewünschten Buch-Branch
starten. Beim Import betrifft dies nur den KI-Schritt `outline`. Die Reports
stehen im Laufprotokoll bei **Analysieren** bzw. **Schritt ausführen**.
Unveränderte Analyseblöcke können aus dem vorhandenen Ergebnis-Cache kommen;
dann gibt es für sie keinen Modellaufruf und entsprechend keinen Prompt-Report.

Jeder Report erscheint auf stderr als eine Zeile mit Präfix
`GHOSTWRITER_PROFILE `. Es gibt keine automatische Dateiablage. Die Ausgabe wird
parallel innerhalb des Prozesses gegen vermischte Zeilen geschützt. Wer den Lauf
in CI startet, muss bedenken, dass stderr in dessen Logs aufbewahrt wird.
Volltexte, HTTP-Header, Zugangsdaten und Antworttexte gelangen nicht in den Report.
Ein Transportfehler erzeugt nur den Status `failed`, keinen kopierten Fehlertext.
Profilerfehler sollen den Modelllauf nicht abbrechen; sie erzeugen einen festen
Hinweis ohne Eingabe- oder Fehlerdetails.

Erfasst wird der Body des bereits gebauten HTTP-Requests vor Übergabe an
`urlopen`, danach ausschließlich die Usage-Antwort. Für die unveränderten
Transportbytes werden zusätzlich Bytezahl und SHA-256 erfasst; sie sind von der
kanonischen JSON-Darstellung des Snapshot-Reports getrennt. `response_received` belegt
den erfolgreichen Transport mit lesbarer JSON-Antwort, nicht die inhaltliche
Qualität. Eine zufällige `call_id` unterscheidet Aufrufe. Die Core-Argumente
`call_llm.system` und `call_llm.user` erhalten getrennte Herkunftsangaben; der
kombinierte Benutzertext wird noch nicht in Buch-/Abschnittsbausteine zerlegt.
Core- und Payload-Sichten beschreiben dieselben Inhalte aus verschiedenen Ebenen
und dürfen nicht zu einer Token-Gesamtzahl addiert werden.

Gemeldete Usage bleibt von den geschätzten Zeichenwerten getrennt. Bei Anthropic
enthält `input_tokens` die Cache-Lese-/Schreib-Tokens nicht; der gesamte Input wird
nur bei vollständigen Angaben als Summe ausgewiesen. Bei OpenAI ist
`cached_tokens` ein Detail der gesamten `prompt_tokens` und wird nicht zusätzlich
addiert. Fehlende Werte bleiben unbekannt. Kosten bleiben ohne tatsächliche
Kostenangabe nicht verfügbar. Grundlage sind die offiziellen Dokumentationen zu
[Anthropic Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
und [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## Mehrere Aufrufe vergleichen

Explizit gesicherte Metadatenzeilen lassen sich aggregieren. Andere Logzeilen
vorher herausfiltern, etwa mit `rg '^GHOSTWRITER_PROFILE '`. Der Aggregator liest
nur von stdin und schreibt nach stdout:

```sh
python3 scripts/prompt_profiler.py --aggregate < /tmp/profile.jsonl
```

Er summiert ausschließlich vorhandene Messwerte und nennt die Anzahl unbekannter
Aufrufe je Wert. Wiederholte Fingerprints werden mit Aufrufindex und Fundstelle
aufgeführt. Das belegt erneut in den erfassten Requests enthaltene Inhalte. Der
Transportstatus bleibt je Fundstelle sichtbar; bei Offline-Snapshots oder Fehlern
ist die tatsächliche Übertragung nicht nachgewiesen. Wiederholung belegt weder
einen Provider-Cache-Treffer noch eine Geldersparnis. Die Eingabe muss jeden Aufruf genau einmal enthalten.

## Open WebUI mit lokalem Modell

Die [Direkt-Pipe 1.7](../integrations/openwebui/README.md) enthält denselben
Profiler als erzeugten Codeblock. Mit **Prompt-Profil** wird eine Diagnose ohne
Modellaufruf angezeigt. Die Valve `PROMPT_PROFILE` schaltet optional die
Metadatenerfassung bei normalen Weiterleitungen ein. Ein lokales Ollama-Modell
benötigt dafür keinen zusätzlichen bezahlten API-Zugang.

Die Sichtbarkeit ist enger als bei den direkt erfassten API-Bodys: Die Pipe sieht
nur ihre Modellfelder vor Übergabe an Open WebUI. Der Report kennzeichnet
unbekannte Plattform-/Provideranteile sowie ausgeschlossene Felder. Ein Aufruf
mit Streaming wird unverändert zurückgegeben und zur Messung nicht konsumiert.
Gemessene Usage und Kosten werden daher nicht behauptet. Der Snapshot-CLI-Modus
`--adapter openwebui-pipe` verwendet dieselbe eingeschränkte Sicht.

## Noch offen für Phase 1

- Core-Bausteine beim Aufbau feiner in Projekt-, Aufgaben- und Abschnittskontext zerlegen.
- Einen realen Modellaufruf und die tatsächlichen Providerwerte abnehmen;
  bisher wurde der Transport mit simulierten HTTP-Antworten geprüft.
- Passende Tokenizer, Buch-/Kapitel-/Abschnittszuordnung und getrennte Kostenwerte.
- Semantische Vorschläge für Überschneidungen und Konflikte mit Fundstellen.
- Open-WebUI-/Ollama-Installation mit echtem Chat prüfen; bisher Adaptertests mit simuliertem Plattformaufruf.
- Repräsentative Aufgabenabnahme einschließlich Regel-Erhalt.

Phase 1 ist mit diesen Bausteinen **noch nicht vollständig abgenommen**.
Anweisungskatalog und Compiler folgen separat nach realen Messungen.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
