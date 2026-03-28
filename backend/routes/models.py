"""Model list API routes"""
from flask import Blueprint
from backend.utils.helpers import ok
from backend.config import config

bp = Blueprint("models", __name__)

# Keys that should never be exposed to the frontend
_SENSITIVE_KEYS = {"api_key", "api_url"}


@bp.route("/api/models", methods=["GET"])
def list_models():
    """Get available model list (without sensitive fields like api_key)"""
    safe_models = [
        {
            "id": m.id,
            "name": m.name,
        }
        for m in config.models
    ]
    return ok(safe_models)