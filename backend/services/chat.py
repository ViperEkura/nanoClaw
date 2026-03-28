"""Chat completion service"""
import json
import logging
import uuid
from typing import Optional, Union
from flask import current_app, Response, request as flask_request
from werkzeug.exceptions import ClientDisconnected
import requests
from backend import db
from backend.models import Conversation, Message
from backend.tools import registry, ToolExecutor
from backend.utils.helpers import (
    record_token_usage,
    build_messages,
)
from backend.services.llm_client import LLMClient
from backend.config import MAX_ITERATIONS, TOOL_MAX_WORKERS

logger = logging.getLogger(__name__)


def _client_disconnected():
    """Check if the client has disconnected."""
    try:
        stream = flask_request.input_stream
        if stream is None:
            return False
        return stream.closed
    except Exception:
        return False


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ChatService:
    """Chat completion service with tool support"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def stream_response(
        self,
        conv: Conversation,
        tools_enabled: bool = True,
        project_id: str = None,
        tool_choice: Optional[Union[str, dict]] = None,
    ):
        """Stream response with tool call support.

        Uses 'process_step' events to send thinking and tool calls in order,
        allowing them to be interleaved properly in the frontend.

        Args:
            conv: Conversation object
            tools_enabled: Whether to enable tools
            project_id: Project ID for workspace isolation
            tool_choice: Optional tool_choice override (e.g. "auto", "required", or dict)
        """
        conv_id = conv.id
        conv_model = conv.model
        conv_max_tokens = conv.max_tokens
        conv_temperature = conv.temperature
        conv_thinking_enabled = conv.thinking_enabled
        app = current_app._get_current_object()
        tools = registry.list_all() if tools_enabled else None
        initial_messages = build_messages(conv, project_id)

        executor = ToolExecutor(registry=registry)

        context = {
            "model": conv_model,
            "max_tokens": conv_max_tokens,
            "temperature": conv_temperature,
        }
        if project_id:
            context["project_id"] = project_id
        elif conv.project_id:
            context["project_id"] = conv.project_id

        def generate():
            messages = list(initial_messages)
            all_tool_calls = []
            all_tool_results = []
            all_steps = []
            step_index = 0
            total_completion_tokens = 0
            total_prompt_tokens = 0

            for iteration in range(MAX_ITERATIONS):
                try:
                    stream_result = self._stream_llm_response(
                        app, messages, tools, tool_choice, step_index,
                        conv_model, conv_max_tokens, conv_temperature,
                        conv_thinking_enabled,
                    )
                except requests.exceptions.HTTPError as e:
                    resp = e.response
                    if resp is not None and resp.status_code >= 500:
                        yield _sse_event("error", {"content": f"LLM service unavailable ({resp.status_code})"})
                    elif resp is not None and resp.status_code == 429:
                        yield _sse_event("error", {"content": "Rate limit exceeded, please try again later"})
                    else:
                        yield _sse_event("error", {"content": f"LLM request failed: {e}"})
                    return
                except requests.exceptions.ConnectionError:
                    yield _sse_event("error", {"content": "Unable to connect to LLM service"})
                    return
                except requests.exceptions.Timeout:
                    yield _sse_event("error", {"content": "LLM request timed out"})
                    return
                except Exception as e:
                    logger.exception("Unexpected error during LLM streaming")
                    yield _sse_event("error", {"content": f"Internal error: {e}"})
                    return

                if stream_result is None:
                    return  # Client disconnected

                full_content, full_thinking, tool_calls_list, \
                    thinking_step_id, thinking_step_idx, \
                    text_step_id, text_step_idx, \
                    completion_tokens, prompt_tokens, \
                    sse_chunks = stream_result

                total_prompt_tokens += prompt_tokens
                total_completion_tokens += completion_tokens

                # Yield accumulated SSE chunks to frontend
                for chunk in sse_chunks:
                    yield chunk

                # Save thinking/text steps to all_steps for DB storage
                if thinking_step_id is not None:
                    all_steps.append({
                        "id": thinking_step_id, "index": thinking_step_idx,
                        "type": "thinking", "content": full_thinking,
                    })
                    step_index += 1

                if text_step_id is not None:
                    all_steps.append({
                        "id": text_step_id, "index": text_step_idx,
                        "type": "text", "content": full_content,
                    })
                    step_index += 1

                # --- Branch: tool calls vs final ---
                if tool_calls_list:
                    all_tool_calls.extend(tool_calls_list)

                    # Emit tool_call steps (before execution)
                    for tc in tool_calls_list:
                        call_step = {
                            "id": f"step-{step_index}",
                            "index": step_index,
                            "type": "tool_call",
                            "id_ref": tc["id"],
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        }
                        all_steps.append(call_step)
                        yield _sse_event("process_step", call_step)
                        step_index += 1

                    # Execute tools with error wrapping
                    tool_results = self._execute_tools_safe(
                        app, executor, tool_calls_list, context
                    )

                    # Emit tool_result steps
                    for tr in tool_results:
                        skipped = False
                        try:
                            result_content = json.loads(tr["content"])
                            skipped = result_content.get("skipped", False)
                        except Exception:
                            skipped = False
                        result_step = {
                            "id": f"step-{step_index}",
                            "index": step_index,
                            "type": "tool_result",
                            "id_ref": tr["tool_call_id"],
                            "name": tr["name"],
                            "content": tr["content"],
                            "skipped": skipped,
                        }
                        all_steps.append(result_step)
                        yield _sse_event("process_step", result_step)
                        step_index += 1

                    # Append assistant message + tool results for the next iteration
                    messages.append({
                        "role": "assistant",
                        "content": full_content or "",
                        "tool_calls": tool_calls_list,
                    })
                    messages.extend(tool_results)
                    all_tool_results.extend(tool_results)
                    continue

                # --- No tool calls: final iteration — save message to DB ---
                msg_id = str(uuid.uuid4())
                suggested_title = self._save_message(
                    app, conv_id, conv_model, msg_id,
                    full_content, all_tool_calls, all_tool_results,
                    all_steps, total_prompt_tokens, total_completion_tokens,
                )

                yield _sse_event("done", {
                    "message_id": msg_id,
                    "token_count": total_completion_tokens,
                    "suggested_title": suggested_title,
                })
                return

            yield _sse_event("error", {"content": "Exceeded maximum tool call iterations"})

        def safe_generate():
            """Wrapper that catches client disconnection during yield."""
            try:
                yield from generate()
            except (ClientDisconnected, BrokenPipeError, ConnectionResetError):
                pass

        return Response(
            safe_generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
                "Transfer-Encoding": "chunked",
            },
        )

    # ------------------------------------------------------------------
    # Private helpers — extracted for testability and readability
    # ------------------------------------------------------------------

    def _stream_llm_response(
        self, app, messages, tools, tool_choice, step_index,
        model, max_tokens, temperature, thinking_enabled,
    ):
        """Call LLM streaming API and parse the response.

        Returns a tuple of parsed results, or None if the client disconnected.
        Raises HTTPError / ConnectionError / Timeout for the caller to handle.
        """
        full_content = ""
        full_thinking = ""
        token_count = 0
        prompt_tokens = 0
        tool_calls_list = []

        thinking_step_id = None
        thinking_step_idx = None
        text_step_id = None
        text_step_idx = None

        sse_chunks = []  # Collect SSE events to yield later

        with app.app_context():
            resp = self.llm.call(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                thinking_enabled=thinking_enabled,
                tools=tools,
                tool_choice=tool_choice,
                stream=True,
            )
            resp.raise_for_status()

        for line in resp.iter_lines():
            if _client_disconnected():
                resp.close()
                return None

            if not line:
                continue
            line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            usage = chunk.get("usage", {})
            if usage:
                token_count = usage.get("completion_tokens", 0)
                prompt_tokens = usage.get("prompt_tokens", 0)

            choices = chunk.get("choices", [])
            if not choices:
                continue

            delta = choices[0].get("delta", {})

            reasoning = delta.get("reasoning_content", "")
            if reasoning:
                full_thinking += reasoning
                if thinking_step_id is None:
                    thinking_step_id = f"step-{step_index}"
                    thinking_step_idx = step_index
                sse_chunks.append(_sse_event("process_step", {
                    "id": thinking_step_id, "index": thinking_step_idx,
                    "type": "thinking", "content": full_thinking,
                }))

            text = delta.get("content", "")
            if text:
                full_content += text
                if text_step_id is None:
                    text_step_idx = step_index + (1 if thinking_step_id is not None else 0)
                    text_step_id = f"step-{text_step_idx}"
                sse_chunks.append(_sse_event("process_step", {
                    "id": text_step_id, "index": text_step_idx,
                    "type": "text", "content": full_content,
                }))

            tool_calls_list = self._process_tool_calls_delta(delta, tool_calls_list)

        return (
            full_content, full_thinking, tool_calls_list,
            thinking_step_id, thinking_step_idx,
            text_step_id, text_step_idx,
            token_count, prompt_tokens,
            sse_chunks,
        )

    def _execute_tools_safe(self, app, executor, tool_calls_list, context):
        """Execute tool calls with top-level error wrapping.

        If an unexpected exception occurs during tool execution, it is
        converted into error tool results instead of crashing the stream.
        """
        try:
            if len(tool_calls_list) > 1:
                with app.app_context():
                    return executor.process_tool_calls_parallel(
                        tool_calls_list, context, max_workers=TOOL_MAX_WORKERS
                    )
            else:
                with app.app_context():
                    return executor.process_tool_calls(
                        tool_calls_list, context
                    )
        except Exception as e:
            logger.exception("Error during tool execution")
            return [
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": tc["function"]["name"],
                    "content": json.dumps({
                        "success": False,
                        "error": f"Tool execution failed: {e}",
                    }, ensure_ascii=False),
                }
                for tc in tool_calls_list
            ]

    def _save_message(
        self, app, conv_id, conv_model, msg_id,
        full_content, all_tool_calls, all_tool_results,
        all_steps, total_prompt_tokens, total_completion_tokens,
    ):
        """Save the final assistant message and auto-generate title if needed.

        Returns the suggested_title or None.
        """
        suggested_title = None
        with app.app_context():
            content_json = {"text": full_content}
            if all_tool_calls:
                content_json["tool_calls"] = self._build_tool_calls_json(
                    all_tool_calls, all_tool_results
                )
            content_json["steps"] = all_steps

            msg = Message(
                id=msg_id,
                conversation_id=conv_id,
                role="assistant",
                content=json.dumps(content_json, ensure_ascii=False),
                token_count=total_completion_tokens,
            )
            db.session.add(msg)
            db.session.commit()

            conv = db.session.get(Conversation, conv_id)

            if conv:
                record_token_usage(
                    conv.user_id, conv_model,
                    total_prompt_tokens, total_completion_tokens,
                )

            if conv and (not conv.title or conv.title == "新对话"):
                user_msg = Message.query.filter_by(
                    conversation_id=conv_id, role="user"
                ).order_by(Message.created_at.asc()).first()
                if user_msg and user_msg.content:
                    try:
                        content_data = json.loads(user_msg.content)
                        title_text = content_data.get("text", "")[:30]
                    except (json.JSONDecodeError, TypeError):
                        title_text = user_msg.content.strip()[:30]
                    suggested_title = title_text or "新对话"
                    db.session.refresh(conv)
                    conv.title = suggested_title
                    db.session.commit()

        return suggested_title

    def _build_tool_calls_json(self, tool_calls: list, tool_results: list) -> list:
        """Build tool calls JSON structure - matches streaming format."""
        result = []
        for i, tc in enumerate(tool_calls):
            result_content = tool_results[i]["content"] if i < len(tool_results) else None

            success = True
            skipped = False
            execution_time = 0
            if result_content:
                try:
                    result_data = json.loads(result_content)
                    success = result_data.get("success", True)
                    skipped = result_data.get("skipped", False)
                    execution_time = result_data.get("execution_time", 0)
                except (json.JSONDecodeError, TypeError):
                    pass

            result.append({
                "id": tc.get("id", ""),
                "type": tc.get("type", "function"),
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                },
                "result": result_content,
                "success": success,
                "skipped": skipped,
                "execution_time": execution_time,
            })
        return result

    def _process_tool_calls_delta(self, delta: dict, tool_calls_list: list) -> list:
        """Process tool calls from streaming delta."""
        tool_calls_delta = delta.get("tool_calls", [])
        for tc in tool_calls_delta:
            idx = tc.get("index", 0)
            if idx >= len(tool_calls_list):
                tool_calls_list.append({
                    "id": tc.get("id", ""),
                    "type": tc.get("type", "function"),
                    "function": {"name": "", "arguments": ""},
                })
            if tc.get("id"):
                tool_calls_list[idx]["id"] = tc["id"]
            if tc.get("function"):
                if tc["function"].get("name"):
                    tool_calls_list[idx]["function"]["name"] = tc["function"]["name"]
                if tc["function"].get("arguments"):
                    tool_calls_list[idx]["function"]["arguments"] += tc["function"]["arguments"]
        return tool_calls_list
