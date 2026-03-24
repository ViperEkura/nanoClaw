"""
NanoClaw Tool System

Usage:
    from backend.tools import registry, ToolExecutor, tool
    from backend.tools import init_tools

    # Initialize built-in tools
    init_tools()

    # List all tools
    tools = registry.list_all()

    # Execute a tool
    result = registry.execute("web_search", {"query": "Python"})
"""

from .core import ToolDefinition, ToolResult, ToolRegistry, registry
from .factory import tool, register_tool
from .executor import ToolExecutor


def init_tools() -> None:
    """
    Initialize all built-in tools

    Importing builtin module automatically registers all decorator-defined tools
    """
    from .builtin import crawler, data  # noqa: F401


# Public API exports
__all__ = [
    # Core classes
    "ToolDefinition",
    "ToolResult",
    "ToolRegistry",
    "ToolExecutor",
    # Instances
    "registry",
    # Factory functions
    "tool",
    "register_tool",
    # Initialization
    "init_tools",
]
