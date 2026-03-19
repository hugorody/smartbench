"""OpenAI Responses API integration scaffold."""

from __future__ import annotations

from typing import Any

from flask import current_app
from openai import OpenAI


class OpenAIService:
    """Lightweight wrapper around OpenAI client and Responses API."""

    def __init__(self) -> None:
        api_key = current_app.config.get("OPENAI_API_KEY")
        self._client = OpenAI(api_key=api_key) if api_key else None

    def is_enabled(self) -> bool:
        return self._client is not None

    def create_response(
        self,
        *,
        model: str,
        input_text: str,
        tools: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call Responses API and return a normalized dict payload."""
        if self._client is None:
            return {
                "output_text": "OpenAI integration is not configured. Set OPENAI_API_KEY to enable.",
                "tool_calls": [],
            }

        response = self._client.responses.create(
            model=model,
            input=[{"role": "user", "content": [{"type": "input_text", "text": input_text}]}],
            tools=tools or [],
            metadata=metadata or {},
        )

        return {
            "response_id": response.id,
            "output_text": response.output_text,
            "output": [item.model_dump() for item in response.output],
        }
