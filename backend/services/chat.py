"""Chat completion service"""
import json
import uuid
from flask import current_app, Response
from backend import db
from backend.models import Conversation, Message
from backend.tools import registry, ToolExecutor
from backend.utils.helpers import (
    get_or_create_default_user,
    record_token_usage,
    build_messages,
)
from backend.services.glm_client import GLMClient


class ChatService:
    """Chat completion service with tool support"""

    MAX_ITERATIONS = 5

    def __init__(self, glm_client: GLMClient):
        self.glm_client = glm_client
        self.executor = ToolExecutor(registry=registry)


    def stream_response(self, conv: Conversation, tools_enabled: bool = True, project_id: str = None):
        """Stream response with tool call support
        
        Uses 'process_step' events to send thinking and tool calls in order,
        allowing them to be interleaved properly in the frontend.
        
        Args:
            conv: Conversation object
            tools_enabled: Whether to enable tools
            project_id: Project ID for workspace isolation
        """
        conv_id = conv.id
        conv_model = conv.model
        app = current_app._get_current_object()
        tools = registry.list_all() if tools_enabled else None
        initial_messages = build_messages(conv, project_id)
        
        # Clear tool call history for new request
        self.executor.clear_history()
        
        # Build context for tool execution
        context = None
        if project_id:
            context = {"project_id": project_id}
        elif conv.project_id:
            context = {"project_id": conv.project_id}
        
        def generate():
            messages = list(initial_messages)
            all_tool_calls = []
            all_tool_results = []
            step_index = 0  # Track global step index for ordering
            
            for iteration in range(self.MAX_ITERATIONS):
                full_content = ""
                full_thinking = ""
                token_count = 0
                prompt_tokens = 0
                msg_id = str(uuid.uuid4())
                tool_calls_list = []
                
                # Send thinking_start event to clear previous thinking in frontend
                yield f"event: thinking_start\ndata: {{}}\n\n"
                
                try:
                    with app.app_context():
                        active_conv = db.session.get(Conversation, conv_id)
                        resp = self.glm_client.call(
                            model=active_conv.model,
                            messages=messages,
                            max_tokens=active_conv.max_tokens,
                            temperature=active_conv.temperature,
                            thinking_enabled=active_conv.thinking_enabled,
                            tools=tools,
                            stream=True,
                        )
                        resp.raise_for_status()
                    
                    for line in resp.iter_lines():
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
                        
                        delta = chunk["choices"][0].get("delta", {})
                        
                        # Process thinking - send as process_step
                        reasoning = delta.get("reasoning_content", "")
                        if reasoning:
                            full_thinking += reasoning
                            # Still send thinking event for backward compatibility
                            yield f"event: thinking\ndata: {json.dumps({'content': reasoning}, ensure_ascii=False)}\n\n"
                        
                        # Process text
                        text = delta.get("content", "")
                        if text:
                            full_content += text
                            yield f"event: message\ndata: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"
                        
                        # Process tool calls
                        tool_calls_list = self._process_tool_calls_delta(delta, tool_calls_list)
                        
                        usage = chunk.get("usage", {})
                        if usage:
                            token_count = usage.get("completion_tokens", 0)
                            prompt_tokens = usage.get("prompt_tokens", 0)
                
                except Exception as e:
                    yield f"event: error\ndata: {json.dumps({'content': str(e)}, ensure_ascii=False)}\n\n"
                    return
                
                # Tool calls exist - execute and continue
                if tool_calls_list:
                    all_tool_calls.extend(tool_calls_list)
                    
                    # Send thinking as a complete step if exists
                    if full_thinking:
                        yield f"event: process_step\ndata: {json.dumps({'index': step_index, 'type': 'thinking', 'content': full_thinking}, ensure_ascii=False)}\n\n"
                        step_index += 1
                    
                    # Send text as a step if exists (text before tool calls)
                    if full_content:
                        yield f"event: process_step\ndata: {json.dumps({'index': step_index, 'type': 'text', 'content': full_content}, ensure_ascii=False)}\n\n"
                        step_index += 1
                    
                    # Also send legacy tool_calls event for backward compatibility
                    yield f"event: tool_calls\ndata: {json.dumps({'calls': tool_calls_list}, ensure_ascii=False)}\n\n"
                    
                    # Process each tool call one by one, send result immediately
                    tool_results = []
                    for tc in tool_calls_list:
                        # Send tool call step
                        yield f"event: process_step\ndata: {json.dumps({'index': step_index, 'type': 'tool_call', 'id': tc['id'], 'name': tc['function']['name'], 'arguments': tc['function']['arguments']}, ensure_ascii=False)}\n\n"
                        step_index += 1
                        
                        # Execute this single tool call (needs app context for db access)
                        with app.app_context():
                            single_result = self.executor.process_tool_calls([tc], context)
                        tool_results.extend(single_result)
                        
                        # Send tool result step immediately
                        tr = single_result[0]
                        try:
                            result_content = json.loads(tr["content"])
                            skipped = result_content.get("skipped", False)
                        except:
                            skipped = False
                        yield f"event: process_step\ndata: {json.dumps({'index': step_index, 'type': 'tool_result', 'id': tr['tool_call_id'], 'name': tr['name'], 'content': tr['content'], 'skipped': skipped}, ensure_ascii=False)}\n\n"
                        step_index += 1
                        
                        # Also send legacy tool_result event
                        yield f"event: tool_result\ndata: {json.dumps({'id': tr['tool_call_id'], 'name': tr['name'], 'content': tr['content'], 'skipped': skipped}, ensure_ascii=False)}\n\n"
                    
                    messages.append({
                        "role": "assistant",
                        "content": full_content or None,
                        "tool_calls": tool_calls_list
                    })
                    messages.extend(tool_results)
                    all_tool_results.extend(tool_results)
                    continue
                
                # No tool calls - finish
                # Send thinking as a step if exists
                if full_thinking:
                    yield f"event: process_step\ndata: {json.dumps({'index': step_index, 'type': 'thinking', 'content': full_thinking}, ensure_ascii=False)}\n\n"
                    step_index += 1

                # Send text as a step if exists
                if full_content:
                    yield f"event: process_step\ndata: {json.dumps({'index': step_index, 'type': 'text', 'content': full_content}, ensure_ascii=False)}\n\n"
                    step_index += 1

                suggested_title = None
                with app.app_context():
                    # Build content JSON
                    content_json = {
                        "text": full_content,
                    }
                    if full_thinking:
                        content_json["thinking"] = full_thinking
                    if all_tool_calls:
                        content_json["tool_calls"] = self._build_tool_calls_json(all_tool_calls, all_tool_results)

                    msg = Message(
                        id=msg_id,
                        conversation_id=conv_id,
                        role="assistant",
                        content=json.dumps(content_json, ensure_ascii=False),
                        token_count=token_count,
                    )
                    db.session.add(msg)
                    db.session.commit()

                    user = get_or_create_default_user()
                    record_token_usage(user.id, conv_model, prompt_tokens, token_count)

                    # Check if we need to set title (first message in conversation)
                    conv = db.session.get(Conversation, conv_id)
                    if conv and (not conv.title or conv.title == "新对话"):
                        # Get user message content
                        user_msg = Message.query.filter_by(
                            conversation_id=conv_id, role="user"
                        ).order_by(Message.created_at.asc()).first()
                        if user_msg and user_msg.content:
                            # Parse content JSON to get text
                            try:
                                content_data = json.loads(user_msg.content)
                                title_text = content_data.get("text", "")[:30]
                            except (json.JSONDecodeError, TypeError):
                                title_text = user_msg.content.strip()[:30]
                            if title_text:
                                suggested_title = title_text
                            else:
                                suggested_title = "新对话"
                            # Refresh conv to avoid stale state
                            db.session.refresh(conv)
                            conv.title = suggested_title
                            db.session.commit()
                        else:
                            suggested_title = None

                yield f"event: done\ndata: {json.dumps({'message_id': msg_id, 'token_count': token_count, 'suggested_title': suggested_title}, ensure_ascii=False)}\n\n"
                return
            
            yield f"event: error\ndata: {json.dumps({'content': 'exceeded maximum tool call iterations'}, ensure_ascii=False)}\n\n"
        
        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
                "Transfer-Encoding": "chunked",
            }
        )
    
    def _build_tool_calls_json(self, tool_calls: list, tool_results: list) -> list:
        """Build tool calls JSON structure - matches streaming format"""
        result = []
        for i, tc in enumerate(tool_calls):
            result_content = tool_results[i]["content"] if i < len(tool_results) else None

            # Parse result to extract success/skipped status
            success = True
            skipped = False
            execution_time = 0
            if result_content:
                try:
                    result_data = json.loads(result_content)
                    success = result_data.get("success", True)
                    skipped = result_data.get("skipped", False)
                    execution_time = result_data.get("execution_time", 0)
                except:
                    pass

            # Keep same structure as streaming format
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
        """Process tool calls from streaming delta"""
        tool_calls_delta = delta.get("tool_calls", [])
        for tc in tool_calls_delta:
            idx = tc.get("index", 0)
            if idx >= len(tool_calls_list):
                tool_calls_list.append({
                    "id": tc.get("id", ""),
                    "type": tc.get("type", "function"),
                    "function": {"name": "", "arguments": ""}
                })
            if tc.get("id"):
                tool_calls_list[idx]["id"] = tc["id"]
            if tc.get("function"):
                if tc["function"].get("name"):
                    tool_calls_list[idx]["function"]["name"] = tc["function"]["name"]
                if tc["function"].get("arguments"):
                    tool_calls_list[idx]["function"]["arguments"] += tc["function"]["arguments"]
        return tool_calls_list
