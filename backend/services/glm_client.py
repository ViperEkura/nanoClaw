"""GLM API client"""
import requests
from typing import Optional, List


class GLMClient:
    """GLM API client for chat completions"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
    
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
            self.api_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            json=body,
            stream=stream,
            timeout=timeout,
        )
