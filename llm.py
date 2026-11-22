"""Thin wrappers around LLM providers. Each returns the model's raw text (a JSON string)."""
from __future__ import annotations

import os
from typing import Protocol

History = list[dict[str, str]]  # [{"role": "user" | "assistant", "content": "..."}]


class LLMError(RuntimeError):
    """Raised when the LLM provider fails or is not configured."""


class LLMClient(Protocol):
    def generate(self, system_prompt: str, history: History) -> str: ...


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, system_prompt: str, history: History) -> str:
        from google.genai import types

        contents = [
            types.Content(
                role="user" if m["role"] == "user" else "model",
                parts=[types.Part(text=m["content"])],
            )
            for m in history
        ]
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            temperature=0.2,
        )
        try:
            resp = self._client.models.generate_content(
                model=self._model, contents=contents, config=config
            )
        except Exception as exc:  # network, quota, bad key ...
            raise LLMError(f"Gemini request failed: {exc}") from exc
        return resp.text or ""


class GroqClient:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._model = model

    def generate(self, system_prompt: str, history: History) -> str:
        messages = [{"role": "system", "content": system_prompt}, *history]
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise LLMError(f"Groq request failed: {exc}") from exc
        return resp.choices[0].message.content or ""


def create_client() -> LLMClient:
    """Build a client from environment variables (.env)."""
    provider = os.getenv("LLM_PROVIDER", "gemini").split("#")[0].strip().lower()
    if provider == "gemini":
        key = os.getenv("GEMINI_API_KEY", "")
        if not key or key.startswith("your_"):
            raise LLMError("GEMINI_API_KEY is missing. Add it to your .env file.")
        return GeminiClient(key, os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    if provider == "groq":
        key = os.getenv("GROQ_API_KEY", "")
        if not key or key.startswith("your_"):
            raise LLMError("GROQ_API_KEY is missing. Add it to your .env file.")
        return GroqClient(key, os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    raise LLMError(f"Unknown LLM_PROVIDER '{provider}'. Use 'gemini' or 'groq'.")
