"""Conversation API routes"""
import uuid
from datetime import datetime
from flask import Blueprint, request
from backend import db
from backend.models import Conversation
from backend.utils.helpers import ok, err, to_dict, get_or_create_default_user
from backend.config import DEFAULT_MODEL

bp = Blueprint("conversations", __name__)


@bp.route("/api/conversations", methods=["GET", "POST"])
def conversation_list():
    """List or create conversations"""
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
    
    # GET - list conversations
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
    """Get, update or delete a conversation"""
    conv = db.session.get(Conversation, conv_id)
    if not conv:
        return err(404, "conversation not found")
    
    if request.method == "GET":
        return ok(to_dict(conv))
    
    if request.method == "DELETE":
        db.session.delete(conv)
        db.session.commit()
        return ok(message="deleted")
    
    # PATCH - update conversation
    d = request.json or {}
    for k in ("title", "model", "system_prompt", "temperature", "max_tokens", "thinking_enabled"):
        if k in d:
            setattr(conv, k, d[k])
    db.session.commit()
    return ok(to_dict(conv))
