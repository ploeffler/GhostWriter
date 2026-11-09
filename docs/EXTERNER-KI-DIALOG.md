# Externen KI-Dialog vorbereiten und auswerten

Deutsch · [English](EXTERNAL-AI-DIALOG.en.md)

Dieser manuelle Chat-Ablauf ergänzt [Auftrag kopieren](DIENSTE-NUTZEN.md#weg-2-ein-anderer-chat-dienst-auftrag-kopieren). Du kannst damit Recherche, Brainstorming, Schreiben, Überarbeitung oder Prüfung bei einem anderen Anbieter durchführen und den Dialog zurückbringen. Ein Anbieterwechsel braucht keine KI-Anbieter-API.

**Stand:** als manueller Ablauf lokal erprobt. Das ist eine Arbeitsanweisung für den Chat-Assistenten, kein neuer Parserbefehl, automatischer Export oder Anbieteranschluss. Download und Kopierfunktion hängen vom Client ab; eine aufklappbare Codebox ist nur eine Darstellungsoption. Text ist der Fallback.

## Starten

Schreibe beispielsweise:

> Externen KI-Dialog für Abschnitt 2.3 vorbereiten.

Oder:

> Externe Überarbeitung für Kapitel 2 vorbereiten.

Diese natürlichen Arbeitsaufträge starten die Vorbereitung im Chat. Für eine Kapitelüberarbeitung gelten weiterhin die Voraussetzungen der [geführten Arbeitsabläufe](ARBEITSABLAEUFE.md). Öffnen und Vorbereitung verändern weder Buchdateien noch Freigaben. Ganze Kapitel und Bücher nicht im Chat ausgeben: umfangreiches Ausgangsmaterial nur als ausdrücklich gewähltes Dateipaket oder in getrennten Abschnittsaufträgen bereitstellen.

Der Assistent liest den aktuellen Projektstand und füllt die [Auftragsvorlage](../templates/external-dialog/auftrag.de.txt) mit folgenden Angaben:

- Auftragskennung, Aufgabe, Einheit und Quellstand;
- Ziel, relevanter Kontext und notwendige Ausgangstexte;
- bestätigte Angaben und bereits beantwortete Fragen;
- offene Fragen, Stil, Ausgabeformat und kreative Freiräume;
- Quellenanforderungen und gewünschte Arbeitsweise: Dialog oder direkte Bearbeitung.

Nicht vorhandene Quellen oder Antworten bleiben offen. Nur nötigen Kontext übertragen. Im Dialog soll der andere Anbieter an Bekanntes anknüpfen, eine offene Hauptfrage pro Nachricht stellen und Antworten aufgreifen. Bei direkter Bearbeitung sind nur entscheidende Lücken zu klären.

## Beim anderen Anbieter

1. Den **ausgefüllten Auftrag** als Text kopieren oder als Datei in einen neuen Chat geben. Ein ZIP mit Testplanung und Anleitungen ist nicht der Auftrag und wird nicht pauschal hochgeladen.
2. Anbieter, angezeigtes Modell und Datum notieren. Ist kein Modell sichtbar, „nicht angezeigt“ festhalten.
3. Im Dialog frei antworten. Für einen Vergleich denselben Ausgangsauftrag verwenden; neu entstehende Antworten dürfen unterschiedlich sein.
4. Wenn genug Material vorliegt, „Jetzt ausarbeiten“ und den [Rückgabeprompt](../templates/external-dialog/rueckgabe.de.txt) senden.
5. Den vollständigen sichtbaren Verlauf mit Fragen, Antworten und Ergebnis exportieren oder kopieren. Interne Modellüberlegungen gehören nicht dazu. Fehlende Nachrichten nicht rekonstruieren.

## Zurückbringen

Schreibe zum Beispiel:

> Das ist die Rückgabe von Anbieter A zu Abschnitt 2.3.

Hänge den Verlauf an oder füge ihn als Text ein; nenne Auftragskennung und Modell, soweit bekannt. Ein privater Link allein gewährt keinen Zugriff. Ein freigegebener Link ist nur verwendbar, wenn er tatsächlich gelesen werden kann. Der Assistent darf einen Textanfang oder eine Zusammenfassung nicht als vollständigen Dialog behandeln. Nachgereichte Schlusswörter oder Korrekturen als Nachtrag dokumentieren und das Original erhalten.

Die Rückgabe ist Material zur Durchsicht, keine automatische Speicherung. Unbekanntes nicht durch Vermutungen über Modell, Fragenherkunft oder ausgelassene Antworten ersetzen. Veränderte Projektstände vor einer Einpflege neu abgleichen. Nicht prüfbare Quellen kenntlich machen; Anforderungen an Quellen und Freigaben gelten weiter.

## Analyse mit Empfehlung

Der Assistent verwendet die [Auswertungsvorlage](../templates/external-dialog/auswertung.de.md) und trennt:

- vorhandene und neu entstandene Angaben sowie Anbieterinterpretationen;
- Gesprächsführung: offene Fragen, Wiederholungen, Lenkung und Umgang mit Antworten;
- Ergebnis: Fakten, Stimme, Logik und Auftragserfüllung;
- Grenzen: fehlende Teile, ungeprüfte Quellen und unterschiedliche Materialbasis.

Jede Auswertung endet mit einer **begründeten Empfehlung**: Was verwenden? Was überarbeiten oder weglassen? Welche gezielte Klärung ist nötig? Was ist der nächste konkrete Schritt? Eine ausdrücklich bestätigte Autorenantwort bleibt auch dann nutzbar, wenn die vorausgehende Frage lenkend war; ihre Herkunft bleibt sichtbar. Metaphern nicht als nachgewiesene medizinische oder technische Mechanismen behandeln. Abkürzungen nicht stillschweigend auflösen. Gute Fähigkeiten nicht mit durchgängigen Erfolgen gleichsetzen.

Mehr Material aus einem Gespräch bedeutet nicht automatisch besseren Schreibstil. Ein einzelner Lauf begründet keinen allgemeinen Anbietersieger. Empfehlung, Autorenentscheidung, Speicherung und formelle Freigabe bleiben getrennt. Für Manuskriptänderungen gelten Schreibfreigabe, Schutz bereits freigegebener Texte, vollständige redaktionelle Prüfung und reguläres Änderungspaket. Der externe Entwurf darf im Chat zur Sichtung vorliegen, ohne eine fehlende formelle Freigabe zu ersetzen.

## Testumfang und Grenzen

Lokal erprobt wurden Auftrag als Datei/Kopiertext, externe Gesprächsrückgabe, Prüfung ihrer Aussagen und Empfehlungen sowie ein nachgereichtes fehlendes Schlusswort. Ausgangsprompt und Modell waren in der vorliegenden Rückgabe nicht vollständig dokumentiert. Das belegt den manuellen Rückgabe- und Auswertungsweg, keinen kontrollierten Vergleich aller Anbieter oder eine Client-Abnahme. Weitere Tests halten Ausgangsstand, Umfang, Modell soweit sichtbar, tatsächliche Rückgabe, Empfehlung und offene Punkte fest. Testberichte und private Buchdialoge bleiben außerhalb der öffentlichen Dokumentationswebsite.

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
