from __future__ import annotations

from graph import build_graph


def test_graph_structure_matches_workflow():
	graph = build_graph()

	assert graph.entrypoint == "Planner"
	assert graph.stage_order() == [
		"Planner",
		"Search",
		"Crawl",
		"Summarize",
		"Verify",
		"Reflection",
	]
	assert graph.node_names() == [
		"Planner",
		"Search",
		"Crawl",
		"Summarize",
		"Verify",
		"Reflection",
	]

	edges = {(edge.source, edge.target, edge.condition) for edge in graph.edges}
	assert ("Planner", "Search", "") in edges
	assert ("Search", "Crawl", "") in edges
	assert ("Crawl", "Summarize", "") in edges
	assert ("Summarize", "Verify", "") in edges
	assert ("Verify", "Reflection", "") in edges
	assert ("Reflection", "Search", "should_continue=True") in edges
	assert ("Reflection", "END", "should_continue=False") in edges

	loop_edges = {(edge.source, edge.target, edge.condition) for edge in graph.loop_edges()}
	assert loop_edges == {
		("Reflection", "Search", "should_continue=True"),
		("Reflection", "END", "should_continue=False"),
	}
