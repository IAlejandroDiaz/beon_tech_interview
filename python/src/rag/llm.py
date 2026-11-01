"""LLM client — a thin wrapper over the local vLLM server.

vLLM exposes an OpenAI-compatible API, so we reuse the official `openai` client
and simply point it at the local base URL. No real API key is needed; vLLM
ignores it, but the client library requires the field to be set.

Configuration is env-driven so nothing is hardcoded for the demo:
  LLM_BASE_URL  (default http://127.0.0.1:8000/v1)
  LLM_MODEL     (default mlx-community/Qwen3-4B-Instruct-2507-4bit)
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_MODEL = "mlx-community/Qwen3-4B-Instruct-2507-4bit"


class LLMClient:
    def __init__(self) -> None:
        self._model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
        self._client = AsyncOpenAI(
            base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
            # vLLM doesn't validate the key, but the client requires a value.
            api_key=os.environ.get("LLM_API_KEY", "not-needed"),
        )

    @property
    def model(self) -> str:
        return self._model

    async def complete(self, messages: list[dict]) -> str:
        """Call the chat-completions endpoint and return the answer text.

        Low temperature keeps answers deterministic and grounded — we want
        faithful retrieval-based answers, not creative ones. A modest
        max_tokens cap enforces the "concise" requirement at the transport
        level, backing up the prompt instruction.
        """
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.1,
            max_tokens=256,
        )
        return (response.choices[0].message.content or "").strip()
