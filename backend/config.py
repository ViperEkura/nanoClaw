"""Configuration management"""
import sys
from backend import load_config

_cfg = load_config()

# Model list (for /api/models endpoint)
MODELS = _cfg.get("models", [])

# Validate each model has required fields at startup
_REQUIRED_MODEL_KEYS = {"id", "name", "api_url", "api_key"}
_model_ids_seen = set()
for _i, _m in enumerate(MODELS):
    _missing = _REQUIRED_MODEL_KEYS - set(_m.keys())
    if _missing:
        print(f"[config] ERROR: models[{_i}] missing required fields: {_missing}", file=sys.stderr)
        sys.exit(1)
    if _m["id"] in _model_ids_seen:
        print(f"[config] ERROR: duplicate model id '{_m['id']}'", file=sys.stderr)
        sys.exit(1)
    _model_ids_seen.add(_m["id"])

# Per-model config lookup: {model_id: {api_url, api_key}}
MODEL_CONFIG = {m["id"]: {"api_url": m["api_url"], "api_key": m["api_key"]} for m in MODELS}

# default_model must exist in models
DEFAULT_MODEL = _cfg.get("default_model", "")
if DEFAULT_MODEL and DEFAULT_MODEL not in MODEL_CONFIG:
    print(f"[config] ERROR: default_model '{DEFAULT_MODEL}' not found in models", file=sys.stderr)
    sys.exit(1)
if MODELS and not DEFAULT_MODEL:
    DEFAULT_MODEL = MODELS[0]["id"]

# Max agentic loop iterations (tool call rounds)
MAX_ITERATIONS = _cfg.get("max_iterations", 5)

# Max parallel workers for tool execution (ThreadPoolExecutor)
TOOL_MAX_WORKERS = _cfg.get("tool_max_workers", 4)

# Sub-agent settings (multi_agent tool)
_sa = _cfg.get("sub_agent", {})
SUB_AGENT_MAX_ITERATIONS = _sa.get("max_iterations", 3)
SUB_AGENT_MAX_CONCURRENCY = _sa.get("max_concurrency", 3)
SUB_AGENT_TIMEOUT = _sa.get("timeout", 60)

# Code execution settings
_ce = _cfg.get("code_execution", {})
CODE_EXECUTION_DEFAULT_STRICTNESS = _ce.get("default_strictness", "standard")
CODE_EXECUTION_EXTRA_MODULES = _ce.get("extra_allowed_modules", {})
