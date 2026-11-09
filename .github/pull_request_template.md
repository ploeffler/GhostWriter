<!-- Was ändert sich und warum? -->

**Checkliste**
- [ ] Doku nachgezogen (START.md und BEFUELLUNG.md für den Chat, DATA-MODEL, API-CONTRACT, WORKFLOW-MODEL); `python scripts/check_docs.py --ui ../ghostwriter-ui` grün
- [ ] Ändert sich die Datenstruktur des Buchs? Dann Migration in `scripts/migrate_project.py` mit Test (#59)
- [ ] Tests ergänzt bzw. angepasst; `python -m unittest discover -s tests -p "test_*.py"` grün
- [ ] Neue Fassung von ghostwriter-ui? Fester Commit in `templates/ui/ghostwriter-ui.yml`

**Dokumentationsauswirkung (verbindlich)**
- Betroffene Anleitungen und Sprachpaare unter `docs/` (oder begründet keine Änderung):
- Fachlich gegen Implementierung und Tests geprüfte Abläufe, Freigaben und Grenzen; offene Lücken:
- [ ] Deutsch/Englisch, Beispiele, Grafiken und Navigation gemeinsam nachgezogen; geplante Funktionen markiert
- [ ] `python scripts/build_docs_site.py` und `python scripts/package_docs_site.py` erfolgreich; Dateiauswahl geprüft
- [ ] Fachliche Prüfung abgeschlossen; Reviewer bestätigt Übereinstimmung mit dem Funktionsstand
- [ ] Bei Programmrelease: Version aus Manifest, Quellencommit und öffentlicher Dokumentationsstand nach [Release-Ablauf](../docs/DOKUMENTATION-PFLEGE.md) festgehalten

Upload und grüne Checks erteilen keine Merge- oder Veröffentlichungsfreigabe.
