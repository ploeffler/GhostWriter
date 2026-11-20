# GhostWriter v1.0 im Marktvergleich

Recherche und Bewertung vom **20. November 2026**. English: [Market comparison](MARKET-COMPARISON-v1.0.en.md).

> **Planungsstand, kein Praxistest:** Verglichen wird der **beschlossene v1.0-Zielumfang** ([Beschlüsse D01–D32](ENTSCHEIDUNGEN-v1.0.md), [Produkt-Roadmap](WORKFLOW-MODEL.md#produkt-roadmap)) mit den öffentlichen Angaben der Anbieter. Die Programmversion laut Manifest ist zum Recherchezeitpunkt 0.7.0. Keine der genannten Apps wurde praktisch getestet. Preise sind Momentaufnahmen. Geplante GhostWriter-Funktionen gelten erst nach Umsetzung und Abnahme als vorhanden.

## Was v1.0 sein soll

Ein vollständiger Buchablauf **ohne eigene Oberfläche und ohne KI-Anbieter-APIs**: Gearbeitet wird im Chat (ChatGPT, Codex, Claude, Open WebUI), das Buch liegt im eigenen GitHub-Repository. Dazu gehören Bibliothek mit mehreren Büchern, ausdrückliche Freigaben, unveränderliche Auflagen, Export als PDF, DOCX und EPUB, Figuren und Bilder mit Herkunftsangaben, Umschlag aus hochgeladener Vorlage, Manuskriptimport, Stil- und Kontinuitätsprüfung, Lektorat sowie Bedienung auf Deutsch und Englisch.

Nach v1.0: eigene Web-App und Offline-Modus (D06, D19), KI-Anbieter-API-Anbindungen; DOCX-Rückführung in v1.1 (D17); Vorwort, Nachwort, Glossar und Buchübersetzung in v1.5.

## Vergleichsprodukte

| App | Schwerpunkt | Modell (Stand der Quelle) |
|---|---|---|
| [Sudowrite](https://www.sudowrite.com/) | KI-Schreibhilfe für Belletristik | Abo mit Credits, etwa 19/29/59 US-Dollar monatlich, günstiger bei Jahreszahlung |
| [Novelcrafter](https://www.novelcrafter.com/pricing) | Story-Bible („Codex“), Planung, optionale KI mit eigenem API-Schlüssel | Browser, ab 4 US-Dollar monatlich |
| [Atticus](https://www.atticus.io/) | Schreiben und Buchsatz für Selfpublisher | Einmalig 147 US-Dollar |
| [Scrivener 3](https://www.literatureandlatte.com/scrivener/overview) | Klassisches Schreibprogramm für lange Texte, Snapshots, Compile | Einmalkauf, Mac etwa 60 US-Dollar |
| BookyAI | KI-Komplettablauf bis Amazon KDP | Siehe [BookyAI-Vergleich](BOOKYAI-VERGLEICH.md) |

## Funktionsvergleich

| Bereich | GhostWriter v1.0 (Ziel) | Vergleichsprodukte | Einschätzung |
|---|---|---|---|
| Schreiboberfläche | Chat; keine eigene Oberfläche bis v1.0 | Eigener Editor, Pinnwand, Gliederung (Scrivener, Atticus, Novelcrafter) | Nachteil |
| Einstieg | GitHub-Konto, Repository, Chat-Zugang | Installation oder Browser-Konto | Nachteil |
| Versionen, Freigaben, Auflagen | Git-Historie, ausdrückliche Freigaben, unveränderliche Auflagen | Snapshots (Scrivener), Revisionsverlauf (Novelcrafter) | Klare Stärke |
| KI-Kosten | Vorhandenes Chat-Abo, keine fiktiven API-Kosten | Credits (Sudowrite), eigener API-Schlüssel (Novelcrafter) | Stärke |
| Anbieterbindung | Dateien im eigenen Repository, KI austauschbar, lokale Modelle über Open WebUI | Plattform- oder Programmformat; Novelcrafter erlaubt lokale Modelle | Stärke |
| Recherche und Belege | Dokumentierte Prüfläufe, Quellen, Bildherkunft und Lizenzangaben | Meist keine belegorientierte Recherche | Eigenes Profil, besonders für Sachbücher |
| Figuren und Welt | Figurenreferenzen, Buchgedächtnis als Prüfung, Serienabgleich geplant | Codex mit Querverweisen und reihenweit geteilten Einträgen (Novelcrafter) | Nachteil im Bedienkomfort |
| Prosawerkzeuge für Romane | Schreiben und Überarbeiten im Chat | Spezialisierte Werkzeuge (Sudowrite), Figurengespräch (Novelcrafter) | Nachteil |
| Satz und Export | PDF, DOCX, EPUB; Bildposition, Textumfluss und Breite noch umzusetzen | Ausgereifte Gestaltungsvorlagen (Atticus), flexibles Compile (Scrivener) | Ausgabequalität noch nicht belegt |
| Zusammenarbeit | Rollen über GitHub-Rechte, kein gleichzeitiges Schreiben | Eingebaute Einladungen (Novelcrafter, Atticus) | Nachteil |
| Lektorat und Qualitätssicherung | Strukturlektorat, Sprachlektorat, Schlusskorrektur, KI-Musterliste | Teilweise Review-Funktionen (Novelcrafter) | Stärke |
| Übersetzung, Hörbuch, KDP-Recherche | Übersetzung erst v1.5; Hörbuch und KDP-Recherche nicht geplant | BookyAI bietet alle drei, teils als Zusatzlizenz | Lücke |
| Clientabdeckung | Vier Umgebungen vorgeschrieben, Testzugänge für ChatGPT und Claude noch nicht nachgewiesen | Eigene Anwendung, ein Bedienweg | Abnahmerisiko |

## Bewertung

GhostWriter tritt nicht als bessere Schreib-App an, sondern als **kontrollierte Buchentwicklung**: Quellen, nachvollziehbare Änderungen, verlässliche Freigaben und keine Bindung an einen KI-Anbieter. Für Bedienkomfort, Romanwerkzeuge oder ausgefeilten Satz sind Novelcrafter, Sudowrite oder Atticus nach eigenen Angaben weiter. Am deutlichsten hebt sich GhostWriter bei Sachbüchern, belegpflichtigen Texten und Projekten ab, in denen Versionen und Freigaben zählen.

**Empfehlung, keine beschlossene Roadmap-Änderung:** Den v1.0-Umfang nicht erweitern. Vorrang haben ein einfacher, durchgehend geprüfter Kernablauf und eine belegte Ausgabequalität von PDF und EPUB. Ob Bedienung und Ausgabe mithalten, zeigt nur ein vollständiger Praxistest von der Idee bis zur druckfähigen Ausgabe.

## Quellen

- Sudowrite: [Preise](https://editor.sudowrite.com/pricing), Zusammenfassung vom 09.11.2026 bei [Activepieces](https://www.activepieces.com/blog/sudowrite-pricing-2026-which-plan-should-you-get)
- Novelcrafter: [Preise](https://novelcrafter.com/pricing), [Codex](https://www.novelcrafter.com/features/codex), [Toolradar](https://toolradar.com/tools/novelcrafter/alternatives)
- Atticus: [Preisübersicht](https://www.publishing.co.uk/guides/how-much-does-atticus-cost/), [Kindlepreneur-Vergleich mit Vellum](https://kindlepreneur.com/vellum-alternatives/) (Atticus-Mitgründer, nicht unabhängig)
- Scrivener: [Mac App Store](https://apps.apple.com/us/app/scrivener-3/id1310686187?mt=12)
- BookyAI: [BookyAI-Vergleich](BOOKYAI-VERGLEICH.md)

---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
