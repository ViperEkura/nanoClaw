"""Common helper functions"""
import json
from datetime import date, datetime
from typing import Any
from flask import jsonify
from backend import db
from backend.models import Conversation, Message, TokenUsage, User


def get_or_create_default_user() -> User:
    """Get or create default user"""
    user = User.query.filter_by(username="default").first()
    if not user:
        user = User(username="default", password=None)
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
    return jsonify(body)


def err(code, message):
    """Error response helper"""
    return jsonify({"code": code, "message": message}), code


def to_dict(inst, **extra):
    """Convert model instance to dict"""
    d = {c.name: getattr(inst, c.name) for c in inst.__table__.columns}
    for k in ("created_at", "updated_at"):
        if k in d and hasattr(d[k], "strftime"):
            d[k] = d[k].strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Filter out None values for cleaner API response
    d = {k: v for k, v in d.items() if v is not None}
    
    d.update(extra)
    return d


def message_to_dict(msg: Message) -> dict:
    """Convert message to dict, parsing JSON content"""
    result = to_dict(msg)

    # Parse content JSON
    if msg.content:
        try:
            content_data = json.loads(msg.content)
            if isinstance(content_data, dict):
                # Extract all fields from JSON
                result["text"] = content_data.get("text", "")
                if content_data.get("attachments"):
                    result["attachments"] = content_data["attachments"]
                if content_data.get("thinking"):
                    result["thinking"] = content_data["thinking"]
                if content_data.get("tool_calls"):
                    result["tool_calls"] = content_data["tool_calls"]
            else:
                # Fallback: plain text
                result["text"] = msg.content
        except (json.JSONDecodeError, TypeError):
            result["text"] = msg.content

    if "text" not in result:
        result["text"] = ""

    return result


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


def build_messages(conv, project_id=None):
    """Build messages list for LLM API from conversation
    
    Args:
        conv: Conversation object
        project_id: Project ID (used for context injection, backend enforces workspace isolation)
    """
    msgs = []
    
    # System prompt (project_id is handled by backend for security)
    if conv.system_prompt:
        msgs.append({"role": "system", "content": conv.system_prompt})
    # Query messages directly to avoid detached instance warning
    messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at.asc()).all()
    for m in messages:
        # Build full content from JSON structure
        full_content = m.content
        try:
            content_data = json.loads(m.content)
            if isinstance(content_data, dict):
                text = content_data.get("text", "")
                attachments = content_data.get("attachments", [])
                
                # Build full content with attachments
                parts = []
                if text:
                    parts.append(text)
                
                for att in attachments:
                    filename = att.get("name", "")
                    file_content = att.get("content", "")
                    if filename and file_content:
                        parts.append(f"```{filename}\n{file_content}\n```")
                
                full_content = "\n\n".join(parts) if parts else ""
        except (json.JSONDecodeError, TypeError):
            # Plain text, use as-is
            pass
        
        msgs.append({"role": m.role, "content": full_content})
    return msgs
