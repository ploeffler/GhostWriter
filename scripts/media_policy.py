"""Gemeinsame Uploadgrenzen und Originalschutz für Buchbilder (D13).

Keine Anbieteraufrufe und keine automatischen Verkleinerungen. Die Prüfung
arbeitet vor dem Anlegen von Dateien; Bestätigungen sind je Auftrag nötig.
"""
import os
from pathlib import Path

MAX_UPLOAD_BYTES = 20_000_000
BOOK_WARNING_BYTES = 500_000_000
EXTENSIONS = {'.png', '.jpg', '.jpeg'}
MEDIA_ROOTS = ('images', 'reference-images', 'cover', 'chapters', 'matter', 'import')


def stored_image_bytes(base):
    """Alle Bilddateien in Buchablagen, Originale eingeschlossen, einmal zählen.

    Unlesbare oder verlinkte Ablagen sind kein bekannter Nullbestand.
    """
    base = Path(base).resolve()
    total, seen = 0, set()
    for name in MEDIA_ROOTS:
        root = base / name
        if root.is_symlink():
            raise ValueError('Bildablage darf kein symbolischer Link sein')
        if not root.exists():
            continue
        if not root.is_dir():
            raise ValueError('Bildablage ist kein lesbarer Ordner')
        def onerror(error):
            raise error
        for folder, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
            for name in dirs + files:
                if (Path(folder) / name).is_symlink():
                    raise ValueError('Bildablage enthält einen symbolischen Link')
            for name in files:
                path = Path(folder) / name
                if path.suffix.lower() not in EXTENSIONS:
                    continue
                stat = path.stat()
                identity = (stat.st_dev, stat.st_ino)
                if identity not in seen:
                    seen.add(identity)
                    total += stat.st_size
    return total


def prepare_upload(base, source, *, additional_bytes=0, confirm_large_collection=False):
    """Validiert Dateigröße und Bestand. Liefert unveränderte Originalbytes."""
    source = Path(source)
    if not source.is_file() or source.is_symlink():
        raise ValueError('Bilddatei fehlt oder ist ein symbolischer Link')
    if source.suffix.lower() not in EXTENSIONS:
        raise ValueError('Nur PNG oder JPEG.')
    if source.stat().st_size > MAX_UPLOAD_BYTES:
        raise ValueError('Bilddatei überschreitet 20 MB')
    data = source.read_bytes()
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError('Bilddatei überschreitet 20 MB')
    projected = stored_image_bytes(base) + len(data) + additional_bytes
    if projected >= BOOK_WARNING_BYTES and not confirm_large_collection:
        raise ValueError('Bildbestand erreicht 500 MB; weiteres Hochladen ausdrücklich bestätigen')
    return data


def safe_destination(base, relative):
    """Kein Schreiben durch verlinkte Buchordner oder außerhalb des Projekts."""
    base = Path(base).resolve()
    destination = base / relative
    try:
        destination.resolve().relative_to(base)
    except ValueError:
        raise ValueError('Bildziel liegt außerhalb des Projekts') from None
    path = destination
    while path != base:
        if path.is_symlink():
            raise ValueError('Bildziel enthält einen symbolischen Link')
        path = path.parent
    return destination
