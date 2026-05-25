"""Database connection utility for Payments Analytics SQL.

This module provides a single function to establish a connection to the
PostgreSQL database using credentials defined in environment variables.
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()


def get_connection():
    """Establishes and returns a psycopg2 connection to PostgreSQL.

    Raises:
        psycopg2.OperationalError: If connection cannot be established.
    """
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "payments_analytics"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD")
    )
