"""Local Ollama LLM client with structured JSON schema output."""

import time
from typing import Dict, Any, Optional

import httpx

from app.utils.config import LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT_S, LLM_NUM_CTX


class OllamaClient:
    """Async adapter for local Ollama /api/chat endpoint."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_s: Optional[int] = None,
        num_ctx: Optional[int] = None,
    ):
        self.base_url = (base_url or LLM_BASE_URL).rstrip("/")
        self.model = model or LLM_MODEL
        self.timeout_s = timeout_s or LLM_TIMEOUT_S
        self.num_ctx = num_ctx or LLM_NUM_CTX

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call Ollama /api/chat enforcing structured JSON output."""
        payload = {
            "model": self.model,
            "stream": False,
            "format": json_schema,
            "options": {
                "temperature": 0,
                "seed": 42,
                "num_ctx": self.num_ctx,
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=float(self.timeout_s)) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        latency_ms = int((time.perf_counter() - t0) * 1000)

        message = data.get("message") or {}
        content = message.get("content") or ""
        return {
            "content": content,
            "model": data.get("model") or self.model,
            "latency_ms": latency_ms,
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
        }

