# Bedienglossar

Deutsch · [English](USER-GLOSSARY.en.md)

[Anleitung](ANLEITUNG.md) · [Hilfe](HILFE.md) · **Bedienglossar**

Dieses Glossar erklärt die Begriffe, die dir bei der Arbeit mit GhostWriter begegnen. Es ist Teil der Programmdokumentation und **nicht das Glossar deines Buchs**; es gelangt nie in Manuskript, Probedruck oder Auflage. Das Glossar im Buch legst du im [Vor- und Nachspann](#vor-und-nachspann) an.

Verbindlich bleiben die verlinkten Anleitungen. Technische Kennungen in `Code-Schrift` sind die Bezeichnungen in den Projektdateien und werden nicht übersetzt.

**Von A bis Z:** [Abgeschlossen](#abgeschlossen) · [Abschließen](#abschliessen) · [Abschnitt](#abschnitt) · [Als Figur sprechen](#als-figur-sprechen) · [Alternativtext](#alternativtext) · [Änderungspaket](#aenderungspaket) · [Arbeitsstand](#arbeitsstand) · [Auflage](#auflage) · [Bereit zum Abschluss](#bereit-zum-abschluss) · [Bibliothek](#bibliothek) · [Bildfreigabe](#bildfreigabe) · [Bildunterschrift](#bildunterschrift) · [Blockiert](#blockiert) · [Brainstorming](#brainstorming) · [Breitenregler](#breitenregler) · [Buch](#buch) · [Buchstand](#buchstand) · [Colorieren](#colorieren) · [DOCX](#docx) · [Entwurf](#entwurf) · [EPUB](#epub) · [Erstellungskreislauf](#erstellungskreislauf) · [Faktenprüfung](#faktenpruefung) · [Figurengespräch](#figurengespraech) · [Freigabe](#freigabe) · [Freigaberecht](#freigaberecht) · [Geplant](#geplant) · [Geprüft](#geprueft) · [Gespeichert](#gespeichert) · [Gliederung](#gliederung) · [Grafik](#grafik) · [Hintergrund-Warteschlange](#hintergrund-warteschlange) · [Illustration](#illustration) · [In Bearbeitung](#in-bearbeitung) · [Kapitel](#kapitel) · [Konflikt](#konflikt) · [Medienabschnitt](#medienabschnitt) · [Medium](#medium) · [PDF](#pdf) · [Persönlicher Inhaltsnachweis](#persoenlicher-inhaltsnachweis) · [Platzierung](#platzierung) · [Probedruck](#probedruck) · [Prüfergebnis](#pruefergebnis) · [Recherche](#recherche) · [Referenzbild](#referenzbild) · [Referenzfreigabe](#referenzfreigabe) · [Rolle](#rolle) · [Rundumprüfung](#rundumpruefung) · [Schreiben erlauben](#schreiben-erlauben) · [Session laden](#session-laden) · [Session sichern](#session-sichern) · [Session übernehmen](#session-uebernehmen) · [Session](#session) · [Sicherungslücke](#sicherungsluecke) · [Strukturfreigabe](#strukturfreigabe) · [Szene](#szene) · [Textumfluss](#textumfluss) · [Überarbeitung](#ueberarbeitung) · [Übernommen](#uebernommen) · [Veröffentlichung](#veroeffentlichung) · [Vor- und Nachspann](#vor-und-nachspann) · [Vorabfassung](#vorabfassung) · [Wieder öffnen](#wieder-oeffnen)

## Die wichtigsten Unterscheidungen

- **Schreiben erlauben** ist nicht **abschließen**: Das eine erlaubt das Schreiben, das andere bestätigt den fertigen Text.
- **Gespeichert** ist nicht **übernommen**, und übernommen ist nicht **abgeschlossen**. Ein gutes [Prüfergebnis](#pruefergebnis) schließt nichts ab.
- **Session sichern** schützt Gesprächsarbeit und ändert das Manuskript nicht. **Laden** ist nicht **Übernehmen**.
- Ein **Referenzbild** dient einem Erstellungsauftrag. Es wird dadurch nicht zur Abbildung im Buch.
- Ein **Probedruck** ist keine **Auflage**. Eine veröffentlichte Auflage bleibt unverändert.

## Buchaufbau

- <a id="bibliothek"></a>**Bibliothek:** Ein Repository, in dem mehrere Bücher liegen. Der Standardbereich enthält das Programm; jedes Buch hat einen eigenen Bereich (technisch: Branch `buch/<kurztitel>`). Siehe [Anleitung](ANLEITUNG.md#1-repository-anlegen).
- <a id="buch"></a>**Buch:** Ein einzelnes Buchprojekt mit Titel, Gliederung, Manuskript und Auflagen. Ein neues Buch ist zunächst *im Aufbau*. Siehe [Buchablauf](BUCHABLAUF.md).
- <a id="gliederung"></a>**Gliederung:** Die Ordnung des Buchs in Kapitel und Abschnitte. Sie wird im Einstiegsgespräch erarbeitet und nach der [Strukturfreigabe](#strukturfreigabe) gespeichert.
- <a id="kapitel"></a>**Kapitel:** Eine Gruppe von Abschnitten. Ein Kapitel wird zusammengeführt, als Ganzes geprüft und dann [abgeschlossen](#abschliessen).
- <a id="abschnitt"></a>**Abschnitt:** Die kleinste Arbeitseinheit des Buchs. Jeder Abschnitt durchläuft den [Erstellungskreislauf](#erstellungskreislauf) und wird einzeln abgeschlossen.
- <a id="szene"></a>**Szene:** In GhostWriter entspricht eine Szene einem Abschnitt. Eine weitere Szene bekommt einen eigenen Abschnitt.
- <a id="vor-und-nachspann"></a>**Vor- und Nachspann:** Teile vor Kapitel 1 bzw. nach dem letzten Kapitel: Widmung, Vorwort, Prolog, Epilog, Nachwort, Glossar des Buchs und Danksagung. Sie werden abgeschlossen wie Abschnitte. Siehe [Anleitung](ANLEITUNG.md#6-am-buch-arbeiten).

## Erstellung

- <a id="erstellungskreislauf"></a>**Erstellungskreislauf:** Der wiederholbare Weg, auf dem ein Abschnitt entsteht: Recherche, Brainstorming, Entwurf und Überarbeitung, bis du ihn abschließt. Neue Ideen führen an die passende Stelle zurück. Siehe [Erstellungskreislauf](ERSTELLUNGSKREISLAUF.md).
- <a id="hintergrund-warteschlange"></a>**Hintergrund-Warteschlange** (kurz **Warteschlange**): Aufträge für KI-Arbeiten, die dauern und kosten, zuerst die Recherche mit Internet (#476). Jeder Start legt einen Auftrag an; je Buch arbeitet ein Lauf sie der Reihe nach ab und speichert jedes Ergebnis. Die Reihenfolge folgt festen Regeln (Vorrang, Abhängigkeit, Buchreihenfolge, Zeit); wartende Aufträge lassen sich in der Ansicht **vorziehen** oder **abbrechen** (#478). Nicht verwechseln mit der **Aufgaben-Warteschlange** (Issues für Agenten, Formular „KI-Dienste“). Siehe [Recherche mit Internet über die API](DIENSTE-NUTZEN.md#recherche-mit-internet-über-die-api-462).
- <a id="recherche"></a>**Recherche:** Quellen, Belege, Widersprüche und offene Fragen zum Abschnitt sammeln (`research`). Frühere Rechercheläufe bleiben erhalten. **Mit Internet** recherchiert der Chat mit Websuche oder die Action „Recherche“ über den eingestellten Dienst mit API-Schlüssel; **ohne Internet** nur aus dem Wissen des Modells, die Laufdatei sagt das ausdrücklich. Siehe [Recherche mit Internet über die API](DIENSTE-NUTZEN.md#recherche-mit-internet-über-die-api-462).
- <a id="brainstorming"></a>**Brainstorming:** Ideen, Varianten und Vorgaben mit dem Assistenten besprechen (`brainstorming`).
- <a id="entwurf"></a>**Entwurf:** Der erste Text eines Abschnitts. Er entsteht erst, nachdem du das [Schreiben erlaubt](#schreiben-erlauben) hast (`writing`).
- <a id="ueberarbeitung"></a>**Überarbeitung:** Der Entwurf wird mit dir verbessert und als Ganzes geprüft (`revision`). Ein wieder geöffneter Abschnitt kehrt hierher zurück.
- <a id="figurengespraech"></a>**Figurengespräch:** Ein Gespräch im Chat, in dem der Assistent in der Rolle einer Figur antwortet (`Figurengespräch <Name>`). Es speichert nichts; Neues kommt nur auf deine Auswahl ins Figurenprofil, nie ins Manuskript. Siehe [Anleitung](ANLEITUNG.md#6-am-buch-arbeiten).
- <a id="als-figur-sprechen"></a>**Als Figur sprechen:** Das umgekehrte [Figurengespräch](#figurengespraech): Du oder die Person selbst (Zeitzeuge) spricht als Figur, der Assistent antwortet aus der gewählten Wissensgrundlage, nur Buchwissen, nur Recherche oder beides (`Als <Name> sprechen`). Was der Sprecher erzählt, ist eine Angabe, keine Erfindung; es kommt nur auf deine Auswahl ins Figurenprofil, in die Chronologie oder in ein gesichertes Gespräch, nie ins Manuskript. Siehe [Anleitung](ANLEITUNG.md#6-am-buch-arbeiten).
- <a id="faktenpruefung"></a>**Faktenprüfung:** Auf Wunsch ein Bericht mit Korrekturvorschlägen (`fact_check`). Sie ändert den Text nicht von selbst.
- <a id="pruefergebnis"></a>**Prüfergebnis:** Ergebnis einer redaktionellen Prüfung: *bestanden*, *bestanden mit Hinweisen* oder *nicht bestanden*. Auch ein bestandenes Ergebnis schließt nichts ab. Siehe [Qualitätssicherung](QUALITAETSSICHERUNG.md#prüfergebnis).
- <a id="rundumpruefung"></a>**Rundumprüfung:** Prüft ein Kapitel in einem Durchgang auf Struktur, Sprache, Rechtschreibung, Grundregeln und Buchgedächtnis. Behoben wird nur, was ohne Autor lösbar ist; alles andere kommt in die Hinweisdurchsicht. Nichts wird [übernommen](#uebernommen). Siehe [Lektorat](LEKTORAT.md#rundumprüfung-eines-kapitels-447).

## Zustände, Abschließen und Freigaben

Seit #292 heißt das Bestätigen fertiger Texte **abschließen**, das Rückgängigmachen **wieder öffnen**. Das Wort **Freigabe** gilt in der Bedienung nur noch für Bilder, Sammelbände, Auflagen und die Struktur. In den Projektdateien bleiben die technischen Namen (`approved`, `approvals.yml`).

- <a id="geplant"></a>**Geplant:** Startzustand eines Kapitels oder Abschnitts (`planned`). Ziel, Fragen und Material werden geklärt.
- <a id="in-bearbeitung"></a>**In Bearbeitung:** Ein Kapitel, an dessen Abschnitten gearbeitet wird (`in_progress`). Danach folgen Zusammenführen und Durchsicht. Siehe [Buchablauf](BUCHABLAUF.md#kapitel-für-kapitel-im-kreis-arbeiten).
- <a id="schreiben-erlauben"></a>**Schreiben erlauben / Schreiben sperren:** Deine ausdrückliche Erlaubnis, dass der Assistent den Text eines Abschnitts schreibt oder ändert (früher „Schreibfreigabe“). Sie schließt den Abschnitt nicht ab.
- <a id="bereit-zum-abschluss"></a>**Bereit zum Abschluss:** Die Fassung liegt dir zum Abschließen vor (`ready_for_approval`), bei Abschnitten wie bei Kapiteln.
- <a id="abschliessen"></a>**Abschließen:** Deine ausdrückliche Bestätigung einer genauen Textfassung: **Abschnitt abschließen** bzw. **Kapitel abschließen** (früher „Abschnittsfreigabe“ bzw. „Kapitelfreigabe“). Speichern, Übernehmen oder eine Prüfung ersetzen sie nicht. Offene Marker werden dabei als Warnung gezeigt.
- <a id="abgeschlossen"></a>**Abgeschlossen:** Zustand nach dem Abschließen (`approved`). Der Text ist gesperrt, bis du ihn wieder öffnest.
- <a id="wieder-oeffnen"></a>**Wieder öffnen:** Hebt einen Abschluss auf (früher „Freigaberücknahme“). Der Abschnitt geht in die Überarbeitung zurück; vor dem nächsten Schreiben musst du das Schreiben erneut erlauben.
- <a id="strukturfreigabe"></a>**Strukturfreigabe:** Deine Bestätigung der vollständigen Gliederung eines neuen Buchs. Erst danach entstehen die weiteren Buchdateien.
- <a id="bildfreigabe"></a>**Bildfreigabe:** Deine Entscheidung, dass ein Bild ins Buch darf. Nur freigegebene Bilder kommen in eine Auflage; der Probedruck zeigt alle mit Vermerk.
- <a id="freigabe"></a>**Freigabe:** In der Bedienung eine eigene ausdrückliche Entscheidung über Struktur, Bild, [Referenzbild](#referenzfreigabe), Sammelband oder Auflage. Für Texte heißt es [abschließen](#abschliessen).
- <a id="freigaberecht"></a>**Freigaberecht:** Die Berechtigung des Eigentümers oder einer ausdrücklich für dieses Buch bevollmächtigten Person, Inhalte freizugeben. Das persönliche GitHub-Konto und die Berechtigung werden geprüft; Schreibzugriff oder ein eingetragener Name belegen sie nicht. Siehe [persönliche Freigabeprüfung](SPEICHERN.md#persönliches-freigaberecht-und-inhaltsnachweis).
- <a id="persoenlicher-inhaltsnachweis"></a>**Persönlicher Inhaltsnachweis:** Ein prüfbarer persönlicher GitHub-Review für den konkreten Buchstand, die Auflage und den Verwendungszweck. Das Speichern seiner Kennungen allein ist noch keine erfolgreiche Prüfung. Er schließt keine Abschnitte automatisch ab und ersetzt keine fachlichen Prüfungen. Siehe [Ablauf und Grenzen](SPEICHERN.md#persönliches-freigaberecht-und-inhaltsnachweis).
- <a id="rolle"></a>**Rolle:** Wer im Buch was darf: *Eigentümer* (alles), *Bearbeiter* (schreiben und speichern; abschließen nur, wenn ausdrücklich freigabeberechtigt) oder *Leser* (nur ansehen). Festgelegt in der Team-Liste des Buchs; die GitHub-Rechte begrenzen immer. Siehe [Anleitung](ANLEITUNG.md#10-später-weiterarbeiten).

## Speichern und Übernehmen

Diese Begriffe beschreiben den Speicherstand. Sie sind keine Zustände von Abschnitten oder Kapiteln. Siehe [Speichern, Übernehmen und Abschließen](SPEICHERN.md#die-zustände-auseinanderhalten).

- <a id="arbeitsstand"></a>**Arbeitsstand:** Der aktuelle Stand mit allen gespeicherten, auch noch nicht übernommenen Änderungen. Die Ansichten lesen ihn aus dem offenen Änderungspaket.
- <a id="buchstand"></a>**Buchstand:** Der übernommene Stand des Buchs. Aus ihm entstehen Probedruck und Auflage.
- <a id="aenderungspaket"></a>**Änderungspaket:** Bündel zusammengehöriger gespeicherter Änderungen (technisch: Pull Request). Es kann mehrere Änderungsschritte (Commits) enthalten. Siehe [Hilfe](HILFE.md#änderungspakete-schnüren-und-übernehmen).
- <a id="gespeichert"></a>**Gespeichert, noch nicht übernommen:** Die Übertragung ins Repository ist bestätigt; das Änderungspaket ist noch offen. Bei Gesprächen heißt es *gesichert*.
- <a id="geprueft"></a>**Geprüft:** Die genannten technischen Prüfungen sind erfolgt. Eine Übernahme ist damit noch nicht zugesichert.
- <a id="uebernommen"></a>**Übernommen:** Das Änderungspaket ist nach deiner Bestätigung im Buchstand (technisch: Merge). Mit *sofort übernehmen* (`changes.auto_merge`) geschieht das für gewöhnliche Buchänderungen automatisch, nie für Gesprächssicherungen und Auflagen.
- <a id="blockiert"></a>**Blockiert:** Ein Vorgang ist fehlgeschlagen oder wartet auf Klärung. Der Assistent nennt, was tatsächlich gespeichert ist, und den nächsten Schritt.
- <a id="konflikt"></a>**Konflikt:** Betroffene Dateien wurden inzwischen anders geändert. Vor dem Schreiben wird neu abgeglichen; ein Konflikt wird nicht übergangen.

## Gesprächsarbeit

- <a id="session"></a>**Session:** Ein Gespräch mit dem Assistenten mit fester Kennung. Ihre Sicherung liegt getrennt vom Manuskript.
- <a id="session-sichern"></a>**Session sichern** (auch *Chat sichern*): Hält die zugängliche Gesprächsarbeit dauerhaft fest: Beiträge, Recherche, Brainstorming, Entscheidungen, Entwürfe und offene Punkte. Nach jeder ausgewerteten Antwort in einer Abschnitts-Fragerunde geschieht das automatisch. Siehe [Session-Sicherung](SESSION-SICHERUNG.md).
- <a id="session-laden"></a>**Session laden:** Liest eine Sicherung zum Weiterarbeiten. Laden speichert und übernimmt nichts.
- <a id="session-uebernehmen"></a>**Session übernehmen:** Prüft die Sicherung, versucht bei Fehlern eine sichere Reparatur und übernimmt sie. Manuskript und Abschlüsse bleiben unverändert.
- <a id="sicherungsluecke"></a>**Sicherungslücke:** Ein Teil des Gesprächs, der nicht gesichert werden konnte, etwa frühere Beiträge oder Anhänge, die nicht mehr zugänglich waren. Lücken werden ausdrücklich genannt, nicht verschwiegen.

## Bilder und Grafiken

**GhostWriter ist für textorientierte Bücher gedacht, nicht für Bildbände oder Fotobücher.** Siehe [Medien im Abschnitt](MEDIENPLATZIERUNG.md) und [Bilder und visuelle Referenzen](BILDER-UND-REFERENZBILDER.md).

- <a id="medium"></a>**Medium:** Ein Bild oder eine Grafik im Abschnitt. Ein Abschnitt enthält höchstens ein Medium; dasselbe Bild zweimal zählt als zwei.
- <a id="colorieren"></a>**Colorieren:** Ein Schwarz-Weiß-Foto einfärben, wobei vom Bildmodell nur die Farbe übernommen wird; Gesichter und Formen bleiben unverändert. Gesperrt für Bilder mit Kindern und für Dokumente. Siehe [Fotos colorieren](BILDER-UND-REFERENZBILDER.md#fotos-colorieren-452).
- <a id="illustration"></a>**Illustration:** Ein Bild für das Buch, meist ohne Schrift.
- <a id="grafik"></a>**Grafik:** Ein Diagramm oder eine Darstellung, bei der Beschriftungen erwünscht sind.
- <a id="referenzbild"></a>**Referenzbild:** Ein Bild als Vorlage für einen Erstellungsauftrag, etwa für das Aussehen einer Figur oder eines Ortes. Es ist keine Abbildung im Buch, solange es nicht eigens als Buchbild verwendet und freigegeben wird.
- <a id="referenzfreigabe"></a>**Referenzfreigabe:** Deine Entscheidung, dass ein Referenzbild bei passenden Aufträgen angeboten werden darf. Welche Referenzen ein Auftrag verwendet, wählst du jedes Mal ausdrücklich. Ein Upload allein ist keine Freigabe.
- <a id="medienabschnitt"></a>**Medienabschnitt:** Ein eigener Abschnitt, der nur ein Bild oder eine Grafik enthält, direkt vor oder nach einem Textabschnitt.
- <a id="bildunterschrift"></a>**Bildunterschrift:** Der sichtbare Text unter dem Medium.
- <a id="alternativtext"></a>**Alternativtext:** Beschreibung des Bilds für Screenreader. Weicht er von der Bildunterschrift ab, erhalten DOCX und EPUB ihn getrennt.
- <a id="platzierung"></a>**Platzierung:** Lage des Mediums im Abschnitt: oben oder unten, jeweils links, mittig oder rechts (sechs Möglichkeiten). Umgesetzt (#54); die praktische Prüfung in allen Formaten steht noch aus.
- <a id="textumfluss"></a>**Textumfluss:** Bei links oder rechts platzierten Medien läuft der Text um das Bild, bei mittigen nicht. Umgesetzt für PDF, EPUB und DOCX (#54); praktische Prüfung ausstehend.
- <a id="breitenregler"></a>**Breitenregler (Satzbreite):** Schieberegler mit Prozentanzeige für die Breite des Mediums als Anteil der nutzbaren Seitenbreite (10–100 %); die Höhe folgt. Umgesetzt (#54). Er ändert die Originaldatei nicht.

## Ausgabe

- <a id="probedruck"></a>**Probedruck:** Ein gekennzeichnetes PDF des übernommenen Buchstands, jederzeit möglich, auch mit unfertigen Texten. Er veröffentlicht nichts und schließt nichts ab.
- <a id="vorabfassung"></a>**Vorabfassung:** Ein Probedruck, der dauerhaft als „Vorabfassung N“ abgelegt wird, etwa für Testleser. Keine Auflage.
- <a id="auflage"></a>**Auflage:** Eine veröffentlichte Fassung des Buchs. Sie braucht mindestens ein abgeschlossenes Kapitel, keine offenen Marker und deine ausdrückliche Bestätigung. Eine veröffentlichte Auflage bleibt unverändert; Korrekturen gehen in eine spätere Auflage. Siehe [Buchablauf](BUCHABLAUF.md#aus-dem-kapitelkreis-zur-auflage).
- <a id="veroeffentlichung"></a>**Veröffentlichung:** Der Schritt, in dem GitHub die Ausgabedateien einer bestätigten Auflage baut und als Release ablegt. Ein laufender oder fehlgeschlagener Aufbau ist noch keine Auflage.
- <a id="pdf"></a>**PDF:** Ausgabe zum Lesen am Bildschirm oder für den Druck.
- <a id="docx"></a>**DOCX (Word-Datei):** Ausgabe zum Weiterbearbeiten in Word oder LibreOffice.
- <a id="epub"></a>**EPUB (E-Book):** Ausgabe für E-Book-Reader mit fließendem Text.

## Technische Begriffe beim Lesen der Doku

Für die Bedienung brauchst du sie nicht. **Branch:** eigener Bereich, etwa für ein Buch. **Commit:** ein Änderungsschritt. **Pull Request (PR):** ein [Änderungspaket](#aenderungspaket). **Merge:** [Übernehmen](#uebernommen). **Tag:** dauerhafte Markierung eines Stands, etwa einer Auflage.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
