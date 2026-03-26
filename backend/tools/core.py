"""Tool system core classes"""
from dataclasses import dataclass
from typing import Callable, Any, Dict, List, Optional


@dataclass
class ToolDefinition:
    """Tool definition"""
    name: str
    description: str
    parameters: dict  # JSON Schema
    handler: Callable[[dict], Any]
    category: str = "general"

    def to_openai_format(self) -> dict:
        """Convert to OpenAI/GLM compatible format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


@dataclass
class ToolResult:
    """Tool execution result"""
    success: bool
    data: Any = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }

    @classmethod
    def ok(cls, data: Any) -> "ToolResult":
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "ToolResult":
        return cls(success=False, error=error)


class ToolRegistry:
    """Tool registry (singleton)"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, ToolDefinition] = {}
        return cls._instance

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name"""
        return self._tools.get(name)

    def list_all(self) -> List[dict]:
        """List all tools in OpenAI format"""
        return [t.to_openai_format() for t in self._tools.values()]

    def execute(self, name: str, arguments: dict) -> dict:
        """Execute a tool"""
        tool = self.get(name)
        if not tool:
            return ToolResult.fail(f"Tool not found: {name}").to_dict()

        try:
            result = tool.handler(arguments)
            if isinstance(result, ToolResult):
                return result.to_dict()
            return ToolResult.ok(result).to_dict()
        except Exception as e:
            return ToolResult.fail(str(e)).to_dict()


# Global registry instance
registry = ToolRegistry()
