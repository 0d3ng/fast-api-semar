"""Local Ollama LLM client with structured JSON schema output and health probe."""

import time
from typing import Dict, Any, List, Optional

import httpx

from app.utils.config import LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT_S, LLM_NUM_CTX
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """Async adapter for local Ollama /api/chat and /api/tags endpoints."""

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

    async def health(self) -> Dict[str, Any]:
        """Probe Ollama connectivity and verify whether the configured model is pulled."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models: List[str] = [
                    m.get("name") for m in (resp.json().get("models") or []) if m.get("name")
                ]
            installed = any(
                m == self.model or m.split(":")[0] == self.model.split(":")[0] and m == self.model
                for m in models
            )
            return {
                "ok": True,
                "base_url": self.base_url,
                "configured_model": self.model,
                "model_installed": installed,
                "available_models": models,
            }
        except Exception as exc:
            return {
                "ok": False,
                "base_url": self.base_url,
                "configured_model": self.model,
                "model_installed": False,
                "available_models": [],
                "error": str(exc),
            }

    async def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call Ollama /api/chat enforcing structured JSON output."""
        payload: Dict[str, Any] = {
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
        # Disable extended thinking tokens on qwen3 models for fast deterministic JSON schema responses
        if "qwen3" in (self.model or "").lower():
            payload["think"] = False

        prompt_chars = len(system_prompt) + len(user_prompt)
        logger.info(
            "Ollama request -> url=%s/api/chat model=%s prompt_chars=%d think=%s num_ctx=%d timeout_s=%s",
            self.base_url,
            self.model,
            prompt_chars,
            payload.get("think"),
            self.num_ctx,
            self.timeout_s,
        )
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout_s)) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            err_detail = f"{type(exc).__name__}: {exc}" if str(exc) else repr(exc)
            logger.warning(
                "Ollama request failed -> url=%s/api/chat model=%s prompt_chars=%d latency_ms=%d error=%s",
                self.base_url,
                self.model,
                prompt_chars,
                latency_ms,
                err_detail,
            )
            raise
        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "Ollama response <- model=%s status=ok latency_ms=%d prompt_tokens=%s completion_tokens=%s resp_chars=%d",
            data.get("model") or self.model,
            latency_ms,
            data.get("prompt_eval_count"),
            data.get("eval_count"),
            len((data.get("message") or {}).get("content") or ""),
        )

        message = data.get("message") or {}
        content = message.get("content") or ""
        return {
            "content": content,
            "model": data.get("model") or self.model,
            "latency_ms": latency_ms,
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
        }
