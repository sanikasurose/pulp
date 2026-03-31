from __future__ import annotations

import re

from pulp.config import Settings
from pulp.models import CleanedPage, CleaningResult, CleaningStats, ExtractionResult


def clean_extraction(extraction: ExtractionResult, *, settings: Settings) -> CleaningResult:
    """Apply heuristic cleaning rules to extracted text and collect cleaning stats."""
    _ = settings  # reserved for future tuning knobs

    stats = CleaningStats()
    pages_lines: list[list[str]] = []

    for page in extraction.pages:
        lines = _normalize_lines(page.raw_text)
        lines, removed_page_numbers = _remove_page_number_lines(lines)
        stats.removed_page_number_lines += removed_page_numbers
        lines = _remove_continued_lines(lines)
        pages_lines.append(lines)

    frequent_header_footer = _detect_repeated_header_footer(pages_lines)
    cleaned_pages: list[CleanedPage] = []

    for idx, page in enumerate(extraction.pages):
        lines = pages_lines[idx]
        lines, removed_hf = _remove_header_footer(lines, frequent_header_footer)
        stats.removed_header_footer_lines += removed_hf

        text = "\n".join(lines).strip()
        text, rejoined = _rejoin_hyphenation(text)
        stats.rejoined_hyphenations += rejoined

        text, reassembled = _reassemble_wrapped_lines(text)
        stats.reassembled_paragraphs += reassembled

        if _meaningful_char_count(text) < 20:
            stats.dropped_blank_pages += 1
            continue

        cleaned_pages.append(CleanedPage(page_number=page.page_number, clean_text=text, warnings=[]))

    _reassemble_across_pages(cleaned_pages, stats=stats)

    warnings = list(extraction.warnings)
    return CleaningResult(meta=extraction.meta, pages=cleaned_pages, stats=stats, warnings=warnings)


_WS_RE = re.compile(r"[ \t]+")
_PAGE_NUM_RE = re.compile(
    r"^(?:\s*(?:page\s*)?\d+\s*(?:of\s*\d+)?\s*|\s*\d+\s*/\s*\d+\s*)$",
    re.IGNORECASE,
)
_CONTINUED_RE = re.compile(r"\b(continued|cont['’]d)\b", re.IGNORECASE)
_HYPHEN_BREAK_RE = re.compile(r"(?<=\w)-\n(?=[a-z])")
_HEADINGISH_RE = re.compile(r"^(?:#+\s+|\d+[\.\)]\s+)")


def _normalize_lines(text: str) -> list[str]:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [(_WS_RE.sub(" ", line).strip()) for line in text.split("\n")]
    # Preserve intentional blank lines but strip leading/trailing blanks.
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def _remove_page_number_lines(lines: list[str]) -> tuple[list[str], int]:
    removed = 0
    kept: list[str] = []
    for line in lines:
        if not line:
            kept.append(line)
            continue
        if _PAGE_NUM_RE.match(line):
            removed += 1
            continue
        kept.append(line)
    return kept, removed


def _remove_continued_lines(lines: list[str]) -> list[str]:
    kept: list[str] = []
    for line in lines:
        if not line:
            kept.append(line)
            continue
        if _CONTINUED_RE.search(line) and len(line) <= 40:
            continue
        kept.append(line)
    return kept


def _detect_repeated_header_footer(pages_lines: list[list[str]]) -> set[str]:
    page_count = len(pages_lines)
    if page_count < 2:
        return set()

    normalized_counts: dict[str, int] = {}
    for lines in pages_lines:
        non_empty = [ln for ln in lines if ln]
        candidates = non_empty[:2] + non_empty[-2:]
        seen_this_page: set[str] = set()
        for line in candidates:
            norm = _normalize_hf(line)
            if not norm or norm in seen_this_page:
                continue
            seen_this_page.add(norm)
            normalized_counts[norm] = normalized_counts.get(norm, 0) + 1

    threshold = int((page_count * 0.6) + 0.9999)  # ceil
    return {line for line, count in normalized_counts.items() if count >= threshold}


def _normalize_hf(line: str) -> str:
    norm = _WS_RE.sub(" ", line.strip()).lower()
    if len(norm) < 3:
        return ""
    if len(norm) > 120:
        return ""
    return norm


def _remove_header_footer(lines: list[str], frequent_norms: set[str]) -> tuple[list[str], int]:
    if not frequent_norms:
        return lines, 0

    removed = 0
    out = list(lines)

    # Remove from the top while matching frequent header lines.
    while out and out[0] and _normalize_hf(out[0]) in frequent_norms:
        out.pop(0)
        removed += 1

    # Remove from the bottom while matching frequent footer lines.
    while out and out[-1] and _normalize_hf(out[-1]) in frequent_norms:
        out.pop()
        removed += 1

    return out, removed


def _rejoin_hyphenation(text: str) -> tuple[str, int]:
    new_text, count = _HYPHEN_BREAK_RE.subn("", text)
    return new_text, count


def _reassemble_wrapped_lines(text: str) -> tuple[str, int]:
    lines = _normalize_lines(text)
    if not lines:
        return "", 0

    out: list[str] = []
    reassembled = 0
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            if out and out[-1] != "":
                out.append("")
            i += 1
            continue

        current = line
        j = i
        while j + 1 < len(lines) and lines[j + 1].strip():
            nxt = lines[j + 1].strip()
            if _should_join_lines(current, nxt):
                current = f"{current.rstrip()} {nxt.lstrip()}"
                reassembled += 1
                j += 1
            else:
                break
        out.append(current)
        i = j + 1

    # Trim trailing blank separators.
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out).strip(), reassembled


def _should_join_lines(prev: str, nxt: str) -> bool:
    if not prev or not nxt:
        return False
    if _HEADINGISH_RE.match(nxt):
        return False
    if nxt.startswith(("-", "*", "•")):
        return False
    prev_end = prev.rstrip()[-1]
    if prev_end in ".!?":
        return False
    if prev_end == ":" and (nxt[:1].isupper() or _HEADINGISH_RE.match(nxt)):
        return False
    # Join when likely a wrapped line in a paragraph.
    if nxt[:1].islower():
        return True
    if prev_end in ",;":
        return True
    return False


def _meaningful_char_count(text: str) -> int:
    return len(re.sub(r"[^A-Za-z0-9]+", "", text or ""))


def _reassemble_across_pages(pages: list[CleanedPage], *, stats: CleaningStats) -> None:
    for i in range(len(pages) - 1):
        prev_lines = pages[i].clean_text.splitlines()
        next_lines = pages[i + 1].clean_text.splitlines()

        prev_idx = _last_non_empty_line_index(prev_lines)
        next_idx = _first_non_empty_line_index(next_lines)
        if prev_idx is None or next_idx is None:
            continue

        prev_line = prev_lines[prev_idx].strip()
        next_line = next_lines[next_idx].strip()
        if not _should_join_lines(prev_line, next_line):
            continue

        prev_lines[prev_idx] = f"{prev_line.rstrip()} {next_line.lstrip()}"
        next_lines.pop(next_idx)
        pages[i].clean_text = "\n".join(prev_lines).strip()
        pages[i + 1].clean_text = "\n".join(next_lines).strip()
        stats.reassembled_paragraphs += 1


def _first_non_empty_line_index(lines: list[str]) -> int | None:
    for idx, line in enumerate(lines):
        if line.strip():
            return idx
    return None


def _last_non_empty_line_index(lines: list[str]) -> int | None:
    for idx in range(len(lines) - 1, -1, -1):
        if lines[idx].strip():
            return idx
    return None
