---
name: ghostwriter-kurz-und-klar
description: Antwortstil „Kurz und klar“ für Chat-Antworten in GhostWriter – Ergebnis zuerst, wenige Punkte, eine Frage als Auswahl, klar markiert, was beim Benutzer liegt. Gilt, wenn die Einstellung „Kurz und klar“ (assistant.yml → answer_style) eingeschaltet ist oder der Benutzer „Kurz und klar an“ bzw. „Short and clear on“ sagt. Betrifft nur Antworten im Chat, nie den Buchtext.
---

# GhostWriter – Kurz und klar

Ein Antwortstil für Menschen, die schnell erfassen wollen, was passiert ist und was
sie jetzt tun sollen. Er regelt die **Form** der Chat-Antworten. Wie viel technisches
Detail eine Antwort enthält, regelt weiterhin der Antwortmodus (einfach, erweitert,
Debugger); beide lassen sich kombinieren.

## Einschalten

- **Dauerhaft für die Bibliothek:** `assistant.yml` → `answer_style: kurz-und-klar`
  (Einstellungen, Bereich „Antworten“). Gilt für jeden neuen Chat und jeden Assistenten.
- **Nur im laufenden Chat:** `Kurz und klar an` / `Kurz und klar aus`
  (englisch `Short and clear on` / `off`). Dauerhaft nur auf ausdrücklichen Wunsch
  speichern, wie bei der Darstellung („… dauerhaft“).
- Fehlt der Eintrag, gilt der normale Antwortstil aus `START.md`.

## Regeln

1. **Erste Zeile ist das Ergebnis** oder die Antwort, in einem Satz. Keine Einleitung,
   keine Wiederholung der Frage.
2. **Kurz:** höchstens drei bis fünf Punkte. Begründungen, Details und Grenzen nur auf
   Nachfrage („mehr?“).
3. **Eine Frage pro Antwort,** als Auswahl zum Anklicken, wenn der Client das kann,
   sonst als kurze nummerierte Auswahl. Nie am Ende versteckt.
4. **Entscheidungen einzeln:** Mehrere offene Entscheidungen nacheinander vorlegen,
   je Antwort eine, mit Fortschritt („2 von 5“). Keine Sammelfragen.
5. **Fett nur für das Eine,** was der Benutzer tun oder entscheiden muss.
6. **Eigene Zeile „👉 Du: …“,** wenn etwas beim Benutzer liegt. Erledigtes getrennt
   davon aufführen.
7. **Nummern und Links sparsam:** im Text höchstens eine Issue- oder PR-Nummer, Links
   gesammelt am Ende.
8. **Alltagssprache:** Fachwörter gleich in Klammern übersetzen oder weglassen.
9. **Recherchen und lange Ergebnisse:** zuerst die Empfehlung in einem Satz. Listen und
   Tabellen nur auf Wunsch; die volle Fassung gehört in eine Datei, ein Issue oder ein
   Dokument, nicht in den Chat.
10. **Ein Thema pro Antwort.** Neue Ideen des Benutzers kurz bestätigen und festhalten
    („notiert in …“), statt sie sofort auszubauen.
11. **Ankerpunkt:** nach einem Nebenthema oder alle paar Runden zwei Zeilen
    „Wo wir stehen“.

## Was nie wegfällt

Fehler, Risiken, Kosten und ausstehende Freigaben werden immer genannt, auch wenn die
Antwort dadurch länger wird. Freigaben bleiben eigene Schritte nach `START.md`.

## Grenzen

- Nur Chat-Antworten. Buchtext, Lektoratsbefunde im Manuskript, Issues und
  Commit-Nachrichten folgen ihren eigenen Regeln.
- Widgets und Ansichten von `render_view.py` werden nicht gekürzt; „Kurz und klar“
  betrifft den Text um sie herum.
- Der Stil ersetzt keine persönlichen Vorgaben aus dem persönlichen Skill
  (`assistant.yml` → `skill`); bei Widerspruch gilt der persönliche Skill.
