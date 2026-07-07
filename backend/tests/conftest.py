"""Shared pytest fixtures for backend tool tests.

These tests run against the live CockroachDB Cloud `zdl_db` seeded via
backend/db/schema.sql + backend/db/seed.sql. Set COCKROACH_URL in the
environment (loaded from agentcore/.env.local) before running:

    export $(grep '^COCKROACH_URL=' agentcore/.env.local | sed 's/"//g')
    python -m pytest backend/tests -v

Vector-search tests additionally require semantic_memory rows to carry real
Titan embeddings. Run `python -m backend.db.seed_embed` once against the
live cluster before running those tests (scripts/dev.sh and scripts/dev.ps1
do this automatically for local dev).
"""
import os
import pytest

from backend.tools.db import get_psycopg_conn


@pytest.fixture(scope="session")
def dev_conn():
    """A session-scoped psycopg connection to the seeded zdl_db."""
    if not os.environ.get("COCKROACH_URL"):
        pytest.skip("COCKROACH_URL not set; skipping DB-backed tool tests")
    conn = get_psycopg_conn()
    yield conn
    conn.close()


@pytest.fixture()
def require_embedded_memory(dev_conn):
    """Skip vector-search tests if semantic_memory has no real embeddings yet.

    Guards against the case where schema/seed have been applied but
    `python -m backend.db.seed_embed` has not been run against this cluster.
    """
    count = dev_conn.execute(
        "SELECT count(*) FROM semantic_memory WHERE embedded_at IS NOT NULL"
    ).fetchone()[0]
    if count == 0:
        pytest.skip(
            "No embedded semantic_memory rows; run "
            "'python -m backend.db.seed_embed' against this cluster first."
        )


@pytest.fixture()
def cleanup_test_rows(dev_conn):
    """Remove rows created by tests (idempotency keys / actors prefixed 'test-')."""
    yield
    dev_conn.execute("DELETE FROM action_timeline WHERE actor_id = 'pytest'")
    dev_conn.execute("DELETE FROM findings WHERE idempotency_key LIKE 'test-%'")
    dev_conn.execute("DELETE FROM semantic_memory WHERE idempotency_key LIKE 'test-%'")
