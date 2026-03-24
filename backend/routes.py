import uuid
import json
import os
import requests
from datetime import datetime
from flask import request, jsonify, Response, Blueprint, current_app
from . import db
from .models import Conversation, Message, User, TokenUsage
from . import load_config
from .tools import registry, ToolExecutor

bp = Blueprint("api", __name__)

cfg = load_config()
API_URL = cfg.get("api_url")
API_KEY = cfg["api_key"]
MODELS = cfg.get("models", [])
DEFAULT_MODEL = cfg.get("default_model", "glm-5")


# -- Helpers ----------------------------------------------

def get_or_create_default_user():
    user = User.query.filter_by(username="default").first()
    if not user:
        user = User(username="default", password="")
        db.session.add(user)
        db.session.commit()
    return user


def ok(data=None, message=None):
    body = {"code": 0}
    if data is not None:
        body["data"] = data
    if message is not None:
        body["message"] = message
    return jsonify(body)


def err(code, message):
    return jsonify({"code": code, "message": message}), code


def to_dict(inst, **extra):
    d = {c.name: getattr(inst, c.name) for c in inst.__table__.columns}
    for k in ("created_at", "updated_at"):
        if k in d and hasattr(d[k], "strftime"):
            d[k] = d[k].strftime("%Y-%m-%dT%H:%M:%SZ")
    d.update(extra)
    return d


def record_token_usage(user_id, model, prompt_tokens, completion_tokens):
    """Record token usage"""
    from datetime import date
    today = date.today()
    usage = TokenUsage.query.filter_by(
        user_id=user_id, date=today, model=model
    ).first()
    if usage:
        usage.prompt_tokens += prompt_tokens
        usage.completion_tokens += completion_tokens
        usage.total_tokens += prompt_tokens + completion_tokens
    else:
        usage = TokenUsage(
            user_id=user_id,
            date=today,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        db.session.add(usage)
    db.session.commit()


def build_glm_messages(conv):
    """Build messages list for GLM API from conversation"""
    msgs = []
    if conv.system_prompt:
        msgs.append({"role": "system", "content": conv.system_prompt})
    # Query messages directly to avoid detached instance warning
    messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at.asc()).all()
    for m in messages:
        msgs.append({"role": m.role, "content": m.content})
    return msgs


# -- Models API -------------------------------------------

@bp.route("/api/models", methods=["GET"])
def list_models():
    """Get available model list"""
    return ok(MODELS)


# -- Tools API --------------------------------------------

@bp.route("/api/tools", methods=["GET"])
def list_tools():
    """Get available tool list"""
    tools = registry.list_all()
    return ok({
        "tools": tools,
        "total": len(tools)
    })


# -- Token Usage Statistics --------------------------------

@bp.route("/api/stats/tokens", methods=["GET"])
def token_stats():
    """Get token usage statistics"""
    from sqlalchemy import func
    from datetime import date, timedelta

    user = get_or_create_default_user()
    period = request.args.get("period", "daily")  # daily, weekly, monthly

    today = date.today()

    if period == "daily":
        # Today's statistics
        stats = TokenUsage.query.filter_by(user_id=user.id, date=today).all()
        result = {
            "period": "daily",
            "date": today.isoformat(),
            "prompt_tokens": sum(s.prompt_tokens for s in stats),
            "completion_tokens": sum(s.completion_tokens for s in stats),
            "total_tokens": sum(s.total_tokens for s in stats),
            "by_model": {s.model: {"prompt": s.prompt_tokens, "completion": s.completion_tokens, "total": s.total_tokens} for s in stats}
        }
    elif period == "weekly":
        # Weekly statistics (last 7 days)
        start_date = today - timedelta(days=6)
        stats = TokenUsage.query.filter(
            TokenUsage.user_id == user.id,
            TokenUsage.date >= start_date,
            TokenUsage.date <= today
        ).all()

        daily_data = {}
        for s in stats:
            d = s.date.isoformat()
            if d not in daily_data:
                daily_data[d] = {"prompt": 0, "completion": 0, "total": 0}
            daily_data[d]["prompt"] += s.prompt_tokens
            daily_data[d]["completion"] += s.completion_tokens
            daily_data[d]["total"] += s.total_tokens

        # Fill missing dates
        for i in range(7):
            d = (today - timedelta(days=6-i)).isoformat()
            if d not in daily_data:
                daily_data[d] = {"prompt": 0, "completion": 0, "total": 0}

        result = {
            "period": "weekly",
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
            "prompt_tokens": sum(s.prompt_tokens for s in stats),
            "completion_tokens": sum(s.completion_tokens for s in stats),
            "total_tokens": sum(s.total_tokens for s in stats),
            "daily": daily_data
        }
    elif period == "monthly":
        # Monthly statistics (last 30 days)
        start_date = today - timedelta(days=29)
        stats = TokenUsage.query.filter(
            TokenUsage.user_id == user.id,
            TokenUsage.date >= start_date,
            TokenUsage.date <= today
        ).all()

        daily_data = {}
        for s in stats:
            d = s.date.isoformat()
            if d not in daily_data:
                daily_data[d] = {"prompt": 0, "completion": 0, "total": 0}
            daily_data[d]["prompt"] += s.prompt_tokens
            daily_data[d]["completion"] += s.completion_tokens
            daily_data[d]["total"] += s.total_tokens

        # Fill missing dates
        for i in range(30):
            d = (today - timedelta(days=29-i)).isoformat()
            if d not in daily_data:
                daily_data[d] = {"prompt": 0, "completion": 0, "total": 0}

        result = {
            "period": "monthly",
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
            "prompt_tokens": sum(s.prompt_tokens for s in stats),
            "completion_tokens": sum(s.completion_tokens for s in stats),
            "total_tokens": sum(s.total_tokens for s in stats),
            "daily": daily_data
        }
    else:
        return err(400, "invalid period")

    return ok(result)


# -- Conversation CRUD ------------------------------------

@bp.route("/api/conversations", methods=["GET", "POST"])
def conversation_list():
    if request.method == "POST":
        d = request.json or {}
        user = get_or_create_default_user()
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user.id,
            title=d.get("title", ""),
            model=d.get("model", DEFAULT_MODEL),
            system_prompt=d.get("system_prompt", ""),
            temperature=d.get("temperature", 1.0),
            max_tokens=d.get("max_tokens", 65536),
            thinking_enabled=d.get("thinking_enabled", False),
        )
        db.session.add(conv)
        db.session.commit()
        return ok(to_dict(conv))

    cursor = request.args.get("cursor")
    limit = min(int(request.args.get("limit", 20)), 100)
    user = get_or_create_default_user()
    q = Conversation.query.filter_by(user_id=user.id)
    if cursor:
        q = q.filter(Conversation.updated_at < (
            db.session.query(Conversation.updated_at).filter_by(id=cursor).scalar() or datetime.utcnow))
    rows = q.order_by(Conversation.updated_at.desc()).limit(limit + 1).all()

    items = [to_dict(r, message_count=r.messages.count()) for r in rows[:limit]]
    return ok({
        "items": items,
        "next_cursor": items[-1]["id"] if len(rows) > limit else None,
        "has_more": len(rows) > limit,
    })


@bp.route("/api/conversations/<conv_id>", methods=["GET", "PATCH", "DELETE"])
def conversation_detail(conv_id):
    conv = db.session.get(Conversation, conv_id)
    if not conv:
        return err(404, "conversation not found")

    if request.method == "GET":
        return ok(to_dict(conv))

    if request.method == "DELETE":
        db.session.delete(conv)
        db.session.commit()
        return ok(message="deleted")

    d = request.json or {}
    for k in ("title", "model", "system_prompt", "temperature", "max_tokens", "thinking_enabled"):
        if k in d:
            setattr(conv, k, d[k])
    db.session.commit()
    return ok(to_dict(conv))


# -- Messages ---------------------------------------------

@bp.route("/api/conversations/<conv_id>/messages", methods=["GET", "POST"])
def message_list(conv_id):
    conv = db.session.get(Conversation, conv_id)
    if not conv:
        return err(404, "conversation not found")

    if request.method == "GET":
        cursor = request.args.get("cursor")
        limit = min(int(request.args.get("limit", 50)), 100)
        q = Message.query.filter_by(conversation_id=conv_id)
        if cursor:
            q = q.filter(Message.created_at < (
                db.session.query(Message.created_at).filter_by(id=cursor).scalar() or datetime.utcnow))
        rows = q.order_by(Message.created_at.asc()).limit(limit + 1).all()

        items = [to_dict(r) for r in rows[:limit]]
        return ok({
            "items": items,
            "next_cursor": items[-1]["id"] if len(rows) > limit else None,
            "has_more": len(rows) > limit,
        })

    d = request.json or {}
    content = (d.get("content") or "").strip()
    if not content:
        return err(400, "content is required")

    user_msg = Message(id=str(uuid.uuid4()), conversation_id=conv_id, role="user", content=content)
    db.session.add(user_msg)
    db.session.commit()

    if d.get("stream", False):
        return _stream_response(conv)

    return _sync_response(conv)


@bp.route("/api/conversations/<conv_id>/messages/<msg_id>", methods=["DELETE"])
def delete_message(conv_id, msg_id):
    conv = db.session.get(Conversation, conv_id)
    if not conv:
        return err(404, "conversation not found")
    msg = db.session.get(Message, msg_id)
    if not msg or msg.conversation_id != conv_id:
        return err(404, "message not found")
    db.session.delete(msg)
    db.session.commit()
    return ok(message="deleted")


# -- Chat Completion ----------------------------------

def _call_glm(conv, stream=False, tools=None, messages=None):
    """Call GLM API"""
    body = {
        "model": conv.model,
        "messages": messages if messages is not None else build_glm_messages(conv),
        "max_tokens": conv.max_tokens,
        "temperature": conv.temperature,
    }
    if conv.thinking_enabled:
        body["thinking"] = {"type": "enabled"}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if stream:
        body["stream"] = True
    return requests.post(
        API_URL,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
        json=body, stream=stream, timeout=120,
    )


def _sync_response(conv):
    """Sync response with tool call support"""
    executor = ToolExecutor(registry=registry)
    tools = registry.list_all()
    messages = build_glm_messages(conv)
    max_iterations = 5  # Max tool call iterations

    for _ in range(max_iterations):
        try:
            resp = _call_glm(conv, tools=tools if tools else None, messages=messages)
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            return err(500, f"upstream error: {e}")

        choice = result["choices"][0]
        message = choice["message"]

        # If no tool calls, return final result
        if not message.get("tool_calls"):
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            msg = Message(
                id=str(uuid.uuid4()), conversation_id=conv.id, role="assistant",
                content=message.get("content", ""),
                token_count=completion_tokens,
                thinking_content=message.get("reasoning_content", ""),
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
        messages.append(message)

        # Execute tools and add results
        tool_results = executor.process_tool_calls(tool_calls)
        messages.extend(tool_results)

        # Save tool call records to database
        for i, call in enumerate(tool_calls):
            tool_msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conv.id,
                role="tool",
                content=tool_results[i]["content"]
            )
            db.session.add(tool_msg)
        db.session.commit()

    return err(500, "exceeded maximum tool call iterations")


def _stream_response(conv):
    """Stream response with tool call support"""
    conv_id = conv.id
    conv_model = conv.model
    app = current_app._get_current_object()
    executor = ToolExecutor(registry=registry)
    tools = registry.list_all()
    # Build messages BEFORE entering generator (in request context)
    initial_messages = build_glm_messages(conv)

    def generate():
        messages = list(initial_messages)  # Copy to avoid mutation
        max_iterations = 5

        for iteration in range(max_iterations):
            full_content = ""
            full_thinking = ""
            token_count = 0
            prompt_tokens = 0
            msg_id = str(uuid.uuid4())
            tool_calls_list = []
            current_tool_call = None

            try:
                with app.app_context():
                    active_conv = db.session.get(Conversation, conv_id)
                    resp = _call_glm(active_conv, stream=True, tools=tools if tools else None, messages=messages)
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

                    # Process thinking chain
                    reasoning = delta.get("reasoning_content", "")
                    if reasoning:
                        full_thinking += reasoning
                        yield f"event: thinking\ndata: {json.dumps({'content': reasoning}, ensure_ascii=False)}\n\n"

                    # Process text content
                    text = delta.get("content", "")
                    if text:
                        full_content += text
                        yield f"event: message\ndata: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"

                    # Process tool calls
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

                    usage = chunk.get("usage", {})
                    if usage:
                        token_count = usage.get("completion_tokens", 0)
                        prompt_tokens = usage.get("prompt_tokens", 0)

            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'content': str(e)}, ensure_ascii=False)}\n\n"
                return

            # If tool calls exist, execute and continue loop
            if tool_calls_list:
                # Send tool call info
                yield f"event: tool_calls\ndata: {json.dumps({'calls': tool_calls_list}, ensure_ascii=False)}\n\n"

                # Execute tools
                tool_results = executor.process_tool_calls(tool_calls_list)
                messages.append({
                    "role": "assistant",
                    "content": full_content or None,
                    "tool_calls": tool_calls_list
                })
                messages.extend(tool_results)

                # Send tool results
                for tr in tool_results:
                    yield f"event: tool_result\ndata: {json.dumps({'name': tr['name'], 'content': tr['content']}, ensure_ascii=False)}\n\n"

                continue

            # No tool calls, finish
            with app.app_context():
                msg = Message(
                    id=msg_id, conversation_id=conv_id, role="assistant",
                    content=full_content, token_count=token_count, thinking_content=full_thinking,
                )
                db.session.add(msg)
                db.session.commit()

                user = get_or_create_default_user()
                record_token_usage(user.id, conv_model, prompt_tokens, token_count)

            yield f"event: done\ndata: {json.dumps({'message_id': msg_id, 'token_count': token_count})}\n\n"
            return

        yield f"event: error\ndata: {json.dumps({'content': 'exceeded maximum tool call iterations'}, ensure_ascii=False)}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def register_routes(app):
    app.register_blueprint(bp)
