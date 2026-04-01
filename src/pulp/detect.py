from __future__ import annotations

from pathlib import Path

import pdfplumber

from pulp.config import Settings
from pulp.models import DetectionResult, DocumentClassification, DocumentMeta


def detect_pdf(input_pdf: Path, *, settings: Settings) -> DetectionResult:
    """Classify PDF as text-layer vs scanned and return basic metadata."""
    input_pdf = Path(input_pdf)
    stat = input_pdf.stat()

    sampled_texts: list[str] = []

    with pdfplumber.open(str(input_pdf)) as pdf:
        page_count = len(pdf.pages)
        if page_count < 1:
            raise ValueError("PDF has no pages.")

        sample_pages = max(1, min(settings.detect_sample_pages, page_count))
        sampled_indices = _sample_page_indices(page_count, sample_pages)

        sampled_chars: list[int] = []
        for page_index in sampled_indices:
            text = pdf.pages[page_index].extract_text() or ""
            sampled_chars.append(len(text.strip()))
            sampled_texts.append(text)

    avg_chars_per_page = sum(sampled_chars) / max(1, len(sampled_chars))
    classification = (
        DocumentClassification.SCANNED
        if (settings.force_ocr or avg_chars_per_page < settings.scanned_chars_threshold)
        else DocumentClassification.TEXT_LAYER
    )

    combined_text = " ".join(sampled_texts)
    language = _detect_language(combined_text)

    meta = DocumentMeta(
        source_path=str(input_pdf),
        page_count=page_count,
        file_size_bytes=stat.st_size,
        classification=classification,
        language=language,
    )

    return DetectionResult(
        meta=meta,
        sampled_pages=len(sampled_indices),
        avg_chars_per_page=avg_chars_per_page,
    )


# Heuristic language detection: score text against letter-frequency profiles.
# Covers the most common European languages without any external dependency.
_LANG_PROFILES: dict[str, set[str]] = {
    "en": set("etaoinshrdlcumwfgypbvkjxqz"),
    "de": set("enisratdhulcgmobwfkzvüäöpj"),
    "fr": set("easntriuolcdmpévqfbghjàèù"),
    "es": set("eaosnrilutdcpmvgbfhyqxzjk"),
    "pt": set("aeosrinmdutlcpvgqfbzhxjkw"),
    "it": set("eaionlrtscdupmvghfbzqxykwj"),
    "nl": set("enatirodslghvkmubpwjczfxy"),
    "pl": set("aioenwrstzlcdkmpgybhujfqvx"),
}

# Unique diacritics that are strong signals for a specific language.
_LANG_DIACRITICS: dict[str, str] = {
    "de": "äöüß",
    "fr": "àâæçéèêëîïôùûüÿœ",
    "es": "áéíóúüñ¿¡",
    "pt": "ãõáéíóúâêôçà",
    "it": "àèéìíîòóùú",
    "nl": "ëïöü",
    "pl": "ąćęłńóśźż",
}


def _detect_language(text: str) -> str | None:
    """Best-effort language detection based on character frequency and diacritics."""
    if not text or len(text.strip()) < 20:
        return None

    lower = text.lower()

    # Strong signal: diacritics unique to a language.
    diacritic_scores: dict[str, int] = {}
    for lang, chars in _LANG_DIACRITICS.items():
        score = sum(lower.count(ch) for ch in chars)
        if score > 0:
            diacritic_scores[lang] = score

    if diacritic_scores:
        return max(diacritic_scores, key=lambda k: diacritic_scores[k])

    # Fallback: letter-frequency overlap with known profiles.
    letters = [ch for ch in lower if ch.isalpha()]
    if not letters:
        return None

    total = len(letters)
    freq: dict[str, float] = {}
    for ch in letters:
        freq[ch] = freq.get(ch, 0) + 1.0 / total

    top_letters = {ch for ch, _ in sorted(freq.items(), key=lambda x: -x[1])[:8]}

    best_lang = "en"
    best_overlap = 0
    for lang, profile in _LANG_PROFILES.items():
        overlap = len(top_letters & profile)
        if overlap > best_overlap:
            best_overlap = overlap
            best_lang = lang

    return best_lang


def _sample_page_indices(page_count: int, sample_pages: int) -> list[int]:
    sample_pages = max(1, min(sample_pages, page_count))
    if sample_pages == 1:
        return [0]

    indices: list[int] = []
    for k in range(sample_pages):
        # Evenly spaced, inclusive of first/last page.
        idx = round(k * (page_count - 1) / (sample_pages - 1))
        if idx not in indices:
            indices.append(idx)

    if len(indices) < sample_pages:
        for idx in range(page_count):
            if idx not in indices:
                indices.append(idx)
            if len(indices) >= sample_pages:
                break

    return indices
