# Buchkontext beim Start

Bei jedem Wiedereinstieg zuerst Projektregeln, Gliederung und Bearbeitungsstand aus dem gewählten Branch lesen. Alle weiteren Lesezugriffe auf denselben Commit beziehen; bei zwischenzeitlicher Änderung den Kontextplan erneuern.

## Feste Startregel

- Bis einschließlich **15.000 Wörter** den gesamten Manuskripttext lesen, soweit ausreichend Kontext für Regeln, Recherche und weiteren Dialog verbleibt.
- Über 15.000 Wörter die aktuellen Buch- und Kapitelzusammenfassungen lesen. Während der Arbeit den aktuellen Abschnitt und relevante Nachbarabschnitte, weitere Originalstellen oder Rechercheergebnisse nachladen.
- Reicht der Kontext auch unterhalb der Grenze nicht, denselben Zusammenfassungsmodus verwenden und die Einschränkung kurz mitteilen. Vollständiges Einlesen garantiert keine dauerhafte Verfügbarkeit im Chat.
- Die Grenze ist bis einschließlich v1.0 fest. Erst **ab v1.1** ist eine Einstellung vorgesehen; jetzt kein Konfigurationsfeld und kein Formular hinzufügen.
- Ein leeres Manuskript benötigt keine inhaltliche Zusammenfassung.

## Lesender Kontextplan

`python3 scripts/plan_context.py <projektordner>` liefert Wortzahl, Modus, Dateipfade, Inhaltsprüfsummen und Aktualitätsstatus, niemals Manuskripttext. `--limited-context` wählt den Zusammenfassungsmodus, wenn der Assistent seinen verfügbaren Kontext als unzureichend einschätzt. Das Skript lädt den Modellkontext nicht selbst; der Assistent führt die im Plan vorgesehenen Lesezugriffe aus. Ohne lokale Ausführung dieselben Regeln mit den GitHub-Lesewerkzeugen anwenden.

Gezählt werden Unicode-Wörter (Bindestrichwörter als ein Wort) ausschließlich im Bereich `## Manuskript` der in `structure.chapters` registrierten Abschnittsdateien, bis zur nächsten Überschrift derselben Ebene. Frontmatter, Ziele, Kurzbeschreibungen, Recherche, Kosten und technische Daten zählen nicht. `Noch nicht begonnen.` zählt als leer. Fehlende Abschnittsdateien sind ein Fehler; aus unvollständigen Daten keine Gesamtwortzahl behaupten.

Der Plan enthält `source_digest` für Buch und Kapitel. Die Kapitelprüfsumme bezieht stabile IDs, Titel, Reihenfolge, Pfade und Manuskripttext ein; die Buchprüfsumme umfasst alle Kapitel. Damit machen relevante Änderungen die betroffenen Zusammenfassungen veraltet, reine Kostenänderungen jedoch nicht.

## Zusammenfassungen pflegen

- Buch: `context/book.md`; Kapitel: `context/<chapter-id>.md`.
- Jede Datei beginnt mit YAML-Frontmatter: `source_commit` als vollständiger SHA des gelesenen Quellcommits und `source_digest` aus dessen Kontextplan. Danach folgt die tatsächliche inhaltliche Zusammenfassung; keine bloße Gliederung und kein vollständiger Originaltext.
- Kapitelzusammenfassungen nennen Kernaussagen, Argumentationsgang, wichtige Begriffe, Stilmerkmale, Querverweise und offene Widersprüche. Die Buchzusammenfassung beschreibt roten Faden, Gesamtaussage, Begriffs- und Stilkonventionen sowie Beziehungen zwischen Kapiteln. Unsicherheiten kennzeichnen; nichts erfinden.
- `missing` oder `stale` bedeutet: nicht als verlässlichen aktuellen Buchstand verwenden. Betroffene Originalabschnitte in passenden Portionen lesen und daraus aktuellen Kontext aufbauen. Fehlt die Buchzusammenfassung, sie aus aktuellen Kapitelzusammenfassungen und bei Bedarf Originalstellen entwickeln.
- Nach Manuskript- oder Strukturänderungen betroffene Kapitelzusammenfassungen und die Buchzusammenfassung aktualisieren. Vor dem Speichern den neuen Quellstand und dessen Prüfsummen lesen. Zusammenfassungen werden nach den regulären Schreib- und Freigaberegeln als Pull Request gespeichert; beim Start niemals ungefragt schreiben. Bis dahin kenntlich machen, dass die dauerhaften Zusammenfassungen fehlen/veraltet sind.
- `source_commit` verweist auf den Quellstand vor dem Commit der Zusammenfassung. Ein späterer Commit nur für Zusammenfassungen macht sie nicht automatisch veraltet; entscheidend ist die Inhaltsprüfsumme. Der Assistent prüft zusätzlich, dass der Quellcommit im gewählten Repository tatsächlich existiert.

Die Regel „kein ganzes Buch im Chat“ bleibt bestehen: Lesen ist erlaubt, Ausgabe höchstens eines Abschnittstexts auf einmal. Zusammenführen und Export bleiben bei der GitHub Action.

## Prompt-Umfang untersuchen

Die [Bestandsaufnahme und der lesende Prompt-Profiler](PROMPT-PROFILER.md)
zeigen die vorhandenen Modellwege und erlauben die Untersuchung explizit
übergebener Request-Snapshots. Der Kontextplan lädt keine Modellanfrage und
ist selbst kein Nachweis übertragener Tokens.

## Prüfung

`python3 -m unittest discover -s tests -p 'test_context.py'` prüft 15.000/15.001 Wörter, Kontextmangel, fehlende und nach Textänderung veraltete Zusammenfassungen, leere Manuskripte und Unicode-Wörter. Der Test läuft auch in der Prüf-Action. Ein realer Chat muss zusätzlich zeigen, dass die vorgesehenen Dateien tatsächlich gelesen und Einschränkungen korrekt gemeldet werden.

## Große Bücher abschnittsweise prüfen

Buchweite redaktionelle Prüfungen abschnittsweise ausführen. Originaldateien lokal
verarbeiten, soweit die Arbeitsumgebung dies unterstützt; keine vollständige
Dateisammlung und keine ursprünglichen/überarbeiteten Volltextkopien als
Chat-Werkzeugausgabe erzeugen. Im Chat nur Fortschritt, kompakte Befunde,
Fundstellen und erforderliche Entscheidungen anzeigen. Lokale Änderungen mit
gezielten Patches bearbeiten; Prüfungen geben Ergebnisse statt Volltexte aus.

Zuerst jeden Abschnitt mit den benötigten Figuren-, Zeit-, Orts- und
Rechercheangaben prüfen. Befunde und Quellstand in Dateien festhalten. Danach
Kapitelzusammenhang und Übergänge anhand der Abschnittsbefunde und gezielt
nachgeladener Originalstellen prüfen. Abschließend Handlungsstränge,
Figurenentwicklung, Zeitlinie und Widersprüche über das Buch abgleichen.
Zusammenfassungen allein belegen keine Widerspruchsfreiheit. Verdächtige Stellen
an den Originalen prüfen; nach Änderungen betroffene Nachbarstellen und
übergreifende Zusammenhänge erneut prüfen. Fehlender Dateizugriff oder fehlende
Ausführungsumgebung sind offenzulegen; keinen Hintergrundlauf vortäuschen.

Die API-Hintergrundanalysen (`scripts/analyze.py`) übertragen pro Aufruf einen
Abschnitt, bei Überlänge einen Teil mit höchstens 12.000 Manuskriptzeichen.
Absatz- und Satzgrenzen werden bevorzugt; notfalls wird an der Zeichengrenze
geteilt. Es gibt keine Überlappung: Beobachtungen über Teilgrenzen brauchen eine
zusätzliche gezielte Prüfung. Vor-/Nachspann wird je Eintrag behandelt.
Die rein lokale Sprachanalyse prüft vollständige Abschnitte ohne diese Teilung.

Geprüfte Ergebnisse werden pro Abschnitt/Teil zwischengespeichert. Alte
Kapitel-Caches werden nicht wiederverwendet. Änderungen an Text, Nummerierung,
Analyseauftrag, konfiguriertem Modell/Anbieter oder bekannten Figuren (bei
Figurenanalyse) machen betroffene Einträge ungültig. Kapitelkurzbeschreibungen
und -ziele sind eine Zusammenstellung der geprüften Abschnittsangaben, keine
zusätzliche freie Kapitelzusammenfassung. Stilvarianten nennen Abschnitte.

Das Zusammenführen überträgt ausschließlich extrahierte Ergebnisse. Größere
Ergebnislisten werden in begrenzten Gruppen paarweise verglichen, damit auch
weit auseinanderliegende Stellen zusammenkommen. Das kann bei vielen Befunden
quadratisch viele Aufrufe benötigen; die Planwerte sind grobe Schätzungen und
keine garantierte Kostenobergrenze. Überlange einzelne Ergebniseinträge führen
zu einem gemeldeten Fehler statt zu unbegrenzten Anfragen. Ein technischer
Fundstellenabgleich bestätigt das Zitat, nicht die inhaltliche Interpretation.
Diese Analysen ersetzen keine vollständige redaktionelle Romanprüfung.


---

<p align="right"><sub>Entwickelt mit Unterstützung von Claude (Anthropic) · <a href="https://claude.ai">claude.ai</a><br>Entwickelt mit Unterstützung von Codex (OpenAI)</sub>&nbsp;&nbsp;<picture><source media="(prefers-color-scheme: dark)" srcset="../assets/logo-dark.svg"><img src="../assets/logo.svg" alt="GhostWriter" height="22" align="absmiddle"></picture></p>
