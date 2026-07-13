"""Layer 3 — End-to-end agent behavioral (snapshot) tests.

These invoke the real Strands agents via `agentcore dev` (local dev server) and
assert on the resulting CockroachDB state — a "snapshot" of what the agent did,
not an exact-match on its natural-language output. Tool calls route through the
LIVE gateway (zdl-gateway-frkgbxbipc) → Lambda (zdl-tools-handler) → CockroachDB,
so a passing test proves the full designed path works end-to-end.

OPT-IN. Skipped unless AGENTCORE_INVOKE=1 (see the `agentcore_invoke` fixture).
Requires:
  - COCKROACH_URL (for the post-run DB assertions)
  - AWS credentials with Bedrock + gateway access
  - the `agentcore` CLI on PATH

Each test cleans up the rows it creates (cleanup_agent_rows) so fair-dolphin
stays tidy. Because LLM behavior is non-deterministic, assertions check that the
agent took the *right kind* of action (called the right tool, wrote the expected
kind of row), not that it produced specific prose.

KNOWN BLOCKER — xfail reason
------------------------------
The agents use the Qwen model (qwen.qwen3-coder-30b-a3b-instruct) served via
Bedrock Mantle's OpenAI-compatible endpoint. Qwen uses a proprietary tool-call
format that appends a `<|channel|>commentary` suffix to the tool name in its
function-call output. Strands' MCPClient registers tools by their exact name
(e.g. `zdl_gateway_frkgbxbipc_zdltools___finding_create_or_update`), but the
model emits `zdl_gateway_frkgbxbipc_zdltools___finding_create_or_update<|channel|>commentary`
which Strands cannot match in its tool registry, causing every MCP tool call to
fail with `"Unknown tool"`.

Resolution options (in order of preference):
  1. Switch to a model with standard OpenAI function-calling support
     (e.g. a Bedrock Claude model via the Converse API), or
  2. Write a custom Strands model adapter that strips the `<|channel|>commentary`
     suffix before tool dispatch.

Until this is resolved, these tests are marked `xfail` so they:
  - Run and capture the failure as expected (CI stays green)
  - Surface immediately if the model/adapter is fixed (xpass becomes a pass)
  - Document the exact failure mode in the test output
"""
import pytest

pytestmark = pytest.mark.agent

_XFAIL_REASON = (
    "Qwen model via Bedrock Mantle appends '<|channel|>commentary' to tool names in its "
    "function-call output. Strands MCPClient cannot match this against the registered tool "
    "name (e.g. 'zdl_gateway_frkgbxbipc_zdltools___finding_create_or_update'), so every "
    "MCP tool call fails with 'Unknown tool'. Fix: switch to a model that emits standard "
    "OpenAI function-call JSON, or write a Strands model adapter that strips the suffix."
)


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_ingest_agent_creates_finding(agentcore_invoke, dev_conn, cleanup_agent_rows):
    """zdl_ingest should turn an ingestion request into a findings row.

    Snapshot: after the run, a finding with the requested CVE + idempotency_key
    exists — proving the agent called finding_create_or_update through the
    gateway → Lambda → CockroachDB path.
    """
    agentcore_invoke(
        runtime="zdl_ingestAgent",
        prompt=(
            "Ingest this vulnerability report and create a finding.\n"
            "CVE: CVE-2024-INGEST-TEST\n"
            "Affected asset: phi-gateway-prod-01 (internet-facing, production)\n"
            "Proposed severity: CRITICAL\n"
            "Use the exact idempotency_key 'test-agent-ingest-1' when you create "
            "the finding so it can be located afterward."
        ),
    )

    row = dev_conn.execute(
        "SELECT cve_id, proposed_severity FROM findings WHERE idempotency_key = %s",
        ("test-agent-ingest-1",),
    ).fetchone()
    assert row is not None, (
        "zdl_ingest did not create a finding via finding_create_or_update "
        "(no row for idempotency_key 'test-agent-ingest-1')"
    )
    assert row[0] == "CVE-2024-INGEST-TEST"


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_governance_agent_writes_policy_check(
    agentcore_invoke, dev_conn, seeded_finding_id, cleanup_agent_rows
):
    """zdl_governance should evaluate policy and record a policy_check event.

    Snapshot: a fresh policy_check event is appended to action_timeline for the
    seeded finding, and its decision is manual_review — because the asset is
    internet-facing + CRITICAL, which the seeded policy rule gates to
    manual_review. This proves policy_evaluate_action + timeline_append_event
    both fired through the live path.
    """
    agentcore_invoke(
        runtime="zdl_governanceAgent",
        prompt=(
            f"Evaluate whether automatic remediation can proceed for finding "
            f"{seeded_finding_id}. The affected asset is internet-facing with "
            f"CRITICAL severity (tier-0 production). Evaluate the action "
            f"'approve_remediation' against policy, then record your decision in "
            f"the audit timeline as a 'policy_check' event on this finding."
        ),
    )

    row = dev_conn.execute(
        """
        SELECT payload_json
        FROM action_timeline
        WHERE finding_id = %s
          AND action = 'policy_check'
          AND created_at > now() - INTERVAL '30 minutes'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (seeded_finding_id,),
    ).fetchone()
    assert row is not None, (
        "zdl_governance did not append a recent policy_check event "
        "(policy_evaluate_action / timeline_append_event not exercised)"
    )
    payload = row[0] or {}
    assert payload.get("decision") == "manual_review", (
        f"expected manual_review for internet-facing CRITICAL, got {payload.get('decision')!r}"
    )


@pytest.mark.xfail(reason=_XFAIL_REASON, strict=True)
def test_ingest_agent_stores_resolved_memory(
    agentcore_invoke, dev_conn, cleanup_agent_rows
):
    """A resolved incident should be persisted to semantic_memory with a vector.

    Snapshot: a semantic_memory row for the distinctive test CVE exists and
    carries a real Titan embedding (embedded_at IS NOT NULL) — proving the agent
    called memory_store, which embeds via Titan and writes to the vector table.
    """
    agentcore_invoke(
        runtime="zdl_ingestAgent",
        prompt=(
            "A finding has reached a terminal, resolved state. Persist it to "
            "long-term memory for future similarity search.\n"
            "CVE: CVE-2024-MEMORY-TEST\n"
            "Asset: phi-gateway-prod-01 (internet-facing)\n"
            "Severity: HIGH\n"
            "Decision: manual_review\n"
            "Outcome: patched_during_window\n"
            "Store this as a prior-incident memory now."
        ),
    )

    row = dev_conn.execute(
        """
        SELECT embedded_at IS NOT NULL
        FROM semantic_memory
        WHERE incident_jsonb->>'cve_id' = 'CVE-2024-MEMORY-TEST'
        """,
    ).fetchone()
    assert row is not None, (
        "zdl_ingest did not call memory_store for the resolved incident "
        "(no semantic_memory row for CVE-2024-MEMORY-TEST)"
    )
    assert row[0] is True, (
        "memory_store wrote a row but left embedding NULL — Titan embed path "
        "did not run through the gateway/Lambda"
    )
