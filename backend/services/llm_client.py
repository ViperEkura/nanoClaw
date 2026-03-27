"""OpenAI-compatible LLM API client

Supports any provider that follows the OpenAI chat completions API format:
- Zhipu GLM (open.bigmodel.cn)
- DeepSeek (api.deepseek.com)
- OpenAI, Moonshot, Qwen, etc.
"""
import os
import re
import time
import requests
from typing import Optional, List, Union


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR} or $VAR with environment variable values."""
    if not isinstance(value, str):
        return value
    def _replace(m):
        var = m.group(1) or m.group(2)
        return os.environ.get(var, m.group(0))
    return re.sub(r'\$\{(\w+)\}|\$(\w+)', _replace, value)


def _detect_provider(api_url: str) -> str:
    """Detect provider from api_url, returns provider name."""
    if "deepseek" in api_url:
        return "deepseek"
    elif "bigmodel" in api_url:
        return "glm"
    else:
        return "openai"


class LLMClient:
    """OpenAI-compatible LLM API client.

    Each model must have its own api_url and api_key configured in MODEL_CONFIG.
    """

    def __init__(self, model_config: dict):
        """Initialize with per-model config lookup.

        Args:
            model_config: {model_id: {"api_url": ..., "api_key": ...}}
        """
        self.model_config = model_config

    def _get_credentials(self, model: str):
        """Get api_url and api_key for a model, with env-var expansion."""
        cfg = self.model_config.get(model)
        if not cfg:
            raise ValueError(f"Unknown model: '{model}', not found in config")
        api_url = _resolve_env_vars(cfg.get("api_url", ""))
        api_key = _resolve_env_vars(cfg.get("api_key", ""))
        if not api_url:
            raise ValueError(f"Model '{model}' has no api_url configured")
        if not api_key:
            raise ValueError(f"Model '{model}' has no api_key configured")
        return api_url, api_key

    def _build_body(self, model, messages, max_tokens, temperature, thinking_enabled,
                    tools, tool_choice, stream, api_url):
        """Build request body with provider-specific parameter adaptation."""
        provider = _detect_provider(api_url)

        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        # --- Provider-specific: max_tokens ---
        if provider == "deepseek":
            body["max_tokens"] = min(max_tokens, 8192)
        elif provider == "glm":
            body["max_tokens"] = min(max_tokens, 65536)
        else:
            body["max_tokens"] = max_tokens

        # --- Provider-specific: thinking ---
        if thinking_enabled:
            if provider == "glm" or provider == "deepseek":
                body["thinking"] = {"type": "enabled"}
            else:
                raise NotImplementedError(f"Thinking not supported for provider '{provider}'")

        if tools:
            body["tools"] = tools
            body["tool_choice"] = tool_choice if tool_choice is not None else "auto"

        if stream:
            body["stream"] = True

        return body

    def call(
        self,
        model: str,
        messages: List[dict],
        max_tokens: int = 65536,
        temperature: float = 1.0,
        thinking_enabled: bool = False,
        tools: Optional[List[dict]] = None,
        tool_choice: Optional[Union[str, dict]] = None,
        stream: bool = False,
        timeout: int = 200,
        max_retries: int = 3,
    ):
        """Call LLM API with retry on rate limit (429)"""
        api_url, api_key = self._get_credentials(model)
        body = self._build_body(
            model, messages, max_tokens, temperature,
            thinking_enabled, tools, tool_choice, stream, api_url,
        )

        for attempt in range(max_retries + 1):
            resp = requests.post(
                api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json=body,
                stream=stream,
                timeout=timeout,
            )

            if resp.status_code == 429 and attempt < max_retries:
                wait = 2 ** attempt
                time.sleep(wait)
                continue

            return resp

        return resp