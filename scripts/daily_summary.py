#!/usr/bin/env python3
"""Ergänzt den täglichen Update-Report um Buchinhalte und GhostWriter-PRs."""
import datetime
import json
import os
import urllib.error
import urllib.request


def _git(*args):
    import subprocess
    result = subprocess.run(["git", *args], text=True, capture_output=True)
    if result.returncode:
        return ""
    return result.stdout


def _content_activity(branch, content_paths, since):
    ref = f"refs/remotes/origin/{branch}"
    if not _git("rev-parse", "--verify", ref):
        return 0, 0
    commits = [line for line in _git(
        "log", ref, f"--since={since}", "--format=%H", "--", *content_paths
    ).splitlines() if line]
    files = set()
    for commit in commits:
        names = _git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).splitlines()
        files.update(name for name in names if any(
            name == path.rstrip("/") or name.startswith(path.rstrip("/") + "/")
            for path in content_paths
        ))
    return len(commits), len(files)


def _recent_pull_requests(repo, since):
    url = f"https://api.github.com/repos/{repo}/pulls?state=all&sort=updated&direction=desc&per_page=100"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            pulls = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, ValueError) as exc:
        return None, f"PR-Übersicht nicht verfügbar ({exc})"
    recent = []
    for pr in pulls:
        updated = pr.get("updated_at", "")
        if updated < since:
            continue
        state = "gemergt" if pr.get("merged_at") else ("geschlossen" if pr.get("state") == "closed" else "offen")
        recent.append((pr.get("number"), pr.get("title", ""), state, pr.get("html_url", "")))
    return recent, None


def append_daily_summary(lines, repo, book_branches, manifest):
    """Hängt Tagesaktivität an; zählt ausschließlich Pfade aus manifest.book."""
    since_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    since = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    paths = [p for p in (manifest.get("book") or []) if p.rstrip("/") in {"chapters", "matter", "cover", "characters", "story", "research"}]
    lines.extend(["", "## Buchinhalte – letzte 24 Stunden", ""])
    rows = []
    for branch in sorted(set(book_branches)):
        commits, files = _content_activity(branch, paths, since)
        if commits:
            rows.append(f"| `{branch}` | {commits} | {files} |")
    if rows:
        lines.extend(["| Buch-Branch | Inhalts-Commits | geänderte Inhaltsdateien |", "|---|---:|---:|", *rows])
    else:
        lines.append("Keine Buchinhaltsänderungen im Berichtszeitraum.")

    lines.extend(["", "## GhostWriter-Pull-Requests – letzte 24 Stunden", ""])
    pulls, error = _recent_pull_requests(repo, since)
    if error:
        lines.append(f"_{error}_")
    elif pulls:
        lines.extend(["| PR | Status |", "|---|---|"])
        lines.extend(f"| [#{number} {title}]({url}) | {state} |" for number, title, state, url in pulls)
    else:
        lines.append("Keine aktualisierten Pull Requests im Berichtszeitraum.")


def main():
    import yaml
    import library
    from pathlib import Path

    manifest = yaml.safe_load(Path("ghostwriter-manifest.yml").read_text(encoding="utf-8")) or {}
    configs = library.branch_configs()
    default = library.default_branch()
    books = library.books(configs, manifest, default)
    lines = ["## Tägliche GitHub-Übersicht"]
    append_daily_summary(lines, os.environ.get("GITHUB_REPOSITORY", ""), [b["branch"] for b in books], manifest)
    rendered = "\\n".join(lines) + "\\n"
    print(rendered)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as stream:
            stream.write(rendered)


if __name__ == "__main__":
    main()
