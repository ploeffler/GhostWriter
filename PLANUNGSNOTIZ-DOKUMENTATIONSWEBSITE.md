# Zentrale Dokumentationswebsite für GhostWriter

Am 8. November 2026 im Gespräch bestätigt. **Ursprüngliche Planungsentscheidung; Umsetzung am 9. November 2026 ausdrücklich vorgezogen beauftragt. Kein Auftrag zur Veröffentlichung.** Die Zuordnung zu **v0.9.0**, einschließlich Aufbau und Veröffentlichung, wurde am 8. November 2026 ausdrücklich bestätigt. Die technische Umsetzung wird als zusammenhängender PR vorbereitet; Übernahme und Aktivierung bleiben gesondert freizugeben.

## Beschlossener Rahmen

- Eine zentrale öffentliche Dokumentationswebsite für das Programm GhostWriter, aus dem Hauptrepository gepflegt.
- Gemeinsame Inhaltsquelle sind die vorhandenen Dokumente unter `docs/`. Keine unabhängig gepflegte zweite Fassung als Wiki.
- Deutsche und englische Inhalte auf derselben Website mit passender Navigation zwischen den Sprachfassungen.
- Benutzerhandbuch für Einrichtung, Bedienung, Arbeitsabläufe, Bilder/Grafiken, Einstellungen, Bedienglossar und Problemlösungen; vorhandene grafische Ablaufseiten wiederverwenden.
- Keine automatisch angelegten Websites für Buch-Repositories, Forks oder einzelne Bücher. Keine Buchtexte, Gesprächssicherungen oder privaten Projektdaten auf die zentrale Website übernehmen.

## Ursprüngliche Klärungspunkte (8. November 2026)

- Geeignetes Werkzeug für den Aufbau der Website, Navigation, Suche, Sprachwechsel und Grafikdarstellung.
- Hosting und öffentliche Adresse; daraus keine zusätzliche Plattformbindung oder Kostenfreigabe ableiten.
- Ob und wie ein Dokumentationsaufbau im Hauptrepository ausgelöst wird, zunächst lokal prüfbar und passend zur sparsamen GitHub-Nutzung.
- Klare Trennung zwischen Prüfen, Website bauen und öffentlich veröffentlichen. Der bestehende Dokumentationscheck erzeugt keine Website.
- Welche Unterlagen öffentliches Benutzerhandbuch sind und welche internen Arbeitsaufträge, Planungsnotizen oder historischen Testberichte nicht auf die Website gehören.
- Pflege der Links und Sprachfassungen sowie Abnahme der gerenderten Seiten, Suche, mobilen Darstellung und der gemeinsamen Doku-Fußzeile.
- Versionszuordnung: v0.9.0 gemäß bestätigter Ergänzung in `PLAN-v1.0-ZWISCHENVERSIONEN.md`; kein kalendarischer Termin festgelegt.

Vor einer Veröffentlichung den konkreten lokalen Stand und das Ziel reviewbar bereitstellen. Diese Notiz allein autorisiert weder GitHub-Übertragung noch öffentliche Bereitstellung oder Änderungen an Buch-Repositories.


## Vorgezogene Umsetzung am 9. November 2026

Ausdrücklich beauftragt: vollständig lokal vorbereiten und prüfen, danach zusammenhängend als **einen PR** hochladen; nicht mergen und keine Veröffentlichung starten. Der bestehende Auftritt bleibt unverändert erreichbar. Browserzugriff erfordert eine gesonderte ausdrückliche Freigabe.

- Python-basierter statischer Aufbau aus ausgewählten Quellen unter `docs/`, Navigation, lokale Suche, direkte Sprachpaare und sichtbare Manifestversion. Keine zweite Wiki-Fassung.
- Öffentliche Auswahl in `docs/site.json`; interne Planungsunterlagen, private Buchtexte und Chats werden nicht mitgebaut. Vorhandene Ablaufgrafiken und bereits veröffentlichte „So einfach“-Seiten werden eingebunden.
- Lokale Vorschau und reproduzierbares Paket mit den bisherigen Beispielseiten. Quelldateien unter `website/` bleiben unverändert.
- Nur prüfendes CI; der bestehende Pages-Ablauf bleibt ausschließlich manuell. Neuer Dokumentationsmodus ist standardmäßig aus und darf erst nach ausdrücklicher Veröffentlichungsfreigabe gewählt werden. Kein Veröffentlichungsworkflow wird für diesen Auftrag gestartet. Die regulären Prüfungen beim PR-Upload bleiben aktiv.
- Verbindliche Pflege und fachliche Prüfung beider Sprachen sowie Dokumentationsabschluss pro Programmrelease: [Dokumentationspflege](docs/DOKUMENTATION-PFLEGE.md), AGENTS.md, CLAUDE.md und PR-Checkliste.

Damit wird der technische Website-Block aus der bisherigen v0.9.0-Zuordnung vorgezogen; die übrige Versionsfolge bleibt unverändert und weiterhin im bisherigen Beschluss-/Vorschlagsstatus. Programmversion bleibt 0.6.0 gemäß Manifest. Die Vorziehung ist kein v0.9.0-Produktrelease.

Die gerenderte Browserabnahme (Desktop, schmale Ansicht und Bedienung) und die öffentliche Abnahme bleiben bis zur Browser-/Veröffentlichungsfreigabe offen. Erfolgreiche lokale Struktur- und Funktionstests ersetzen diese Abnahmen nicht.
