"""Tool executor with caching and deduplication"""
import json
import time
import hashlib
from typing import List, Dict, Optional, Any
from backend.tools.core import ToolRegistry, registry


class ToolExecutor:
    """Tool call executor with caching and deduplication"""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        enable_cache: bool = True,
        cache_ttl: int = 300,  # 5 minutes
    ):
        self.registry = registry or ToolRegistry()
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple] = {}  # key -> (result, timestamp)
        self._call_history: List[dict] = []  # Track calls in current session

    def _make_cache_key(self, name: str, args: dict) -> str:
        """Generate cache key from tool name and arguments"""
        args_str = json.dumps(args, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(f"{name}:{args_str}".encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[dict]:
        """Get cached result if valid"""
        if not self.enable_cache:
            return None
        if key in self._cache:
            result, timestamp = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return result
            del self._cache[key]
        return None

    def _set_cache(self, key: str, result: dict) -> None:
        """Cache a result"""
        if self.enable_cache:
            self._cache[key] = (result, time.time())

    def _check_duplicate_in_history(self, name: str, args: dict) -> Optional[dict]:
        """Check if same tool+args was called before in this session"""
        args_str = json.dumps(args, sort_keys=True, ensure_ascii=False)
        for record in self._call_history:
            if record["name"] == name and record["args_str"] == args_str:
                return record["result"]
        return None

    def clear_history(self) -> None:
        """Clear call history (call this at start of new conversation turn)"""
        self._call_history.clear()

    def process_tool_calls(
        self,
        tool_calls: List[dict],
        context: Optional[dict] = None
    ) -> List[dict]:
        """
        Process tool calls and return message list

        Args:
            tool_calls: Tool call list returned by LLM
            context: Optional context info (user_id, project_id, etc.)

        Returns:
            Tool response message list, can be appended to messages
        """
        results = []
        seen_calls = set()  # Track calls within this batch

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

            # Inject context into tool arguments
            if context:
                if name.startswith("file_") and "project_id" in context:
                    args["project_id"] = context["project_id"]

            # Check for duplicate within same batch
            call_key = f"{name}:{json.dumps(args, sort_keys=True)}"
            if call_key in seen_calls:
                # Skip duplicate, but still return a result
                results.append(self._create_tool_result(
                    call_id, name,
                    {"success": True, "data": None, "cached": True, "duplicate": True}
                ))
                continue
            seen_calls.add(call_key)

            # Check history for previous call in this session
            history_result = self._check_duplicate_in_history(name, args)
            if history_result is not None:
                result = {**history_result, "cached": True}
                results.append(self._create_tool_result(call_id, name, result))
                continue

            # Check cache
            cache_key = self._make_cache_key(name, args)
            cached_result = self._get_cached(cache_key)
            if cached_result is not None:
                result = {**cached_result, "cached": True}
                results.append(self._create_tool_result(call_id, name, result))
                continue

            # Execute tool with retry
            result = self._execute_tool(name, args)
            
            # Cache the result (only cache successful results)
            if result.get("success"):
                self._set_cache(cache_key, result)
            
            # Add to history
            self._call_history.append({
                "name": name,
                "args_str": json.dumps(args, sort_keys=True, ensure_ascii=False),
                "result": result
            })
            
            results.append(self._create_tool_result(call_id, name, result))

        return results

    def _execute_tool(
        self,
        name: str,
        arguments: dict,
    ) -> dict:
        """Execute a tool and return the result."""
        return self.registry.execute(name, arguments)

    def _create_tool_result(
        self,
        call_id: str,
        name: str,
        result: dict,
        execution_time: float = 0,
    ) -> dict:
        """Create tool result message"""
        result["execution_time"] = execution_time
        content = json.dumps(result, ensure_ascii=False, default=str)
        return {
            "role": "tool",
            "tool_call_id": call_id,
            "name": name,
            "content": content
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



