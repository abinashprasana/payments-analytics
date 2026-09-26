import json
from pathlib import Path

import anyio
import pytest
from mcp import Client

from scripts.analytics_engine import QUERY_PARAMETERS
from settlement_gap_mcp import server


@pytest.fixture(scope="session", autouse=True)
def warm_engine():
    server.engine()  # build the in-memory snapshot once (~3 s)


@pytest.fixture(autouse=True)
def audit_log(tmp_path, monkeypatch):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("SETTLEMENT_GAP_AUDIT_LOG", str(path))
    return path


def call(name, arguments=None):
    async def go():
        async with Client(server.mcp) as client:
            return await client.call_tool(name, arguments or {})

    return anyio.run(go)


def lines(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def text(result):
    return " ".join(getattr(block, "text", "") for block in result.content)


def test_list_queries_returns_the_registry(audit_log):
    result = call("list_queries")
    assert not result.is_error
    ids = {q["id"] for q in result.structured_content["queries"]}
    assert ids == set(QUERY_PARAMETERS) - set(server.UNAVAILABLE)
    trace = next(q for q in result.structured_content["queries"] if q["id"] == "payment_trace")
    assert trace["required"] == ["payment_id", "scenario"]
    assert lines(audit_log)[-1]["outcome"] == "allowed"


def test_registry_metadata_cannot_drift():
    assert set(server.QUERY_INFO) | set(server.UNAVAILABLE) == set(QUERY_PARAMETERS)


def test_run_query_returns_rows_and_columns(audit_log):
    result = call("run_query", {"query_id": "exception_queue", "params": {"scenario": "missing_retail_cad"}})
    data = result.structured_content
    assert not result.is_error
    assert data["total_rows"] == 48 and data["row_count"] == 48
    assert "payment_id" in data["columns"] and len(data["rows"][0]) == len(data["columns"])
    assert lines(audit_log)[-1] == {**lines(audit_log)[-1], "outcome": "allowed", "row_count": 48}


def test_run_query_caps_rows():
    data = call("run_query", {"query_id": "exception_queue", "params": {"scenario": "missing_retail_cad"}, "limit": 10}).structured_content
    assert data["row_count"] == 10 and data["total_rows"] == 48 and data["truncated"] is True
    assert call("run_query", {"query_id": "exception_queue", "params": {"scenario": "normal"}, "limit": 500}).is_error


@pytest.mark.parametrize(
    "arguments",
    [
        {"query_id": "drop_everything"},
        {"query_id": "exception_scoring"},
        {"query_id": "close_summary", "params": {"scenario": "normal", "sql": "DROP TABLE settlements"}},
        {"query_id": "close_summary", "params": {"scenario": "normal'; DROP TABLE settlements; --"}},
        {"query_id": "close_summary", "params": {"scenario": "normal", "currency": "USD"}},
        {"query_id": "close_summary", "params": {"scenario": "normal", "start_date": "yesterday"}},
        {"query_id": "payment_trace", "params": {"scenario": "normal", "payment_id": -1}},
        {"query_id": "close_summary"},
        {"query_id": "close_summary", "params": {"scenario": "normal"}, "sql": "SELECT * FROM settlements"},
    ],
)
def test_bad_requests_are_refused_and_audited(audit_log, arguments):
    result = call("run_query", arguments)
    assert result.is_error
    entry = lines(audit_log)[-1]
    assert entry["outcome"] == "refused" and entry["row_count"] is None


def test_extra_argument_value_is_not_logged(audit_log):
    call("run_query", {"query_id": "catalog_metrics", "api_key": "sk-secret"})
    entry = lines(audit_log)[-1]
    assert entry["outcome"] == "refused"
    assert entry["params"]["api_key"] == "<withheld>"
    assert "sk-secret" not in audit_log.read_text(encoding="utf-8")


def test_unknown_tool_is_refused_and_audited(audit_log):
    result = call("execute_sql", {"sql": "DELETE FROM settlements"})
    assert result.is_error
    assert lines(audit_log)[-1]["outcome"] == "refused"


def test_trace_payment_that_never_settles(audit_log):
    result = call("trace_payment", {"payment_id": 240})
    data = result.structured_content
    assert not result.is_error
    assert data["scenario"] == "missing_retail_cad"
    assert data["primary_reason"] == "missing" and data["exception_reasons"] == ["missing"]
    assert data["days_overdue"] == 35
    assert data["settlement"] is None
    raised = {f["rule"] for f in data["flags"] if f["raised"]}
    assert raised == {"missing"}
    assert lines(audit_log)[-1]["outcome"] == "allowed"


def test_trace_payment_other_scenarios():
    fee = call("trace_payment", {"payment_id": 2}).structured_content
    assert fee["primary_reason"] == "fee_mismatch" and fee["settlement"]["fee_delta_minor_units"] != 0
    late = call("trace_payment", {"payment_id": 12, "as_of_date": "2025-01-10"}).structured_content
    assert late["scenario"] == "delayed_travel_gbp" and late["primary_reason"] == "late"


@pytest.mark.parametrize(
    "arguments",
    [{"payment_id": 99999999}, {"payment_id": 0}, {"payment_id": 240, "scenario": "nope"}, {"payment_id": 240, "as_of_date": "soon"}],
)
def test_trace_payment_refusals(audit_log, arguments):
    assert call("trace_payment", arguments).is_error
    assert lines(audit_log)[-1]["outcome"] == "refused"


def test_every_call_writes_exactly_one_audit_line(audit_log):
    call("list_queries")
    call("run_query", {"query_id": "nope"})
    call("trace_payment", {"payment_id": 240})
    assert [e["outcome"] for e in lines(audit_log)] == ["allowed", "refused", "allowed"]


def test_rules_match_the_sql_model():
    sql = (server.REPO_ROOT / server.RULE_SOURCE).read_text(encoding="utf-8")
    for rule, (column, _) in server.RULES.items():
        assert f"'{rule}'" in sql and f"AS {column}" in sql


def test_tools_are_declared_read_only():
    async def go():
        async with Client(server.mcp) as client:
            return (await client.list_tools()).tools

    tools = anyio.run(go)
    assert {t.name for t in tools} == {"list_queries", "run_query", "trace_payment"}
    assert all(t.annotations.read_only_hint for t in tools)
