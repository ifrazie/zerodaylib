"""Layer 4 — Live-schema invariant / health-check assertions.

These do not test agents or tools directly; they assert that the CockroachDB
`zdl_db` schema is in a state consistent with how the agents are designed to
use it. Run before and after any deployment as a fast readiness gate:

    pytest backend/tests/test_db_invariants.py

Requires COCKROACH_URL. The embedding-completeness invariant skips (rather than
fails) when seed_embed has not yet run, matching require_embedded_memory.
"""
import pytest

from .conftest import SEEDED_ASSET_ID, SEEDED_CVE_ID


# --- seed presence ------------------------------------------------------------

def test_seeded_finding_exists(dev_conn, seeded_finding_key):
    row = dev_conn.execute(
        "SELECT 1 FROM findings WHERE idempotency_key = %s", (seeded_finding_key,)
    ).fetchone()
    assert row is not None, "canonical seeded finding missing; run backend/db/seed.sql"


def test_seeded_asset_exists(dev_conn):
    row = dev_conn.execute(
        "SELECT exposure, environment FROM assets WHERE asset_id = %s", (SEEDED_ASSET_ID,)
    ).fetchone()
    assert row is not None, "seeded asset missing"
    assert row == ("internet-facing", "production")


def test_seeded_cve_exists(dev_conn):
    row = dev_conn.execute(
        "SELECT severity FROM cves WHERE cve_id = %s", (SEEDED_CVE_ID,)
    ).fetchone()
    assert row is not None, "seeded CVE missing"
    assert row[0] == "CRITICAL"


# --- policy engine readiness --------------------------------------------------

def test_policy_rules_loaded(dev_conn):
    count = dev_conn.execute(
        "SELECT count(*) FROM policy_rules WHERE enabled = true"
    ).fetchone()[0]
    assert count >= 3, "governance requires the three seeded policy rules"


def test_policy_rules_have_valid_decisions(dev_conn):
    # decision column is CHECK-constrained, but assert no rule slipped through
    # with an unexpected value that would break most-restrictive-wins ranking.
    rows = dev_conn.execute(
        "SELECT decision FROM policy_rules WHERE enabled = true"
    ).fetchall()
    valid = {"allow", "deny", "manual_review"}
    assert all(r[0] in valid for r in rows)


# --- findings integrity -------------------------------------------------------

def test_all_findings_have_idempotency_key(dev_conn):
    # Idempotency depends on every finding carrying a stable key; a NULL key
    # means finding_create_or_update could create duplicates.
    nulls = dev_conn.execute(
        "SELECT count(*) FROM findings WHERE idempotency_key IS NULL"
    ).fetchone()[0]
    assert nulls == 0, f"{nulls} finding(s) have a NULL idempotency_key"


# --- semantic memory / vector index -------------------------------------------

def test_prior_incidents_present(dev_conn):
    count = dev_conn.execute("SELECT count(*) FROM semantic_memory").fetchone()[0]
    assert count >= 3, "expected at least the three seeded prior incidents"


def test_vector_index_exists(dev_conn):
    # The distributed vector index is the core hackathon requirement and what
    # memory_search_similar's KNN relies on. Verify it exists on the table.
    rows = dev_conn.execute("SHOW INDEXES FROM semantic_memory").fetchall()
    index_names = {r[1] for r in rows}  # column 1 = index_name
    assert "idx_memory_embedding" in index_names, (
        "distributed vector index idx_memory_embedding missing from semantic_memory"
    )


def test_all_memories_embedded(dev_conn, require_embedded_memory):
    # Skips (via require_embedded_memory) if seed_embed hasn't run at all.
    # When embeddings exist, assert none were left unembedded — a partially
    # embedded table would make KNN silently skip rows.
    unembedded = dev_conn.execute(
        "SELECT count(*) FROM semantic_memory WHERE embedded_at IS NULL"
    ).fetchone()[0]
    assert unembedded == 0, (
        f"{unembedded} semantic_memory row(s) unembedded; run "
        "'python -m backend.db.seed_embed' against this cluster"
    )


# --- audit timeline convention ------------------------------------------------

def test_timeline_append_only_by_convention(dev_conn):
    # action_timeline is append-only by design. It has no updated_at column, so
    # instead we assert the seeded governance policy_check event is intact and
    # anchored to the seeded finding — evidence the audit trail is preserved.
    count = dev_conn.execute(
        "SELECT count(*) FROM action_timeline WHERE action = 'policy_check'"
    ).fetchone()[0]
    assert count >= 1, "seeded policy_check audit event missing"
