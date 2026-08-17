"""
Tool: apply_patch_action

Simulated remediation executor for the Zero Day Librarian remediation agent
(zdl_remediation). Given a finding that governance has explicitly ALLOWED, this
"applies" the remediation described in the finding's governance decision
(decisions.proposal_jsonb) and records the outcome.

This is a simulated action: it mutates the application's own data model only
(it does not touch real infrastructure). Concretely, on success it:
  1. Sets findings.status = 'remediated'.
  2. Appends an immutable REMEDIATION_EXECUTED event to action_timeline,
     attributed to actor 'zdl_remediation', carrying the applied action/change/
     target from the governance proposal.

HARD SAFETY GUARDRAIL (enforced in code, not merely in the agent prompt):
    A patch is applied ONLY when the finding's decision_state == 'allow'.
    Findings in 'manual_review', 'deny', 'pending', or any other state are
    refused. This is a deterministic server-side check so the outcome does not
    depend on the model's judgement. In particular, the hero HIPAA finding
    (manual_review) can never be auto-remediated through this tool.

Idempotency: a stable idempotency_key is derived from the finding + proposal
action_id, and a finding already in 'remediated' state is treated as a no-op
success (so retries are safe and do not append duplicate audit events).
"""
import json
from typing import Any, Optional

from .db import get_psycopg_conn

# The one and only decision state that authorizes remediation.
_ALLOWED_DECISION_STATE = "allow"
# Terminal status written on successful remediation.
_REMEDIATED_STATUS = "remediated"
# Audit action name for the remediation event (matches reset_demo / demo tooling).
_REMEDIATION_ACTION = "REMEDIATION_EXECUTED"
_ACTOR_TYPE = "agent"
_ACTOR_ID = "zdl_remediation"


def apply_patch_action(
    finding_id: str,
    action_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Apply the governance-approved remediation for a finding (simulated).

    Args:
        finding_id: UUID of the finding to remediate.
        action_id:  Optional idempotency hint. If omitted, it is taken from the
                    finding's governance proposal (proposal_jsonb.action_id).

    Returns on success:
        {
            "success": True,
            "finding_id": str,
            "status": "remediated",
            "applied": {"action": ..., "target": ..., "change": ...},
            "event_id": str,        # REMEDIATION_EXECUTED timeline event
            "already_remediated": bool,
        }
    Returns on refusal / error:
        {"success": False, "error": str, "decision_state": Optional[str]}
    """
    if not finding_id:
        return {"success": False, "error": "finding_id is required."}

    conn = get_psycopg_conn()
    try:
        with conn.cursor() as cur:
            # 1) Load the finding and its latest governance proposal.
            cur.execute(
                """
                SELECT f.decision_state, f.status, d.proposal_jsonb
                FROM findings f
                LEFT JOIN decisions d ON d.finding_id = f.finding_id
                WHERE f.finding_id = %s
                ORDER BY d.proposed_at DESC NULLS LAST
                LIMIT 1
                """,
                (finding_id,),
            )
            row = cur.fetchone()
            if row is None:
                return {
                    "success": False,
                    "error": f"Finding {finding_id} not found.",
                    "decision_state": None,
                }

            decision_state, status, proposal = row[0], row[1], row[2]

            # Idempotent no-op: already remediated → success without re-writing.
            if status == _REMEDIATED_STATUS:
                return {
                    "success": True,
                    "finding_id": finding_id,
                    "status": _REMEDIATED_STATUS,
                    "applied": None,
                    "event_id": None,
                    "already_remediated": True,
                }

            # 2) HARD GUARDRAIL: only 'allow' findings may be remediated.
            if decision_state != _ALLOWED_DECISION_STATE:
                return {
                    "success": False,
                    "error": (
                        f"Refusing to apply patch: finding {finding_id} has "
                        f"decision_state={decision_state!r}, but remediation "
                        f"requires decision_state={_ALLOWED_DECISION_STATE!r}. "
                        "Findings under manual review or denied must not be "
                        "auto-remediated."
                    ),
                    "decision_state": decision_state,
                }

            # 3) Extract the remediation the governance agent approved.
            if isinstance(proposal, (str, bytes, bytearray)):
                try:
                    proposal = json.loads(proposal)
                except (ValueError, TypeError):
                    proposal = {}
            proposal = proposal or {}
            applied = {
                "action": proposal.get("action"),
                "target": proposal.get("target"),
                "change": proposal.get("change"),
            }
            resolved_action_id = action_id or proposal.get("action_id")

            # 4) Apply (simulated): flip status → remediated, then append audit.
            with conn.transaction():
                cur.execute(
                    "UPDATE findings "
                    "SET status = %s, updated_at = now() "
                    "WHERE finding_id = %s",
                    (_REMEDIATED_STATUS, finding_id),
                )
                cur.execute(
                    """
                    INSERT INTO action_timeline
                        (finding_id, actor_type, actor_id, action,
                         target_table, target_id, payload_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING event_id
                    """,
                    (
                        finding_id,
                        _ACTOR_TYPE,
                        _ACTOR_ID,
                        _REMEDIATION_ACTION,
                        "findings",
                        finding_id,
                        json.dumps(
                            {
                                "action_id": resolved_action_id,
                                "action": applied["action"],
                                "target": applied["target"],
                                "change": applied["change"],
                                "outcome": "applied",
                            }
                        ),
                    ),
                )
                event_id = cur.fetchone()[0]

            return {
                "success": True,
                "finding_id": finding_id,
                "status": _REMEDIATED_STATUS,
                "applied": applied,
                "event_id": str(event_id),
                "already_remediated": False,
            }
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
