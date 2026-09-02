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
from .modes import resolve_mode
from .tools import LocalTools


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NanoCode Agent UI</title>
  <style>
    :root { color-scheme: light; --ink:#182230; --muted:#667085; --line:#d0d5dd; --panel:#f8fafc; --soft:#eef4ff; --accent:#1570ef; --ok:#067647; --bad:#b42318; --violet:#6941c6; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Segoe UI", Arial, sans-serif; color: var(--ink); background: #ffffff; }
    header { padding: 14px 22px; border-bottom: 1px solid var(--line); display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    h1 { margin: 0; font-size: 22px; font-weight: 750; }
    h2 { margin: 0 0 12px; font-size: 16px; }
    main { display: grid; grid-template-columns: minmax(280px, 360px) minmax(0, 1fr) minmax(300px, 400px); min-height: calc(100vh - 62px); }
    section { padding: 16px; border-right: 1px solid var(--line); overflow: auto; }
    section:last-child { border-right: 0; }
    label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 8px; }
    textarea { width: 100%; min-height: 230px; resize: vertical; border: 1px solid var(--line); border-radius: 6px; padding: 12px; font: 14px Consolas, monospace; line-height: 1.45; }
    input[type="number"] { width: 90px; border: 1px solid var(--line); border-radius: 6px; padding: 8px; }
    button { border: 0; border-radius: 6px; background: var(--accent); color: white; padding: 10px 14px; font-weight: 700; cursor: pointer; }
    button.secondary { color: var(--ink); background: var(--soft); border: 1px solid #b2ccff; }
    button:disabled { opacity: .55; cursor: wait; }
    select { border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fff; }
    .row { display: flex; gap: 10px; align-items: center; margin-top: 12px; flex-wrap: wrap; }
    .hint, .status { color: var(--muted); font-size: 13px; line-height: 1.5; }
    .stats { display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 8px; margin-bottom: 12px; }
    .stat { border: 1px solid var(--line); background: var(--panel); border-radius: 6px; padding: 8px; }
    .stat b { display: block; font-size: 18px; }
    .stat span { color: var(--muted); font-size: 12px; }
    .event { border: 1px solid var(--line); border-left: 4px solid #98a2b3; border-radius: 6px; padding: 10px; margin-bottom: 10px; background: #fff; }
    .event.mode, .event.profile, .event.skill { border-left-color: #475467; }
    .event.tool_call { border-left-color: var(--accent); }
    .event.observation { border-left-color: var(--ok); }
    .event.reflect, .event.verify { border-left-color: #b54708; }
    .event.final { border-left-color: var(--violet); }
    .event.limit, .event.error { border-left-color: var(--bad); }
    .event .type { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
    pre { white-space: pre-wrap; word-break: break-word; font: 13px Consolas, monospace; background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 10px; margin: 8px 0 0; }
    .metric { background: #fff; border: 1px solid var(--line); border-radius: 6px; padding: 10px; margin-bottom: 10px; }
    .metric b { display: block; font-size: 13px; color: var(--muted); margin-bottom: 4px; }
    @media (max-width: 980px) { main { grid-template-columns: 1fr; } section { border-right: 0; border-bottom: 1px solid var(--line); } .stats { grid-template-columns: repeat(2, minmax(0,1fr)); } }
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
        <button class="secondary" data-preset="map">Repo map</button>
        <button class="secondary" data-preset="test">Verify calculator</button>
        <button class="secondary" data-preset="patch">Patch example</button>
      </div>
      <div class="row">
        <label>Max steps <input id="maxSteps" type="number" min="1" max="40" value="12"></label>
        <label>Mode <select id="mode"><option value="review">Review</option><option value="trust">Trust</option></select></label>
      </div>
      <div class="row"><button id="runBtn">Run Agent</button></div>
      <p class="hint">The UI is only a display layer. The same handwritten agent loop and local tools execute underneath.</p>
    </section>
    <section>
      <h2>Step Timeline</h2>
      <div class="stats">
        <div class="stat"><b id="countSteps">0</b><span>steps</span></div>
        <div class="stat"><b id="countPlans">0</b><span>plans</span></div>
        <div class="stat"><b id="countTools">0</b><span>tool calls</span></div>
        <div class="stat"><b id="countObs">0</b><span>observations</span></div>
        <div class="stat"><b id="countErrors">0</b><span>errors</span></div>
      </div>
      <div id="events"></div>
    </section>
    <section>
      <h2>Result</h2>
      <div class="metric"><b>Final answer</b><pre id="final">No run yet.</pre></div>
      <div class="metric"><b>Mode</b><pre id="modeOut">review</pre></div>
      <div class="metric"><b>Token usage</b><pre id="usage">-</pre></div>
      <div class="metric"><b>Git diff summary</b><pre id="diff">-</pre></div>
      <div class="metric"><b>Run log</b><pre id="logPath">-</pre></div>
    </section>
  </main>
<script>
const presets = {
  map: 'Use repo_map on nanocode, then explain the most important modules and how the agent loop connects to local tools.',
  test: 'Please inspect examples/calculator, explain whether divide(a, b) and its pytest tests exist, and run the relevant tests.',
  patch: 'Use apply_patch_file on a small relevant example only if a change is needed, then run tests and summarize the git diff.'
};
const runBtn = document.getElementById('runBtn');
const statusEl = document.getElementById('status');
const eventsEl = document.getElementById('events');
const finalEl = document.getElementById('final');
const usageEl = document.getElementById('usage');
const diffEl = document.getElementById('diff');
const logEl = document.getElementById('logPath');
const modeOutEl = document.getElementById('modeOut');

function classify(event) {
  if (event.startsWith('[mode]')) return 'mode';
  if (event.startsWith('[profile]')) return 'profile';
  if (event.startsWith('[skill]')) return 'skill';
  if (event.startsWith('[plan]')) return 'plan';
  if (event.startsWith('[reflect]')) return 'reflect';
  if (event.startsWith('[verify]')) return 'verify';
  if (event.includes('tool_call')) return 'tool_call';
  if (event.includes('observation')) return 'observation';
  if (event.startsWith('[final]')) return 'final';
  if (event.startsWith('[limit]')) return 'limit';
  if (event.toLowerCase().includes('error') || event.includes('ok=False')) return 'error';
  return 'planning';
}

function updateStats(events) {
  const types = events.map(classify);
  document.getElementById('countSteps').textContent = new Set(events.map(e => (e.match(/\[step (\d+)\]/) || [])[1]).filter(Boolean)).size;
  document.getElementById('countPlans').textContent = types.filter(t => t === 'plan').length;
  document.getElementById('countTools').textContent = types.filter(t => t === 'tool_call').length;
  document.getElementById('countObs').textContent = types.filter(t => t === 'observation').length;
  document.getElementById('countErrors').textContent = types.filter(t => t === 'error' || t === 'limit').length;
}

function renderEvents(events) {
  eventsEl.innerHTML = '';
  updateStats(events);
  for (const event of events) {
    const type = classify(event);
    const node = document.createElement('div');
    node.className = `event ${type}`;
    node.innerHTML = `<div class="type">${type.replace('_', ' ')}</div><pre></pre>`;
    node.querySelector('pre').textContent = event;
    eventsEl.appendChild(node);
  }
}

document.querySelectorAll('[data-preset]').forEach(btn => {
  btn.addEventListener('click', () => { document.getElementById('task').value = presets[btn.dataset.preset]; });
});

runBtn.addEventListener('click', async () => {
  runBtn.disabled = true;
  statusEl.textContent = 'Running...';
  renderEvents([]);
  finalEl.textContent = 'Waiting for result...';
  modeOutEl.textContent = document.getElementById('mode').value;
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
        mode: document.getElementById('mode').value
      })
    });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Run failed');
    renderEvents(data.transcript);
    finalEl.textContent = data.final || '';
    modeOutEl.textContent = data.mode || '-';
    usageEl.textContent = data.usage_text || '-';
    diffEl.textContent = data.diff_summary || '-';
    logEl.textContent = data.log_path || '-';
    statusEl.textContent = data.stopped_by_limit ? 'Stopped by step limit' : `Finished in ${data.steps} step(s)`;
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
    try:
        mode = resolve_mode(str(payload.get("mode") or "review"))
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    tools = LocalTools(workspace, confirm_commands=False)
    model = OpenAICompatibleLLM(config.api_key, config.base_url, config.model)
    agent = CodingAgent(model=model, tools=tools, max_steps=max(1, max_steps), mode=mode)
    result = agent.run(task)
    diff_summary = collect_git_diff_summary(workspace)
    log_path = write_ui_run_log(workspace, task, result, diff_summary)
    return {
        "ok": True,
        "final": result.final,
        "steps": result.steps,
        "stopped_by_limit": result.stopped_by_limit,
        "mode": mode.name,
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
