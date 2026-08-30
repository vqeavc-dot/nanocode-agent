from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .agent import CodingAgent
from .cli import collect_git_diff_summary, format_usage
from .config import load_config
from .llm import OpenAICompatibleLLM
from .tools import LocalTools


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NanoCode Agent UI</title>
  <style>
    :root { color-scheme: light; --ink:#172033; --muted:#667085; --line:#d8dee9; --panel:#f7f9fc; --accent:#1f7a5a; --warn:#9a3412; --bad:#b42318; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; color: var(--ink); background: #ffffff; }
    header { padding: 16px 24px; border-bottom: 1px solid var(--line); display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    h1 { margin: 0; font-size: 22px; font-weight: 700; }
    main { display: grid; grid-template-columns: minmax(260px, 360px) minmax(0, 1fr) minmax(280px, 380px); min-height: calc(100vh - 66px); }
    section { padding: 18px; border-right: 1px solid var(--line); overflow: auto; }
    section:last-child { border-right: 0; }
    label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 8px; }
    textarea { width: 100%; min-height: 220px; resize: vertical; border: 1px solid var(--line); border-radius: 6px; padding: 12px; font: 14px Consolas, monospace; }
    input[type="number"] { width: 90px; border: 1px solid var(--line); border-radius: 6px; padding: 8px; }
    button { border: 0; border-radius: 6px; background: var(--accent); color: white; padding: 10px 14px; font-weight: 700; cursor: pointer; }
    button:disabled { opacity: .55; cursor: wait; }
    .row { display: flex; gap: 10px; align-items: center; margin-top: 12px; flex-wrap: wrap; }
    .hint { color: var(--muted); font-size: 13px; line-height: 1.5; }
    .event { border: 1px solid var(--line); border-left: 4px solid #98a2b3; border-radius: 6px; padding: 10px; margin-bottom: 10px; background: #fff; }
    .event.tool_call { border-left-color: #2563eb; }
    .event.observation { border-left-color: var(--accent); }
    .event.final { border-left-color: #7c3aed; }
    .event.limit, .event.error { border-left-color: var(--bad); }
    .event .type { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
    pre { white-space: pre-wrap; word-break: break-word; font: 13px Consolas, monospace; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px; margin: 8px 0 0; }
    .metric { background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px; margin-bottom: 10px; }
    .metric b { display: block; font-size: 13px; color: var(--muted); margin-bottom: 4px; }
    .status { font-size: 13px; color: var(--muted); }
    @media (max-width: 980px) { main { grid-template-columns: 1fr; } section { border-right: 0; border-bottom: 1px solid var(--line); } }
  </style>
</head>
<body>
  <header>
    <h1>NanoCode Agent</h1>
    <div class="status" id="status">Ready</div>
  </header>
  <main>
    <section>
      <label for="task">Task</label>
      <textarea id="task">Please inspect examples/calculator, explain whether divide(a, b) and its pytest tests exist, and run the relevant tests.</textarea>
      <div class="row">
        <label>Max steps <input id="maxSteps" type="number" min="1" max="40" value="12"></label>
        <label><input id="confirmActions" type="checkbox"> Confirm shell commands</label>
      </div>
      <div class="row"><button id="runBtn">Run Agent</button></div>
      <p class="hint">The UI is only a display layer. The same handwritten agent loop and local tools execute underneath.</p>
    </section>
    <section>
      <h2>Step Timeline</h2>
      <div id="events"></div>
    </section>
    <section>
      <h2>Result</h2>
      <div class="metric"><b>Final answer</b><pre id="final">No run yet.</pre></div>
      <div class="metric"><b>Token usage</b><pre id="usage">-</pre></div>
      <div class="metric"><b>Git diff summary</b><pre id="diff">-</pre></div>
      <div class="metric"><b>Run log</b><pre id="logPath">-</pre></div>
    </section>
  </main>
<script>
const runBtn = document.getElementById('runBtn');
const statusEl = document.getElementById('status');
const eventsEl = document.getElementById('events');
const finalEl = document.getElementById('final');
const usageEl = document.getElementById('usage');
const diffEl = document.getElementById('diff');
const logEl = document.getElementById('logPath');

function classify(event) {
  if (event.includes('tool_call')) return 'tool_call';
  if (event.includes('observation')) return 'observation';
  if (event.startsWith('[final]')) return 'final';
  if (event.startsWith('[limit]')) return 'limit';
  if (event.toLowerCase().includes('error')) return 'error';
  return 'planning';
}

function renderEvents(events) {
  eventsEl.innerHTML = '';
  for (const event of events) {
    const type = classify(event);
    const node = document.createElement('div');
    node.className = `event ${type}`;
    node.innerHTML = `<div class="type">${type.replace('_', ' ')}</div><pre></pre>`;
    node.querySelector('pre').textContent = event;
    eventsEl.appendChild(node);
  }
}

runBtn.addEventListener('click', async () => {
  runBtn.disabled = true;
  statusEl.textContent = 'Running...';
  eventsEl.innerHTML = '';
  finalEl.textContent = 'Waiting for result...';
  usageEl.textContent = '-';
  diffEl.textContent = '-';
  logEl.textContent = '-';
  try {
    const response = await fetch('/api/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        task: document.getElementById('task').value,
        max_steps: Number(document.getElementById('maxSteps').value || 12),
        confirm_actions: document.getElementById('confirmActions').checked
      })
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Run failed');
    renderEvents(data.transcript);
    finalEl.textContent = data.final || '';
    usageEl.textContent = data.usage_text || '-';
    diffEl.textContent = data.diff_summary || '-';
    logEl.textContent = data.log_path || '-';
    statusEl.textContent = data.stopped_by_limit ? 'Stopped by step limit' : 'Finished';
  } catch (err) {
    statusEl.textContent = 'Error';
    finalEl.textContent = String(err.message || err);
  } finally {
    runBtn.disabled = false;
  }
});
</script>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NanoCode Agent Web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--workspace", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config()
    workspace = config.workspace if args.workspace == "." else (config.workspace / args.workspace).resolve()
    handler = make_handler(config=config, workspace=workspace)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"NanoCode UI running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping NanoCode UI.")
    finally:
        server.server_close()
    return 0


def make_handler(config: Any, workspace: Path):
    class UIHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in {"/", "/index.html"}:
                self._send_json({"ok": False, "error": "not found"}, status=404)
                return
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if self.path != "/api/run":
                self._send_json({"ok": False, "error": "not found"}, status=404)
                return
            if not config.api_key:
                self._send_json({"ok": False, "error": "NANOCODE_API_KEY is not set"}, status=400)
                return
            try:
                payload = self._read_json()
                result = run_agent_from_payload(config, workspace, payload)
                self._send_json(result)
            except Exception as exc:  # pragma: no cover - defensive HTTP boundary
                self._send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, status=500)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8")) if raw else {}

        def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return UIHandler


def run_agent_from_payload(config: Any, workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
    task = str(payload.get("task") or "").strip()
    if not task:
        return {"ok": False, "error": "task is required"}
    max_steps = int(payload.get("max_steps") or config.max_steps)
    confirm_actions = bool(payload.get("confirm_actions", False))
    tools = LocalTools(workspace, confirm_commands=confirm_actions)
    model = OpenAICompatibleLLM(config.api_key, config.base_url, config.model)
    agent = CodingAgent(model=model, tools=tools, max_steps=max(1, max_steps))
    result = agent.run(task)
    diff_summary = collect_git_diff_summary(workspace)
    log_path = write_ui_run_log(workspace, task, result, diff_summary)
    return {
        "ok": True,
        "final": result.final,
        "steps": result.steps,
        "stopped_by_limit": result.stopped_by_limit,
        "transcript": result.transcript,
        "usage": result.usage,
        "usage_text": format_usage(result.usage) if result.usage else "",
        "diff_summary": diff_summary,
        "log_path": str(log_path),
    }


def write_ui_run_log(workspace: Path, task: str, result: Any, diff_summary: str) -> Path:
    from .cli import _write_run_log

    return _write_run_log(str(workspace / "run_logs"), task, result, diff_summary)


if __name__ == "__main__":
    raise SystemExit(main())
