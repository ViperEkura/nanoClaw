"""Tool executor with caching and deduplication"""
import json
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    @staticmethod
    def _inject_context(name: str, args: dict, context: Optional[dict]) -> None:
        """Inject context fields into tool arguments in-place.

        - file_* tools: inject project_id
        - agent tools (multi_agent): inject _model and _project_id
        """
        if not context:
            return
        if name.startswith("file_") and "project_id" in context:
            args["project_id"] = context["project_id"]
        if name == "multi_agent":
            if "model" in context:
                args["_model"] = context["model"]
            if "project_id" in context:
                args["_project_id"] = context["project_id"]

    def _prepare_call(
        self,
        call: dict,
        context: Optional[dict],
        seen_calls: set,
    ) -> tuple:
        """Parse, inject context, check dedup/cache for a single tool call.

        Returns a tagged tuple:
          ("error",   call_id, name, error_msg)
          ("cached",  call_id, name, result_dict)  -- dedup or cache hit
          ("execute", call_id, name, args, cache_key)
        """
        name = call["function"]["name"]
        args_str = call["function"]["arguments"]
        call_id = call["id"]

        # Parse JSON arguments
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
        except json.JSONDecodeError:
            return ("error", call_id, name, "Invalid JSON arguments")

        # Inject context
        self._inject_context(name, args, context)

        # Dedup within same batch
        call_key = f"{name}:{json.dumps(args, sort_keys=True)}"
        if call_key in seen_calls:
            return ("cached", call_id, name,
                    {"success": True, "data": None, "cached": True, "duplicate": True})
        seen_calls.add(call_key)

        # History dedup
        history_result = self._check_duplicate_in_history(name, args)
        if history_result is not None:
            return ("cached", call_id, name, {**history_result, "cached": True})

        # Cache check
        cache_key = self._make_cache_key(name, args)
        cached_result = self._get_cached(cache_key)
        if cached_result is not None:
            return ("cached", call_id, name, {**cached_result, "cached": True})

        return ("execute", call_id, name, args, cache_key)

    def _execute_and_record(
        self,
        name: str,
        args: dict,
        cache_key: str,
    ) -> dict:
        """Execute a tool, cache result, record history, and return raw result dict."""
        result = self._execute_tool(name, args)
        if result.get("success"):
            self._set_cache(cache_key, result)
        self._call_history.append({
            "name": name,
            "args_str": json.dumps(args, sort_keys=True, ensure_ascii=False),
            "result": result,
        })
        return result

    def process_tool_calls_parallel(
        self,
        tool_calls: List[dict],
        context: Optional[dict] = None,
        max_workers: int = 4,
    ) -> List[dict]:
        """
        Process tool calls concurrently and return message list (ordered by input).

        Args:
            tool_calls: Tool call list returned by LLM
            context: Optional context info (user_id, project_id, etc.)
            max_workers: Maximum concurrent threads (1-6, default 4)

        Returns:
            Tool response message list in the same order as input tool_calls.
        """
        if len(tool_calls) <= 1:
            return self.process_tool_calls(tool_calls, context)

        max_workers = min(max(max_workers, 1), 6)

        # Phase 1: prepare (sequential – avoids race conditions on shared state)
        prepared = [self._prepare_call(call, context, set()) for call in tool_calls]

        # Phase 2: separate pre-resolved from tasks needing execution
        results: List[dict] = [None] * len(tool_calls)
        exec_tasks: Dict[int, tuple] = {}

        for i, item in enumerate(prepared):
            tag = item[0]
            if tag == "error":
                _, call_id, name, error_msg = item
                results[i] = self._create_error_result(call_id, name, error_msg)
            elif tag == "cached":
                _, call_id, name, result_dict = item
                results[i] = self._create_tool_result(call_id, name, result_dict)
            else:  # "execute"
                _, call_id, name, args, cache_key = item
                exec_tasks[i] = (call_id, name, args, cache_key)

        # Phase 3: execute remaining calls in parallel
        if exec_tasks:
            def _run(idx: int, call_id: str, name: str, args: dict, cache_key: str) -> tuple:
                t0 = time.time()
                result = self._execute_and_record(name, args, cache_key)
                elapsed = time.time() - t0
                return idx, self._create_tool_result(call_id, name, result, execution_time=elapsed)

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(_run, idx, cid, n, a, ck): idx
                    for idx, (cid, n, a, ck) in exec_tasks.items()
                }
                for future in as_completed(futures):
                    idx, result_msg = future.result()
                    results[idx] = result_msg

        return results

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
        seen_calls: set = set()

        for call in tool_calls:
            prepared = self._prepare_call(call, context, seen_calls)
            tag = prepared[0]

            if tag == "error":
                _, call_id, name, error_msg = prepared
                results.append(self._create_error_result(call_id, name, error_msg))
            elif tag == "cached":
                _, call_id, name, result_dict = prepared
                results.append(self._create_tool_result(call_id, name, result_dict))
            else:  # "execute"
                _, call_id, name, args, cache_key = prepared
                result = self._execute_and_record(name, args, cache_key)
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



