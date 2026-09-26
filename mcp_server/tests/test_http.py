import json
import socket
import threading
import time

import anyio
import httpx2
import pytest
import uvicorn
from mcp import Client

from settlement_gap_mcp import server
from settlement_gap_mcp.http import RateLimit, create_app


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def base_url():
    server.engine()
    port = _free_port()
    uv = uvicorn.Server(uvicorn.Config(create_app(per_minute=1000), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=uv.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 20
    while not uv.started:
        assert time.monotonic() < deadline, "server did not start"
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    uv.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(autouse=True)
def audit_log(tmp_path, monkeypatch):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("SETTLEMENT_GAP_AUDIT_LOG", str(path))
    return path


def test_healthz(base_url):
    body = httpx2.get(base_url + "/healthz").json()
    assert body["status"] == "ok" and body["dataset_version"].startswith("settlement-gap")


def test_trace_over_http_is_audited_with_hashed_client(base_url, audit_log):
    async def go():
        async with Client(base_url + "/mcp") as client:
            return await client.call_tool("trace_payment", {"payment_id": 240})

    result = anyio.run(go)
    assert result.structured_content["primary_reason"] == "missing"
    entry = json.loads(audit_log.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["transport"] == "http" and entry["outcome"] == "allowed"
    assert entry["client"] and "127.0.0.1" not in audit_log.read_text(encoding="utf-8")


def _rpc(base_url, body, **headers):
    return httpx2.post(
        base_url + "/mcp",
        content=body,
        headers={"content-type": "application/json", "accept": "application/json, text/event-stream", **headers},
    )


def test_foreign_host_is_rejected(base_url):
    response = _rpc(base_url, b"{}", host="evil.example")
    assert response.status_code == 421


def test_foreign_origin_is_rejected(base_url):
    response = _rpc(base_url, b"{}", origin="https://evil.example")
    assert response.status_code == 403


def test_oversized_body_is_rejected(base_url):
    response = _rpc(base_url, b"{" + b" " * (32 * 1024) + b"}")
    assert response.status_code == 413


def test_rate_limit_bucket():
    limiter = RateLimit(app=None, per_minute=3)
    assert [limiter.allow("a") for _ in range(4)] == [True, True, True, False]
    assert limiter.allow("b")


def test_stdout_sink_for_hosted_mode(monkeypatch, capsys, tmp_path):
    from settlement_gap_mcp import audit

    monkeypatch.setenv("SETTLEMENT_GAP_AUDIT_SINK", "stdout")
    audit.record("list_queries", {}, outcome="allowed", row_count=9)
    out = capsys.readouterr().out
    assert out.startswith("audit ") and json.loads(out[6:])["row_count"] == 9
    assert not (tmp_path / "audit.jsonl").exists()
