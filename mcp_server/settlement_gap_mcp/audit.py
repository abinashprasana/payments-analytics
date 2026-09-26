"""Append-only JSON Lines audit trail: one line per tool call, allowed or refused."""

from __future__ import annotations

import contextvars
import datetime as dt
import hashlib
import json
import os
import secrets
import sys
import threading
from pathlib import Path
from typing import Any

DEFAULT_LOG = Path(__file__).resolve().parents[1] / "logs" / "audit.jsonl"
# Only these argument names are ever written. Anything else is recorded by name
# with its value withheld, so a stray token or pasted secret never lands on disk.
LOGGED_ARGS = frozenset(
    {"query_id", "params", "payment_id", "scenario", "as_of_date", "limit"}
)
MAX_VALUE_CHARS = 200

_lock = threading.Lock()
# Set per HTTP request by the transport; stays None over stdio.
client: contextvars.ContextVar[str | None] = contextvars.ContextVar("client", default=None)
_SALT = os.getenv("SETTLEMENT_GAP_AUDIT_SALT") or secrets.token_hex(16)


def client_hash(address: str) -> str:
    """Salted, truncated hash: enough to spot one noisy caller, useless for identifying anyone."""
    return hashlib.sha256((_SALT + address).encode()).hexdigest()[:12]


def log_path() -> Path:
    return Path(os.getenv("SETTLEMENT_GAP_AUDIT_LOG") or DEFAULT_LOG)


def _clip(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k)[:MAX_VALUE_CHARS]: _clip(v) for k, v in value.items()}
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:MAX_VALUE_CHARS]


def record(
    tool: str,
    arguments: dict[str, Any],
    *,
    outcome: str,
    row_count: int | None = None,
    reason: str | None = None,
) -> None:
    caller = client.get()
    entry = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "transport": "http" if caller else "stdio",
        "client": caller,
        "tool": str(tool)[:MAX_VALUE_CHARS],
        "params": {
            key: _clip(value) if key in LOGGED_ARGS else "<withheld>"
            for key, value in arguments.items()
        },
        "row_count": row_count,
        "outcome": outcome,
        "reason": reason[:MAX_VALUE_CHARS] if reason else None,
    }
    line = json.dumps(entry, default=str)
    if os.getenv("SETTLEMENT_GAP_AUDIT_SINK") == "stdout":
        # HTTP mode only: stdout is the host's log stream there, not a protocol channel.
        with _lock:
            print("audit " + line, file=sys.stdout, flush=True)
        return
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock, path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
