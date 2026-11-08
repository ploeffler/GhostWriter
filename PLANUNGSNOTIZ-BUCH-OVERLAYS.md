# Überlegungen zu buchbezogenen Overlays

Festgehalten am 8. November 2026 auf Wunsch des Benutzers. **Ideensammlung und Planungsstand, kein Umsetzungsauftrag und keine bereits verfügbare Funktion.** Zunächst nur lokal gespeichert; keine Übertragung zu GitHub beauftragt.

## Ausgangsidee

Benutzer sollen per Chat Anpassungen für ein einzelnes Buch formulieren können. Zusammengehörige Anpassungen könnten als Overlay gebündelt und in den Bucheinstellungen aktiviert oder deaktiviert werden. Gemeint ist eine zusätzliche Anpassungsschicht über dem normalen Stand des Buch-Branchs, nicht bloß eine weitere Git-Branch.

Ausgangspunkt des Gesprächs war: „Für dieses Buch keine Abschnittsbezeichnungen ausgeben.“ Als mögliche Auslegung wurde besprochen, Abschnittsnummern und Abschnittsüberschriften in der Buchausgabe auszublenden, während die Abschnitte intern für Bearbeitung und Freigaben erhalten bleiben. Ob dafür schon eine Einstellung existiert und welche Ausgabeformate betroffen sein sollen, ist vor einer Umsetzung zu prüfen.

Weitere mögliche Inhalte eines Overlays sind zusammengehörige Ausgaberegeln, zusätzliche Schritte im Erstellungskreislauf, Vorlagen und Voreinstellungen. Die Beispiele sind noch kein festgelegter Funktionsumfang.

## Besprochener Lösungsansatz

- Eigene benannte Pakete statt beliebiger Änderungen an verteilten Programmdateien.
- Aktivierung und gegebenenfalls individuelle Werte im Buchprofil, wirksam nur für das betreffende Buch.
- Als vorläufige Reihenfolge wurde vorgeschlagen: GhostWriter-Grundfunktionen → aktivierte Overlays → Einstellungen dieses Buchs. Diese Prioritätsregel ist noch festzulegen.
- Ein Änderungspaket (PR) könnte ein Overlay beziehungsweise dessen Unterstützung bereitstellen. Aktivieren und Deaktivieren erfolgt anschließend über Einstellungen; ein bereits übernommener PR ist selbst kein Ein-/Ausschalter.
- Allgemein wiederverwendbare Erweiterungen zentral in GhostWriter entwickeln. Buchbezogene Auswahl und Anpassungen vor Programmupdates schützen.
- Beim Ausschalten die Wirkung auf künftige Abläufe und Ausgaben beenden, ohne bereits erstellte Texte, Recherche oder andere Inhalte automatisch zu löschen oder rückwirkend umzuschreiben.
- Verbindliche Schutz- und Freigaberegeln bleiben übergeordnet und dürfen durch Overlays nicht abgeschwächt werden.

## Offene Fragen

1. Welche Anpassungen sind bereits normale Bucheinstellungen, und welche brauchen tatsächlich ein Overlay?
2. Welche Eingriffe sind erlaubt: Ausgabe, Vorlagen, Arbeitsabläufe, Prüfungen oder auch ausführbarer Code?
3. Wo liegen Pakete und buchbezogene Anpassungen, und wie werden sie verteilt und aktualisiert?
4. Wie werden mehrere Overlays geordnet und widersprüchliche Einstellungen erkannt und erklärt?
5. Wie werden Versionen, Abhängigkeiten und Kompatibilität mit GhostWriter-Updates geprüft?
6. Wie wirken Ein-/Ausschalten und Updates auf bereits begonnene Arbeitsabläufe? Welche Bestätigung und welcher Änderungsnachweis sind nötig?
7. Wie zeigt der Chat verständlich, welche Regeln für das ausgewählte Buch tatsächlich wirksam sind?

## Nächster Schritt bei Wiederaufnahme

Zuerst vorhandene Einstellungen und den Update-Mechanismus untersuchen. Danach anhand eines kleinen Beispiels, etwa ausgeblendeter Abschnittsüberschriften, Umfang und Architektur vorschlagen. Keine Pakete, Schalter, neuen Branches oder Änderungen an Buchdateien allein aus dieser Notiz ableiten.
