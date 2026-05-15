"""Search agent."""

from __future__ import annotations

from models import ResearchState
from tools.search import search_web


def run_search(state: ResearchState) -> ResearchState:
	queries = state.get("search_queries", [])
	results: list[dict[str, str]] = []
	seen_urls: set[str] = set()

	for query in queries:
		for result in search_web(query):
			url = result.get("url", "")
			if not url or url in seen_urls:
				continue
			seen_urls.add(url)
			results.append(
				{
					"title": result.get("title", ""),
					"url": url,
					"snippet": result.get("snippet", ""),
					"score": 1.0,
					"query": query,
				}
			)

	state["search_results"] = results
	return state
