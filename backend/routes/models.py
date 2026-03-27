"""Model list API routes"""
from flask import Blueprint
from backend.utils.helpers import ok
from backend.config import MODELS

bp = Blueprint("models", __name__)

# Keys that should never be exposed to the frontend
_SENSITIVE_KEYS = {"api_key", "api_url"}


@bp.route("/api/models", methods=["GET"])
def list_models():
    """Get available model list (without sensitive fields like api_key)"""
    safe_models = [
        {k: v for k, v in m.items() if k not in _SENSITIVE_KEYS}
        for m in MODELS
    ]
    return ok(safe_models)
