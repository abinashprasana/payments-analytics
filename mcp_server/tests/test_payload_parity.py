"""The case study replays one trace_payment call. This keeps that replay honest:
the committed site payload must match what the real tool returns today."""

import json

import anyio
from mcp import Client

from settlement_gap_mcp import server

PAYLOAD = server.REPO_ROOT / "site" / "src" / "data" / "project-data.json"


def test_site_replay_matches_the_live_tool():
    ask = json.loads(PAYLOAD.read_text(encoding="utf-8"))["ask"]
    assert ask["call"]["tool"] == "trace_payment"

    async def go():
        async with Client(server.mcp) as client:
            return await client.call_tool("trace_payment", ask["call"]["arguments"])

    result = anyio.run(go)
    assert not result.is_error
    live = result.structured_content
    settlement = live["settlement"] or {}
    assert ask["result"] == {
        "scenario": live["scenario"],
        "as_of_date": live["as_of_date"][:10],
        "primary_reason": live["primary_reason"],
        "exception_reasons": live["exception_reasons"],
        "days_overdue": live["days_overdue"],
        "settlement_status": settlement.get("settlement_status"),
        "fee_delta_minor_units": settlement.get("fee_delta_minor_units"),
    }
    assert {t["name"] for t in ask["tools"]} == {"list_queries", "run_query", "trace_payment"}
