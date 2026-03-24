"""Configuration management"""
from backend import load_config

_cfg = load_config()

API_URL = _cfg.get("api_url")
API_KEY = _cfg["api_key"]
MODELS = _cfg.get("models", [])
DEFAULT_MODEL = _cfg.get("default_model", "glm-5")
