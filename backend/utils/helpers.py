"""Common helper functions"""
import json
from datetime import datetime, date
from backend import db
from backend.models import Conversation, Message, User, TokenUsage


def get_or_create_default_user():
    """Get or create default user"""
    user = User.query.filter_by(username="default").first()
    if not user:
        user = User(username="default", password="")
        db.session.add(user)
        db.session.commit()
    return user


def ok(data=None, message=None):
    """Success response helper"""
    body = {"code": 0}
    if data is not None:
        body["data"] = data
    if message is not None:
        body["message"] = message
    from flask import jsonify
    return jsonify(body)


def err(code, message):
    """Error response helper"""
    from flask import jsonify
    return jsonify({"code": code, "message": message}), code


def to_dict(inst, **extra):
    """Convert model instance to dict"""
    d = {c.name: getattr(inst, c.name) for c in inst.__table__.columns}
    for k in ("created_at", "updated_at"):
        if k in d and hasattr(d[k], "strftime"):
            d[k] = d[k].strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Parse tool_calls JSON if present
    if "tool_calls" in d and d["tool_calls"]:
        try:
            d["tool_calls"] = json.loads(d["tool_calls"])
        except:
            pass
    
    # Filter out None values for cleaner API response
    d = {k: v for k, v in d.items() if v is not None}
    
    d.update(extra)
    return d


def record_token_usage(user_id, model, prompt_tokens, completion_tokens):
    """Record token usage"""
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
