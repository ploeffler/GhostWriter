# Probleme lösen

Deutsch · [English](TROUBLESHOOTING.en.md)

## Der Assistent kann das Repository nicht lesen

Prüfe die GitHub-Verbindung deiner Chat-App und ob das richtige Repository freigegeben ist. Ein Link allein lädt keine Dateien. Ohne Verbindung kannst du START.md anhängen und Dateien selbst übertragen. Siehe [Chat-Apps](CHAT-APPS.md) und [Verbindung einrichten](CONNECTOR-SETUP.md). Keine Zugangsschlüssel im Chat teilen.

## Die Ansicht erscheint nicht oder ist nicht bedienbar

Schreibe **Nur Text**. ChatGPT und andere Clients können native Textansichten verwenden; nicht jeder Client unterstützt dieselben Widgets. Mit **Übersicht**, **Kapitel 2** oder **Abschnitt 2.3** öffnest du die gewünschte Stelle. [Hilfe](HILFE.md) erklärt weitere Befehle.

## Meine Änderung fehlt

Frage: „Was ist bereits gespeichert und was liegt nur in diesem Gespräch?“ Ein offenes Änderungspaket ist gespeichert, aber noch nicht übernommen. **Session laden** liest Gesprächssicherungen; **Session übernehmen** prüft und übernimmt das zugehörige Paket. Buchänderungen haben ihren eigenen Übernahmeschritt. Siehe [Speichern](SPEICHERN.md) und [Gespräch sichern](SESSION-SICHERUNG.md).

## Speichern meldet einen neueren Stand oder einen Fehler

Nicht blind erneut überschreiben. Lass den Assistenten den aktuellen Stand lesen, die Unterschiede prüfen und die beabsichtigte Änderung darauf abgleichen. Eine Erfolgsmeldung darf erst nach bestätigter Speicherung erscheinen. Fehlende Werkzeuge oder Rechte muss der Assistent offen nennen.

## Schreiben oder Auflage ist gesperrt

Schreiben braucht eine Schreibfreigabe. Bereits freigegebener Text muss vor Änderungen ausdrücklich zurückgenommen und erneut zum Schreiben freigegeben werden. Für eine Auflage müssen die erforderlichen Kapitel und Abschnitte freigegeben und offene Marker geklärt sein. Lass dir die konkrete Sperre nennen; zum Lesen kannst du einen **Probedruck** anfordern. Siehe [Anleitung](ANLEITUNG.md).

## Bücherregal oder Übersicht bleiben alt

Zeigt jeder Lauf unter **Actions** *„The job was not started because recent account payments have failed or your spending limit needs to be increased“*, sind die Actions-Minuten des Monats aufgebraucht (privat 2000). Gespeichert wird weiter, aber Bücherregal, Übersichtsdatei, Prüfung und Auflagen laufen erst mit dem neuen Monat oder nach einem Ausgabenlimit in den GitHub-Einstellungen wieder. Danach *Bücherregal aktualisieren* einmal von Hand starten. Siehe [Updates](UPDATES.md), Abschnitt „Actions-Minuten privater Bibliotheken“.

## Ein Bild nutzt meine Referenz nicht

Eine gespeicherte Referenz ist noch keine bestätigte Übergabe an einen Bilddienst. Der Assistent muss die ausgewählten Dateien separat an einen Dienst übergeben, der Referenzen unterstützt, oder die Grenze nennen. Siehe [Bilder und Referenzen](BILDER-UND-REFERENZBILDER.md).

## Das Problem bleibt

Notiere Befehl, Fehlermeldung, Client und Programmversion (**Daten**). Melde Programmfehler im Hauptrepository, ohne private Buchtexte, Chats oder Schlüssel offenzulegen. Suche vorher nach einem gleichen Problem. Für den Update-Stand siehe [Updates](UPDATES.md).

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
