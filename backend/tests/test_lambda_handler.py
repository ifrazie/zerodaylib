"""Layer 1 — AgentCore Gateway Lambda dispatch tests (backend/lambda_handler.py).

These exercise the exact code path the deployed `zdl-tools-handler` Lambda runs
when the gateway routes an MCP tool call to it: `handler(event, context)` where
`context.bedrockAgentCoreToolName` carries the "<target>__<tool>" name and
`event` is the flat dict of tool arguments.

We call `handler` in-process (not via lambda.invoke) so we test the dispatch
table, tool-name parsing, error handling, and the query_text→Titan path against
the live CockroachDB `zdl_db`. This mirrors the deployed Lambda's logic exactly
because the same module is imported.

Requires COCKROACH_URL (via conftest dev_conn). Titan-backed tests additionally
require AWS credentials with bedrock:InvokeModel and embedded seed rows.
"""
import os
import sys
from types import SimpleNamespace

import pytest

# The Lambda module imports `from tools.finding import ...` (Lambda package
# layout), so backend/ must be importable as a top-level path — exactly as it is
# inside the deployed Lambda (/var/task). Add it before importing the handler.
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from lambda_handler import _resolve_cockroach_url, handler  # noqa: E402


def _ctx(tool: str) -> SimpleNamespace:
    """Build a mock Lambda context as AgentCore Gateway populates it."""
    return SimpleNamespace(
        bedrockAgentCoreToolName=f"zdl-tools__{tool}",
        aws_request_id=f"test-{tool}",
    )


# --- dispatch: happy paths ----------------------------------------------------

def test_dispatch_policy_evaluate_action(dev_conn):
    result = handler(
        {"action": "approve_remediation",
         "fact_set": {"exposure": "internet-facing", "severity": "CRITICAL"}},
        _ctx("policy_evaluate_action"),
    )
    assert result["decision"] == "manual_review"
    assert result["matched_rule_name"] == "manual-review-critical-internet"


def test_dispatch_finding_create_or_update(dev_conn, cleanup_test_rows):
    key = "test-lambda-finding-1"
    result = handler(
        {"idempotency_key": key, "cve_id": "CVE-2024-7169", "status": "new"},
        _ctx("finding_create_or_update"),
    )
    assert result["success"] is True
    row = dev_conn.execute(
        "SELECT cve_id, status FROM findings WHERE idempotency_key = %s", (key,)
    ).fetchone()
    assert row == ("CVE-2024-7169", "new")


def test_dispatch_timeline_append_event(dev_conn, cleanup_test_rows):
    result = handler(
        {"actor_type": "test", "actor_id": "pytest", "action": "lambda_test",
         "payload_json": {"via": "lambda_handler"}},
        _ctx("timeline_append_event"),
    )
    assert result["success"] is True
    eid = result["event_id"]
    count = dev_conn.execute(
        "SELECT count(*) FROM action_timeline WHERE event_id = %s", (eid,)
    ).fetchone()[0]
    assert count == 1


def test_dispatch_memory_search_query_vector(dev_conn, require_embedded_memory):
    result = handler(
        {"query_vector": [0.11] * 1024, "limit": 3},
        _ctx("memory_search_similar"),
    )
    assert result["success"] is True
    assert len(result["matches"]) >= 1


def test_dispatch_memory_search_query_text(dev_conn, require_embedded_memory):
    # No query_vector: handler must embed query_text via Titan, then KNN.
    result = handler(
        {"query_text": "critical OpenSSL CVE on internet-facing production", "limit": 3},
        _ctx("memory_search_similar"),
    )
    assert result["success"] is True
    assert len(result["matches"]) >= 1


def test_dispatch_memory_store(dev_conn, cleanup_test_rows):
    key = "test-lambda-store-1"
    result = handler(
        {"summary": "TEST lambda store: internal medium CVE auto-patched",
         "incident_jsonb": {"cve_id": "TEST-CVE-L1", "severity": "MEDIUM"},
         "tags": ["test", "lambda"],
         "idempotency_key": key},
        _ctx("memory_store"),
    )
    assert result["success"] is True
    assert result["created"] is True
    embedded = dev_conn.execute(
        "SELECT embedded_at IS NOT NULL FROM semantic_memory WHERE idempotency_key = %s",
        (key,),
    ).fetchone()[0]
    assert embedded is True


# --- dispatch: tool-name parsing ----------------------------------------------

def test_tool_name_strips_target_prefix(dev_conn):
    # "<target>__<tool>" → the "<target>__" prefix must be stripped.
    result = handler(
        {"action": "approve_remediation", "fact_set": {"tier": "tier-0"}},
        _ctx("policy_evaluate_action"),
    )
    assert result["decision"] == "manual_review"
    assert result["matched_rule_name"] == "manual-review-tier0"


def test_tool_name_without_prefix_still_dispatches(dev_conn):
    # A bare tool name (no "__") must still route correctly.
    ctx = SimpleNamespace(bedrockAgentCoreToolName="policy_evaluate_action",
                          aws_request_id="test-bare")
    result = handler(
        {"action": "approve_remediation", "fact_set": {"exposure": "internal-vpc", "severity": "HIGH"}},
        ctx,
    )
    assert result["decision"] == "allow"


# --- dispatch: error handling -------------------------------------------------

def test_unknown_tool_returns_error(dev_conn):
    result = handler({}, _ctx("does_not_exist"))
    assert result["success"] is False
    assert "Unknown tool" in result["error"]


def test_missing_required_arg_returns_error(dev_conn):
    # finding_create_or_update requires idempotency_key; omitting it must be
    # caught (KeyError) and returned as a clean tool error, not a 500 crash.
    result = handler({"cve_id": "CVE-2024-7169"}, _ctx("finding_create_or_update"))
    assert result["success"] is False
    assert "idempotency_key" in result["error"] or "Missing required argument" in result["error"]


def test_memory_search_requires_vector_or_text(dev_conn):
    result = handler({}, _ctx("memory_search_similar"))
    assert result["success"] is False
    assert "query_vector or query_text" in result["error"]


def test_memory_store_requires_summary(dev_conn):
    result = handler({"incident_jsonb": {"cve_id": "X"}}, _ctx("memory_store"))
    assert result["success"] is False
    assert "summary" in result["error"]


# --- Secrets Manager resolution ----------------------------------------------

def test_resolve_cockroach_url_noop_when_already_set(monkeypatch):
    # COCKROACH_URL present → resolver must early-return without consulting
    # COCKROACH_SECRET_ARN or Secrets Manager. We assert it does not raise and
    # leaves the existing URL untouched.
    sentinel = "postgresql://noop@localhost:26257/zdl_db"
    monkeypatch.setenv("COCKROACH_URL", sentinel)
    monkeypatch.setenv("COCKROACH_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:0:secret:should-not-be-read")
    _resolve_cockroach_url()  # must return cleanly without raising
    assert os.environ["COCKROACH_URL"] == sentinel
