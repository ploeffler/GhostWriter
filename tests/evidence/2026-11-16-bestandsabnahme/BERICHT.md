# Fortschritte der Bestandsabnahme Richtung v1.0

Stand: 16. November 2026. [English](REPORT.en.md).
Basis: `007f529b9b38543b019e9859f195aaf5cb96cff2`, Programmversion 0.6.1.
Die Versionsnummer ersetzt keine vollständige Abnahme. Die weitere
Zwischenversionsfolge bleibt ein Vorschlag.

## Umgesetzt und lokal geprüft

- Ein neuer fiktiver Buchlebenszyklus prüft Buchanlage, Struktur, Entwurf,
  Überarbeitung, Abschluss, Erkennung nachträglicher Textänderungen,
  Wiederöffnen, neue Schreibfreigabe, erneuten Abschluss, lokale Übernahme
  sowie DOCX-/EPUB-Probedruck und Testauflage. Bibliotheks-Hauptstand, zweites
  Buch und lokaler Auflagen-Tag bleiben erhalten. Bestätigungen sind im
  Testtreiber simuliert, keine echte Personen- oder Clientabnahme.
- Die Open-WebUI-Branchlöschung und beide Löschwege der Aufräum-Action verwenden
  GitHubs GraphQL `updateRefs` mit erwartetem `beforeOid`. Bei Versionsbranches
  muss in derselben atomaren Operation auch der Erhaltungstag unverändert
  vorhanden sein. Neue Commits oder geänderte Tags verhindern die Löschung.
  GraphQL-Fehler und unklare Antworten sind kein Erfolg; kein unbedingter
  Löschversuch als Ersatz, keine automatische Wiederholung. Vorschau bleibt
  ohne Löschmutation; unbestätigte Löschungen werden getrennt ausgewiesen.
- Historische Testplanaussagen sind fachlich präzisiert: Bibliotheksansicht auch
  bei nur einem Buch; Versionsangabe aus dem Manifest. Ein zunächst angenommener
  Versionswiderspruch wurde verworfen: Der geprüfte Hauptstand trägt bereits 0.6.1.

## B04: bestätigter Befund und Entscheidung

Die lokale Diagnose [`b04_probe.py`](b04_probe.py) zeigt am fiktiven abgeschlossenen
Buch: Ein fremder Name in `approvals.yml` wird nicht authentifiziert. Validator
und Assembler akzeptieren den unveränderten Inhalt weiterhin. Eine anschließend
vorgenommene Textänderung wird dagegen von beiden erkannt. Mit simuliertem HTTP-
Transport akzeptiert das bisherige Open-WebUI-`commit_files` einen Auftrag ohne
anfragende Personenidentität sowohl an Arbeits- als auch Buchbranch.
[`b04-befund.json`](b04-befund.json) hält die Beobachtungen fest. Kein echter
GitHub-Zugriff und keine Umgehung tatsächlicher Repository-Rechte nachgewiesen.
Die Diagnose schreibt das unerwünschte Verhalten nicht als Soll-Regression fest.

Der Benutzer hat **persönliche GitHub-Konten für die Zusammenarbeit bestätigt**.
Nur Eigentümer oder ausdrücklich benannte Freigabeberechtigte dürfen inhaltlich
freigeben (D03). Gemeinsame privilegierte Tokens, Chatnamen, Profilautoren und das
frei eingetragene Feld `by` sind kein Berechtigungsnachweis.

Die technische Personenbindung ist **noch nicht implementiert oder abgenommen**.
Nächste Schritte: persönliche Zugänge ohne gemeinsamen privilegierten Rückfall
an Schreibaufträge binden; Identität über den tatsächlich verwendeten GitHub-
Zugang verifizieren; eine geschützte Eigentümer-/Delegationsquelle bestimmen;
alle angenommenen Buch- und Veröffentlichungswege berücksichtigen, auch externe
Git-Werkzeuge und manuelle Actions. Regeln für eigene PRs und Organisationen sowie
lokale Grenzen gesondert prüfen. Keine neue Kontenverwaltung beauftragt.

## Prüfnachweise und Grenzen

| Prüfung | Ergebnis |
|---|---|
| Gesamtlauf mit B03-Produktkorrektur und A02-Tests | 556 Tests, keine Fehler, 16 übersprungen |
| Gezielter B03-Lauf | 56 Tests erfolgreich |
| B04-Dokumentation/Start-/Freigabeknöpfe | 27 Tests erfolgreich, keine übersprungen |
| Dokuprüfung | Erfolgreich, ohne externe UI-Prüfung |
| Website, Offline-Paket und Wiki | Lokal erfolgreich; Wiki 43 Seiten, Version 0.6.1 |
| Aufräum-Action | Tatsächliche Shell-Schritte gegen lokale Bare-Remotes; gh-Ersatz bildet die dokumentierte atomare Prüfung mit echten Git-Transaktionen nach |

Die Läufe überlappen; Zahlen nicht addieren. Die 16 übersprungenen Fälle bleiben
offen. Insbesondere fehlen praktische Client-/Rollenabnahme und PDF-/Sichtprüfung.
Die bedingte Löschung ist lokal mit simuliertem GitHub-Transport geprüft; echte
GitHub-/Tokenabnahme steht aus. Kein realer Branch wurde durch die Prüfung gelöscht.
Die Dokumentationsnachträge ändern den geprüften Produktcode nicht.

Für die gemeinsame Sicherung wird dasselbe Paket erneut lokal geprüft. Die
Ergebnisse dieses abschließenden Laufs stehen in der PR-Beschreibung. Dieses
Paket ist weder Produktrelease noch Veröffentlichung, Update einer Buchinstanz
oder Bestätigung der vollständigen A01-/A02-Abnahme. Persönliche Übergaben,
lokale Rohprotokolle, Patcharchive und erzeugte Testbücher sind ausgeschlossen.

Die Abhängigkeiten für lokale Tests folgen den bestehenden Projektprüfungen;
für die B04-Diagnose werden zusätzlich die temporär installierten optionalen
Open-WebUI-Bibliotheken benötigt. Wiederholung nach deren Installation:

```sh
python3 tests/evidence/2026-11-16-bestandsabnahme/b04_probe.py \
  --source . --output /tmp/b04-befund.json
```

## Quellen

- [GitHub: atomare Ref-Änderungen und beforeOid](https://docs.github.com/en/graphql/reference/git#updaterefs)
- [Open WebUI: Benutzerkontext und persönliche Valves](https://docs.openwebui.com/features/extensibility/plugin/development/reserved-args/)
- [GitHub: Code Owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

---

Entwickelt mit Unterstützung von Claude (Anthropic)
Entwickelt mit Unterstützung von Codex (OpenAI)
