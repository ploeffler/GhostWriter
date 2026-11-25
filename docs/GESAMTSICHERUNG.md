# Gesamtsicherung

Deutsch · [English](FULL-BACKUP.en.md)

Die **Gesamtsicherung** (#489) packt das ganze Repository in **eine** ZIP-Datei: lesbar ohne Git und ohne GitHub, und vollständig wiederherstellbar bei GitHub oder auf einem eigenen Git-Server (Gitea, Forgejo, nacktes Git). Sie ist nicht dasselbe wie [Session sichern](SESSION-SICHERUNG.md), das nur Gesprächsarbeit festhält.

**Starten:** im Chat `Sicherung erstellen` (die Datei kommt als Download) oder auf GitHub unter *Actions → Gesamtsicherung → Run workflow*. Dort liegt das Ergebnis als **privates Workflow-Artefakt** (nur für Personen mit Zugriff auf das Repository, 14 Tage), nie als Release. Lokal: `python3 scripts/sicherung.py erstellen <ordner> -o sicherung.zip`.

## Was in der Datei steht

```
GhostWriter-Sicherung_<repo>_<datum>.zip
├── LIESMICH.html              zuerst öffnen: Inhalt, Lesen, Wiederherstellen, Grenzen
├── buecher/<buch>/
│   ├── buch.html              ganzes Buch, im Browser lesbar
│   ├── buch.epub              für E-Reader
│   ├── buch.pdf               zum Drucken (wenn LaTeX zur Verfügung stand)
│   └── quelltext/             Kapitel (.md), Bilder, Buchprofil
├── repository.bundle          vollständiges Git: alle Branches (auch buch/*), Tags, Historie
├── github-einstellungen.json  Einstellungen, die nicht im Git liegen (Secrets nur mit Namen)
├── github-daten/              Issues und Pull Requests mit Kommentaren: lesbar.md und JSON
├── wiederherstellen/          auf-github.sh/.bat, lokal-oeffnen.sh/.bat
└── pruefsummen.txt            SHA-256 aller Dateien, Datum, Programmversion, Stand der Branches
```

Die Lesefassung zeigt den **Arbeitsstand** aller Abschnitte, keine Auflage. Sie wird ohne KI aus dem Text zusammengestellt, nichts wird umformuliert.

## Wiederherstellen

- **Lokal:** `git clone repository.bundle mein-buch`; danach auf jedes beliebige Ziel pushen.
- **GitHub:** leeres Repository anlegen, dann `./wiederherstellen/auf-github.sh https://github.com/NAME/neues-repo.git` (Windows: `auf-github.bat`). Das Skript prüft vorher die Prüfsummen und `git bundle verify`, klont einen Spiegel und überträgt alles mit `git push --mirror`; der GitHub-Import selbst nimmt keine Bundles an. Mit `gh` und `python3` setzt es zusätzlich die Einstellungen (siehe unten) und fragt jeden Secret-Wert einzeln ab (leer = später).
- **Eigener Git-Server:** `./auf-github.sh <url> nur-git` überträgt nur das Git.
- **Prüfen ohne Wiederherstellen:** `python3 scripts/sicherung.py pruefen <datei.zip>`.

## Einstellungen, die nicht im Git liegen

Workflows (`.github/workflows/`) kommen mit dem Git zurück. Alles andere steht in `github-einstellungen.json` und wird, soweit der Zugang es erlaubt, gesichert:

| Einstellung | Gesichert | Beim Wiederherstellen |
|---|---|---|
| Secrets | **nur Namen**, nie Werte | das Skript fragt die Werte ab; Übersprungenes steht in der Liste „noch offen“ |
| Variablen (`vars.*`) | Namen und Werte | per `gh` gesetzt |
| Actions aktiviert, Workflow-Rechte (lesen/schreiben, Pull Requests anlegen) | Zustand | gesetzt (GhostWriter braucht Schreibrecht) |
| Pages, Environments, Branch-Schutz, Mitarbeitende | Konfiguration, soweit lesbar | von Hand nach `LIESMICH.html` |
| Installierte GitHub-Apps | nicht über die API lesbar | bitte notieren |
| Laufverlauf, Logs, Artefakte | – | gehen verloren |

Was der Zugang nicht lesen durfte (etwa Mitarbeitende ohne Admin-Recht), steht mit Grund unter `nicht_lesbar`; die Sicherung bleibt gültig. Am Ende der Wiederherstellung hilft ein Probelauf („Projektdateien prüfen“ unter *Actions*): Läuft er, laufen die Actions.

## Grenzen

- **Nie** werden Secret-Werte gelesen oder ausgegeben. Die Sicherung prüft sich selbst auf Schlüssel-Muster; findet sie eines (zum Beispiel in einem Issue-Text), wird sie nicht ausgeliefert.
- Die Datei enthält **private Bucharbeit**: nur als Download im Chat oder als privates Artefakt weitergeben, nie als Release und nie öffentlich.
- Ein flacher Klon (ohne Historie) wird abgelehnt: erst `git fetch --unshallow`.
- Nicht in dieser Fassung: Verschlüsselung mit Passwort und eine automatische monatliche Sicherung (beides später, bei Bedarf).


---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
