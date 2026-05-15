"""Core domain models for the webSearch research workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict


class ResearchState(TypedDict, total=False):
	user_query: str
	tasks: list[str]
	search_queries: list[str]
	search_results: list[dict[str, Any]]
	documents: list[dict[str, Any]]
	summaries: list[dict[str, Any]]
	verified_results: list[dict[str, Any]]
	reflection: dict[str, Any]
	final_report: str
	citations: list[dict[str, Any]]


@dataclass(slots=True)
class Task:
	text: str
	priority: int = 0


@dataclass(slots=True)
class SearchResult:
	title: str
	url: str
	snippet: str = ""
	score: float = 0.0


@dataclass(slots=True)
class Document:
	url: str
	title: str = ""
	content: str = ""
	source: str = ""


@dataclass(slots=True)
class Summary:
	url: str
	bullets: list[str] = field(default_factory=list)
	short_summary: str = ""


@dataclass(slots=True)
class VerifiedResult:
	url: str
	status: str
	notes: str = ""


@dataclass(slots=True)
class Citation:
	url: str
	location: str = ""
	note: str = ""


@dataclass(slots=True)
class FinalReport:
	title: str
	content: str
