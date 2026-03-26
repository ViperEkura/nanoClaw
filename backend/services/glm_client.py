"""GLM API client"""
import requests
from typing import Optional, List


class GLMClient:
    """GLM API client for chat completions"""

    def __init__(self, model_config: dict):
        """Initialize with per-model config lookup.

        Args:
            model_config: {model_id: {"api_url": ..., "api_key": ...}}
        """
        self.model_config = model_config

    def _get_credentials(self, model: str):
        """Get api_url and api_key for a model, with fallback."""
        cfg = self.model_config.get(model, {})
        return cfg.get("api_url", ""), cfg.get("api_key", "")

    def call(
        self,
        model: str,
        messages: List[dict],
        max_tokens: int = 65536,
        temperature: float = 1.0,
        thinking_enabled: bool = False,
        tools: Optional[List[dict]] = None,
        stream: bool = False,
        timeout: int = 120,
    ):
        """Call GLM API"""
        api_url, api_key = self._get_credentials(model)
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if thinking_enabled:
            body["thinking"] = {"type": "enabled"}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if stream:
            body["stream"] = True

        return requests.post(
            api_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=body,
            stream=stream,
            timeout=timeout,
        )
