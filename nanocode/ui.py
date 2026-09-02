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
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NanoCode Agent 工作台</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --surface: #ffffff;
      --surface-2: #f2f4f7;
      --ink: #101828;
      --muted: #667085;
      --line: #d0d5dd;
      --blue: #175cd3;
      --green: #067647;
      --amber: #b54708;
      --red: #b42318;
      --violet: #6941c6;
      --shadow: 0 1px 2px rgba(16, 24, 40, .06);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-width: 320px;
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
    }
    header {
      height: 64px;
      padding: 0 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      z-index: 3;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 760; }
    h2 { margin: 0 0 12px; font-size: 15px; font-weight: 720; }
    h3 { margin: 0; font-size: 13px; font-weight: 720; }
    button, select, input, textarea { font: inherit; }
    button {
      border: 1px solid transparent;
      border-radius: 6px;
      padding: 9px 12px;
      background: var(--blue);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }
    button.secondary { color: var(--ink); background: var(--surface); border-color: var(--line); }
    button.ghost { color: var(--blue); background: #eff4ff; border-color: #b2ccff; }
    button:disabled { opacity: .6; cursor: wait; }
    select, input[type="number"] {
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 10px;
      background: var(--surface);
      color: var(--ink);
    }
    textarea {
      width: 100%;
      min-height: 190px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      line-height: 1.55;
      background: var(--surface);
      color: var(--ink);
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font: 12px Consolas, "Microsoft YaHei", monospace;
      line-height: 1.55;
    }
    .status { color: var(--muted); font-size: 13px; }
    .shell {
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr) 380px;
      gap: 16px;
      padding: 16px;
    }
    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .panel-head {
      padding: 13px 14px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .panel-body { padding: 14px; }
    .muted { color: var(--muted); font-size: 12px; line-height: 1.5; }
    .form-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: end; margin-top: 12px; }
    .field { display: grid; gap: 6px; }
    .field label { color: var(--muted); font-size: 12px; }
    .preset-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
    .run-row { display: flex; gap: 10px; margin-top: 12px; }
    .run-row button { flex: 1; }
    .architecture {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 12px;
    }
    .arch-item {
      min-height: 70px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 10px;
    }
    .arch-item b { display: block; font-size: 13px; margin-bottom: 4px; }
    .arch-item span { color: var(--muted); font-size: 12px; line-height: 1.45; }
    .stats { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; margin-bottom: 12px; }
    .stat {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
    }
    .stat b { display: block; font-size: 18px; line-height: 1.1; }
    .stat span { color: var(--muted); font-size: 12px; }
    .lanes {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .lane {
      min-height: 190px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      overflow: hidden;
    }
    .lane-title {
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      background: var(--surface-2);
      display: flex;
      justify-content: space-between;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .lane-body { padding: 10px; max-height: 300px; overflow: auto; }
    .empty { color: var(--muted); font-size: 12px; }
    .event {
      border: 1px solid var(--line);
      border-left: 4px solid #98a2b3;
      border-radius: 7px;
      padding: 8px;
      margin-bottom: 8px;
      background: #fff;
    }
    .event.mode, .event.profile, .event.skill, .event.plan { border-left-color: var(--blue); }
    .event.tool_call { border-left-color: var(--violet); }
    .event.observation { border-left-color: var(--green); }
    .event.reflect, .event.verify { border-left-color: var(--amber); }
    .event.final { border-left-color: var(--green); background: #f6fef9; }
    .event.limit, .event.error { border-left-color: var(--red); background: #fffbfa; }
    .event-type { color: var(--muted); font-size: 11px; margin-bottom: 4px; }
    .result-stack { display: grid; gap: 10px; }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      overflow: hidden;
    }
    .metric b {
      display: block;
      padding: 8px 10px;
      background: var(--surface-2);
      border-bottom: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
    }
    .metric pre { padding: 10px; max-height: 260px; overflow: auto; }
    .pill {
      display: inline-flex;
      align-items: center;
      height: 24px;
      padding: 0 8px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--muted);
      font-size: 12px;
    }
    @media (max-width: 1180px) {
      .shell { grid-template-columns: 1fr; }
      .lanes { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 720px) {
      header { align-items: flex-start; height: auto; padding: 14px; flex-direction: column; }
      .shell { padding: 10px; }
      .architecture, .stats, .lanes { grid-template-columns: 1fr; }
      .preset-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>NanoCode Agent 工作台</h1>
      <div class="muted">ReAct + 轻量 Planner + Skill-like Tools，本地执行、可审查、可验证</div>
    </div>
    <div class="status" id="status">就绪</div>
  </header>

  <main class="shell">
    <section class="panel">
      <div class="panel-head">
        <h2>任务输入</h2>
        <span class="pill">workspace</span>
      </div>
      <div class="panel-body">
        <div class="field">
          <label for="task">编程任务</label>
          <textarea id="task">请检查 examples/calculator，确认 divide(a, b) 和对应 pytest 是否存在，必要时做最小修改，然后运行测试并总结 diff。</textarea>
        </div>
        <div class="preset-grid">
          <button class="secondary" data-preset="map">仓库理解</button>
          <button class="secondary" data-preset="test">测试验证</button>
          <button class="secondary" data-preset="patch">补丁编辑</button>
          <button class="secondary" data-preset="review">安全审查</button>
        </div>
        <div class="form-row">
          <div class="field">
            <label for="mode">授权模式</label>
            <select id="mode">
              <option value="review">审查模式 Review</option>
              <option value="trust">信任模式 Trust</option>
            </select>
          </div>
          <div class="field">
            <label for="maxSteps">最大步数</label>
            <input id="maxSteps" type="number" min="1" max="40" value="12" />
          </div>
        </div>
        <div class="run-row">
          <button id="runBtn">运行 Agent</button>
          <button class="ghost" id="clearBtn">清空结果</button>
        </div>
        <p class="muted">审查模式强调计划、观察和 diff；信任模式适合演示或熟悉工作区。Web UI 是展示层，底层仍是手写 agent loop 与本地工具。</p>
      </div>
    </section>

    <section>
      <div class="architecture">
        <div class="arch-item"><b>任务画像</b><span>识别任务类型、风险与授权模式</span></div>
        <div class="arch-item"><b>上下文选择</b><span>RepoMap、搜索排序、窗口式读文件</span></div>
        <div class="arch-item"><b>本地行动</b><span>patch 编辑、文件写入、安全命令</span></div>
        <div class="arch-item"><b>验证反思</b><span>测试信号、失败分类、继续修正</span></div>
      </div>
      <div class="panel">
        <div class="panel-head">
          <h2>执行过程可视化</h2>
          <span class="pill" id="runState">未运行</span>
        </div>
        <div class="panel-body">
          <div class="stats">
            <div class="stat"><b id="countSteps">0</b><span>步骤</span></div>
            <div class="stat"><b id="countPlans">0</b><span>计划</span></div>
            <div class="stat"><b id="countTools">0</b><span>工具</span></div>
            <div class="stat"><b id="countObs">0</b><span>观察</span></div>
            <div class="stat"><b id="countVerify">0</b><span>验证</span></div>
            <div class="stat"><b id="countErrors">0</b><span>风险</span></div>
          </div>
          <div class="lanes">
            <div class="lane"><div class="lane-title"><span>决策层</span><span>mode/profile/skill/plan</span></div><div class="lane-body" id="laneDecision"></div></div>
            <div class="lane"><div class="lane-title"><span>上下文层</span><span>repo_map/search/view</span></div><div class="lane-body" id="laneContext"></div></div>
            <div class="lane"><div class="lane-title"><span>行动层</span><span>patch/write/command</span></div><div class="lane-body" id="laneAction"></div></div>
            <div class="lane"><div class="lane-title"><span>反馈层</span><span>observation/reflect</span></div><div class="lane-body" id="laneFeedback"></div></div>
            <div class="lane"><div class="lane-title"><span>验证层</span><span>run_tests/verify</span></div><div class="lane-body" id="laneVerify"></div></div>
            <div class="lane"><div class="lane-title"><span>安全层</span><span>secret/sandbox/risk</span></div><div class="lane-body" id="laneSafety"></div></div>
          </div>
        </div>
      </div>
    </section>

    <aside class="panel">
      <div class="panel-head">
        <h2>结果与证据</h2>
        <span class="pill">auditable</span>
      </div>
      <div class="panel-body result-stack">
        <div class="metric"><b>最终回答</b><pre id="final">尚未运行。</pre></div>
        <div class="metric"><b>当前模式</b><pre id="modeOut">review</pre></div>
        <div class="metric"><b>Token 用量</b><pre id="usage">-</pre></div>
        <div class="metric"><b>Git diff 摘要</b><pre id="diff">-</pre></div>
        <div class="metric"><b>运行日志</b><pre id="logPath">-</pre></div>
      </div>
    </aside>
  </main>

<script>
const presets = {
  map: '请使用 repo_map 分析 nanocode 目录，说明 Agent Loop、Tool Registry、Memory、Verifier 如何协作。',
  test: '请检查 examples/calculator，确认 divide(a, b) 和对应 pytest 是否存在，然后运行相关测试。',
  patch: '请检查 examples/calculator，必要时用 apply_patch_file 做最小修改，然后运行 python -m pytest examples/calculator 并总结 diff。',
  review: '请审查当前仓库状态，使用 secret_scan 检查是否存在疑似密钥，并总结安全边界。'
};
const lanes = {
  decision: document.getElementById('laneDecision'),
  context: document.getElementById('laneContext'),
  action: document.getElementById('laneAction'),
  feedback: document.getElementById('laneFeedback'),
  verify: document.getElementById('laneVerify'),
  safety: document.getElementById('laneSafety')
};
const runBtn = document.getElementById('runBtn');
const clearBtn = document.getElementById('clearBtn');
const statusEl = document.getElementById('status');
const runStateEl = document.getElementById('runState');
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

function targetLane(event, type) {
  const lowered = event.toLowerCase();
  if (['mode', 'profile', 'skill', 'plan', 'planning'].includes(type)) return 'decision';
  if (type === 'verify' || lowered.includes('run_tests') || lowered.includes('pytest')) return 'verify';
  if (type === 'reflect' || type === 'observation') return 'feedback';
  if (lowered.includes('secret_scan') || lowered.includes('sandbox') || lowered.includes('blocked by safety')) return 'safety';
  if (lowered.includes('repo_map') || lowered.includes('search_code') || lowered.includes('view_file') || lowered.includes('list_symbols')) return 'context';
  if (lowered.includes('apply_patch_file') || lowered.includes('edit_file') || lowered.includes('write_file') || lowered.includes('run_command')) return 'action';
  if (type === 'error' || type === 'limit') return 'safety';
  return 'feedback';
}

function updateStats(events) {
  const types = events.map(classify);
  document.getElementById('countSteps').textContent = new Set(events.map(e => (e.match(/\[step (\d+)\]/) || [])[1]).filter(Boolean)).size;
  document.getElementById('countPlans').textContent = types.filter(t => t === 'plan').length;
  document.getElementById('countTools').textContent = types.filter(t => t === 'tool_call').length;
  document.getElementById('countObs').textContent = types.filter(t => t === 'observation').length;
  document.getElementById('countVerify').textContent = types.filter(t => t === 'verify').length;
  document.getElementById('countErrors').textContent = types.filter(t => t === 'error' || t === 'limit' || t === 'reflect').length;
}

function eventNode(event) {
  const type = classify(event);
  const node = document.createElement('div');
  node.className = `event ${type}`;
  node.innerHTML = `<div class="event-type">${labelFor(type)}</div><pre></pre>`;
  node.querySelector('pre').textContent = event;
  return node;
}

function labelFor(type) {
  const labels = {
    mode: '模式',
    profile: '任务画像',
    skill: 'Skill 选择',
    plan: '计划',
    planning: '下一步决策',
    tool_call: '工具调用',
    observation: '观察结果',
    reflect: '失败反思',
    verify: '测试验证',
    final: '最终输出',
    limit: '步数限制',
    error: '错误/风险'
  };
  return labels[type] || type;
}

function resetLanes() {
  Object.values(lanes).forEach(lane => { lane.innerHTML = '<div class="empty">等待事件...</div>'; });
  updateStats([]);
}

function renderEvents(events) {
  Object.values(lanes).forEach(lane => { lane.innerHTML = ''; });
  updateStats(events);
  for (const event of events) {
    const type = classify(event);
    lanes[targetLane(event, type)].appendChild(eventNode(event));
  }
  Object.values(lanes).forEach(lane => {
    if (!lane.children.length) lane.innerHTML = '<div class="empty">本次未触发</div>';
  });
}

document.querySelectorAll('[data-preset]').forEach(btn => {
  btn.addEventListener('click', () => { document.getElementById('task').value = presets[btn.dataset.preset]; });
});

clearBtn.addEventListener('click', () => {
  resetLanes();
  finalEl.textContent = '尚未运行。';
  usageEl.textContent = '-';
  diffEl.textContent = '-';
  logEl.textContent = '-';
  runStateEl.textContent = '未运行';
  statusEl.textContent = '就绪';
});

runBtn.addEventListener('click', async () => {
  runBtn.disabled = true;
  statusEl.textContent = '运行中...';
  runStateEl.textContent = '运行中';
  resetLanes();
  finalEl.textContent = '等待结果...';
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
    if (!response.ok || !data.ok) throw new Error(data.error || '运行失败');
    renderEvents(data.transcript);
    finalEl.textContent = data.final || '';
    modeOutEl.textContent = data.mode || '-';
    usageEl.textContent = data.usage_text || '-';
    diffEl.textContent = data.diff_summary || '-';
    logEl.textContent = data.log_path || '-';
    runStateEl.textContent = data.stopped_by_limit ? '达到步数上限' : `完成：${data.steps} 步`;
    statusEl.textContent = data.stopped_by_limit ? '达到步数上限' : '已完成';
  } catch (err) {
    statusEl.textContent = '运行错误';
    runStateEl.textContent = '错误';
    finalEl.textContent = String(err.message || err);
  } finally {
    runBtn.disabled = false;
  }
});

resetLanes();
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
