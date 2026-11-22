---
name: {{SKILL}}
description: {{TITLE}}: Arbeit an der GhostWriter-{{KIND}} {{REPO}} – Repo einrichten, Schreibzugriff als {{GIT_LOGIN}} prüfen, Texte in der Standard-Erzählstimme schreiben, Fehler oder Wünsche als Issue im Hauptrepo {{UPSTREAM}} melden.
---

# {{TITLE}}

Erzeugt aus `assistant.yml` mit `python scripts/assistant.py . skill` (#136). Nicht von Hand ändern: Änderungen gehören ins Profil (Befehl `Profil`), danach wird diese Datei neu erzeugt. Eigenes (etwa erprobte Werkzeugwege) gehört in den Bereich „Eigene Ergänzungen“ am Ende; er bleibt beim Neuerzeugen erhalten. Den allgemeinen Ablauf beschreibt der Skill `ghostwriter` (Einrichten, Schreibzugriff, Issues melden); dies hier sind nur die Angaben für dieses Repository. Dieser Skill hängt von Benutzer und Repository ab und lebt nur hier im Repository: nicht als Skill im Claude-Konto anlegen. Ist dort ein gleichnamiger Skill gelistet, gilt diese Fassung.

## Repository

- Repository: `{{REPO}}` ({{KIND}}); bei jedem Aufruf von `scripts/render_view.py` `--repo {{REPO}}` mitgeben.
- Schreibzugriff prüfen, ohne etwas zu ändern: `gh api repos/{{REPO}} --jq .permissions.push`, mit Klon `git push --dry-run origin HEAD`.
{{GIT_LINES}}
{{DISPLAY_LINE}}
{{WORK_MODE_LINE}}
{{SUBAGENT_LINE}}

## Autor und Stimme

{{AUTHOR_LINE}}

{{VOICE_LINES}}

Vorrang: Vorgaben im Abschnitt, dann das Stilprofil des Buchs (`style` in dessen `ghostwriter.yml`), dann diese Standard-Erzählstimme.

## Fehler und Wünsche

Fehler und Wünsche zum Programm ohne Rückfrage als Issue im Hauptrepo `{{UPSTREAM}}` melden und dem Benutzer Nummer und Link nennen; der Ablauf (Duplikate, Gliederung **Beobachtet** / **Ursache** / **Vorschlag**, Werkzeugweg über `gh api`) steht im Skill `ghostwriter`, Abschnitt 13. Im Issue das Repository `{{REPO}}` nennen. Keine Manuskripttexte, keine Secrets.

## Eigene Ergänzungen

{{OWN_START}}
{{OWN_END}}
