"""Model list API routes"""
from flask import Blueprint
from backend.utils.helpers import ok
from backend.config import MODELS

bp = Blueprint("models", __name__)


@bp.route("/api/models", methods=["GET"])
def list_models():
    """Get available model list"""
    return ok(MODELS)
