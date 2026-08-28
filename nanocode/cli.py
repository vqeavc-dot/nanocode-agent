from __future__ import annotations

import argparse
import sys

from .agent import CodingAgent
from .config import load_config
from .llm import OpenAICompatibleLLM
from .tools import LocalTools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NanoCode Agent")
    parser.add_argument("task", help="Programming task for the agent")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum agent steps")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()
    if not config.api_key:
        print("NANOCODE_API_KEY is not set. Copy .env.example to .env and fill it.", file=sys.stderr)
        return 2

    tools = LocalTools(config.workspace if args.workspace == "." else config.workspace / args.workspace)
    model = OpenAICompatibleLLM(config.api_key, config.base_url, config.model)
    agent = CodingAgent(model=model, tools=tools, max_steps=args.max_steps or config.max_steps)
    result = agent.run(args.task)
    print(result.final)
    return 1 if result.stopped_by_limit else 0


if __name__ == "__main__":
    raise SystemExit(main())

