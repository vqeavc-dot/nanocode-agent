from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI, OpenAIError


@dataclass
class LLMResponse:
    message: dict[str, Any]
    usage: dict[str, int] = field(default_factory=dict)


class OpenAICompatibleLLM:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_retries: int = 2,
        retry_delay: float = 1.0,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_retries = max(0, max_retries)
        self.retry_delay = max(0.0, retry_delay)

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMResponse:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                message = response.choices[0].message.model_dump(exclude_none=True)
                usage = response.usage.model_dump() if getattr(response, "usage", None) else {}
                normalized_usage = {key: value for key, value in usage.items() if isinstance(value, int)}
                return LLMResponse(message=message, usage=normalized_usage)
            except OpenAIError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_delay * (attempt + 1))
        raise RuntimeError(f"LLM request failed after {self.max_retries + 1} attempts: {last_error}")
