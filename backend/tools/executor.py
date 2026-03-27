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

    def clear_history(self) -> None:
        """Clear call history (call this at start of new conversation turn)"""
        self._call_history.clear()

    @staticmethod
    def _inject_context(name: str, args: dict, context: Optional[dict]) -> None:
        """Inject context fields into tool arguments in-place.

        - file_* tools: inject project_id
        - agent_task: inject model and project_id (prefixed with _ to avoid collisions)
        - parallel_execute: inject project_id (prefixed with _ to avoid collisions)
        """
        if not context:
            return
        if name.startswith("file_") and "project_id" in context:
            args["project_id"] = context["project_id"]
        if name == "agent_task":
            if "model" in context:
                args["_model"] = context["model"]
            if "project_id" in context:
                args["_project_id"] = context["project_id"]
        if name == "parallel_execute":
            if "project_id" in context:
                args["_project_id"] = context["project_id"]

    def process_tool_calls_parallel(
        self,
        tool_calls: List[dict],
        context: Optional[dict] = None,
        max_workers: int = 4,
    ) -> List[dict]:
        """
        Process tool calls concurrently and return message list (ordered by input).

        Identical logic to process_tool_calls but uses ThreadPoolExecutor so that
        independent tool calls (e.g. reading 3 files, running 2 searches) execute
        in parallel instead of sequentially.

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

        # Phase 1: prepare each call (parse args, inject context, check dedup/cache)
        # This phase is fast and sequential – it must be done before parallelism
        # to avoid race conditions on seen_calls / _call_history / _cache.
        prepared: List[Optional[tuple]] = [None] * len(tool_calls)
        seen_calls: set = set()

        for i, call in enumerate(tool_calls):
            name = call["function"]["name"]
            args_str = call["function"]["arguments"]
            call_id = call["id"]

            # Parse JSON arguments
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except json.JSONDecodeError:
                prepared[i] = self._create_error_result(call_id, name, "Invalid JSON arguments")
                continue

            # Inject context into tool arguments
            self._inject_context(name, args, context)

            # Dedup within same batch
            call_key = f"{name}:{json.dumps(args, sort_keys=True)}"
            if call_key in seen_calls:
                prepared[i] = self._create_tool_result(
                    call_id, name,
                    {"success": True, "data": None, "cached": True, "duplicate": True}
                )
                continue
            seen_calls.add(call_key)

            # History dedup
            history_result = self._check_duplicate_in_history(name, args)
            if history_result is not None:
                prepared[i] = self._create_tool_result(call_id, name, {**history_result, "cached": True})
                continue

            # Cache check
            cache_key = self._make_cache_key(name, args)
            cached_result = self._get_cached(cache_key)
            if cached_result is not None:
                prepared[i] = self._create_tool_result(call_id, name, {**cached_result, "cached": True})
                continue

            # Mark as needing actual execution
            prepared[i] = ("execute", call_id, name, args, cache_key)

        # Separate pre-resolved results from tasks needing execution
        results: List[dict] = [None] * len(tool_calls)
        exec_tasks: Dict[int, tuple] = {}  # index -> (call_id, name, args, cache_key)

        for i, item in enumerate(prepared):
            if isinstance(item, dict):
                results[i] = item
            elif isinstance(item, tuple) and item[0] == "execute":
                _, call_id, name, args, cache_key = item
                exec_tasks[i] = (call_id, name, args, cache_key)

        # Phase 2: execute remaining calls in parallel
        if exec_tasks:
            def _run(idx: int, call_id: str, name: str, args: dict, cache_key: str) -> tuple:
                t0 = time.time()
                result = self._execute_tool(name, args)
                elapsed = time.time() - t0

                if result.get("success"):
                    self._set_cache(cache_key, result)

                self._call_history.append({
                    "name": name,
                    "args_str": json.dumps(args, sort_keys=True, ensure_ascii=False),
                    "result": result,
                })

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
            self._inject_context(name, args, context)

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



