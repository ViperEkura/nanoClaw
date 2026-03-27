"""Multi-agent tools for concurrent and batch task execution.

Provides:
- parallel_execute: Run multiple tool calls concurrently
- agent_task: Spawn sub-agents with their own LLM conversation loops
"""
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from backend.tools.factory import tool
from backend.tools.core import registry
from backend.tools.executor import ToolExecutor


# ---------------------------------------------------------------------------
# parallel_execute – run multiple tool calls concurrently
# ---------------------------------------------------------------------------

@tool(
    name="parallel_execute",
    description=(
        "Execute multiple tool calls concurrently for better performance. "
        "Use when you have several independent operations that don't depend on each other "
        "(e.g. reading multiple files, running multiple searches, fetching several pages). "
        "Results are returned in the same order as the input."
    ),
    parameters={
        "type": "object",
        "properties": {
            "tool_calls": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Tool name to execute",
                        },
                        "arguments": {
                            "type": "object",
                            "description": "Arguments for the tool",
                        },
                    },
                    "required": ["name", "arguments"],
                },
                "description": "List of tool calls to execute in parallel (max 10)",
            },
            "concurrency": {
                "type": "integer",
                "description": "Max concurrent executions (1-5, default 3)",
                "default": 3,
            },
        },
        "required": ["tool_calls"],
    },
    category="agent",
)
def parallel_execute(arguments: dict) -> dict:
    """Execute multiple tool calls concurrently.

    Args:
        arguments: {
            "tool_calls": [
                {"name": "file_read", "arguments": {"path": "a.py"}},
                {"name": "web_search", "arguments": {"query": "python"}}
            ],
            "concurrency": 3,
            "_project_id": "..."  // injected by executor
        }

    Returns:
        {"results": [{index, tool_name, success, data/error}]}
    """
    tool_calls = arguments["tool_calls"]
    concurrency = min(max(arguments.get("concurrency", 3), 1), 5)

    if len(tool_calls) > 10:
        return {"success": False, "error": "Maximum 10 tool calls allowed per parallel execution"}

    # Build executor context from injected fields
    context = {}
    project_id = arguments.get("_project_id")
    if project_id:
        context["project_id"] = project_id

    # Format tool_calls into executor-compatible format
    executor_calls = []
    for i, tc in enumerate(tool_calls):
        executor_calls.append({
            "id": f"pe-{i}",
            "type": "function",
            "function": {
                "name": tc["name"],
                "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
            },
        })

    # Use ToolExecutor for proper context injection, caching and dedup
    executor = ToolExecutor(registry=registry, enable_cache=False)
    executor_results = executor.process_tool_calls_parallel(
        executor_calls, context, max_workers=concurrency
    )

    # Format output
    results = []
    for er in executor_results:
        try:
            content = json.loads(er["content"]) if isinstance(er["content"], str) else er["content"]
        except (json.JSONDecodeError, TypeError):
            content = {"success": False, "error": "Failed to parse result"}
        results.append({
            "index": len(results),
            "tool_name": er["name"],
            **content,
        })

    return {
        "success": True,
        "results": results,
        "total": len(results),
    }


# ---------------------------------------------------------------------------
# agent_task – spawn sub-agents with independent LLM conversation loops
# ---------------------------------------------------------------------------

def _run_sub_agent(
    task_name: str,
    instruction: str,
    tool_names: Optional[List[str]],
    model: str,
    max_tokens: int,
    project_id: Optional[str],
    app: Any,
    max_iterations: int = 3,
) -> dict:
    """Run a single sub-agent with its own agentic loop.

    Each sub-agent gets its own ToolExecutor instance and runs a simplified
    version of the main agent loop, limited to prevent runaway cost.
    """
    from backend.tools import get_service

    llm_client = get_service("llm_client")
    if not llm_client:
        return {
            "task_name": task_name,
            "success": False,
            "error": "LLM client not available",
        }

    # Build tool list – filter to requested tools or use all
    all_tools = registry.list_all()
    if tool_names:
        allowed = set(tool_names)
        tools = [t for t in all_tools if t["function"]["name"] in allowed]
    else:
        tools = all_tools

    executor = ToolExecutor(registry=registry)
    context = {"project_id": project_id} if project_id else None

    # System prompt: instruction + reminder to give a final text answer
    system_msg = (
        f"{instruction}\n\n"
        "IMPORTANT: After gathering information via tools, you MUST provide a final "
        "text response with your analysis/answer. Do NOT end with only tool calls."
    )
    messages = [{"role": "system", "content": system_msg}]

    for _ in range(max_iterations):
        try:
            with app.app_context():
                resp = llm_client.call(
                    model=model,
                    messages=messages,
                    tools=tools if tools else None,
                    stream=False,
                    max_tokens=min(max_tokens, 4096),
                    temperature=0.7,
                    timeout=60,
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
                messages.append(message)
                tc_list = message["tool_calls"]
                # Convert OpenAI tool_calls to executor format
                executor_calls = []
                for tc in tc_list:
                    executor_calls.append({
                        "id": tc.get("id", ""),
                        "type": tc.get("type", "function"),
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    })
                tool_results = executor.process_tool_calls(executor_calls, context)
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

    # Exhausted iterations without final response — return last LLM output if any
    return {
        "task_name": task_name,
        "success": True,
        "response": "Agent task completed but did not produce a final text response within the iteration limit.",
    }


# @tool(
#     name="agent_task",
#     description=(
#         "Spawn one or more sub-agents to work on tasks concurrently. "
#         "Each agent runs its own independent conversation with the LLM and can use tools. "
#         "Useful for parallel research, multi-file analysis, or dividing complex tasks into sub-tasks. "
#         "Each agent is limited to 3 iterations and 4096 tokens to control cost."
#     ),
#     parameters={
#         "type": "object",
#         "properties": {
#             "tasks": {
#                 "type": "array",
#                 "items": {
#                     "type": "object",
#                     "properties": {
#                         "name": {
#                             "type": "string",
#                             "description": "Short name/identifier for this task",
#                         },
#                         "instruction": {
#                             "type": "string",
#                             "description": "Detailed instruction for the sub-agent",
#                         },
#                         "tools": {
#                             "type": "array",
#                             "items": {"type": "string"},
#                             "description": (
#                                 "Tool names this agent can use (empty = all tools). "
#                                 "e.g. ['file_read', 'file_list', 'web_search']"
#                             ),
#                         },
#                     },
#                     "required": ["name", "instruction"],
#                 },
#                 "description": "Tasks for parallel sub-agents (max 5)",
#             },
#         },
#         "required": ["tasks"],
#     },
#     category="agent",
# )
def agent_task(arguments: dict) -> dict:
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
        {"success": true, "results": [{task_name, success, response/error}]}
    """
    from flask import current_app

    tasks = arguments["tasks"]

    if len(tasks) > 5:
        return {"success": False, "error": "Maximum 5 concurrent agents allowed"}

    # Get current conversation context for model/project info
    app = current_app._get_current_object()

    # Use injected model/project_id from executor context, fall back to defaults
    model = arguments.get("_model", "glm-5")
    project_id = arguments.get("_project_id")

    # Execute agents concurrently (max 3 at a time)
    concurrency = min(len(tasks), 3)
    results = [None] * len(tasks)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {
            pool.submit(
                _run_sub_agent,
                task["name"],
                task["instruction"],
                task.get("tools"),
                model,
                4096,
                project_id,
                app,
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
