from __future__ import annotations

import os
import json
from collections.abc import Callable
from typing import Any
from app.trace import TraceCollector


def get_llm_client():
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provider == "gemini":
        import google.genai as genai
        api_key = os.environ.get("LLM_API_KEY", "")
        model_name = os.environ.get("LLM_MODEL", "gemini-2.0-flash")
        client = genai.Client(api_key=api_key) if api_key else None
        return _GeminiWrapper(client, model_name)
    raise ValueError(f"Unknown LLM provider: {provider}")


class _GeminiWrapper:
    def __init__(self, client, model_name: str):
        self._client = client
        self._model = model_name

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: str, trace: TraceCollector | None = None, json_mode: bool = False, temperature: float = 0.0) -> str:
        if not self._client:
            return json.dumps({"error": "No LLM client configured"}) if json_mode else ""
        import google.genai.types as types
        config = types.GenerateContentConfig(temperature=temperature)
        if json_mode:
            config.response_mime_type = "application/json"
        response = self._client.models.generate_content(model=self._model, contents=prompt, config=config)
        text = response.text or ""
        if trace:
            usage = response.usage_metadata
            inp = sum(getattr(usage, "prompt_token_count", 0) or 0)
            out = sum(getattr(usage, "candidates_token_count", 0) or 0)
            trace.record_model(self._model, inp, out)
        return text

    def generate_vision(self, prompt: str, image_bytes: bytes, mime_type: str, trace: TraceCollector | None = None) -> str:
        if not self._client:
            return json.dumps({"error": "No LLM client configured"})
        import google.genai.types as types
        img = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        response = self._client.models.generate_content(model=self._model, contents=[prompt, img])
        text = response.text or ""
        if trace:
            usage = response.usage_metadata
            inp = getattr(usage, "prompt_token_count", 0) or 0
            out = getattr(usage, "candidates_token_count", 0) or 0
            trace.record_model(self._model, inp, out)
        return text