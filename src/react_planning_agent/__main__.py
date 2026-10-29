"""Local document and arithmetic agent with bounded tool use."""

from __future__ import annotations

import argparse
import ast
import json
import operator
from pathlib import Path

from .engine import ReActAgent
from .llm import OpenAICompatibleLLM
from .web import serve

WEB_ACTIONS = {"run": [("task", "Task", "textarea", True)]}
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def calculate(expression: str) -> str:
    if len(expression) > 200:
        raise ValueError("expression too long")
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 30:
        raise ValueError("expression too complex")

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            value = -evaluate(node.operand)
        elif isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            value = OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))
        else:
            raise ValueError("only arithmetic is allowed")
        if abs(value) > 1e12:
            raise ValueError("result too large")
        return value

    return str(evaluate(tree))


def _inside(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if path == root or root not in path.parents:
        raise ValueError("file is outside configured root")
    return path


def tools_for(root: Path):
    root = root.resolve()

    def read_file(name: str) -> str:
        path = _inside(root, name)
        if not path.is_file() or path.stat().st_size > 100_000:
            raise ValueError("file missing or over 100 KB")
        return path.read_text(encoding="utf-8")

    def search_files(query: str) -> str:
        if not query.strip() or len(query) > 100:
            raise ValueError("query must be 1 to 100 characters")
        matches = []
        scanned = 0
        for path in root.rglob("*"):
            if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
                continue
            if not path.is_file() or path.stat().st_size > 100_000:
                continue
            scanned += 1
            if scanned > 1000:
                break
            try:
                resolved = _inside(root, str(path.relative_to(root)))
                text = resolved.read_text(encoding="utf-8")
            except (UnicodeError, OSError, ValueError):
                continue
            if query.lower() in text.lower():
                matches.append(str(path.relative_to(root)))
                if len(matches) == 10:
                    break
        return json.dumps(matches)

    return {
        "calculate": calculate,
        "read_file": read_file,
        "search_files": search_files,
    }


def execute(action: str, values: dict, *, root: Path, max_steps: int) -> object:
    if action != "run":
        raise ValueError("unknown action")
    result = ReActAgent(
        OpenAICompatibleLLM.from_env(), tools_for(root), max_steps=max_steps
    ).run(values["task"])
    return {
        "answer": result.answer,
        "stopped_reason": result.stopped_reason,
        "steps": [step.__dict__ for step in result.steps],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bounded local file and arithmetic agent"
    )
    parser.add_argument("--root", default=".", help="Allowed document directory")
    parser.add_argument("--max-steps", type=int, default=5)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("task")
    browser = commands.add_parser("serve")
    browser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    if args.command == "serve":
        serve(
            "ReAct Planning Agent",
            WEB_ACTIONS,
            lambda action, values: execute(
                action, values, root=Path(args.root), max_steps=args.max_steps
            ),
            port=args.port,
        )
    else:
        print(
            json.dumps(
                execute(
                    args.command,
                    vars(args),
                    root=Path(args.root),
                    max_steps=args.max_steps,
                ),
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
