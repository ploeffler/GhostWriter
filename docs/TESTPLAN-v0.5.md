# Testplan v0.5

Abnahme aller v0.5-Funktionen (`workflow.yml`, `product_roadmap.v0_5.scope`) mit
zwei Testprojekten (#18):

- **ADHS:** Testbuch „ADHS im Erwachsenenleben“, Branch `test/test-book`
  (Repository-Fassung von `tests/fixtures/adhs`, gekennzeichnete Testdaten).
- **Leer:** `tests/fixtures/leeres-projekt` (kein Titel, keine Kapitel).

Automatische Tests: `python -m unittest discover -s tests -p "test_*.py"`
(läuft in `validate.yml` bei jedem Push). Alles andere wird im Chat bzw. auf
GitHub geprüft; Ergebnisse stehen als Kommentar in #18 (v0.5) bzw. #28 (v0.3).

Legende: ✅ bestanden · ⏳ offen · — nicht anwendbar

## 1. Projekt anlegen und einrichten (`project_create_and_setup`)

| Prüfung | ADHS | Leer | Wo |
|---|---|---|---|
| Wiedereinstieg: Link zum Repository → Projektübersicht | ✅ | ⏳ | Chat, #28 |
| Projektdaten bearbeiten und speichern (Formular, Commit) | ✅ | ⏳ | Chat, #28 |
| Projekteinstellungen (Updates, Buchsatz) | ⏳ | ⏳ | Chat, #28 |
| KI-Dienste wählen, Schlüssel nur als GitHub-Secret | ✅ | ⏳ | Chat, #28 |
| Onboarding im leeren Projekt bis zur Kapitelstruktur | — | ⏳ | Chat, #28 |
| Buchstruktur als ein Commit (bzw. ein zusammengefasster Merge), Commit-Nachrichten deutsch | — | ⏳ | Erststart, #63 |
| Prüf-Action `validate.yml` grün | ✅ | ✅ | Actions |

## 2. Kapitel anlegen und einrichten (`chapter_create_and_setup`)

| Prüfung | ADHS | Leer | Wo |
|---|---|---|---|
| Kapitel anlegen (stabile ID, Nummer aus Reihenfolge) | ⏳ | ⏳ | Chat, #28 |
| Kapitel umordnen, IDs bleiben | ⏳ | — | Chat, #28 |
| Abschnitt anlegen und umordnen | ⏳ | — | Chat, #28 |
| Freigegebenes Kapitel wird bei neuem Abschnitt `in_progress` | ⏳ | — | Chat, #28 |

## 3. Kapitel und Abschnitte bearbeiten (`chapter_and_section_editing`)

| Prüfung | ADHS | Leer | Wo |
|---|---|---|---|
| Kapitel- und Abschnittsansicht öffnen | ✅ | — | Chat |
| Abschnitt bearbeiten und speichern (Formular, Commit) | ✅ | — | Chat |
| Änderungen übernehmen (Arbeits-Branch → Buch-Branch) | ⏳ | — | Chat |
| Freigaben: Schreib-, Abschnitts-, Kapitelfreigabe mit Bestätigung, Eintrag in `approvals.yml` | ⏳ | — | Chat, #28 |
| Formular schließen → vorherige Ansicht | ✅ | — | Chat |
| Darstellung in ChatGPT (Textfassung) | ⏳ | ⏳ | #22 |

## 4. KI-Läufe „Sofort“ im Chat (`ai_runs_immediate_in_chat`)

| Prüfung | ADHS | Leer | Wo |
|---|---|---|---|
| Recherchelauf anlegen (unveränderlich, eigene Datei) | ✅ | — | Chat |
| Ghostwriting-Lauf nur mit Schreibfreigabe | ⏳ | — | Chat |
| Kosten nur für Backend-KI-API, Chat-Arbeit ohne Kosteneintrag | ✅ | — | `costs/`, #13 |
| Alte Kosteneinträge als `legacy_chat_estimate` markiert | ✅ | — | Migration |

## 5. Auflage erzeugen (`book_edition_create`)

| Prüfung | ADHS | Leer | Wo |
|---|---|---|---|
| Prüfung vor der Auflage (`assemble.py check`) | ✅ | ✅ | Test, Chat |
| Formular zeigt Hindernisse, legt nichts an | ✅ | ✅ | Test (`EmptyProjectTest`), Chat |
| Probedruck auf GitHub (alle Abschnitte, Marker hervorgehoben) | ✅ | ✅ (Abbruch mit Meldung) | Lauf 41313059245 |
| Auflagen-Pull-Request mit Release Notes, Merge nach Bestätigung | ✅ | — | PR #44 |
| Release mit Tag, PDF, EPUB, DOCX | ✅ | — | Lauf 41314044342 |
| Veröffentlichte Auflage bleibt unverändert | ✅ | — | Lauf 41314550210 |
| Im Chat nur Name, Tag, Release Notes, Links | ✅ | ✅ | Chat |

## 6. Export PDF, DOCX, EPUB (`book_export_pdf_docx_epub`)

| Prüfung | ADHS | Leer | Wo |
|---|---|---|---|
| Nur freigegebene Kapitel und Abschnitte, mit Quellen | ✅ | — | Test |
| PDF: A5, Titelei, Impressum, Inhaltsverzeichnis, Schrift | ✅ (Sichtprüfung 01.11.2026) | — | Probedruck |
| DOCX: Seitengröße, Formatvorlagen, Überschriftenebenen | ✅ | — | Release |
| EPUB baut ohne Fehler | ✅ | — | Release |

## 7. Updates (Teil von v0.5)

| Prüfung | ADHS | Leer | Wo |
|---|---|---|---|
| Tägliche Prüfung gegen das Hauptrepository, Einspielen | ✅ | — | Action „GhostWriter aktualisieren“ |
| Buchdateien bleiben unverändert, Migrationen idempotent | ✅ | ✅ | Update-Lauf, Migration |
| Kein Zurücksetzen auf ältere Version | ✅ | — | Update-Skript |
| Fork in einem zweiten Konto bekommt das Update (eigenes Buch auf `main`) | ⏳ | — | #64 |

## Offen bis zum Abschluss von #18

- Abnahme v0.3 (#28) durch den Benutzer: alle ⏳ in Abschnitt 1–3 (seit 01.11.2026 Teil von v0.5).
- Darstellung in ChatGPT (#22).
- Erststart: Buchstruktur in einem Commit, deutsche Nachrichten (#63).
- Update-Test im Fork (#64).
- Ghostwriting-Lauf mit Schreibfreigabe und Freigabeablauf einmal vollständig im Testbuch.

Funktionen nach v0.5 (Änderungen sofort übernehmen, Befehle, Kapitelrecherche, Doku-Prüfung) werden in der Abnahme v0.6 (#41) geprüft.

---

<sub>Entwickelt mit Unterstützung von Claude (Anthropic) · [claude.ai](https://claude.ai)</sub>
