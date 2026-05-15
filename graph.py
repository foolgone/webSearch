"""Workflow graph definition for the webSearch research pipeline.

This module keeps the first version framework-light while still expressing the
real control-flow structure of the project: a bounded research loop with a
single orchestrator entrypoint and a reflection-driven exit condition.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class WorkflowNode:
	name: str
	description: str


@dataclass(slots=True, frozen=True)
class WorkflowEdge:
	source: str
	target: str
	condition: str = ""


@dataclass(slots=True)
class WorkflowGraph:
	entrypoint: str
	nodes: list[WorkflowNode] = field(default_factory=list)
	edges: list[WorkflowEdge] = field(default_factory=list)

	def node_names(self) -> list[str]:
		return [node.name for node in self.nodes]

	def stage_order(self) -> list[str]:
		return [node.name for node in self.nodes if node.name != "END"]

	def outgoing(self, source: str) -> list[WorkflowEdge]:
		return [edge for edge in self.edges if edge.source == source]

	def loop_edges(self) -> list[WorkflowEdge]:
		return [edge for edge in self.edges if edge.source == "Reflection"]

	def describe(self) -> str:
		lines = [f"Entrypoint: {self.entrypoint}", f"Stage order: {' -> '.join(self.stage_order())}", "Nodes:"]
		for node in self.nodes:
			lines.append(f"- {node.name}: {node.description}")
		lines.append("Edges:")
		for edge in self.edges:
			condition = f" [{edge.condition}]" if edge.condition else ""
			lines.append(f"- {edge.source} -> {edge.target}{condition}")
		if self.loop_edges():
			lines.append("Loop edges:")
			for edge in self.loop_edges():
				condition = f" [{edge.condition}]" if edge.condition else ""
				lines.append(f"- {edge.source} -> {edge.target}{condition}")
		return "\n".join(lines)


def build_graph() -> WorkflowGraph:
	"""Build the first-version workflow graph."""
	return WorkflowGraph(
		entrypoint="Planner",
		nodes=[
			WorkflowNode("Planner", "Break the user question into research tasks and seed queries."),
			WorkflowNode("Search", "Collect and rank candidate sources for the current round."),
			WorkflowNode("Crawl", "Fetch pages and extract readable text."),
			WorkflowNode("Summarize", "Create faithful structured summaries."),
			WorkflowNode("Verify", "Check whether summaries are supported by sources."),
			WorkflowNode("Reflection", "Decide whether the next round should continue."),
		],
		edges=[
			WorkflowEdge("Planner", "Search"),
			WorkflowEdge("Search", "Crawl"),
			WorkflowEdge("Crawl", "Summarize"),
			WorkflowEdge("Summarize", "Verify"),
			WorkflowEdge("Verify", "Reflection"),
			WorkflowEdge("Reflection", "Search", condition="should_continue=True"),
			WorkflowEdge("Reflection", "END", condition="should_continue=False"),
		],
	)
