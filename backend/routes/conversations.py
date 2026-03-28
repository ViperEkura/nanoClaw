"""Conversation API routes"""
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, g
from backend import db
from backend.models import Conversation, Project
from backend.utils.helpers import ok, err, to_dict
from backend.config import config

bp = Blueprint("conversations", __name__)


def _conv_to_dict(conv, **extra):
    """Convert conversation to dict with project info"""
    d = to_dict(conv, **extra)
    if conv.project_id:
        project = db.session.get(Project, conv.project_id)
        if project:
            d["project_name"] = project.name
    return d


@bp.route("/api/conversations", methods=["GET", "POST"])
def conversation_list():
    """List or create conversations"""
    user = g.current_user

    if request.method == "POST":
        d = request.json or {}

        # Validate project_id if provided
        project_id = d.get("project_id")
        if project_id:
            project = db.session.get(Project, project_id)
            if not project or project.user_id != user.id:
                return err(404, "Project not found")

        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user.id,
            project_id=project_id or None,
            title=d.get("title", ""),
            model=d.get("model", config.default_model),
            system_prompt=d.get("system_prompt", ""),
            temperature=d.get("temperature", 1.0),
            max_tokens=d.get("max_tokens", 65536),
            thinking_enabled=d.get("thinking_enabled", False),
        )
        db.session.add(conv)
        db.session.commit()
        return ok(_conv_to_dict(conv))

    # GET - list conversations
    cursor = request.args.get("cursor")
    limit = min(int(request.args.get("limit", 20)), 100)
    project_id = request.args.get("project_id")
    q = Conversation.query.filter_by(user_id=user.id)

    # Filter by project if specified
    if project_id:
        q = q.filter_by(project_id=project_id)

    if cursor:
        q = q.filter(Conversation.updated_at < (
            db.session.query(Conversation.updated_at).filter_by(id=cursor).scalar() or datetime.now(timezone.utc)))
    rows = q.order_by(Conversation.updated_at.desc()).limit(limit + 1).all()

    items = [_conv_to_dict(r, message_count=r.messages.count()) for r in rows[:limit]]
    return ok({
        "items": items,
        "next_cursor": items[-1]["id"] if len(rows) > limit else None,
        "has_more": len(rows) > limit,
    })


@bp.route("/api/conversations/<conv_id>", methods=["GET", "PATCH", "DELETE"])
def conversation_detail(conv_id):
    """Get, update or delete a conversation"""
    user = g.current_user
    conv = db.session.get(Conversation, conv_id)
    if not conv or conv.user_id != user.id:
        return err(404, "conversation not found")

    if request.method == "GET":
        return ok(_conv_to_dict(conv))

    if request.method == "DELETE":
        db.session.delete(conv)
        db.session.commit()
        return ok(message="deleted")

    # PATCH - update conversation
    d = request.json or {}
    for k in ("title", "model", "system_prompt", "temperature", "max_tokens", "thinking_enabled"):
        if k in d:
            setattr(conv, k, d[k])

    # Support updating project_id
    if "project_id" in d:
        project_id = d["project_id"]
        if project_id:
            project = db.session.get(Project, project_id)
            if not project or project.user_id != user.id:
                return err(404, "Project not found")
        conv.project_id = project_id or None

    db.session.commit()
    return ok(_conv_to_dict(conv))