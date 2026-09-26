"""Public Streamable-HTTP transport for the same read-only tools.

Stateless JSON mode (no sessions to lose when the free instance sleeps), a Host
allow-list against DNS rebinding, a small request-body cap, and a per-client
token bucket. Audit lines go to stdout, which the host's log stream keeps.
"""

from __future__ import annotations

import os
import time

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from settlement_gap_mcp import audit
from settlement_gap_mcp.server import engine, mcp

MAX_BODY_BYTES = 16 * 1024
RATE_PER_MINUTE = int(os.getenv("SETTLEMENT_GAP_RATE_PER_MINUTE", "30"))


def allowed_hosts() -> list[str]:
    hosts = ["127.0.0.1:*", "localhost:*", "127.0.0.1", "localhost"]
    public = os.getenv("RENDER_EXTERNAL_HOSTNAME") or os.getenv("SETTLEMENT_GAP_PUBLIC_HOST")
    if public:
        hosts.append(public)
    return hosts


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_: Request) -> JSONResponse:
    meta = engine().build_metadata
    return JSONResponse({"status": "ok", "dataset_version": meta["dataset_version"], "as_of_date": meta["as_of_date"]})


def client_id(scope) -> str:
    # Behind one trusted proxy (Render), the rightmost X-Forwarded-For entry is
    # the address the proxy saw; anything to its left is caller-supplied.
    for name, value in scope.get("headers", []):
        if name == b"x-forwarded-for":
            return value.decode("latin-1").split(",")[-1].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimit:
    """Token bucket per client: RATE_PER_MINUTE requests, refilled continuously."""

    def __init__(self, app, per_minute: int = RATE_PER_MINUTE) -> None:
        self.app = app
        self.capacity = float(per_minute)
        self.refill = per_minute / 60.0
        self.buckets: dict[str, tuple[float, float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        tokens, last = self.buckets.get(key, (self.capacity, now))
        tokens = min(self.capacity, tokens + (now - last) * self.refill)
        if len(self.buckets) > 10_000:
            self.buckets.clear()
        if tokens < 1:
            self.buckets[key] = (tokens, now)
            return False
        self.buckets[key] = (tokens - 1, now)
        return True

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope["path"] == "/healthz":
            await self.app(scope, receive, send)
            return
        key = client_id(scope)
        if not self.allow(key):
            await PlainTextResponse("Rate limit exceeded; try again in a minute.", status_code=429)(scope, receive, send)
            return
        token = audit.client.set(audit.client_hash(key))
        try:
            await self.app(scope, receive, send)
        finally:
            audit.client.reset(token)


def create_app(per_minute: int = RATE_PER_MINUTE):
    app = mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
        max_request_body_size=MAX_BODY_BYTES,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts(),
            allowed_origins=["https://claude.ai", "http://127.0.0.1:*", "http://localhost:*"],
        ),
    )
    return RateLimit(app, per_minute)


def main() -> None:
    os.environ.setdefault("SETTLEMENT_GAP_AUDIT_SINK", "stdout")
    engine()  # build the snapshot before accepting traffic
    uvicorn.run(create_app(), host="0.0.0.0", port=int(os.getenv("PORT", "8000")), proxy_headers=False)


if __name__ == "__main__":
    main()
