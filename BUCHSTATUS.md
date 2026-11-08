# Buchstatus und Branch-Zuordnung

Diese Datei ist eine **allgemeine Arbeitsanweisung für KI-Assistenten**. Sie enthält keine individuellen Buchdaten und keine festgeschriebene Liste von Branches. Die tatsächlichen Branches können sich jederzeit ändern.

## Verbindlicher Wiedereinstieg

Bei jedem neuen Chat und bei jedem Wiedereinstieg:

1. Lies diese Datei sowie `START.md`, `README.md` und `ghostwriter.yml`.
2. Ermittle die **aktuelle Branch-Liste direkt in GitHub**. Eine alte Chat-Zusammenfassung oder diese Datei ersetzt die Live-Prüfung nicht.
3. Bestimme den Buch-Branch aus dem Repository-Link bzw. aus der Bibliotheksstruktur.
4. Prüfe, ob der zugehörige Arbeits-Branch existiert und ob dazu ein offener Pull Request besteht.
5. Lies bei offenen Änderungen aus dem Arbeits-Branch; andernfalls aus dem Buch-Branch.
6. Zeige keine Entwurfsinhalte als freigegebenen Buchtext an. Kennzeichne Entwurf, Prüfung und Freigabe getrennt.

## Branch-Namensregeln

| Zweck | Namensregel | Bedeutung |
|---|---|---|
| Einzelbuch | Standard-Branch (häufig `main`) | Buch-Branch, wenn dort das Buch liegt |
| Buch in einer Bibliothek | `buch/<slug>` | Eigenständiger Buch-Branch |
| Arbeits-Branch eines Einzelbuchs | `ghostwriter/<buch-branch>`, z. B. `ghostwriter/main` | Gesammelte, noch nicht übernommene Änderungen |
| Arbeits-Branch eines Bibliotheksbuchs | `ghostwriter/buch/<slug>` | Gesammelte, noch nicht übernommene Änderungen dieses Buchs |

Ein Branch mit einem ähnlichen Namen ist nicht automatisch der passende Arbeits-Branch. Prüfe den exakten Namen, den offenen Pull Request und dessen Ziel-Branch. Andere Entwicklungs- oder Aufgaben-Branches sind nicht ohne weitere Hinweise als Manuskript-Branches zu behandeln.

Die [Entscheidung #169](docs/ENTSCHEIDUNG-169.md) bestätigt dieses Modell: Arbeits-Branch erst bei Speicherung, nach vollständiger Übernahme entfernen. Verwaiste Branches nicht ungeprüft weiterverwenden oder löschen.

## Schutzregeln

- Der Buch-Branch enthält den für das Buch übernommenen Stand.
- Der Arbeits-Branch kann Entwürfe, Änderungen und redaktionelle Zwischenstände enthalten.
- Ein offener Pull Request bedeutet **nicht**, dass seine Inhalte bereits freigegeben oder übernommen sind.
- Übernimm Manuskripttext nur nach ausdrücklicher Zustimmung des Autors und gemäß den Freigaberegeln in `START.md`.
- Merge oder übertrage niemals einen ganzen Arbeits-Branch allein deshalb, weil er existiert.
- Keine Branches automatisch löschen, umbenennen oder zusammenführen.
- Wenn Zuordnung oder Status unklar sind, nenne die Unsicherheit und frage nur dann nach, wenn sie die nächste Aktion verhindert.

## Pflege

Diese Datei wird als Teil der GhostWriter-Vorlage zentral gepflegt. Individuelle Branch-Namen, Buch-Titel und persönliche Projektentscheidungen gehören in die jeweilige Buchdokumentation, nicht in diese allgemeine Vorlage.
