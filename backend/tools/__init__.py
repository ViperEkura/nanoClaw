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

from backend.tools.core import registry
from backend.tools.factory import tool
from backend.tools.executor import ToolExecutor


# ---------------------------------------------------------------------------
# Service locator – allows tools (e.g. multi_agent) to access LLM client
# ---------------------------------------------------------------------------
_services: dict = {}


def register_service(name: str, service) -> None:
    """Register a shared service (e.g. LLM client) for tool access."""
    _services[name] = service


def get_service(name: str):
    """Retrieve a previously registered service, or None."""
    return _services.get(name)


def init_tools() -> None:
    """
    Initialize all built-in tools

    Importing builtin module automatically registers all decorator-defined tools
    """
    from backend.tools.builtin import code, crawler, data, weather, file_ops, agent  # noqa: F401


# Public API exports
__all__ = [
    # Instances
    "registry",
    # Factory functions
    "tool",
    # Classes
    "ToolExecutor",
    # Initialization
    "init_tools",
    # Service locator
    "register_service",
    "get_service",
]
