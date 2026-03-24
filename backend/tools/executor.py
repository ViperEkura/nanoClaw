"""Tool executor"""
import json
import time
from typing import List, Dict, Optional, Generator, Any
from .core import ToolRegistry, registry


class ToolExecutor:
    """Tool call executor"""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.registry = registry or ToolRegistry()
        self.api_url = api_url
        self.api_key = api_key

    def process_tool_calls(
        self,
        tool_calls: List[dict],
        context: Optional[dict] = None
    ) -> List[dict]:
        """
        Process tool calls and return message list

        Args:
            tool_calls: Tool call list returned by LLM
            context: Optional context info (user_id, etc.)

        Returns:
            Tool response message list, can be appended to messages
        """
        results = []

        for call in tool_calls:
            name = call["function"]["name"]
            args_str = call["function"]["arguments"]
            call_id = call["id"]

            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                results.append(self._create_error_result(
                    call_id, name, "Invalid JSON arguments"
                ))
                continue

            result = self.registry.execute(name, args)
            results.append(self._create_tool_result(call_id, name, result))

        return results

    def _create_tool_result(
        self,
        call_id: str,
        name: str,
        result: dict,
        execution_time: float = 0
    ) -> dict:
        """Create tool result message"""
        result["execution_time"] = execution_time
        return {
            "role": "tool",
            "tool_call_id": call_id,
            "name": name,
            "content": json.dumps(result, ensure_ascii=False, default=str)
        }

    def _create_error_result(
        self,
        call_id: str,
        name: str,
        error: str
    ) -> dict:
        """Create error result message"""
        return {
            "role": "tool",
            "tool_call_id": call_id,
            "name": name,
            "content": json.dumps({
                "success": False,
                "error": error
            }, ensure_ascii=False)
        }

    def build_request(
        self,
        messages: List[dict],
        model: str = "glm-5",
        tools: Optional[List[dict]] = None,
        **kwargs
    ) -> dict:
        """
        Build API request body

        Args:
            messages: Message list
            model: Model name
            tools: Tool list (default: all tools in registry)
            **kwargs: Other parameters (temperature, max_tokens, etc.)

        Returns:
            Request body dict
        """
        return {
            "model": model,
            "messages": messages,
            "tools": tools or self.registry.list_all(),
            "tool_choice": kwargs.get("tool_choice", "auto"),
            **{k: v for k, v in kwargs.items() if k not in ["tool_choice"]}
        }

    def execute_with_retry(
        self,
        name: str,
        arguments: dict,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> dict:
        """
        Execute tool with retry

        Args:
            name: Tool name
            arguments: Tool arguments
            max_retries: Max retry count
            retry_delay: Retry delay in seconds

        Returns:
            Execution result
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return self.registry.execute(name, arguments)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        return {
            "success": False,
            "error": f"Failed after {max_retries} retries: {last_error}"
        }
