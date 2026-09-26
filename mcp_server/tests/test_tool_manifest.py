"""Tool definitions are what the model reads, so they are pinned like an API.

Any change to a tool's name, description, input schema, or annotations fails here
until tests/tool_manifest.json is regenerated on purpose:

    UPDATE_TOOL_MANIFEST=1 uv run pytest tests/test_tool_manifest.py
"""

import json
import os
from pathlib import Path

import anyio
from mcp import Client

from settlement_gap_mcp import server

MANIFEST = Path(__file__).with_name("tool_manifest.json")


def current_manifest() -> list[dict]:
    async def go():
        async with Client(server.mcp) as client:
            return (await client.list_tools()).tools

    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
            "annotations": tool.annotations.model_dump(exclude_none=True, by_alias=True),
        }
        for tool in sorted(anyio.run(go), key=lambda t: t.name)
    ]


def test_tool_definitions_match_the_pinned_manifest():
    current = current_manifest()
    if os.getenv("UPDATE_TOOL_MANIFEST") == "1":
        MANIFEST.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    assert json.loads(MANIFEST.read_text(encoding="utf-8")) == current
