"""
backend/lambda_handler.py — AgentCore Gateway Lambda target for zdl-tools-handler.

AgentCore invokes this handler for each MCP tool call routed through the gateway:
  - event       : flat dict of tool input parameters (no envelope)
  - context     : Lambda context; tool name is at context.bedrockAgentCoreToolName
                  in the form  "<target_name>__<tool_name>"

This module is intentionally thin: it dispatches to the unchanged tool contracts
in backend/tools/ so that local FastAPI testing and cloud Lambda execution share
identical business logic and the same test coverage.

Tools exposed:
  finding_create_or_update    — idempotent upsert of a finding record
  policy_evaluate_action      — deterministic rule evaluation → allow/deny/manual_review
  timeline_append_event       — append-only write to action_timeline
  memory_search_similar       — KNN vector search over semantic_memory (CRDB vector index)
                                accepts either query_vector or query_text (Titan embedding)

Environment variables (read at cold-start or per-invocation):
  COCKROACH_URL               — psycopg connection string (prefer Secrets Manager; see below)
  COCKROACH_SECRET_ARN        — Secrets Manager ARN for COCKROACH_URL (preferred over env)
  COCKROACH_SSLROOTCERT       — optional; defaults to bundled backend/certs/cc-ca.crt
  AWS_REGION / AWS_DEFAULT_REGION — resolved automatically in Lambda runtime

Secrets Manager resolution:
  If COCKROACH_SECRET_ARN is set and COCKROACH_URL is absent (or empty), this module
  fetches the secret once per Lambda container lifetime and caches it in the process.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

# ── Make sure backend/ is importable whether invoked as a Lambda package
# (where cwd is /var/task/backend) or as part of the monorepo (cwd is repo root).
_this_dir = os.path.dirname(os.path.abspath(__file__))
for _candidate in (_this_dir, os.path.dirname(_this_dir)):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from tools.finding import finding_create_or_update
from tools.policy import policy_evaluate_action
from tools.timeline import timeline_append_event
from tools.memory import memory_search_similar

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ── Shared Titan embedding helper (query-side and write-side) ─────────────────
try:
    from embed import embed_text as _embed_text
    _TITAN_AVAILABLE = True
except ImportError:
    _TITAN_AVAILABLE = False

    def _embed_text(text: str) -> list[float]:  # type: ignore[misc]
        raise RuntimeError("boto3 not available; cannot embed text")


# ── Secrets Manager resolution ────────────────────────────────────────────────
_secret_cache: dict[str, str] = {}

def _resolve_cockroach_url() -> None:
    """
    If COCKROACH_URL is not set but COCKROACH_SECRET_ARN is, fetch the secret
    once per container lifetime and write it into the environment so that
    backend/tools/db.py picks it up transparently.
    """
    if os.environ.get("COCKROACH_URL"):
        return  # already present (env var or previous resolution)

    secret_arn = os.environ.get("COCKROACH_SECRET_ARN")
    if not secret_arn:
        logger.warning(
            "Neither COCKROACH_URL nor COCKROACH_SECRET_ARN is set; "
            "tool calls will fall back to local defaults."
        )
        return

    if secret_arn in _secret_cache:
        os.environ["COCKROACH_URL"] = _secret_cache[secret_arn]
        return

    try:
        import boto3
        region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        sm = boto3.client("secretsmanager", region_name=region)
        value = sm.get_secret_value(SecretId=secret_arn)
        # Secret stored as a plain string (the full connection URL).
        url = value.get("SecretString") or ""
        if not url:
            # If stored as a JSON object with a 'url' key, unwrap it.
            try:
                url = json.loads(value.get("SecretString", "{}")).get("url", "")
            except (json.JSONDecodeError, AttributeError):
                pass
        if url:
            _secret_cache[secret_arn] = url
            os.environ["COCKROACH_URL"] = url
            logger.info("COCKROACH_URL resolved from Secrets Manager.")
        else:
            logger.error("COCKROACH_SECRET_ARN secret value was empty.")
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to resolve COCKROACH_URL from Secrets Manager: %s", exc)


# ── Tool dispatch table ───────────────────────────────────────────────────────

def _dispatch_finding_create_or_update(args: dict[str, Any]) -> dict[str, Any]:
    sla_dt = None
    if args.get("sla_due_at"):
        try:
            sla_dt = datetime.fromisoformat(args["sla_due_at"])
        except (ValueError, TypeError):
            pass
    return finding_create_or_update(
        idempotency_key=args["idempotency_key"],
        cve_id=args.get("cve_id"),
        asset_id=args.get("asset_id"),
        status=args.get("status"),
        proposed_severity=args.get("proposed_severity"),
        approved_severity=args.get("approved_severity"),
        exploitability_score=args.get("exploitability_score"),
        exploitability_rationale=args.get("exploitability_rationale"),
        remediation_priority=args.get("remediation_priority"),
        sla_due_at=sla_dt,
        owner_team=args.get("owner_team"),
        decision_state=args.get("decision_state"),
    )


def _dispatch_policy_evaluate_action(args: dict[str, Any]) -> dict[str, Any]:
    return policy_evaluate_action(
        action=args["action"],
        fact_set=args.get("fact_set") or {},
    )


def _dispatch_timeline_append_event(args: dict[str, Any]) -> dict[str, Any]:
    return timeline_append_event(
        finding_id=args.get("finding_id"),
        actor_type=args["actor_type"],
        actor_id=args["actor_id"],
        action=args["action"],
        target_table=args.get("target_table"),
        target_id=args.get("target_id"),
        payload_json=args.get("payload_json") or {},
    )


def _dispatch_memory_search_similar(args: dict[str, Any]) -> dict[str, Any]:
    """
    Accept either:
      query_vector : list[float]  — raw 1024-dim embedding (bypasses Titan)
      query_text   : str          — natural-language text, embedded via Titan v2
    """
    query_vector = args.get("query_vector")
    query_text = args.get("query_text")

    if not query_vector:
        if not query_text:
            return {"success": False, "error": "Either query_vector or query_text must be provided."}
        if not _TITAN_AVAILABLE:
            return {"success": False, "error": "query_text provided but boto3/Titan embedding unavailable."}
        try:
            query_vector = _embed_text(query_text)
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": f"Titan embedding failed: {exc}"}

    return memory_search_similar(
        query_vector=query_vector,
        limit=int(args.get("limit", 3)),
        filters=args.get("filters"),
    )


# Map bare tool name (after stripping "<target>__" prefix) → dispatch function.
_DISPATCH: dict[str, Any] = {
    "finding_create_or_update": _dispatch_finding_create_or_update,
    "policy_evaluate_action":   _dispatch_policy_evaluate_action,
    "timeline_append_event":    _dispatch_timeline_append_event,
    "memory_search_similar":    _dispatch_memory_search_similar,
}


# ── Lambda entry point ────────────────────────────────────────────────────────

def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Lambda handler invoked by AgentCore Gateway for every MCP tool call.

    Routing:
      context.bedrockAgentCoreToolName = "<target_name>__<tool_name>"
      event                            = flat dict of tool input parameters
    """
    # Resolve DB credentials once per container lifetime.
    _resolve_cockroach_url()

    # Identify which tool was invoked.
    raw_tool_name: str = getattr(context, "bedrockAgentCoreToolName", "") or ""
    # Strip "<target>__" prefix to get the bare tool name.
    tool_name = raw_tool_name.split("__", 1)[-1] if "__" in raw_tool_name else raw_tool_name

    logger.info(
        "zdl-tools-handler invoked | tool=%s | raw=%s | request_id=%s",
        tool_name,
        raw_tool_name,
        getattr(context, "aws_request_id", "local"),
    )

    dispatch_fn = _DISPATCH.get(tool_name)
    if dispatch_fn is None:
        err = f"Unknown tool '{tool_name}'. Known tools: {list(_DISPATCH)}"
        logger.error(err)
        return {"success": False, "error": err}

    try:
        result = dispatch_fn(event or {})
    except KeyError as exc:
        err = f"Missing required argument for tool '{tool_name}': {exc}"
        logger.error(err)
        return {"success": False, "error": err}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled error in tool '%s': %s", tool_name, exc)
        return {"success": False, "error": str(exc)}

    logger.info("tool=%s | success=%s", tool_name, result.get("success"))
    return result
