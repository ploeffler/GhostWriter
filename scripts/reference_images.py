#!/usr/bin/env python3
"""Projektweite Referenzbilder verwalten, unabhängig von Abschnittsillustrationen.

Bilder liegen unter reference-images/ und werden nicht automatisch in Manuskript
oder Buchausgabe aufgenommen. Upload/Import allein erteilt keine Referenzfreigabe.
"""
import argparse
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from render_view import tag_slug  # noqa: E402

EXT = {".png": ".png", ".jpg": ".jpg", ".jpeg": ".jpg"}
KINDS = {"project", "person", "place", "object", "scene", "chapter", "section"}
ROLES = {"book_image", "visual_reference"}
STATUSES = {"stored", "approved", "withdrawn"}


def directory(base):
    return base / "reference-images"


def all_references(base):
    out = {}
    folder = directory(base)
    if not folder.is_dir():
        return out
    for meta_path in sorted(folder.glob("ref-img-*.yml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        out[meta["id"]] = (meta, folder / meta["file"], meta_path)
    return out


def add(base, file, caption, description="", purpose="", roles=None, origin="unknown",
        license_info="", consent="", links=None):
    src = Path(file)
    if not src.is_file():
        raise SystemExit(f"{file}: Datei fehlt")
    ext = EXT.get(src.suffix.lower())
    if not ext:
        raise SystemExit("Nur PNG oder JPEG.")
    roles = list(dict.fromkeys(roles or ["visual_reference"]))
    if not roles or set(roles) - ROLES:
        raise SystemExit("Ungültige Bildrolle.")
    links = links or []
    for link in links:
        if link.get("kind") not in KINDS or not str(link.get("id", "")).strip():
            raise SystemExit("Jede Zuordnung braucht einen gültigen Typ und eine ID.")
    folder = directory(base)
    folder.mkdir(parents=True, exist_ok=True)
    slug = tag_slug(caption)[:48].strip("-") or "bild"
    iid, n = f"ref-img-{slug}", 2
    taken = set(all_references(base))
    while iid in taken:
        iid, n = f"ref-img-{slug}-{n}", n + 1
    dest = folder / f"{iid}{ext}"
    shutil.copyfile(src, dest)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    meta = {
        "id": iid, "file": dest.name, "caption": caption.strip(),
        "description": description.strip(), "purpose": purpose.strip(),
        "roles": roles, "status": "stored", "origin": origin,
        "license": license_info.strip(), "consent": consent.strip(),
        "created_at": now, "links": links
    }
    try:
        from PIL import Image
        with Image.open(dest) as im:
            meta["width_px"], meta["height_px"] = im.size
    except ImportError:
        pass
    (folder / f"{iid}.yml").write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=10**6),
        encoding="utf-8")
    return meta


def set_status(base, image_id, status):
    if status not in STATUSES:
        raise SystemExit("Ungültiger Status.")
    hit = all_references(base).get(image_id)
    if not hit:
        raise SystemExit(f"Referenzbild {image_id} nicht gefunden")
    meta, _, meta_path = hit
    meta["status"] = status
    meta_path.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=10**6),
                         encoding="utf-8")
    return meta


def select(base, image_ids):
    refs = all_references(base)
    selected = []
    for image_id in image_ids:
        hit = refs.get(image_id)
        if not hit:
            raise SystemExit(f"Referenzbild {image_id} nicht gefunden")
        meta, path, _ = hit
        if meta.get("status") != "approved" or "visual_reference" not in meta.get("roles", []):
            raise SystemExit(f"{image_id} ist nicht als visuelle Referenz freigegeben")
        selected.append({"id": image_id, "file": str(path), "caption": meta["caption"],
                         "description": meta.get("description", ""), "purpose": meta.get("purpose", "")})
    return selected


def parse_link(value):
    if ":" not in value:
        raise argparse.ArgumentTypeError("Zuordnung muss TYP:ID sein, z. B. person:char-opi")
    kind, ident = value.split(":", 1)
    if kind not in KINDS or not ident.strip():
        raise argparse.ArgumentTypeError("Ungültige Zuordnung; Typ: project, person, place, object, scene, chapter, section")
    return {"kind": kind, "id": ident.strip()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("project")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("add")
    p.add_argument("file")
    p.add_argument("--caption", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--purpose", default="")
    p.add_argument("--role", action="append", choices=sorted(ROLES), dest="roles")
    p.add_argument("--origin", choices=["own", "provided", "licensed", "generated", "unknown"], default="unknown")
    p.add_argument("--license", default="")
    p.add_argument("--consent", default="")
    p.add_argument("--link", action="append", type=parse_link, default=[])
    p = sub.add_parser("list")
    p.add_argument("--status", choices=sorted(STATUSES))
    p = sub.add_parser("approve")
    p.add_argument("image_id")
    p = sub.add_parser("withdraw")
    p.add_argument("image_id")
    p = sub.add_parser("select")
    p.add_argument("image_ids", nargs="+")
    a = ap.parse_args(argv)
    base = Path(a.project)
    if a.command == "add":
        meta = add(base, a.file, a.caption, a.description, a.purpose, a.roles, a.origin,
                   a.license, a.consent, a.link)
        print(f"Referenz {meta['id']} gespeichert (nicht freigegeben).")
    elif a.command == "list":
        for meta, path, _ in all_references(base).values():
            if not a.status or meta["status"] == a.status:
                print(f"{meta['id']}  {meta['status']}  {meta['caption']}  ({path})")
    elif a.command == "approve":
        meta = set_status(base, a.image_id, "approved")
        print(f"{meta['id']} als Referenz freigegeben.")
    elif a.command == "withdraw":
        meta = set_status(base, a.image_id, "withdrawn")
        print(f"{meta['id']} zurückgezogen; Datei und Historie bleiben erhalten.")
    elif a.command == "select":
        print(json.dumps(select(base, a.image_ids), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
