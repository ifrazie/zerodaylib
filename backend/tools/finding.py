"""
Tool: finding_create_or_update

Idempotent upsert for finding records with field-level controls.
Agents use this to record new or updated findings while preventing duplicates
 via the idempotency_key (unique constraint enforced by the table schema).
"""
import json
import uuid
import psycopg
from datetime import datetime
from typing import Any, Optional
from .contracts import FindingUpsertRequest

from .db import get_psycopg_conn


def _iso_or_null(d: Optional[datetime]) -> Optional[str]:
    return d.isoformat() if d else None


def finding_create_or_update(
    idempotency_key: str,
    cve_id: Optional[str] = None,
    asset_id: Optional[str] = None,
    status: Optional[str] = None,
    proposed_severity: Optional[str] = None,
    approved_severity: Optional[str] = None,
    exploitability_score: Optional[float] = None,
    exploitability_rationale: Optional[str] = None,
    remediation_priority: Optional[str] = None,
    sla_due_at: Optional[datetime] = None,
    owner_team: Optional[str] = None,
    decision_state: Optional[str] = None,
) -> dict[str, Any]:
    """
    Upsert a finding atomically via idempotency_key.

    Returns: {
        finding_id: uuid.UUID,
        created: bool,  // true if created, false if updated
        updated_at: datetime
    } or error.
    """
    conn = get_psycopg_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO findings (
                finding_id, cve_id, asset_id, status, proposed_severity, approved_severity,
                exploitability_score, exploitability_rationale, remediation_priority,
                sla_due_at, owner_team, decision_state, idempotency_key
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (idempotency_key) DO UPDATE SET
                cve_id = COALESCE(EXCLUDED.cve_id, findings.cve_id),
                asset_id = COALESCE(EXCLUDED.asset_id, findings.asset_id),
                status = COALESCE(EXCLUDED.status, findings.status),
                proposed_severity = COALESCE(EXCLUDED.proposed_severity, findings.proposed_severity),
                approved_severity = COALESCE(EXCLUDED.approved_severity, findings.approved_severity),
                exploitability_score = COALESCE(EXCLUDED.exploitability_score, findings.exploitability_score),
                exploitability_rationale = COALESCE(EXCLUDED.exploitability_rationale, findings.exploitability_rationale),
                remediation_priority = COALESCE(EXCLUDED.remediation_priority, findings.remediation_priority),
                sla_due_at = COALESCE(EXCLUDED.sla_due_at, findings.sla_due_at),
                owner_team = COALESCE(EXCLUDED.owner_team, findings.owner_team),
                decision_state = COALESCE(EXCLUDED.decision_state, findings.decision_state),
                updated_at = now()
            RETURNING finding_id, created_at, updated_at
            """,
            (
                str(uuid.uuid4()),  # new finding_id if insert
                cve_id,
                asset_id,
                status,
                proposed_severity,
                approved_severity,
                exploitability_score,
                exploitability_rationale,
                remediation_priority,
                sla_due_at,
                owner_team,
                decision_state,
                idempotency_key,
            ),
        )
        row = cur.fetchone()
        return {
            "success": True,
            "finding_id": str(row[0]),
            "created_at": row[1].isoformat(),
            "updated_at": row[2].isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()
