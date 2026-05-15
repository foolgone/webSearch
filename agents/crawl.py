"""Crawl agent."""

from __future__ import annotations

from models import ResearchState
from tools.fetch import fetch_url
from tools.parse import parse_html


def run_crawl(state: ResearchState) -> ResearchState:
	results = state.get("search_results", [])
	documents: list[dict[str, str]] = []

	for result in results:
		url = result.get("url", "").strip()
		if not url:
			continue
		try:
			html = fetch_url(url)
			parsed = parse_html(html)
			documents.append(
				{
					"url": url,
					"title": parsed.get("title") or result.get("title", ""),
					"content": parsed.get("content", ""),
					"source": "crawl",
					"search_snippet": result.get("snippet", ""),
				}
			)
		except Exception as exc:  # noqa: BLE001 - keep the first version simple
			documents.append(
				{
					"url": url,
					"title": result.get("title", ""),
					"content": "",
					"source": "crawl",
					"search_snippet": result.get("snippet", ""),
					"error": str(exc),
				}
			)

	state["documents"] = documents
	return state
