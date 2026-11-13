# Prompt-Optimierung – gesicherter Arbeitsstand

Stand: 7. November 2026. Fortsetzung von
[Issue #204](https://github.com/ploeffler/GhostWriter/issues/204).

## Wiedereinstieg

Zuerst diese Datei, den [inhaltlichen Abgleich](PROMPT-ABGLEICH.md) und die
[Profiler-Dokumentation](PROMPT-PROFILER.md) lesen. Der nächste Umsetzungsschritt
ist ein maschinenlesbarer Anweisungskatalog mit Quellen, Geltungsbereichen,
Aktivierungsbedingungen, Prioritäten und Konfliktregeln. Noch keine weiteren
Prompts kürzen. Der Compiler ist nicht implementiert.

Entwicklung in `ploeffler/GhostWriter`, zuletzt auf
`codex/navigation-diagnose`, Programmstand `446b669`.
[PR #206](https://github.com/ploeffler/GhostWriter/pull/206) und
[PR #207](https://github.com/ploeffler/GhostWriter/pull/207) wurden nach main
übernommen. Die folgenden Ergänzungen wurden auf dem Diagnosebranch bereitgestellt:

- `d3217a7`: Direkt-Pipe 1.7.1, Navigation prüfen.
- `2509fc3`: GitHub-Werkzeug 1.4.1, falschen Zugriff auf `library_source` im
  Bibliothekskontext durch den tatsächlich gelieferten Quellstand ersetzt.
- `446b669`: Direkt-Pipe 1.8.0, explizite Herkunftsangaben im Profiler.

Dazu gehört [PR #208](https://github.com/ploeffler/GhostWriter/pull/208).
Vor weiteren Veröffentlichungen seinen aktuellen Status prüfen; aus dieser
Notiz keinen Merge-Status ableiten. Andere lokale Änderungen nicht ungeprüft
in diese Arbeit aufnehmen.

## Implementiert und getestet

- Lesender Snapshot-Profiler für OpenAI-/Anthropic-Formate und Open-WebUI-Pipe.
- Optionaler Mitschnitt vor direkten API-Aufrufen und getrennte Provider-Usage.
- Offline-Aggregation, exakte Nachrichtenduplikate, Metadaten und Fingerprints.
- Open-WebUI-Diagnose `Prompt-Profil`, ausführlich `Prompt-Profil JSON`, ohne
  Modellaufruf und ohne bezahlten API-Zugang.
- Optionale Valve `PROMPT_PROFILE` für Metadaten bei normalen Weiterleitungen.
- Herkunft: `read_start_md.content`, `openwebui.input.messages`,
  `pipe.current_context`; keine Herkunft anhand ähnlicher Texte erraten.
- Zentraler Profiler wird mit `scripts/build_openwebui_profiler.py` in die
  einzeln installierbare Pipe eingebettet; `--check` prüft Übereinstimmung.
- Zuletzt 26 Pipe- und 15 Profiler-Tests bestanden. Regressionstest für den
  Bibliothekskontext ebenfalls bestanden; Doku-Prüfung bestanden.

Bekannte Prüfgrenzen: Im Standard-Gesamtlauf zuvor 347 Tests, ein bekannter
Fehler im englischen Auflagenformular und 68 übersprungene Tests. Der Fehler
wird separat in PR #205 behandelt. Ein Gesamtlauf mit optionalen Abhängigkeiten
blieb lokal unter Python 3.14 im unveränderten GitHub-Werkzeugtest hängen und
wurde abgebrochen. Diese Grenzen nicht als erfolgreich geprüfte Gesamtsuite
beschreiben. Nach dem letzten rein dokumentarischen Abgleich kein erneuter
Gesamtlauf erforderlich gewesen.

## Live-Test und beobachteter Umfang

Der Benutzer hat die Direkt-Pipe und das GitHub-Werkzeug in Open WebUI manuell
aktualisiert. Repository-Updates ersetzen importierten Open-WebUI-Code nicht
automatisch. Navigationsdiagnose und ein echter strukturierter Profilerbericht
funktionierten anschließend. Ein anfangs ausgegebenes Stil-JSON war kein
Profilerreport und wurde nicht als bestätigte Stilvorgabe übernommen.

Die Diagnosevorschau verwendete `llama3.2:3b` und schätzte mit Zeichen/3,5:

| Bestandteil | Vor Deaktivierung des Zusatzprompts | Danach |
|---|---:|---:|
| GhostWriter-Startnachricht | 5.925 Zeichen / ~1.693 Tokens | unverändert |
| Open-WebUI-Systemnachricht | 1.760 Zeichen / ~503 Tokens | 789 Zeichen / ~226 Tokens |
| Frischer Kontext samt Gesprächsregeln | 2.128 Zeichen / ~608 Tokens | unverändert |
| Gesamte sichtbare Anfrage | 10.470 Zeichen / ~2.992 Tokens | 9.499 Zeichen / ~2.714 Tokens |

Die übrigen Nachrichten-Fingerprints waren identisch. Beobachtete Differenz:
971 Zeichen bzw. rund 278 geschätzte Tokens (9,3 % der vorherigen
Gesamtschätzung). Das ist ein Umfangsvergleich an der Pipe-Grenze, keine
Provider-Token-, Kosten- oder Qualitätsmessung. Die zusätzliche
Herkunftserfassung änderte den untersuchten Anfrageinhalt nicht.

Der Benutzer stellte den entfernten Prompt bereit: Er regelte Start,
Werkzeugnutzung, Deutsch, kurze Antworten und Freigaben. Er enthielt keine
eigenständige Erzählstimme. Die Vermutung, es handle sich um eine Stimmvorgabe,
wurde dadurch nicht bestätigt. Der Benutzer hat diesen Zusatz deaktiviert.
Die Quelle und der Inhalt des verbleibenden externen Blocks sind ungeklärt.
Nicht erneut den bereits gelieferten entfernten Prompt verlangen und nicht
aus der Restlänge auf einen weiteren Benutzereintrag schließen.

## Ergebnisse des inhaltlichen Abgleichs

- Allgemeine Startanweisungen fordern Werkzeug-/Dateizugriffe, die dem Modell
  im freien Pipe-Gespräch nicht bereitgestellt werden. Die Pipe erledigt ihre
  implementierten Aktionen selbst. Fähigkeiten und Geltungsbereiche müssen
  ausdrücklich getrennt werden.
- Sprache, Kürze, Aktualität und Freigabeschutz überschneiden sich teilweise,
  besitzen aber unterschiedliche Geltungsbereiche. Keine automatische Löschung.
- Nummernbedeutung, ausgewählter Abschnitt, getrennte Kapitel-/Abschnittsstatus
  und Dateneinordnung sind zusätzliche Schutzregeln der Pipe.
- Phase 1 ist noch nicht vollständig abgenommen. Semantische Befunde sind
  Vorschläge, keine autoritativen Regelentscheidungen.

## Noch offen

1. Anweisungskatalog vorbereiten; maßgebliche Originalregeln erhalten.
2. Externe Open-WebUI-Vorgaben nur mit belegter Herkunft einordnen.
3. Tests für Regel-Erhalt und repräsentative Aufgaben vor einer Compilerfassung.
4. Danach kontrollierte Vorher-/Nachher-Vergleiche; Rückfall auf Original
   sicherstellen. Keine Einsparung allein aus ungeprüften Kürzungen behaupten.
5. Keine zusätzlichen kostenpflichtigen API-Aufrufe für die lokale Diagnose
   voraussetzen. GitHub-Analyse-Actions benötigen weiterhin eigene API-Schlüssel;
   dieser Weg ist von der kostenlosen Pipe-Diagnose getrennt.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a></sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
