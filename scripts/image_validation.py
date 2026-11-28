"""Vollständige Prüfung von Bilddateien vor dem Speichern oder Übertragen."""
from io import BytesIO

_FORMATS = {'image/png': 'PNG', 'image/jpeg': 'JPEG', 'image/webp': 'WEBP'}

def validate_image(data, name='Bild', mime=None):
    """Prüft Dateiende und dekodiert das Bild vollständig; wirft ValueError mit verständlichem Hinweis."""
    data = bytes(data)
    label = f'{name} ({len(data)} Bytes)'
    if not data:
        raise ValueError(f'Eingabebild beschädigt oder unvollständig: {label} ist leer.')
    expected = _FORMATS.get(mime) if mime else None
    try:
        from PIL import Image
    except ImportError:
        if mime == 'image/png':
            valid = data.startswith(bytes.fromhex('89504e470d0a1a0a')) and data.endswith(bytes.fromhex('0000000049454e44ae426082'))
        elif mime == 'image/jpeg':
            valid = data.startswith(bytes.fromhex('ffd8ff')) and data.endswith(bytes.fromhex('ffd9'))
        elif mime == 'image/webp':
            valid = (len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP'
                     and int.from_bytes(data[4:8], 'little') + 8 == len(data))
        else:
            valid = False
        if not valid:
            raise ValueError(f'Eingabebild beschädigt oder unvollständig: {label} hat kein gültiges Dateiende.')
        return
    try:
        with Image.open(BytesIO(data)) as image:
            if expected and image.format != expected:
                raise ValueError(f'Format {image.format or "unbekannt"} statt {expected}')
            image.load()
    except Exception as exc:
        raise ValueError(
            f'Eingabebild beschädigt oder unvollständig: {label} ({type(exc).__name__}). '
            'Bild neu hochladen oder ersetzen; es wurde nichts gesendet und nichts gespeichert.'
        ) from None
