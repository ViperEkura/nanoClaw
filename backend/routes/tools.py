"""Tool list API routes"""
from flask import Blueprint
from backend.tools import registry
from backend.utils.helpers import ok

bp = Blueprint("tools", __name__)


@bp.route("/api/tools", methods=["GET"])
def list_tools():
    """Get available tool list"""
    tools = registry.list_all()
    return ok({
        "tools": tools,
        "total": len(tools)
    })
