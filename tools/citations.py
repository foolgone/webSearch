"""Citation helper utilities."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from models import Citation


def build_citation(url: str, location: str = "") -> dict[str, str]:
    citation = Citation(url=url.strip(), location=location.strip(), note="")
    return asdict(citation)


def build_citation_with_note(url: str, location: str = "", note: str = "") -> dict[str, str]:
    citation = Citation(url=url.strip(), location=location.strip(), note=note.strip())
    return asdict(citation)


def dedupe_citations(citations: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    unique_citations: list[dict[str, str]] = []

    for citation in citations:
        normalized = build_citation_with_note(
            str(citation.get("url", "")),
            str(citation.get("location", "")),
            str(citation.get("note", "")),
        )
        key = (normalized["url"], normalized["location"], normalized["note"])
        if key in seen:
            continue
        seen.add(key)
        unique_citations.append(normalized)

    return unique_citations


def format_citation(citation: dict[str, Any]) -> str:
    url = str(citation.get("url", "")).strip() or "unknown"
    location = str(citation.get("location", "")).strip()
    note = str(citation.get("note", "")).strip()

    parts = [url]
    if location:
        parts.append(f"[{location}]")
    if note:
        parts.append(f"- {note}")
    return " ".join(parts)
