from __future__ import annotations

import codecs


def decode_text_upload(data: bytes) -> str:
    """Decode common plain-text file encodings without silently dropping bytes."""
    if not data:
        return ""

    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16")

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")

    # UTF-16 without a BOM can look like valid UTF-8 containing many NULs.
    if "\x00" in text:
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            pass

    return text
