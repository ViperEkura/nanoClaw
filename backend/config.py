"""Configuration management using dataclasses"""
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from backend import load_config


@dataclass
class ModelConfig:
    """Individual model configuration."""
    id: str
    name: str
    api_url: str
    api_key: str


@dataclass
class SubAgentConfig:
    """Sub-agent (multi_agent tool) settings."""
    max_iterations: int = 3
    max_concurrency: int = 3
    timeout: int = 60


@dataclass
class CodeExecutionConfig:
    """Code execution settings."""
    default_strictness: str = "standard"
    extra_allowed_modules: Dict = field(default_factory=dict)


@dataclass
class AppConfig:
    """Main application configuration."""
    models: List[ModelConfig] = field(default_factory=list)
    default_model: str = ""
    max_iterations: int = 5
    tool_max_workers: int = 4
    sub_agent: SubAgentConfig = field(default_factory=SubAgentConfig)
    code_execution: CodeExecutionConfig = field(default_factory=CodeExecutionConfig)

    # Per-model config lookup: {model_id: ModelConfig}
    _model_config_map: Dict[str, ModelConfig] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        """Build lookup map after initialization."""
        self._model_config_map = {m.id: m for m in self.models}

    def get_model_config(self, model_id: str) -> Optional[ModelConfig]:
        """Get model config by ID."""
        return self._model_config_map.get(model_id)

    def get_model_credentials(self, model_id: str) -> tuple:
        """Get (api_url, api_key) for a model."""
        cfg = self.get_model_config(model_id)
        if not cfg:
            raise ValueError(f"Unknown model: '{model_id}', not found in config")
        if not cfg.api_url:
            raise ValueError(f"Model '{model_id}' has no api_url configured")
        if not cfg.api_key:
            raise ValueError(f"Model '{model_id}' has no api_key configured")
        return cfg.api_url, cfg.api_key


def _parse_config(raw: dict) -> AppConfig:
    """Parse raw YAML config into AppConfig dataclass."""
    # Parse models
    models = []
    for m in raw.get("models", []):
        models.append(ModelConfig(
            id=m["id"],
            name=m["name"],
            api_url=m["api_url"],
            api_key=m["api_key"],
        ))

    # Parse sub_agent
    sa_raw = raw.get("sub_agent", {})
    sub_agent = SubAgentConfig(
        max_iterations=sa_raw.get("max_iterations", 3),
        max_concurrency=sa_raw.get("max_concurrency", 3),
        timeout=sa_raw.get("timeout", 60),
    )

    # Parse code_execution
    ce_raw = raw.get("code_execution", {})
    code_execution = CodeExecutionConfig(
        default_strictness=ce_raw.get("default_strictness", "standard"),
        extra_allowed_modules=ce_raw.get("extra_allowed_modules", {}),
    )

    return AppConfig(
        models=models,
        default_model=raw.get("default_model", ""),
        max_iterations=raw.get("max_iterations", 5),
        tool_max_workers=raw.get("tool_max_workers", 4),
        sub_agent=sub_agent,
        code_execution=code_execution,
    )


# Load and validate configuration at startup
_raw_cfg = load_config()
config = _parse_config(_raw_cfg)
