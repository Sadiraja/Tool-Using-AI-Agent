"""
Tool Registry module for managing, selecting, and documenting available agent tools.
"""

import difflib
from typing import Any, Dict, List, Optional
from tools.base import BaseTool


class ToolRegistry:
    """Central registry and selector for agent tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance in the registry."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieves a tool by exact name."""
        return self._tools.get(name)

    def select_tool(self, requested_name: str) -> BaseTool:
        """
        Selects a tool by name, raising a helpful exception with suggestions
        if the exact tool name is not found.
        """
        cleaned = requested_name.strip().lower()
        if cleaned in self._tools:
            return self._tools[cleaned]

        # Common aliases mapping
        aliases = {
            "sql": "database_query",
            "sql_query": "database_query",
            "db_query": "database_query",
            "calc": "calculator",
            "math": "calculator",
            "eval": "calculator",
            "search": "web_search",
            "google": "web_search",
            "read_file": "file_reader",
            "read": "file_reader",
            "write_file": "file_writer",
            "write": "file_writer",
        }
        if cleaned in aliases and aliases[cleaned] in self._tools:
            return self._tools[aliases[cleaned]]

        # Suggest closest match
        matches = difflib.get_close_matches(cleaned, list(self._tools.keys()), n=2, cutoff=0.5)
        suggestion_str = f" Did you mean: {', '.join(matches)}?" if matches else ""
        available = ", ".join(self._tools.keys())
        raise KeyError(
            f"Tool '{requested_name}' is not registered.{suggestion_str} Available tools are: {available}."
        )

    def list_tools(self) -> List[str]:
        """Returns list of registered tool names."""
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns OpenAPI/JSON schemas for all registered tools."""
        return [tool.get_schema() for tool in self._tools.values()]

    def format_tools_prompt(self) -> str:
        """Formats tools documentation for inclusion in LLM prompt."""
        descriptions = []
        for name, tool in self._tools.items():
            schema = tool.get_schema()
            params = schema.get("parameters", {}).get("properties", {})
            req = schema.get("parameters", {}).get("required", [])

            param_lines = []
            for p_name, p_info in params.items():
                is_req = "required" if p_name in req else "optional"
                p_type = p_info.get("type", "any")
                p_desc = p_info.get("description", "")
                param_lines.append(f"    - {p_name} ({p_type}, {is_req}): {p_desc}")

            param_str = "\n".join(param_lines) if param_lines else "    None"
            descriptions.append(f"Tool: {name}\n  Description: {tool.description}\n  Parameters:\n{param_str}")

        return "\n\n".join(descriptions)
