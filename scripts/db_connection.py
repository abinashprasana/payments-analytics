"""Database connection factories for application reads and bulk loading."""

from __future__ import annotations

import os
from typing import Any

import psycopg2
from dotenv import load_dotenv
from sqlalchemy import URL, Engine, create_engine

load_dotenv()


def _database_settings() -> dict[str, Any]:
    """Return one normalized set of connection settings for both clients."""

    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "payments_analytics"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD"),
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "3")),
    }


def get_connection():
    """Return a raw psycopg2 connection for COPY-based bulk loading.

    Callers own the returned connection and must close it. Dashboard and
    Pandas reads should use :func:`get_read_engine` instead.
    """

    return psycopg2.connect(**_database_settings())


def get_read_engine() -> Engine:
    """Return a caller-owned SQLAlchemy engine for Pandas/database reads."""

    settings = _database_settings()
    url = URL.create(
        "postgresql+psycopg2",
        username=settings["user"],
        password=settings["password"],
        host=settings["host"],
        port=settings["port"],
        database=settings["database"],
    )
    return create_engine(
        url,
        connect_args={"connect_timeout": settings["connect_timeout"]},
        pool_pre_ping=True,
    )
