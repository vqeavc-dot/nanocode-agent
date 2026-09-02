from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .memory import Memory
from .modes import ModePolicy, resolve_mode
from .failure import analyze_failure
from .planner import LightweightPlanner
from .prompts import SYSTEM_PROMPT
from .security import redact_secrets
from .tools import LocalTools
from .verifier import inspect_transcript


class ChatModel(Protocol):
    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        ...


@dataclass
class AgentResult:
    final: str
    steps: int
    stopped_by_limit: bool = False
    transcript: list[str] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


class CodingAgent:
    def __init__(
        self,
        model: ChatModel,
        tools: LocalTools,
        max_steps: int = 20,
        memory: Memory | None = None,
        verbose: bool = False,
        event_sink: Callable[[str], None] | None = None,
        planner: LightweightPlanner | None = None,
        mode: str | ModePolicy = "review",
    ):
        self.model = model
        self.tools = tools
        self.max_steps = max_steps
        self.memory = memory or Memory()
        self.verbose = verbose
        self.event_sink = event_sink
        self.usage: dict[str, int] = {}
        self.planner = planner or LightweightPlanner()
        self.mode = mode if isinstance(mode, ModePolicy) else resolve_mode(mode)

    def run(self, task: str) -> AgentResult:
        plan = self.planner.build(task)
        self.memory.set_task_profile(plan.profile.render())
        self.memory.set_plan(plan.render())
        base_messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
            {"role": "user", "content": self.mode.render()},
            {"role": "user", "content": f"Initial lightweight plan:\n{plan.render()}"},
        ]
        transcript: list[str] = []
        self._record(transcript, f"[mode]\n{self.mode.render()}")
        self._record(transcript, f"[profile]\n{plan.profile.render()}")
        self._record(transcript, f"[skill]\n{plan.skill.render()}")
        self._record(transcript, f"[plan]\n{plan.render()}")

        for step in range(1, self.max_steps + 1):
            self._record(transcript, f"[step {step}] planning next action")
            messages = [*base_messages, *self.memory.as_messages()]
            response = self.model.chat(messages, self.tools.schemas())
            self._add_usage(getattr(response, "usage", None))
            message = response.message
            content = message.get("content")
            if content:
                self._record(transcript, f"[step {step}] assistant: {_truncate_text(content)}")

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                final = content or "Model stopped without a final answer."
                self._record(transcript, f"[final] {final}")
                return AgentResult(final=final, steps=step, transcript=transcript, usage=dict(self.usage))

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
                if isinstance(args.get("path"), str):
                    self.memory.note_file(args["path"])
                self._record(transcript, f"[step {step}] observation {name} ok={result.ok}: {_truncate_text(result.content)}")
                if not result.ok:
                    failure = analyze_failure(name, result.content)
                    self._record(transcript, f"[reflect] {failure.render()}")
                if name in {"run_command", "run_tests"}:
                    signal = inspect_transcript(transcript)
                    self.memory.set_verification(signal.render())
                    self._record(transcript, f"[verify] {signal.render()}")
                if name == "final_answer" and result.ok:
                    return AgentResult(final=result.content, steps=step, transcript=transcript, usage=dict(self.usage))

        final = f"Stopped after reaching max_steps={self.max_steps}."
        self._record(transcript, f"[limit] {final}")
        return AgentResult(
            final=final,
            steps=self.max_steps,
            stopped_by_limit=True,
            transcript=transcript,
            usage=dict(self.usage),
        )

    def _record(self, transcript: list[str], event: str) -> None:
        event = redact_secrets(event)
        transcript.append(event)
        if self.verbose:
            print(event)
        if self.event_sink is not None:
            self.event_sink(event)

    def _add_usage(self, usage: dict[str, Any] | None) -> None:
        if not usage:
            return
        for key, value in usage.items():
            if isinstance(value, int):
                self.usage[key] = self.usage.get(key, 0) + value


def _safe_json(value: dict[str, Any], limit: int = 500) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return _truncate_text(text, limit)


def _truncate_text(text: str, limit: int = 1000) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
