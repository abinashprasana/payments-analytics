"""Minimal tool calling loop: one question in, the model's tool calls and answer out.

Tool schemas come from ``mcp_server/tests/tool_manifest.json``, the pinned copy
the manifest test guards, so the model sees exactly what a real client sees.
Every call runs through the real server (``settlement_gap_mcp.server.mcp``)
over an in-process MCP client, which exercises ``AuditedServer.call_tool``,
argument refusal, and the audit log. Nothing is mocked on the tool side.

The model side is either Groq's OpenAI compatible endpoint (``GroqModel``,
key read from ``GROQ_API_KEY`` only) or ``ScriptedModel`` for offline dry runs.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "mcp_server" / "tests" / "tool_manifest.json"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_TURNS = 4
MAX_RESULT_CHARS = 8_000
for path in (PROJECT_ROOT, PROJECT_ROOT / "mcp_server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


class BudgetExhausted(RuntimeError):
    """Raised before a model request that would exceed --max-requests."""


class Budget:
    """Caps live model requests and paces them to stay under the rate limit."""

    def __init__(self, max_requests: int, pace_seconds: float) -> None:
        self.max_requests = max_requests
        self.pace_seconds = pace_seconds
        self.used = 0
        self._last = 0.0

    def take(self) -> None:
        if self.used >= self.max_requests:
            raise BudgetExhausted(f"--max-requests {self.max_requests} reached")
        wait = self._last + self.pace_seconds - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        self.used += 1


def load_tools() -> list[dict[str, Any]]:
    """The pinned MCP tool schemas in OpenAI function calling form."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in manifest
    ]


def system_prompt() -> str:
    from settlement_gap_mcp import server

    return (
        f"{server.mcp.instructions}\n\n"
        "Answer the user's question using the available tools. "
        "If a request cannot be answered with them, say so."
    )


class GroqModel:
    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = 0.0) -> None:
        from openai import OpenAI

        key = os.environ.get("GROQ_API_KEY")
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set in the environment")
        self.model = model
        self.temperature = temperature
        self._client = OpenAI(api_key=key, base_url=GROQ_BASE_URL, max_retries=5)

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        response = self._client.chat.completions.create(
            model=self.model, messages=messages, tools=tools,
            tool_choice="auto", temperature=self.temperature,
        )
        return response.choices[0].message


def _tool_call(index: int, name: str, arguments: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"call_{index}", type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


class ScriptedModel:
    """Replays planned turns. Each turn is a list of (tool, arguments) or a final string."""

    model = "scripted"

    def __init__(self, turns: list[Any]) -> None:
        self._turns = list(turns)
        self._count = 0

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Any:
        turn = self._turns.pop(0) if self._turns else "Done."
        if isinstance(turn, str):
            return SimpleNamespace(content=turn, tool_calls=None)
        calls = []
        for name, arguments in turn:
            self._count += 1
            calls.append(_tool_call(self._count, name, arguments))
        return SimpleNamespace(content="", tool_calls=calls)


def _result_text(result: Any) -> str:
    if result.is_error or result.structured_content is None:
        return " ".join(getattr(block, "text", "") for block in result.content)
    text = json.dumps(result.structured_content, default=str)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + ' ... [truncated by the eval harness]"'
    return text


async def run_trial(model: Any, question: str, budget: Budget | None,
                    tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Ask one question; return every tool call with its server outcome and the final text."""
    from mcp import Client
    from settlement_gap_mcp import server

    tools = tools or load_tools()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": question},
    ]
    calls: list[dict[str, Any]] = []
    final_text = ""
    requests = 0
    async with Client(server.mcp) as client:
        for _ in range(MAX_TURNS):
            if budget is not None:
                budget.take()
            requests += 1
            message = model.complete(messages, tools)
            tool_calls = list(message.tool_calls or [])
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                **({"tool_calls": [
                    {"id": c.id, "type": "function",
                     "function": {"name": c.function.name, "arguments": c.function.arguments}}
                    for c in tool_calls
                ]} if tool_calls else {}),
            })
            if not tool_calls:
                final_text = message.content or ""
                break
            for tool_call in tool_calls:
                name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                    if not isinstance(arguments, dict):
                        raise ValueError("arguments are not an object")
                except ValueError as exc:
                    calls.append({"tool": name, "arguments": None, "outcome": "malformed",
                                  "detail": str(exc)})
                    content = f"Malformed tool arguments: {exc}"
                else:
                    result = await client.call_tool(name, arguments)
                    content = _result_text(result)
                    calls.append({
                        "tool": name, "arguments": arguments,
                        "outcome": "refused" if result.is_error else "allowed",
                        "detail": content[:300] if result.is_error else None,
                    })
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": content})
        else:
            final_text = final_text or "[stopped after the turn limit]"
    return {"calls": calls, "final_text": final_text, "requests": requests}
