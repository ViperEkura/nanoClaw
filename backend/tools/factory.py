"""Tool factory - decorator registration"""
from typing import Callable
from backend.tools.core import ToolDefinition, registry


def tool(
    name: str,
    description: str,
    parameters: dict,
    category: str = "general"
) -> Callable:
    """
    Tool registration decorator

    Usage:
        @tool(
            name="web_search",
            description="Search the web",
            parameters={"type": "object", "properties": {...}},
            category="crawler"
        )
        def web_search(arguments: dict) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=func,
            category=category
        )
        registry.register(tool_def)
        return func
    return decorator

