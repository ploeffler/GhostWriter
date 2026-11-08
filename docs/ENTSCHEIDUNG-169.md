# Entscheidung #169: Arbeits-Branch bei Bedarf beibehalten

Entschieden am 08.11.2026. Bezug: [Issue #169](https://github.com/ploeffler/GhostWriter/issues/169).

## Entscheidung und Zweck

GhostWriter behält einen gemeinsamen Arbeits-Branch je Buch bei, solange offene Änderungen vorliegen. Er wird erst für die erste autorisierte Speicherung benötigt, nicht beim Öffnen oder Lesen. Nach bestätigter Übernahme wird er entfernt, sofern sein aktueller Stand vollständig übernommen ist. Die nächste Speicherung beginnt wieder vom aktuellen Buchstand.

Der Buch-Branch enthält den übernommenen Stand. Das Änderungspaket sammelt gespeicherte Vorschläge, ermöglicht ihren Vergleich und bündelt ihre Übernahme. Das ist keine inhaltliche Freigabe: Auch übernommener Text kann unfertig sein. Abschnitts-, Kapitel- und Auflagenfreigaben bleiben eigenständige Entscheidungen.

Die bestehende Einstellung `changes.auto_merge: true` bietet den einfachen Weg für Einzelautoren: autorisierte Änderungen speichern, prüfen und unmittelbar übernehmen. Der Arbeits-Branch bleibt dabei ein technischer Zwischenschritt. Formale Freigaben und die gesonderte Bestätigung einer Auflage werden dadurch nicht ersetzt.

## Bedienvorgabe D04

Nach dem bestätigten [Beschluss D04](ENTSCHEIDUNGEN-v1.0.md#d04--entscheidung-169-verbindlich-machen) ist die technische Trennung für Benutzer unsichtbar: keine Branch-Auswahl oder Branch-Verwaltung im normalen Bucharbeitsablauf. Gespeichert, übernommen, freigegeben und fehlgeschlagen bleiben verständlich unterscheidbar. Technische Diagnose auf ausdrücklichen Wunsch bleibt möglich. Die Dokumentation dieser Vorgabe ist noch kein Nachweis, dass alle bestehenden Anzeigen bereits entsprechend geprüft oder angepasst wurden.

## Tatsächlicher Ablauf und Grenzen der Umsetzung

- `scripts/library.py::work_branch` setzt den konfigurierten Präfix vor den vollständigen Buch-Branch. `new_book` liefert diesen Namen nur als Planungswert zurück. `create_book` legt den Buch-Branch an und speichert dessen Startdaten; es legt keinen allgemeinen Buch-Arbeits-Branch an.
- `START.md`, „Schreiben ins Repository“, steuert derzeit den allgemeinen Schreibweg durch den ausführenden Assistenten und dessen Git-/GitHub-Werkzeuge: erst bei einer Änderung vom aktuellen Buch-Head abzweigen, zusammengehörige Dateien atomar speichern und genau ein offenes Änderungspaket zum Buch-Branch führen.
- Die Open-WebUI-Direktanbindung ist kein allgemeiner Buch-Schreibdienst. Der entsprechende Dienst in `docs/API-CONTRACT.md` ist ein Vertragsentwurf, keine bereits implementierte zentrale Schreib- und Sperrverwaltung.
- `scripts/library.py::build_library` ermittelt offene Commit-Unterschiede zwischen Buch- und Arbeits-Branch. Der tatsächliche offene Pull Request und sein Ziel müssen zusätzlich geprüft werden; ein Branchname allein beweist keinen aktiven Arbeitsstand.
- `.github/workflows/cleanup.yml` besitzt einen Aufräumweg für übernommene Branches. Das ist keine Garantie, dass jeder Client nach jeder Übernahme sofort löscht. Ein übrig gebliebener Branch darf nicht ungeprüft zum neuen Arbeitsstand werden.
- `ghostwriter/chat/<session>` aus `scripts/chat_backup.py` ist eine gesonderte Sitzungssicherung und kein Buch-Arbeits-Branch. Programmänderungen haben eigene Entwicklungsbranches und Änderungspakete.

## Lebenszyklus und Fehlerfälle

1. **Öffnen:** Buch-Branch, exakt zugehörigen Arbeits-Branch und offenen Pull Request live prüfen. Bei passendem offenem Änderungspaket aus dem Arbeits-Branch lesen, sonst aus dem Buch-Branch.
2. **Erste Speicherung:** aktuelle Basis und Berechtigung prüfen. Nur bei tatsächlichen Änderungen den Arbeits-Branch aus dem aktuellen Buchstand erzeugen. Alle Dateien einer Aufgabe in einem Commit speichern und den passenden Pull Request anlegen.
3. **Weitere Speicherung:** denselben offenen Arbeitsstand verwenden. Er ist gemeinsam, kein privater Bereich eines einzelnen Chats. Vor jedem Schreiben Heads und betroffene Dateien gegen den gelesenen Ausgangsstand prüfen.
4. **Parallelität:** Branch-Erzeugung und Ref-Aktualisierung dürfen keinen konkurrierenden Stand überschreiben. Bei neuerem Stand erneut lesen; nicht kollidierende Änderungen auf aktueller Basis vorbereiten, kollidierende Änderungen mit erhaltener Benutzereingabe klären. Kein Force-Push als Konfliktlösung.
5. **Übernahme:** den tatsächlich bestätigten Head prüfen. Bei nachträglichen Änderungen erneut bestätigen lassen. Mit Merge-Commit übernehmen, damit die einzelnen Aufgaben-Commits erhalten bleiben. Danach nur den vollständig übernommenen, unveränderten Arbeits-Branch entfernen.
6. **Fehler:** fehlgeschlagene Speicherung oder Übernahme offen melden und den bestätigten Speicherstand nennen. Existiert ein Commit ohne Pull Request, zuerst dessen Basis, Inhalt und Ziel prüfen und die fehlende Zuordnung reparieren; nicht löschen oder blind erneut schreiben. Bei unbekanntem Ausgang keine Erfolgsmeldung.
7. **Abgebrochenes Änderungspaket:** Schließen ohne Übernahme löscht keine Inhalte automatisch. Ein zurückgebliebener Branch mit eigenen Commits verlangt eine ausdrückliche Entscheidung über Fortsetzen, Sichern oder Verwerfen. Verwerfen braucht eine gesonderte Bestätigung.

Das sind verbindliche Anforderungen an Assistenten und künftige Schreibdienste. Sie behaupten weder eine bereits vorhandene zentrale Transaktionssperre noch eine vollständige Synchronisationsgarantie. Der clientübergreifende Standabgleich bleibt Aufgabe #179; die eigene Verwaltungs-API bleibt #19. Keine dieser Entscheidungen erfordert eine KI-Anbieter-API.

## Warum der Name bleibt

`ghostwriter/<vollständiger-buch-branch>` ist eine technische Konvention, keine fachliche Hierarchie. Sie liefert eine eindeutige, deterministische Zuordnung: `buch/roman` wird zu `ghostwriter/buch/roman`, ein Einzelbuch auf `main` zu `ghostwriter/main`. Das zusätzliche `buch/` erhält den vollständigen Ausgangsnamen und vermeidet eine neue Zuordnungstabelle. Eine Umbenennung würde vorhandene Clients, offene Änderungspakete und Bibliotheksabfragen ändern, ohne den Benutzerablauf zu vereinfachen.

## Bewertete Alternativen

| Alternative | Vorteil | Nachteil und Entscheidung |
|---|---|---|
| Direkt auf den Buch-Branch schreiben | Weniger technische Zwischenschritte | Gespeicherte Vorschläge wären sofort übernommen; die bestehende Übernahmeentscheidung und Vergleichsstelle entfielen. Für v1.0 verworfen. |
| Ein neuer Branch je Aufgabe | Änderungen isoliert prüfen | Mehrere konkurrierende Lesestände und Änderungspakete je Buch; zusätzliche Integration und Konflikte. Für den gemeinsamen Buchworkflow verworfen. |
| Nur lokale oder im Chat gehaltene Entwürfe | Weniger GitHub-Objekte | Kein gemeinsamer dauerhaft gespeicherter Vorschlagsstand für andere Clients. Als alleiniger Speicherweg verworfen. |
| Ein gemeinsamer Arbeits-Branch bei Bedarf | Ein nachvollziehbarer offener Arbeitsstand; vorhandene Regeln und Werkzeuge nutzbar | Heads, Konflikte und Bereinigung müssen geprüft werden. Gewählt; automatische Übernahme bleibt die vorhandene Bedienvereinfachung. |

## Konsequenzen für v1.0

Keine Umstellung der Branch-Namen, keine Migration und kein neuer Schreibmodus. START.md und API-Vertrag behalten den bestehenden Ablauf; dieses Dokument präzisiert seine Grenzen und Fehlerfälle. Für #19, #35 und #179 ist das Modell die Grundlage. Die konkrete Implementierung zentraler Parallelitäts- und Wiederanlaufprüfungen bleibt dort zu prüfen und abzunehmen. Offene Buchänderungen werden durch diese Architekturentscheidung weder übernommen noch verworfen.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
