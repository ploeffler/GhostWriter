# Prompt-Caching prüfen

Gespeicherter Prüfablauf vom 7. November 2026 für Open WebUI mit gebündeltem
Ollama im Docker-Container `open-webui-ollama` (Image
`ghcr.io/open-webui/open-webui:ollama`, Compose-Dienst `open-webui`).

## Ausgangslage

Die GhostWriter-Direkt-Pipe steuert Prompt-Caching nicht ausdrücklich.
Der SQLite-Startspeicher vermeidet wiederholte GitHub-Abrufe von START.md;
er ist kein Prompt-Cache des Sprachmodells. Ob Ollama Prompt-Kontext tatsächlich
wiederverwendet, muss an der laufenden Installation geprüft werden.

## Prüfablauf

1. Die installierte Version feststellen:

   ```bash
   docker exec open-webui-ollama ollama --version
   ```

2. In der Compose-Datei unter `environment:` des Dienstes `open-webui` ergänzen:

   ```yaml
   - OLLAMA_DEBUG=1
   ```

   Diese Einstellung aktiviert Diagnoseausgaben; sie schaltet nicht erst den
   Prompt-Cache ein.

3. Im Ordner der Compose-Datei den Container neu erstellen. Dabei wird der
   laufende Dienst kurz unterbrochen; die bestehenden benannten Volumes bleiben
   erhalten:

   ```bash
   docker compose up -d --force-recreate open-webui
   ```

4. Cache-bezogene Meldungen verfolgen:

   ```bash
   docker logs --since 2m -f open-webui-ollama 2>&1 | grep -Ei 'cache|cached|slot|prompt'
   ```

5. In Open WebUI mit GhostWriter einen Abschnitt öffnen und direkt hintereinander
   zwei normale Fragen zum selben Abschnitt stellen. Navigation wie „Start“ oder
   „Kapitel 1“ eignet sich nicht: Diese Befehle benötigen keinen Modellaufruf.

6. Die Cache-Meldungen beider Modellaufrufe zusammen mit der Ollama-Version
   beurteilen. Manche Versionen melden beispielsweise:

   ```text
   loading cache slot ... prompt=160 used=120 remaining=40
   ```

   In diesem Meldungsformat weist `used > 0` auf wiederverwendeten Prompt-Kontext
   hin. Wortlaut und Felder hängen von Ollama-Version und Modell-Backend ab.
   Fehlende Meldungen beweisen daher keinen ausgeschalteten Cache. Eine kürzere
   Gesamtantwortzeit allein ist ebenfalls kein verlässlicher Nachweis.

7. Nach dem Test mit Strg+C die Logansicht beenden, `OLLAMA_DEBUG=1` wieder aus
   der Compose-Datei entfernen und den Container mit dem Befehl aus Schritt 3
   erneut erstellen.

## Ergebnisstand

Der Ablauf ist gespeichert. Die laufende Installation wurde damit noch nicht
geprüft; Versionsausgabe und Cache-Meldungen stehen noch aus.
„Kontext prüfen“ in GhostWriter bestätigt vorbereitete Kontextparameter,
aber keine tatsächlichen Cache-Treffer.

## Grundlagen

- [GhostWriter-Open-WebUI-Integration](../integrations/openwebui/README.md)
- [Startskript des kombinierten Open-WebUI-Images](https://github.com/open-webui/open-webui/blob/main/backend/start.sh)
- [Ollama-Umgebungsvariablen](https://github.com/ollama/ollama/blob/main/envconfig/config.go)

Die externen Quellen beziehen sich auf den bei der Besprechung gelesenen
Entwicklungsstand; das installierte Docker-Image kann davon abweichen.
---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
