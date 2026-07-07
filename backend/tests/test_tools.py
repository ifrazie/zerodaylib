"""Tests for Zero Day Librarian tool contracts against the seeded zdl_db.

Covers the gateway tools:
  - policy_evaluate_action
  - finding_create_or_update
  - timeline_append_event
  - memory_search_similar
"""
import pytest

from backend.tools.timeline import timeline_append_event
from backend.tools.policy import policy_evaluate_action
from backend.tools.finding import finding_create_or_update
from backend.tools.memory import memory_search_similar


# --- policy_evaluate_action ---------------------------------------------------

def test_policy_internet_facing_critical_manual_review(dev_conn):
    decision = policy_evaluate_action(
        action="approve_remediation",
        fact_set={"exposure": "internet-facing", "severity": "CRITICAL"},
    )
    assert decision["decision"] == "manual_review"
    assert decision["matched_rule_name"] == "manual-review-critical-internet"
    assert decision["enabled_many"] >= 3
    assert decision["evaluated"] >= 1


def test_policy_tier0_manual_review(dev_conn):
    decision = policy_evaluate_action("approve_remediation", fact_set={"tier": "tier-0"})
    assert decision["decision"] == "manual_review"
    assert decision["matched_rule_name"] == "manual-review-tier0"


def test_policy_internal_noncritical_allow(dev_conn):
    decision = policy_evaluate_action(
        "approve_remediation", fact_set={"exposure": "internal-vpc", "severity": "HIGH"}
    )
    assert decision["decision"] == "allow"
    assert decision["matched_rule_name"] == "allow-noncrit-internal"


def test_policy_default_deny_no_match(dev_conn):
    decision = policy_evaluate_action("approve_remediation", fact_set={})
    assert decision["decision"] == "deny"
    assert decision["matched_rule_id"] is None


def test_policy_most_restrictive_wins(dev_conn):
    # Matches BOTH manual-review-critical-internet AND manual-review-tier0;
    # both are manual_review, so result must be manual_review (not allow).
    decision = policy_evaluate_action(
        "approve_remediation",
        fact_set={"exposure": "internet-facing", "severity": "CRITICAL", "tier": "tier-0"},
    )
    assert decision["decision"] == "manual_review"
    assert decision["evaluated"] >= 2


# --- finding_create_or_update -------------------------------------------------

def test_finding_upsert_idempotent(dev_conn, cleanup_test_rows):
    key = "test-CVE-2024-7169-upsert"
    r1 = finding_create_or_update(key, cve_id="CVE-2024-7169", status="new")
    assert r1["success"] is True
    fid = r1["finding_id"]

    # same key -> UPDATE existing row, finding_id stable
    r2 = finding_create_or_update(key, status="investigating")
    assert r2["success"] is True
    assert r2["finding_id"] == fid


def test_finding_partial_update_preserves_fields(dev_conn, cleanup_test_rows):
    key = "test-partial-update"
    finding_create_or_update(key, cve_id="CVE-2024-7169", status="new", owner_team="platform-infra")
    # Update only status; cve_id and owner_team must be preserved (COALESCE).
    finding_create_or_update(key, status="triaged")
    row = dev_conn.execute(
        "SELECT cve_id, status, owner_team FROM findings WHERE idempotency_key = %s", (key,)
    ).fetchone()
    assert row == ("CVE-2024-7169", "triaged", "platform-infra")


# --- timeline_append_event ----------------------------------------------------

def test_timeline_append_writes_row(dev_conn, cleanup_test_rows):
    # anchor to the seeded finding
    seeded_fid = dev_conn.execute(
        "SELECT finding_id FROM findings WHERE idempotency_key = %s",
        ("ingest-CVE-2024-7169-api-prodcolasld-1",),
    ).fetchone()[0]

    result = timeline_append_event(
        finding_id=str(seeded_fid),
        actor_type="test",
        actor_id="pytest",
        action="test_append",
        target_table="findings",
        target_id=str(seeded_fid),
        payload_json={"test": "harness"},
    )
    assert result["success"] is True
    eid = result["event_id"]

    count = dev_conn.execute(
        "SELECT count(*) FROM action_timeline WHERE event_id = %s", (eid,)
    ).fetchone()[0]
    assert count == 1


# --- memory_search_similar ----------------------------------------------------

def test_memory_vector_knn(dev_conn, require_embedded_memory):
    # Seed has 3 memory rows, each embedded with a real Titan vector by
    # backend/db/seed_embed.py. We don't assert on specific distance values
    # (those depend on the live embedding content) — only on correct KNN
    # mechanics: success, count, and ascending distance order.
    result = memory_search_similar(
        query_vector=[0.11] * 1024,
        limit=3,
    )
    assert result["success"] is True
    assert len(result["matches"]) >= 3
    assert result["limit"] == 3
    assert result["total_unfiltered"] >= 3
    # Results must be sorted by ascending distance (closest first).
    distances = [m["distance"] for m in result["matches"]]
    assert distances == sorted(distances)


def test_memory_filtered_knn(dev_conn, require_embedded_memory):
    result = memory_search_similar(
        query_vector=[0.11] * 1024,
        limit=2,
        filters={"cve_id": "CVE-2023-5678"},  # OpenSSL prior incident
    )
    assert result["success"] is True
    assert len(result["matches"]) == 1  # only one match for that CVE
    assert result["matches"][0]["incident_jsonb"]["cve_id"] == "CVE-2023-5678"
