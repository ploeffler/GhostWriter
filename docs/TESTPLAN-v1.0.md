# Testplan v1.0

Handabnahme für v1.0. Die automatischen Tests laufen in `validate` (volle Suite am Release-PR, `docs/DOKUMENTATION-PFLEGE.md`, „Release vorbereiten“). Hier stehen nur die Prüfungen, die ein Mensch in den Chat-Programmen oder in einer echten Bibliothek machen muss. Grüne Tests ersetzen sie nicht.

Clientgruppen (D-Planung vom 08.11.2026): **GPT** (ChatGPT und Codex), **Claude** (claude.ai, Claude-Web-App, Claude Code) und **Open WebUI**. Fehlende Testzugänge werden als offen ausgewiesen, nicht als bestanden. Kosten verursachende Prüfungen sind keine Voraussetzung (D08) und als *optional* markiert.

Bibliothek für die Abnahme: `chillyconcane/YAWA`, sonst eine eigene Testbibliothek. Fremde Bibliotheken nur mit Freigabe des Eigentümers. Ergebnisse als Kommentar ins jeweilige Issue, mit Datum, Client, Programmversion und Beleg.

Legende: ✅ bestanden · ❌ fehlgeschlagen · ⏳ offen · — nicht anwendbar

## 1. GitHub-Verbindung (#22)

| Prüfung | GPT | Claude | Open WebUI |
|---|---|---|---|
| Datei ändern, Branch, Pull Request anlegen und mergen über die Verbindung | ✅ (22.11.) | ✅ (22.11.) | ⏳ |
| Formular aus dem Testbuch speichert als Pull Request | ✅ (22.11.) | ⏳ | ⏳ |
| Einzelbeleg „eigener Connector“ (welche Verbindung je App genutzt wurde) | ⏳ | ⏳ | — |

Beleg aus einer Claude-Sitzung (24.11.2026): Über den GitHub-Connector von claude.ai gingen Lesen von Issues, PRs und Dateien. Ein Issue-Kommentar wurde abgelehnt (`403 Resource not accessible by integration`). Schreiben ging dort über die Arbeitsumgebung (`gh api`). Die Rechte des Connectors je Repository sind deshalb vor der Abnahme zu prüfen.

## 2. Sprache (#74)

| Prüfung | GPT | Claude | Open WebUI |
|---|---|---|---|
| „Interface: English“ schaltet Fragen, Menüs und Ansichten um; Buchtext bleibt unverändert | ⏳ | ⏳ | ⏳ |
| Englische Textfassung von Projektübersicht, Abschnitt und Freigabe verständlich | ⏳ | ⏳ | ⏳ |
| Englisches Widget mit `--ui-ref` (nur Claude) | — | ⏳ | — |
| Buch auf Englisch mit Bedienung auf Deutsch | ⏳ | ⏳ | ⏳ |

## 3. Team und Rollen (#455)

| Prüfung | Ergebnis |
|---|---|
| Buch mit `team`: Bearbeiter ohne `approve` schreibt und speichert, bekommt kein „abschließen“ angeboten | ⏳ |
| Von Hand eingetragener Abschluss eines Bearbeiters lässt `validate` („Rollen im Buch prüfen“) scheitern | ⏳ |
| Leser sieht Ansichten und Probedruck, keine Schreibaktionen | ⏳ |
| Commits des Bearbeiters tragen seinen Namen | ⏳ |
| Buch ohne `team` verhält sich unverändert (Schritt meldet nichts zu prüfen bzw. grün) | ⏳ |

## 4. Bilder, Referenzen, Bildrecherche (#143, #218, A04, A05)

| Prüfung | GPT | Claude | Open WebUI |
|---|---|---|---|
| Eigenes Referenzbild hochladen: Status `stored`, keine Freigabe | ⏳ | ⏳ | ⏳ |
| Freigabe, Auswahl im Bildauftrag, Rücknahme | ⏳ | ⏳ | ⏳ |
| Bildrecherche: Kandidat mit Quelle, Urheber, Lizenz; ungeklärte Rechte deutlich genannt | ⏳ | ⏳ | ⏳ |
| Abgebrochene Übernahme ändert nichts; bestätigte Übernahme ergibt `stored`, keine Buchabbildung | ⏳ | ⏳ | ⏳ |
| Ausgabe in PDF, DOCX und EPUB mit Bildunterschrift und Alternativtext | ⏳ | | |

## 5. Hintergrund-Warteschlange (#476)

| Prüfung | Ergebnis |
|---|---|
| Drei Rechercheaufträge kurz hintereinander (Chat bzw. Web-App) werden alle erledigt | ⏳ *optional, kostet* |
| Abgebrochener Lauf: Ergebnis des ersten Auftrags bleibt, Rest läuft beim nächsten Lauf | ⏳ *optional, kostet* |
| Claude-Web-App: Recherche mit Internet → Nachsehen → „Trotzdem starten“ | ⏳ *optional, kostet* |
| „GhostWriter aktualisieren“ von Hand stößt liegengebliebene Aufträge an; bei Pause startet nichts | ⏳ |

## 6. Kosten (#66)

| Prüfung | Ergebnis |
|---|---|
| `costs.py . summary` trennt tatsächlich, geschätzt, manuell und unbekannt; unbekannte Beträge nicht als 0 | ⏳ |
| `costs.py . add` trägt eine Rechnung ein; Projektübersicht zeigt die Summe | ⏳ |

## 7. Release (#488)

| Prüfung | Ergebnis |
|---|---|
| „Release vorbereiten“ meldet „bereit zum Scharfschalten“; Release-PR mit grünem `validate` | ✅ (24.11., PR #546, technisch; Notes noch Entwurf) |
| Notes überarbeitet, Markierung entfernt, Release-PR übernommen | ⏳ |
| „Release 1.0.0 freigeben und veröffentlichen“: Tag `v1.0`, Release, Website zeigt 1.0.0 (#530) | ⏳ |
---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
