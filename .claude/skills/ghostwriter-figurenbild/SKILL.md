---
name: ghostwriter-figurenbild
description: Figuren- und Personenbilder für ein GhostWriter-Buch gestalten – Bildstil des Projekts festlegen, aus Figurenprofil und Stil einen vollständigen Bildprompt bauen, Bildvarianten mit Prompt und Prüfsumme bei der Figur ablegen, gezielte Änderungen wie „nur Kleidung“. Startet bei Befehl Figurenbild, Figurenbild-Assistent, Character image, Kürzel FB. Nicht für Buchillustrationen, Referenzfreigabe oder Fotos von echten Personen.
---

# GhostWriter-Figurenbild

Arbeite im ausgewählten Buch nach dessen Repository-Regeln. Der Ablauf, die
Datenstruktur und die Grenzen stehen im Buchrepo und werden hier nicht
wiederholt: `START.md`, Abschnitt „Figurenbild-Assistent (#540)“, das Skript
`scripts/figurenbild.py` (`stil`, `prompt`, `variante`, `waehlen`, `liste`,
`pruefen`) und `docs/BILDER-UND-REFERENZBILDER.md`. Fehlt die Datei im Buchrepo,
gilt die Fassung im Hauptrepo [GhostWriter](https://github.com/ploeffler/GhostWriter).

## Auslöser

- Befehl `Figurenbild`, `Figurenbild-Assistent` bzw. `Character image`, Kürzel **FB**.
- Der Wunsch, eine Figur zu bebildern oder ein vorhandenes Figurenbild gezielt zu
  ändern. Erst klären, welche Figur(en); dann `scripts/figurenbild.py stil`.

## Ablauf in Kürze

1. **Grundlagen lesen:** aktuelles Figurenprofil aus dem richtigen Stand
   (`characters.py profile`), Bildstil (`figurenbild.py stil`), vorhandene Bilder
   (`figurenbild.py liste`). Fehlende Angaben bleiben offen.
2. **Stil festlegen und speichern:** Medium (Foto, Comic, Illustration, Aquarell
   oder frei) und Eigenschaften anbieten; gespeichert wird erst nach ausdrücklicher
   Bestätigung (`stil set`). Der Bildstil ist nicht die Erzählstimme.
3. **Vorgaben und Gestaltung trennen:** Profilmerkmale sind Vorgaben, Wünsche des
   Autors ergänzen sie, unbestimmte Details (Frisur, Kleidungsfarbe) sind sichtbar
   gekennzeichnete Bildvorschläge und keine Manuskriptfakten. Bei wesentlichen
   Unklarheiten kurz nachfragen.
4. **Prompt je Figur:** `figurenbild.py prompt <figur>` baut ihn aus Profil und
   Stil, mit der Herkunft je Angabe. Gemeinsamer Stil heißt nicht gleiche
   Kleidung: Farben, Materialien und Silhouetten je Figur unterscheiden.
5. **Erzeugen:** mit dem Bilddienst des Chats, wenn vorhanden; sonst den
   vollständigen Auftrag zum Kopieren ausgeben. Nichts stillschweigend an einen
   externen Anbieter schicken, keine Kosten voraussetzen.
6. **Änderungen:** ein vorhandenes Bild als echte Eingabereferenz nehmen, im
   Prompt nur die Änderung nennen und alles andere ausdrücklich erhalten
   (Gesicht, Alter, Ausdruck, Frisur, Körperbau, Pose, Hände, Requisiten,
   Hintergrund, Ausschnitt, Licht). Das Ergebnis ansehen; es ist eine neue
   Variante, das Original bleibt.
7. **Ablegen:** `figurenbild.py variante` mit dem tatsächlich gesendeten Prompt,
   Werkzeug und Modell (sonst „unbekannt“, nichts erfinden), danach `pruefen`.
   Ein Commit für zusammengehörige Änderungen.

## Grenzen

- Keine Referenzfreigabe durch dieses Skill; sie bleibt ein eigener Schritt
  (`reference_images.py`, Freigabe im Chat). Ein Bild allein ist keine Freigabe.
- Keine neuen Manuskriptfakten, keine Profiländerung ohne ausdrücklichen Auftrag.
- Figuren in sexuellen oder sexualisierten Darstellungen nie darstellen.
  Keine Bilder von Minderjährigen, die reale Personen zeigen; keine Fotos echter
  Personen an externe Dienste ohne Einverständnis (`material.external_allowed`).
- Grafische Hilfe (Stilkarten, Variantenvergleich) nur, wo der Client sie
  tatsächlich anzeigt; sonst gleichwertig als Text.
