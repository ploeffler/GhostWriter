# KI-Anbieter und Auswahl

[English](PROVIDERS.en.md) · Deutsch

GhostWriter ist anbieterunabhängig. Für jedes Buchprojekt wird pro Aufgabe festgelegt, welcher KI-Anbieter sie übernimmt. Die maschinenlesbare Liste steht in [`providers.yml`](../providers.yml), die Auswahl des Projekts in [`ghostwriter.yml`](../ghostwriter.yml) unter `ai_providers`.

> Stand der Liste: 31.10.2026. Funktionen, Modelle, Preise und Datenschutzbedingungen ändern sich laufend. Die Liste ist eine Auswahlhilfe, keine Empfehlung. Vor dem Einsatz beim Anbieter prüfen.

## Mit dem anfangen, was du hast

Du brauchst für GhostWriter keine neuen Abos. Im Wizard wird gefragt, welche KI-Dienste du schon nutzt; nur diese werden eingetragen (`ai_providers.available`) und den Aufgaben zugeteilt. Wer nichts nennt, arbeitet mit dem aktuellen Chat für alles.

Später kannst du jederzeit weitere Dienste ergänzen: In der Projektübersicht öffnet der Knopf **KI-Dienste** (Textfassung `D`) ein Formular. Dort hakst du ab, was du hast, teilst die Aufgaben zu und findest bei jedem Dienst zwei Links: **Anleitung**, wie du ihn mit GhostWriter nutzt ([DIENSTE-NUTZEN.md](DIENSTE-NUTZEN.md); für Claude und ChatGPT die Verbindung mit GitHub in [CONNECTOR-SETUP.md](CONNECTOR-SETUP.md)), und **Website** des Anbieters. Unter **Einstellungen** hältst du je eigenem Dienst fest, wie du ihn nutzt: Zugang (Chat-App, API-Schlüssel mit dem Namen des GitHub-Secrets, lokal …), Modell, ob er mit GitHub verbunden ist, Tarif, Kosten pro Monat und eine Notiz (`ai_providers.services` in `ghostwriter.yml`). Für Läufe über die API (z. B. [Recherche mit Internet](DIENSTE-NUTZEN.md#recherche-mit-internet-über-die-api-462)) kannst du je Dienst Preise in Projektwährung eintragen: `price_input_per_mtok` und `price_output_per_mtok` (je 1 Mio. Tokens) und `price_per_1k_searches` (je 1000 Suchanfragen). Daraus schätzt GhostWriter den Betrag im Kosteneintrag; ohne Preise werden nur Tokens und Suchanfragen erfasst. Die Prüf-Action meldet, wenn eine Aufgabe einem Dienst zugeteilt ist, der nicht in `available` steht, oder wenn Einstellungen für einen Dienst eingetragen sind, den du nicht hast.

```yaml
ai_providers:
  available: [anthropic, perplexity]
  services:
    anthropic:  { access: app, model: "", github_connected: true, plan: "Max", monthly_cost: 90 }
    perplexity: { access: app, model: "sonar-pro", github_connected: false, plan: "Pro", note: "nur Recherche" }
  default:  { provider: "anthropic", model: "" }
  research: { provider: "perplexity", model: "" }
```

## Rollen

| Rolle | Aufgabe | Worauf achten |
|---|---|---|
| `research` | Recherche zu Abschnitten | Internetrecherche nötig; Quellen müssen echt und abrufbar sein |
| `brainstorming` | Ideen, Argumentationslinien, Beispiele | Kreativität, Kontextlänge |
| `writing` | Ghostwriting des Manuskripts | Sprachqualität im Deutschen, Stiltreue, lange Texte |
| `revision` | Überarbeitung | Stilkonsistenz, präzises Umsetzen von Korrekturen |
| `fact_check` | Prüfbericht zu Behauptungen | Möglichst **anderer** Anbieter als beim Schreiben; Internetrecherche |
| `queue_processing` | Abarbeiten der GitHub-Issue-Queue | Nur hier zählt, welcher Agent technisch mit GitHub arbeiten kann |

Nicht belegte Rollen erben von `default`. Der Sonderwert `chat` bedeutet: der Assistent, mit dem gerade gechattet wird.

## Beispielkonfiguration

```yaml
ai_providers:
  default:       { provider: "chat", model: "" }
  research:      { provider: "perplexity", model: "", search_tools: ["semantic_scholar"] }
  brainstorming: { provider: "chat", model: "" }
  writing:       { provider: "anthropic", model: "" }
  revision:      { provider: "anthropic", model: "" }
  fact_check:    { provider: "google", model: "" }
  queue_processing: { agent: "github_copilot_agent", model: "" }
```

## Sprachmodell-Anbieter

| ID | Anbieter | Sitz | Zugang | Websuche | Geeignet für |
|---|---|---|---|---|---|
| `openai` | OpenAI (ChatGPT / API) | US | App, API | eingebaut | alle Rollen |
| `anthropic` | Anthropic (Claude / API) | US | App, API | eingebaut | alle Rollen |
| `google` | Google (Gemini / API) | US | App, API | eingebaut | alle Rollen |
| `mistral` | Mistral AI (Le Chat / API) | FR | App, API | über Werkzeug | Recherche bis Fact-Check; europäischer Anbieter |
| `xai` | xAI (Grok / API) | US | App, API | eingebaut | Recherche bis Fact-Check |
| `perplexity` | Perplexity (App / Sonar API) | US | App, API | eingebaut | Recherche, Fact-Check |
| `microsoft_copilot` | Microsoft Copilot | US | App | eingebaut | Recherche, Brainstorming, Schreiben, Revision |
| `cohere` | Cohere (Command / API) | CA | API | über Werkzeug | Recherche mit eigenen Dokumenten, Revision, Fact-Check |
| `deepseek` | DeepSeek | CN | App, API | über Werkzeug | Brainstorming, Schreiben, Revision; Datenschutz prüfen |
| `qwen` | Alibaba Qwen | CN | App, API | über Werkzeug | Brainstorming, Schreiben, Revision |
| `moonshot` | Moonshot AI (Kimi) | CN | App, API | über Werkzeug | Brainstorming, Schreiben, Revision |
| `meta_llama` | Meta Llama (offene Modelle) | US | über Plattformen/lokal | keine | Brainstorming, Schreiben, Revision |

## Plattformen, Aggregatoren, lokal

| ID | Name | Hinweis |
|---|---|---|
| `openrouter` | OpenRouter | Ein Schlüssel für viele Modelle; konkretes Modell in `model` angeben |
| `aws_bedrock` | Amazon Bedrock | Mehrere Anbieter; Rechenzentrumsregion wählbar |
| `azure_ai_foundry` | Microsoft Azure AI Foundry | Mehrere Anbieter; Rechenzentrumsregion wählbar |
| `google_vertex` | Google Cloud Vertex AI | Gemini u. a.; Rechenzentrumsregion wählbar |
| `local_ollama` | Ollama | Lokal, offline, keine laufenden Kosten, keine Websuche |
| `local_lmstudio` | LM Studio | Lokal, offline, keine laufenden Kosten, keine Websuche |

## Ergänzende Recherchequellen (`search_tools`)

Diese liefern Suchtreffer und Quellen, schreiben aber keine Texte. Sie ergänzen den Recherche-Anbieter.

| ID | Name | Stärke |
|---|---|---|
| `brave_search` | Brave Search API | Eigener, von Google unabhängiger Index |
| `tavily` | Tavily | Für KI-Agenten gebaute Such-API |
| `exa` | Exa | Semantische Suche, ähnliche Seiten finden |
| `parallel` | Parallel | Für LLMs aufbereitete Auszüge |
| `perplexity_sonar` | Perplexity Sonar API | Belegte Antworten mit Quellen |
| `serpapi` | SerpAPI | Klassische Suchmaschinen inkl. Google Scholar |
| `semantic_scholar` | Semantic Scholar API | Wissenschaftliche Literatur, kostenlos |
| `openalex` | OpenAlex | Offener Publikationskatalog, kostenlos |

## Agenten für die Queue-Bearbeitung (`queue_agents`)

Nur bei der Queue ist entscheidend, welcher Anbieter technisch mit dem Repository arbeitet: Der Agent liest ein Issue, bearbeitet die Dateien und erstellt einen Pull Request. Freigaben bleiben trotzdem Sache des Benutzers im Chat (siehe `workflow.yml`).

| ID | Agent | Anbieter | Hinweis |
|---|---|---|---|
| `github_copilot_agent` | GitHub Copilot Coding Agent | Microsoft/GitHub | Issue in GitHub zuweisen → Pull Request |
| `openai_codex` | OpenAI Codex | OpenAI | Auch als Partner-Agent direkt in GitHub zuweisbar (je nach Copilot-Plan) |
| `claude_code` | Claude Code | Anthropic | Auch als Partner-Agent direkt in GitHub zuweisbar (je nach Copilot-Plan) |
| `google_jules` | Jules | Google | Asynchroner Agent für GitHub-Repositories |
| `gemini_cli` | Gemini CLI | Google | Z. B. in GitHub Actions einsetzbar |
| `manual` | Manuell im Chat | – | Standard; keine automatische Abarbeitung |

## Regeln

- Die globalen KI-Regeln (`strict`, `required`, `explicit` …) gelten für **jeden** Anbieter. Ein Anbieterwechsel lockert sie nie.
- Jeder Lauf (Recherche, Brainstorming, Fact-Check) und jeder Kosteneintrag dokumentiert `provider` und `model`.
- Ist ein gewählter Anbieter nicht direkt aufrufbar, bereitet der Chat-Assistent den Auftrag so vor, dass der Benutzer ihn beim gewählten Anbieter ausführen kann. Ein stilles Ersetzen durch einen anderen Anbieter ist nicht erlaubt.
- Ein Anbieter ohne Internetrecherche darf die Rolle `research` nur übernehmen, wenn alle Aussagen ausdrücklich als ungeprüft gekennzeichnet werden.

## Liste pflegen

Neue Anbieter werden in `providers.yml` ergänzt (eindeutige `id`, Felder wie oben) und hier in die passende Tabelle eingetragen. Beim Prüfen `checked_at` aktualisieren.

**Modellvorgaben (#554):** Die Modelle, die GhostWriter selbst benutzt, wenn im Buch keines eingestellt ist (Recherche in der Action, Colorieren), stehen in `providers.yml` unter `model_defaults`, je Anbieter und Aufgabe mit `model` und `checked_at` (Datum der letzten Prüfung). Läuft ein Modell aus, genügt eine Änderung dort (Beispiel #638: Die OpenAI-Recherche nutzt `gpt-6.1-terra` statt des am 11.12.2026 abgeschalteten `gpt-5`); ein Buch kann es in den Einstellungen („KI-Dienste“, Modell) überschreiben. `python3 scripts/model_defaults.py show` zeigt die Vorgaben (mit `retire_at`, wenn der Anbieter eine Abschaltung angekündigt hat; die Prüfung warnt 90 Tage vorher, auch ohne Schlüssel), `python3 scripts/model_defaults.py check` vergleicht sie und die eingestellten Modelle mit den kostenlosen Modelllisten der Anbieter, aber nur für Anbieter, deren Schlüssel in der Umgebung steht (lesender Aufruf, nie ein Live-Test, nie eine automatische Umschaltung auf ein anderes Modell). **Im täglichen Update (#596):** Die Action „GhostWriter aktualisieren“ ruft `model_defaults.py check --report` auf; Hinweise stehen im Tagesbericht (Abschnitt „KI-Modelle“). Geprüft wird nur mit den Secrets `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` und `GEMINI_API_KEY`; Modelle mit anderem Secret-Namen und alles ohne Schlüssel bleiben ungeprüft, nahe Abschaltungen aus `providers.yml` erscheinen trotzdem. Fehlgeschlagene Aufträge mit „Modell nicht mehr verfügbar“ nennt die Meldung beim Wiedereinstieg samt Befehl zum erneuten Versuch (#484).

**Preistabelle (#66):** Unter `prices` in `providers.yml` stehen die Preise je Anbieter und Modell (Währung, Eingabe und Ausgabe je 1 Mio. Tokens, optional je 1000 Suchanfragen, Quelle, Prüfdatum). Daraus entsteht je Aufruf automatisch ein Kosteneintrag „geschätzt“; ein Modell ohne Eintrag bleibt „unbekannt“, nie 0. Preise nur von der Seite des Anbieters eintragen und `checked_at` neu setzen. Der Betrag wird mit dem EZB-Referenzkurs des Tages in die Projektwährung umgerechnet (`python3 scripts/pricing.py estimate <anbieter> <modell> --input N --output N`). Eigene Preise im Buch (Formular „KI-Dienste“) haben Vorrang.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
