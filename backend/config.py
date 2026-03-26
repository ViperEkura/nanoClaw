"""Configuration management"""
from backend import load_config

_cfg = load_config()

# Global defaults
DEFAULT_API_URL = _cfg.get("api_url", "") or _cfg.get("default_api_url", "")
DEFAULT_API_KEY = _cfg.get("api_key", "") or _cfg.get("default_api_key", "")

# Model list (for /api/models endpoint)
MODELS = _cfg.get("models", [])

# Per-model config lookup: {model_id: {api_url, api_key}}
# Falls back to global defaults if not specified per model
MODEL_CONFIG = {}
for _m in MODELS:
    _mid = _m["id"]
    MODEL_CONFIG[_mid] = {
        "api_url": _m.get("api_url", DEFAULT_API_URL),
        "api_key": _m.get("api_key", DEFAULT_API_KEY),
    }

DEFAULT_MODEL = _cfg.get("default_model", "glm-5")
