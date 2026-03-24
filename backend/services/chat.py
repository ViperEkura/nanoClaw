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
    build_glm_messages,
    ok,
    err,
    to_dict,
)
from backend.services.glm_client import GLMClient


class ChatService:
    """Chat completion service with tool support"""
    
    MAX_ITERATIONS = 5
    
    def __init__(self, glm_client: GLMClient):
        self.glm_client = glm_client
        self.executor = ToolExecutor(registry=registry)
    
    def sync_response(self, conv: Conversation, tools_enabled: bool = True):
        """Sync response with tool call support"""
        tools = registry.list_all() if tools_enabled else None
        messages = build_glm_messages(conv)
        
        # Clear tool call history for new request
        self.executor.clear_history()
        
        all_tool_calls = []
        all_tool_results = []
        
        for _ in range(self.MAX_ITERATIONS):
            try:
                resp = self.glm_client.call(
                    model=conv.model,
                    messages=messages,
                    max_tokens=conv.max_tokens,
                    temperature=conv.temperature,
                    thinking_enabled=conv.thinking_enabled,
                    tools=tools,
                )
                resp.raise_for_status()
                result = resp.json()
            except Exception as e:
                return err(500, f"upstream error: {e}")
            
            choice = result["choices"][0]
            message = choice["message"]
            
            # No tool calls - return final result
            if not message.get("tool_calls"):
                usage = result.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                
                merged_tool_calls = self._merge_tool_results(all_tool_calls, all_tool_results)
                
                msg = Message(
                    id=str(uuid.uuid4()),
                    conversation_id=conv.id,
                    role="assistant",
                    content=message.get("content", ""),
                    token_count=completion_tokens,
                    thinking_content=message.get("reasoning_content", ""),
                    tool_calls=json.dumps(merged_tool_calls) if merged_tool_calls else None
                )
                db.session.add(msg)
                db.session.commit()
                
                user = get_or_create_default_user()
                record_token_usage(user.id, conv.model, prompt_tokens, completion_tokens)
                
                return ok({
                    "message": to_dict(msg, thinking_content=msg.thinking_content or None),
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": usage.get("total_tokens", 0)
                    },
                })
            
            # Process tool calls
            tool_calls = message["tool_calls"]
            all_tool_calls.extend(tool_calls)
            messages.append(message)
            
            tool_results = self.executor.process_tool_calls(tool_calls)
            all_tool_results.extend(tool_results)
            messages.extend(tool_results)
        
        return err(500, "exceeded maximum tool call iterations")
    
    def stream_response(self, conv: Conversation, tools_enabled: bool = True):
        """Stream response with tool call support"""
        conv_id = conv.id
        conv_model = conv.model
        app = current_app._get_current_object()
        tools = registry.list_all() if tools_enabled else None
        initial_messages = build_glm_messages(conv)
        
        # Clear tool call history for new request
        self.executor.clear_history()
        
        def generate():
            messages = list(initial_messages)
            all_tool_calls = []
            all_tool_results = []
            
            for iteration in range(self.MAX_ITERATIONS):
                full_content = ""
                full_thinking = ""
                token_count = 0
                prompt_tokens = 0
                msg_id = str(uuid.uuid4())
                tool_calls_list = []
                
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
                        
                        # Process thinking
                        reasoning = delta.get("reasoning_content", "")
                        if reasoning:
                            full_thinking += reasoning
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
                    yield f"event: tool_calls\ndata: {json.dumps({'calls': tool_calls_list}, ensure_ascii=False)}\n\n"
                    
                    tool_results = self.executor.process_tool_calls(tool_calls_list)
                    messages.append({
                        "role": "assistant",
                        "content": full_content or None,
                        "tool_calls": tool_calls_list
                    })
                    messages.extend(tool_results)
                    all_tool_results.extend(tool_results)
                    
                    for tr in tool_results:
                        yield f"event: tool_result\ndata: {json.dumps({'name': tr['name'], 'content': tr['content']}, ensure_ascii=False)}\n\n"
                    continue
                
                # No tool calls - finish
                merged_tool_calls = self._merge_tool_results(all_tool_calls, all_tool_results)
                
                with app.app_context():
                    msg = Message(
                        id=msg_id,
                        conversation_id=conv_id,
                        role="assistant",
                        content=full_content,
                        token_count=token_count,
                        thinking_content=full_thinking,
                        tool_calls=json.dumps(merged_tool_calls) if merged_tool_calls else None
                    )
                    db.session.add(msg)
                    db.session.commit()
                    
                    user = get_or_create_default_user()
                    record_token_usage(user.id, conv_model, prompt_tokens, token_count)
                
                yield f"event: done\ndata: {json.dumps({'message_id': msg_id, 'token_count': token_count})}\n\n"
                return
            
            yield f"event: error\ndata: {json.dumps({'content': 'exceeded maximum tool call iterations'}, ensure_ascii=False)}\n\n"
        
        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )
    
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
    
    def _merge_tool_results(self, tool_calls: list, tool_results: list) -> list:
        """Merge tool results into tool calls"""
        merged = []
        for i, tc in enumerate(tool_calls):
            merged_tc = dict(tc)
            if i < len(tool_results):
                merged_tc["result"] = tool_results[i]["content"]
            merged.append(merged_tc)
        return merged
