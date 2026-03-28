"""Multi-agent tool for spawning concurrent sub-agents.

Provides:
- multi_agent: Spawn sub-agents with independent LLM conversation loops
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from backend.tools import get_service
from backend.tools.factory import tool
from backend.tools.core import registry
from backend.tools.executor import ToolExecutor
from backend.config import (
    DEFAULT_MODEL,
    SUB_AGENT_MAX_ITERATIONS,
    SUB_AGENT_MAX_CONCURRENCY,
    SUB_AGENT_TIMEOUT,
)

logger = logging.getLogger(__name__)

# Sub-agents are forbidden from using multi_agent to prevent infinite recursion
BLOCKED_TOOLS = {"multi_agent"}


def _to_executor_calls(tool_calls: list, id_prefix: str = "tc") -> list:
    """Normalize tool calls into executor-compatible format.

    Accepts two input shapes:
      - LLM format: {"function": {"name": ..., "arguments": ...}}
      - Simple format: {"name": ..., "arguments": ...}
    """
    executor_calls = []
    for i, tc in enumerate(tool_calls):
        if "function" in tc:
            func = tc["function"]
            executor_calls.append({
                "id": tc.get("id", f"{id_prefix}-{i}"),
                "type": tc.get("type", "function"),
                "function": {
                    "name": func["name"],
                    "arguments": func["arguments"],
                },
            })
        else:
            executor_calls.append({
                "id": f"{id_prefix}-{i}",
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                },
            })
    return executor_calls


def _run_sub_agent(
    task_name: str,
    instruction: str,
    tool_names: Optional[List[str]],
    model: str,
    max_tokens: int,
    temperature: float,
    project_id: Optional[str],
    app: Any,
    max_iterations: int = 3,
) -> dict:
    """Run a single sub-agent with its own agentic loop.

    Each sub-agent gets its own ToolExecutor instance and runs a simplified
    version of the main agent loop, limited to prevent runaway cost.
    """

    llm_client = get_service("llm_client")
    if not llm_client:
        return {
            "task_name": task_name,
            "success": False,
            "error": "LLM client not available",
        }

    # Build tool list – filter to requested tools, then remove blocked
    all_tools = registry.list_all()
    if tool_names:
        allowed = set(tool_names)
        tools = [t for t in all_tools if t["function"]["name"] in allowed]
    else:
        tools = list(all_tools)

    # Remove blocked tools to prevent recursion
    tools = [t for t in tools if t["function"]["name"] not in BLOCKED_TOOLS]

    executor = ToolExecutor(registry=registry)
    context = {"model": model}
    if project_id:
        context["project_id"] = project_id

    # System prompt: instruction + reminder to give a final text answer
    system_msg = (
        f"{instruction}\n\n"
        "IMPORTANT: After gathering information via tools, you MUST provide a final "
        "text response with your analysis/answer. Do NOT end with only tool calls."
    )
    messages = [{"role": "system", "content": system_msg}]

    for i in range(max_iterations):
        is_final = (i == max_iterations - 1)
        try:
            with app.app_context():
                resp = llm_client.call(
                    model=model,
                    messages=messages,
                    # On the last iteration, don't pass tools so the LLM is
                    # forced to produce a final text response instead of calling
                    # more tools.
                    tools=None if is_final else (tools if tools else None),
                    stream=False,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=SUB_AGENT_TIMEOUT,
                )

            if resp.status_code != 200:
                error_detail = resp.text[:500] if resp.text else f"HTTP {resp.status_code}"
                return {
                    "task_name": task_name,
                    "success": False,
                    "error": f"LLM API error: {error_detail}",
                }

            data = resp.json()
            choice = data["choices"][0]
            message = choice["message"]

            if message.get("tool_calls"):
                # Only extract needed fields — LLM response may contain extra
                # fields (e.g. reasoning_content) that the API rejects on re-send
                messages.append({
                    "role": "assistant",
                    "content": message.get("content") or "",
                    "tool_calls": message["tool_calls"],
                })
                tc_list = message["tool_calls"]
                executor_calls = _to_executor_calls(tc_list)
                # Execute tools inside app_context – file ops and other DB-
                # dependent tools require an active Flask context and session.
                with app.app_context():
                    if len(executor_calls) > 1:
                        tool_results = executor.process_tool_calls_parallel(
                            executor_calls, context
                        )
                    else:
                        tool_results = executor.process_tool_calls(
                            executor_calls, context
                        )
                messages.extend(tool_results)
            else:
                # Final text response
                return {
                    "task_name": task_name,
                    "success": True,
                    "response": message.get("content", ""),
                }

        except Exception as e:
            return {
                "task_name": task_name,
                "success": False,
                "error": str(e),
            }

    # Exhausted iterations without final response
    return {
        "task_name": task_name,
        "success": True,
        "response": "Agent task completed but did not produce a final text response within the iteration limit.",
    }


@tool(
    name="multi_agent",
    description=(
        "Spawn multiple sub-agents to work on tasks concurrently. "
        "Each agent runs its own independent conversation with the LLM and can use tools. "
        "Useful for parallel research, multi-file analysis, or dividing complex tasks into sub-tasks. "
        "Resource limits (iterations, tokens, concurrency) are configured in config.yml -> sub_agent."
    ),
    parameters={
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Short name/identifier for this task",
                        },
                        "instruction": {
                            "type": "string",
                            "description": "Detailed instruction for the sub-agent",
                        },
                        "tools": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Tool names this agent can use (empty = all tools). "
                                "e.g. ['file_read', 'file_list', 'web_search']"
                            ),
                        },
                    },
                    "required": ["name", "instruction"],
                },
                "description": "Tasks for parallel sub-agents (max 5)",
            },
        },
        "required": ["tasks"],
    },
    category="agent",
)
def multi_agent(arguments: dict) -> dict:
    """Spawn sub-agents to work on tasks concurrently.

    Args:
        arguments: {
            "tasks": [
                {
                    "name": "research",
                    "instruction": "Research Python async patterns...",
                    "tools": ["web_search", "fetch_page"]
                },
                {
                    "name": "code_review",
                    "instruction": "Review code quality...",
                    "tools": ["file_read", "file_list"]
                }
            ]
        }

    Returns:
        {"success": true, "results": [{task_name, success, response/error}], "total": int}
    """
    from flask import current_app

    tasks = arguments["tasks"]

    if len(tasks) > 5:
        return {"success": False, "error": "Maximum 5 concurrent agents allowed"}

    # Get current conversation context for model/project info
    app = current_app._get_current_object()

    # Use injected model/project_id from executor context, fall back to defaults
    model = arguments.get("_model") or DEFAULT_MODEL
    project_id = arguments.get("_project_id")
    max_tokens = arguments.get("_max_tokens", 65536)
    temperature = arguments.get("_temperature", 0.7)

    # Execute agents concurrently
    concurrency = min(len(tasks), SUB_AGENT_MAX_CONCURRENCY)
    results = [None] * len(tasks)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {
            pool.submit(
                _run_sub_agent,
                task["name"],
                task["instruction"],
                task.get("tools"),
                model,
                max_tokens,
                temperature,
                project_id,
                app,
                SUB_AGENT_MAX_ITERATIONS,
            ): i
            for i, task in enumerate(tasks)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = {
                    "task_name": tasks[idx]["name"],
                    "success": False,
                    "error": str(e),
                }

    return {
        "success": True,
        "results": results,
        "total": len(results),
    }
