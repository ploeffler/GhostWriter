# Wiki-Gestaltung und Aufbau

Das Wiki verwendet Logo, Seitenfolge, Titel und Inhalte der Dokumentationswebsite. GitHub bestimmt Schriftbild und Seitenrahmen; eigenes CSS wird nicht eingebunden. Die Startseiten bieten Sprachwechsel, Inhaltsübersicht und Links zur Website mit Suche. Die gemeinsame Seitenleiste enthält beide Sprachen, da GitHub nur eine globale Seitenleiste vorsieht. Jede Inhaltsseite zeigt die Programmversion. Die KI-Hinweise stehen ausschließlich in der gemeinsamen grauen GitHub-Fußzeilenbox: Claude unmittelbar gefolgt von Codex, auf Deutsch und Englisch. Inhaltsseiten und Home enthalten keine zusätzlichen KI-Fußzeilen. Verständliche Dateinamen liefern die sichtbaren Seitentitel, zum Beispiel „Einstellungen und Ausgabe“ und „Settings and output“. Gleichlautende Titel erhalten einen Sprachzusatz. Sprachwechsel, Seitenleiste und interne Links verwenden diese Namen. Beim Veröffentlichen ersetzen die neuen Seitennamen die bisherigen technischen Kennungen wie de-settings; alte externe Wiki-Links müssen gegebenenfalls angepasst werden.

```sh
python3 scripts/build_docs_wiki.py
python3 scripts/build_docs_wiki.py --check
```

Abhängigkeiten: `scripts/docsite/requirements.txt`. Ausgabe: `build/documentation-wiki/`, ausschließlich aus der öffentlichen Auswahl in `docs/site.json`. Nicht von Hand bearbeiten. Bestehende ältere Ausblickdateien unter `wiki/` werden nicht überschrieben. Quellenänderungen erfordern einen erneuten Aufbau. Quellenprüfsummen und Version stehen in `build-info.json`; diese Datei und die Markierungsdatei gehören nicht in das veröffentlichte Wiki.

Die Markdown-Dateien enthalten GitHub-kompatibles HTML für Tabellen und Abbildungen sowie explizite Sprungziele. Bilder verweisen auf dieselben öffentlichen Dateien im Hauptrepository. Neue Bilder müssen vor der Wiki-Veröffentlichung dort vorhanden sein. Interne Planungslinks werden wie beim Website-Aufbau entfernt; unbekannte relative Verweise brechen den Aufbau ab.

Vor einer Veröffentlichung beide Sprachen im echten GitHub-Wiki ansehen: Logo bei hellem/dunklem Hintergrund, schmale Ansicht, Tabellen, Bilder, Sprungziele, Sprachwechsel, Seitenleiste und Fußzeile. Die lokale Strukturprüfung ersetzt diese Sichtprüfung nicht. Browserzugriff nur nach ausdrücklicher Freigabe. Keine automatische Übertragung, keine Wiki-Aktivierung und kein Löschen vorhandener öffentlicher Wiki-Seiten. Bei später beauftragter Übertragung vorhandene Seiten zuerst abgleichen.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
