<!-- Was ändert sich und warum? -->

**Checkliste**
- [ ] Doku nachgezogen (START.md und BEFUELLUNG.md für den Chat, DATA-MODEL, API-CONTRACT, WORKFLOW-MODEL); `python scripts/check_docs.py --ui ../ghostwriter-ui` grün
- [ ] Ändert sich die Datenstruktur des Buchs? Dann Migration in `scripts/migrate_project.py` mit Test (#59)
- [ ] Tests ergänzt bzw. angepasst; `python -m unittest discover -s tests -p "test_*.py"` grün
- [ ] Neue Fassung von ghostwriter-ui? Fester Commit in `templates/ui/ghostwriter-ui.yml`
