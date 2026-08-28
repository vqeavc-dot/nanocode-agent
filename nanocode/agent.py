from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from .memory import Memory
from .prompts import SYSTEM_PROMPT
from .tools import LocalTools


class ChatModel(Protocol):
    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        ...


@dataclass
class AgentResult:
    final: str
    steps: int
    stopped_by_limit: bool = False
    transcript: list[str] = field(default_factory=list)


class CodingAgent:
    def __init__(
        self,
        model: ChatModel,
        tools: LocalTools,
        max_steps: int = 20,
        memory: Memory | None = None,
    ):
        self.model = model
        self.tools = tools
        self.max_steps = max_steps
        self.memory = memory or Memory()

    def run(self, task: str) -> AgentResult:
        base_messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        transcript: list[str] = []

        for step in range(1, self.max_steps + 1):
            messages = [*base_messages, *self.memory.as_messages()]
            response = self.model.chat(messages, self.tools.schemas())
            message = response.message
            transcript.append(f"step {step}: {message.get('content', '')}")

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                final = message.get("content") or "Model stopped without a final answer."
                return AgentResult(final=final, steps=step, transcript=transcript)

            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                name = function.get("name", "")
                raw_args = function.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError as exc:
                    result_content = f"Invalid JSON arguments for {name}: {exc}"
                    self.memory.add(name or "unknown_tool", result_content, ok=False)
                    continue

                result = self.tools.run(name, args)
                self.memory.add(name, result.to_json(), ok=result.ok)
                transcript.append(f"tool {name}: {result.content}")
                if name == "final_answer" and result.ok:
                    return AgentResult(final=result.content, steps=step, transcript=transcript)

        return AgentResult(
            final=f"Stopped after reaching max_steps={self.max_steps}.",
            steps=self.max_steps,
            stopped_by_limit=True,
            transcript=transcript,
        )

