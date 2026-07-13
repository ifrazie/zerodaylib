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
from backend.tools.memory_store import memory_store, _derive_idempotency_key


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
        ("ingest-CVE-2024-7169-phi-gateway-prod-01",),
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
    # Seed has 5 memory rows, each embedded with a real Titan vector by
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


def test_memory_similarity_score_present_and_descending(dev_conn, require_embedded_memory):
    # similarity_score = 1/(1+distance) is computed in SQL; since results are
    # ordered by ascending distance, scores must be non-increasing.
    result = memory_search_similar(query_vector=[0.11] * 1024, limit=3)
    assert result["success"] is True
    scores = [m["similarity_score"] for m in result["matches"]]
    assert len(scores) >= 3
    assert all(0.0 < s <= 1.0 for s in scores)
    assert scores == sorted(scores, reverse=True)


def test_memory_similarity_threshold_filters_low_scores(dev_conn, require_embedded_memory):
    # An unreachable threshold (0.99) must exclude all real-data matches,
    # while the default threshold (0) returns the full seeded set.
    unfiltered = memory_search_similar(query_vector=[0.11] * 1024, limit=10)
    thresholded = memory_search_similar(
        query_vector=[0.11] * 1024, limit=10, similarity_threshold=0.99
    )
    assert unfiltered["success"] is True and thresholded["success"] is True
    assert len(thresholded["matches"]) == 0
    assert len(unfiltered["matches"]) >= 3


def test_memory_filtered_by_severity(dev_conn, require_embedded_memory):
    # Seed incident_jsonb carries a severity field independent of embedding
    # content; pre-filtering on it narrows the KNN candidate set to exactly the
    # CRITICAL rows. Count is derived from the DB so the test is robust to how
    # many CRITICAL incidents the seed ships.
    expected_critical = dev_conn.execute(
        "SELECT count(*) FROM semantic_memory "
        "WHERE incident_jsonb->>'severity' = 'CRITICAL' AND embedded_at IS NOT NULL"
    ).fetchone()[0]

    result = memory_search_similar(
        query_vector=[0.11] * 1024,
        limit=10,
        filters={"severity": "CRITICAL"},
    )
    assert result["success"] is True
    assert len(result["matches"]) == expected_critical
    assert expected_critical >= 1
    # Every returned match must satisfy the severity filter.
    assert all(m["incident_jsonb"]["severity"] == "CRITICAL" for m in result["matches"])


# --- memory_store -------------------------------------------------------------

def test_derive_idempotency_key_deterministic_and_cve_sensitive():
    k1 = _derive_idempotency_key("same summary", {"cve_id": "CVE-2024-1"})
    k2 = _derive_idempotency_key("same summary", {"cve_id": "CVE-2024-1"})
    k3 = _derive_idempotency_key("same summary", {"cve_id": "CVE-2024-2"})
    assert k1 == k2  # deterministic
    assert k1 != k3  # cve_id participates in the key
    assert k1.startswith("mem-")


def test_memory_store_creates_row(dev_conn, cleanup_test_rows):
    key = "test-store-create"
    result = memory_store(
        summary="TEST create: internal medium CVE auto-patched",
        incident_jsonb={"cve_id": "TEST-CVE-1", "severity": "MEDIUM", "outcome": "auto-patched"},
        tags=["test", "medium"],
        idempotency_key=key,
    )
    assert result["success"] is True
    assert result["created"] is True
    assert result["idempotency_key"] == key
    memory_id = result["memory_id"]
    assert memory_id

    # Row exists, carries a real embedding, and embedded_at is stamped.
    row = dev_conn.execute(
        "SELECT embedded_at IS NOT NULL, summary FROM semantic_memory WHERE idempotency_key = %s",
        (key,),
    ).fetchone()
    assert row[0] is True
    assert row[1] == "TEST create: internal medium CVE auto-patched"


def test_memory_store_idempotent(dev_conn, cleanup_test_rows):
    key = "test-store-idempotent"
    payload = dict(
        summary="TEST idempotent: repeated store must not duplicate",
        incident_jsonb={"cve_id": "TEST-CVE-2", "severity": "HIGH"},
        idempotency_key=key,
    )
    r1 = memory_store(**payload)
    r2 = memory_store(**payload)
    assert r1["success"] and r2["success"]
    assert r1["created"] is True
    assert r2["created"] is False  # conflict → existing row returned
    assert r1["memory_id"] == r2["memory_id"]

    count = dev_conn.execute(
        "SELECT count(*) FROM semantic_memory WHERE idempotency_key = %s", (key,)
    ).fetchone()[0]
    assert count == 1  # exactly one row despite two stores


def test_memory_store_then_search_retrievable(dev_conn, cleanup_test_rows, require_embedded_memory):
    # Store a distinctive incident, then confirm a KNN search over the same
    # embedded text surfaces it (RAG loop closed end-to-end).
    key = "test-store-retrievable"
    summary = "TEST retrievable: Redis unauthenticated RCE on internet-facing cache cluster, manual review"
    store = memory_store(
        summary=summary,
        incident_jsonb={"cve_id": "TEST-CVE-3", "severity": "CRITICAL", "exposure": "internet-facing"},
        tags=["test", "redis", "critical"],
        idempotency_key=key,
    )
    assert store["success"] is True

    # Embed the same text and search; the stored row should be the top match.
    from backend.embed import embed_text
    qvec = embed_text(summary)
    result = memory_search_similar(query_vector=qvec, limit=5)
    assert result["success"] is True
    stored_ids = [m["memory_id"] for m in result["matches"]]
    assert store["memory_id"] in stored_ids
    # Its distance to itself should be the smallest (top-ranked).
    assert result["matches"][0]["memory_id"] == store["memory_id"]
