from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

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
        verbose: bool = False,
        event_sink: Callable[[str], None] | None = None,
    ):
        self.model = model
        self.tools = tools
        self.max_steps = max_steps
        self.memory = memory or Memory()
        self.verbose = verbose
        self.event_sink = event_sink

    def run(self, task: str) -> AgentResult:
        base_messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        transcript: list[str] = []

        for step in range(1, self.max_steps + 1):
            self._record(transcript, f"[step {step}] planning next action")
            messages = [*base_messages, *self.memory.as_messages()]
            response = self.model.chat(messages, self.tools.schemas())
            message = response.message
            content = message.get("content")
            if content:
                self._record(transcript, f"[step {step}] assistant: {_truncate_text(content)}")

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                final = content or "Model stopped without a final answer."
                self._record(transcript, f"[final] {final}")
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
                    self._record(transcript, f"[step {step}] tool {name or 'unknown_tool'} invalid arguments: {exc}")
                    continue

                self._record(transcript, f"[step {step}] tool_call {name} args={_safe_json(args)}")
                result = self.tools.run(name, args)
                self.memory.add(name, result.to_json(), ok=result.ok)
                self._record(transcript, f"[step {step}] observation {name} ok={result.ok}: {_truncate_text(result.content)}")
                if name == "final_answer" and result.ok:
                    return AgentResult(final=result.content, steps=step, transcript=transcript)

        final = f"Stopped after reaching max_steps={self.max_steps}."
        self._record(transcript, f"[limit] {final}")
        return AgentResult(
            final=final,
            steps=self.max_steps,
            stopped_by_limit=True,
            transcript=transcript,
        )

    def _record(self, transcript: list[str], event: str) -> None:
        transcript.append(event)
        if self.verbose:
            print(event)
        if self.event_sink is not None:
            self.event_sink(event)


def _safe_json(value: dict[str, Any], limit: int = 500) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return _truncate_text(text, limit)


def _truncate_text(text: str, limit: int = 1000) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
