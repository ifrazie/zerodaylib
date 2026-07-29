"""Layer 2 — FastAPI HTTP endpoint tests (backend/main.py).

Exercise the HTTP surface the frontend dashboard and external callers use, via
a TestClient (`api_client` fixture) backed by the live CockroachDB `zdl_db`.
These verify the dashboard read paths (findings, semantic-memory, audit,
governance) and the POST /v1/* tool endpoints, including the query_text→Titan
embedding path.

Requires COCKROACH_URL. Titan/vector paths additionally require AWS credentials
and embedded seed rows (require_embedded_memory).
"""
import pytest


# --- dashboard read endpoints -------------------------------------------------

def test_get_system_status(api_client):
    resp = api_client.get("/api/system")
    assert resp.status_code == 200
    body = resp.json()
    # Identity block
    for key in ("environment", "region", "version", "git_commit"):
        assert key in body
    # Counts block — all present and non-negative ints
    counts = body["counts"]
    for key in (
        "findings",
        "findings_critical",
        "findings_manual_review",
        "assets",
        "policies",
        "audit_events",
        "semantic_memory",
    ):
        assert key in counts
        assert isinstance(counts[key], int)
        assert counts[key] >= 0
    # Seeded data guarantees at least the canonical finding + its asset + policies
    assert counts["findings"] >= 1
    assert counts["policies"] >= 1
    # Agents block
    agents = body["agents"]
    for agent in ("ingest", "semantic_memory", "governance"):
        assert agent in agents
        assert "status" in agents[agent]
    # Infrastructure block
    infra = body["infrastructure"]
    for component in ("cockroachdb", "bedrock", "agentcore"):
        assert component in infra
        assert "status" in infra[component]


def test_get_findings_returns_list(api_client, seeded_finding_id):
    resp = api_client.get("/api/findings")
    assert resp.status_code == 200
    findings = resp.json()
    assert isinstance(findings, list)
    ids = [f["id"] for f in findings]
    assert seeded_finding_id in ids


def test_get_findings_field_shape(api_client):
    resp = api_client.get("/api/findings")
    assert resp.status_code == 200
    findings = resp.json()
    assert findings, "expected at least the seeded finding"
    sample = findings[0]
    for key in ("id", "cve_id", "status", "severity", "created_at"):
        assert key in sample


def test_get_finding_detail(api_client, seeded_finding_id):
    resp = api_client.get(f"/api/findings/{seeded_finding_id}")
    assert resp.status_code == 200
    finding = resp.json()
    assert finding["id"] == seeded_finding_id
    assert finding["cve_id"] == "CVE-2024-7169"
    assert finding["severity"] == "CRITICAL"


def test_get_finding_not_found(api_client):
    resp = api_client.get("/api/findings/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_get_semantic_memory(api_client, seeded_finding_id, require_embedded_memory):
    # Embeds the finding's own context via Titan, runs KNN over the vector index.
    resp = api_client.get(f"/api/semantic-memory/{seeded_finding_id}")
    assert resp.status_code == 200
    similarities = resp.json()
    assert isinstance(similarities, list)
    assert len(similarities) >= 1
    top = similarities[0]
    for key in ("id", "title", "summary", "similarity_score"):
        assert key in top
    assert 0.0 < top["similarity_score"] <= 1.0


def test_get_audit_timeline(api_client, seeded_finding_id):
    resp = api_client.get(f"/api/audit/{seeded_finding_id}")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)
    actions = [e["action"] for e in events]
    assert "policy_check" in actions  # seeded governance event


def test_get_governance_status(api_client, seeded_finding_id):
    resp = api_client.get(f"/api/governance/{seeded_finding_id}")
    assert resp.status_code == 200
    gov = resp.json()
    assert gov["finding_id"] == seeded_finding_id
    # Seed now includes a decisions row (decision_score=manual_review), so the
    # endpoint returns that decision directly; the policy_check timeline event
    # remains as a fallback.
    assert gov["state"] == "manual_review"


# --- POST /v1/* tool endpoints ------------------------------------------------

def test_post_policy_evaluate(api_client):
    resp = api_client.post(
        "/v1/policy_evaluate_action",
        json={"action": "approve_remediation",
              "fact_set": {"exposure": "internet-facing", "severity": "CRITICAL"}},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] == "manual_review"


def test_post_finding_upsert(api_client, dev_conn, cleanup_test_rows):
    key = "test-api-finding-1"
    resp = api_client.post(
        "/v1/finding_create_or_update",
        json={"idempotency_key": key, "cve_id": "CVE-2024-7169", "status": "new"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    row = dev_conn.execute(
        "SELECT cve_id FROM findings WHERE idempotency_key = %s", (key,)
    ).fetchone()
    assert row[0] == "CVE-2024-7169"


def test_post_timeline_append(api_client, dev_conn, cleanup_test_rows):
    resp = api_client.post(
        "/v1/timeline_append_event",
        json={"actor_type": "test", "actor_id": "pytest", "action": "api_test",
              "payload_json": {"via": "fastapi"}},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_post_memory_search_query_text(api_client, require_embedded_memory):
    resp = api_client.post(
        "/v1/memory_search_similar",
        json={"query_text": "critical OpenSSL CVE on internet-facing production", "limit": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["matches"]) >= 1


def test_post_memory_search_missing_vector_and_text(api_client):
    resp = api_client.post("/v1/memory_search_similar", json={"limit": 3})
    assert resp.status_code == 400


def test_post_memory_store(api_client, dev_conn, cleanup_test_rows):
    key = "test-api-store-1"
    resp = api_client.post(
        "/v1/memory_store",
        json={"summary": "TEST api store: internal medium CVE auto-patched",
              "incident_jsonb": {"cve_id": "TEST-CVE-API1", "severity": "MEDIUM"},
              "tags": ["test", "api"],
              "idempotency_key": key},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["created"] is True
