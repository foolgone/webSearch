"""MCP-facing adapter for the first version."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from orchestrator import Orchestrator


@dataclass(slots=True, frozen=True)
class MCPTool:
    name: str
    description: str
    handler: Callable[[str], dict[str, Any]]


def _run_query(user_query: str) -> dict[str, Any]:
    orchestrator = Orchestrator()
    return orchestrator.run(user_query)


def run_mcp_query(user_query: str) -> dict:
    return _run_query(user_query)


def get_tools() -> list[MCPTool]:
    return [
        MCPTool(
            name="research_search",
            description="Run the multi-agent research pipeline for a user query.",
            handler=_run_query,
        ),
    ]


def call_tool(name: str, user_query: str) -> dict[str, Any]:
    for tool in get_tools():
        if tool.name == name:
            return tool.handler(user_query)
    raise ValueError(f"Unknown MCP tool: {name}")
