"""Message API routes"""
import json
import uuid
from datetime import datetime
from flask import Blueprint, request
from backend import db
from backend.models import Conversation, Message
from backend.utils.helpers import ok, err, to_dict, message_to_dict, get_or_create_default_user
from backend.services.chat import ChatService


bp = Blueprint("messages", __name__)

# ChatService will be injected during registration
_chat_service = None


def init_chat_service(glm_client):
    """Initialize chat service with GLM client"""
    global _chat_service
    _chat_service = ChatService(glm_client)


@bp.route("/api/conversations/<conv_id>/messages", methods=["GET", "POST"])
def message_list(conv_id):
    """List or create messages"""
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
        
        items = [message_to_dict(r) for r in rows[:limit]]
        return ok({
            "items": items,
            "next_cursor": items[-1]["id"] if len(rows) > limit else None,
            "has_more": len(rows) > limit,
        })
    
    # POST - create message and get AI response
    d = request.json or {}
    text = (d.get("text") or "").strip()
    attachments = d.get("attachments")  # [{"name": "a.py", "extension": "py", "content": "..."}]
    project_id = d.get("project_id")  # Get project_id from request

    if not text and not attachments:
        return err(400, "text or attachments is required")

    # Build content JSON structure
    content_json = {"text": text}
    if attachments:
        content_json["attachments"] = attachments

    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="user",
        content=json.dumps(content_json, ensure_ascii=False),
    )
    db.session.add(user_msg)
    db.session.commit()

    tools_enabled = d.get("tools_enabled", True)
    project_id = d.get("project_id")
    
    return _chat_service.stream_response(conv, tools_enabled, project_id)


@bp.route("/api/conversations/<conv_id>/messages/<msg_id>", methods=["DELETE"])
def delete_message(conv_id, msg_id):
    """Delete a message"""
    conv = db.session.get(Conversation, conv_id)
    if not conv:
        return err(404, "conversation not found")
    msg = db.session.get(Message, msg_id)
    if not msg or msg.conversation_id != conv_id:
        return err(404, "message not found")
    db.session.delete(msg)
    db.session.commit()
    return ok(message="deleted")


@bp.route("/api/conversations/<conv_id>/regenerate/<msg_id>", methods=["POST"])
def regenerate_message(conv_id, msg_id):
    """Regenerate an assistant message"""
    conv = db.session.get(Conversation, conv_id)
    if not conv:
        return err(404, "conversation not found")

    # 获取要重新生成的消息
    msg = db.session.get(Message, msg_id)
    if not msg or msg.conversation_id != conv_id:
        return err(404, "message not found")

    if msg.role != "assistant":
        return err(400, "can only regenerate assistant messages")

    # 删除该消息及其后面的所有消息
    Message.query.filter(
        Message.conversation_id == conv_id,
        Message.created_at >= msg.created_at
    ).delete(synchronize_session=False)
    db.session.commit()

    # 获取工具启用状态
    d = request.json or {}
    tools_enabled = d.get("tools_enabled", True)
    project_id = d.get("project_id")  # Get project_id from request

    # 流式重新生成
    return _chat_service.stream_response(conv, tools_enabled, project_id)
