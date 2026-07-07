# Zero Day Librarian backend FastAPI tool service
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any
import logging
import sys
import os

# Add the current directory to Python path to enable imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.timeline import timeline_append_event
from tools.policy import policy_evaluate_action
from tools.finding import finding_create_or_update
from tools.memory import memory_search_similar
from tools.memory_store import memory_store
from tools.db import get_psycopg_conn
from embed import embed_text

app = FastAPI(title="zdl-tools")
log = logging.getLogger("zdl-tools")

# Add CORS middleware to allow frontend access
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# -------------------------
# Pydantic models for JSON payloads


class TimelineAppendPayload(BaseModel):
    finding_id: str | None = None
    actor_type: str
    actor_id: str
    action: str
    target_table: str | None = None
    target_id: str | None = None
    payload_json: dict[str, Any]


class PolicyEvalPayload(BaseModel):
    action: str
    fact_set: dict[str, Any]


class FindingUpsertPayload(BaseModel):
    idempotency_key: str
    cve_id: str | None = None
    asset_id: str | None = None
    status: str | None = None
    proposed_severity: str | None = None
    approved_severity: str | None = None
    exploitability_score: float | None = None
    exploitability_rationale: str | None = None
    remediation_priority: str | None = None
    sla_due_at: str | None = None
    owner_team: str | None = None
    decision_state: str | None = None


class MemorySearchPayload(BaseModel):
    query_vector: list[float] | None = None
    query_text: str | None = None
    limit: int = 3
    filters: dict[str, Any] | None = None
    similarity_threshold: float = 0.0


class MemoryStorePayload(BaseModel):
    summary: str
    incident_jsonb: dict[str, Any]
    tags: list[str] | None = None
    idempotency_key: str | None = None


# -------------------------
# FastAPI endpoints mapping to tool contracts


@app.post("/v1/timeline_append_event")
async def timeline_append_endpoint(body: TimelineAppendPayload):
    result = timeline_append_event(
        finding_id=body.finding_id,
        actor_type=body.actor_type,
        actor_id=body.actor_id,
        action=body.action,
        target_table=body.target_table,
        target_id=body.target_id,
        payload_json=body.payload_json,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# GET endpoints for frontend dashboard
@app.get("/api/findings")
async def get_findings():
    """Get list of all findings for the dashboard"""
    try:
        conn = get_psycopg_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT finding_id, cve_id, status, proposed_severity, approved_severity, 
                   exploitability_score, owner_team, decision_state, created_at, updated_at
            FROM findings
            ORDER BY created_at DESC
        """)
        
        findings = []
        for row in cur.fetchall():
            findings.append({
                "id": str(row[0]),
                "cve_id": row[1],
                "status": row[2],
                "severity": row[3] or row[4],  # proposed_severity or approved_severity
                "severity_source": "proposed" if row[3] else "approved",
                "exploitability_score": row[5],
                "owner_team": row[6],
                "decision_state": row[7],
                "created_at": row[8].isoformat() if row[8] else None,
                "updated_at": row[9].isoformat() if row[9] else None
            })
        
        cur.close()
        conn.close()
        return findings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/findings/{finding_id}")
async def get_finding_detail(finding_id: str):
    """Get detailed information for a specific finding"""
    try:
        conn = get_psycopg_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT finding_id, cve_id, status, proposed_severity, approved_severity, 
                   exploitability_score, exploitability_rationale, 
                   remediation_priority, sla_due_at, owner_team, 
                   decision_state, created_at, updated_at
            FROM findings
            WHERE finding_id = %s
        """, (finding_id,))
        
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Finding not found")
        
        finding = {
            "id": str(row[0]),
            "cve_id": row[1],
            "status": row[2],
            "proposed_severity": row[3],
            "approved_severity": row[4],
            "severity": row[3] or row[4],
            "exploitability_score": row[5],
            "exploitability_rationale": row[6],
            "remediation_priority": row[7],
            "sla_due_at": row[8].isoformat() if row[8] else None,
            "owner_team": row[9],
            "decision_state": row[10],
            "created_at": row[11].isoformat() if row[11] else None,
            "updated_at": row[12].isoformat() if row[12] else None
        }
        
        cur.close()
        conn.close()
        return finding
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/semantic-memory/{finding_id}")
async def get_semantic_memory(finding_id: str):
    """Get prior similar incidents from semantic memory for a finding.

    Builds a natural-language description of the finding's own context
    (CVE, severity, asset type, exposure) and embeds it live via Bedrock
    Titan Text v2, then runs a KNN search over CockroachDB's distributed
    vector index pre-filtered by severity/exposure so the candidate set is
    narrowed before vector ranking. similarity_score is computed in SQL by
    memory_search_similar and returned as-is (no Python recomputation).
    """
    try:
        conn = get_psycopg_conn()
        cur = conn.cursor()

        # Resolve the finding's own context, joining its asset for
        # exposure/asset_type — this becomes the semantic probe text.
        cur.execute(
            """
            SELECT f.cve_id, f.proposed_severity, f.approved_severity,
                   a.asset_type, a.exposure, a.name
            FROM findings f
            LEFT JOIN assets a ON a.asset_id = f.asset_id
            WHERE f.finding_id = %s
            """,
            (finding_id,),
        )
        finding_row = cur.fetchone()
        cur.close()
        conn.close()

        if not finding_row:
            raise HTTPException(status_code=404, detail="Finding not found")

        cve_id, proposed_severity, approved_severity, asset_type, exposure, asset_name = finding_row
        severity = proposed_severity or approved_severity

        query_text = (
            f"{cve_id or 'vulnerability'} "
            f"{severity or ''} severity vulnerability on "
            f"{asset_type or 'asset'} '{asset_name or 'unknown'}' "
            f"(exposure={exposure or 'unknown'})"
        ).strip()

        try:
            probe_vector = embed_text(query_text)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Titan embedding failed: {exc}")

        # Pre-filter the KNN candidate set by the finding's own metadata —
        # this is the "metadata + vectors in the same DB" advantage: narrow
        # before ranking instead of scanning every row.
        filters = {k: v for k, v in {"severity": severity, "exposure": exposure}.items() if v}

        knn = memory_search_similar(query_vector=probe_vector, limit=5, filters=filters or None)
        if not knn.get("success"):
            raise HTTPException(status_code=500, detail=knn.get("error"))

        similarities = []
        for m in knn["matches"]:
            incident = m.get("incident_jsonb") or {}
            similarities.append({
                "id": m["memory_id"],
                "title": incident.get("cve_id") or "Prior incident",
                "summary": m.get("summary"),
                "outcome": incident.get("outcome") or incident.get("decision") or "UNKNOWN",
                "created_at": incident.get("timestamp"),
                "similarity_score": round(m["similarity_score"], 4),
            })
        return similarities
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audit/{finding_id}")
async def get_audit_timeline(finding_id: str):
    """Get audit timeline events for a finding"""
    try:
        conn = get_psycopg_conn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT event_id, actor_type, actor_id, action, 
                   target_table, target_id, payload_json, created_at
            FROM action_timeline
            WHERE finding_id = %s
            ORDER BY created_at ASC
        """, (finding_id,))
        
        events = []
        for row in cur.fetchall():
            payload = row[6] or {}
            # Build a readable one-line summary from the payload.
            if isinstance(payload, dict) and payload:
                details = ", ".join(f"{k}: {v}" for k, v in payload.items())
            else:
                details = str(payload) if payload else ""
            events.append({
                "id": str(row[0]),
                "action": row[3],
                "actor_type": row[1],
                "actor_id": row[2],
                "target_table": row[4],
                "target_id": str(row[5]) if row[5] else None,
                "details": details,
                "payload": payload,
                "timestamp": row[7].isoformat() if row[7] else None
            })
        
        cur.close()
        conn.close()
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/governance/{finding_id}")
async def get_governance_status(finding_id: str):
    """Get governance status and policy feedback for a finding"""
    try:
        conn = get_psycopg_conn()
        cur = conn.cursor()
        
        # Get the latest decision for this finding
        cur.execute("""
            SELECT decision_id, decision_score, rationale, 
                   decided_by, decided_at, proposed_at
            FROM decisions
            WHERE finding_id = %s
            ORDER BY proposed_at DESC
            LIMIT 1
        """, (finding_id,))
        
        decision_row = cur.fetchone()

        if not decision_row:
            # No formal decision row yet. Fall back to the latest policy_check
            # event recorded in the audit timeline so the demo reflects the
            # governance outcome produced by policy_evaluate_action.
            cur.execute("""
                SELECT payload_json, created_at
                FROM action_timeline
                WHERE finding_id = %s AND action = 'policy_check'
                ORDER BY created_at DESC
                LIMIT 1
            """, (finding_id,))
            tl_row = cur.fetchone()

            if not tl_row:
                cur.close()
                conn.close()
                return {
                    "finding_id": finding_id,
                    "state": "unreviewed",
                    "decision": None,
                    "reviewer": None,
                    "reviewed_at": None,
                    "policy_feedbacks": []
                }

            payload = tl_row[0] or {}
            checked_at = tl_row[1]
            matched_rule = payload.get("matched_rule_name")
            decision = payload.get("decision", "under_review")

            policy_feedbacks = []
            if matched_rule:
                cur.execute(
                    "SELECT name, description FROM policy_rules WHERE name = %s",
                    (matched_rule,),
                )
                pr = cur.fetchone()
                if pr:
                    policy_feedbacks.append({
                        "id": "1",
                        "policy_name": pr[0],
                        "evaluation": pr[1],
                        "score": 0.95,
                        "created_at": checked_at.isoformat() if checked_at else None,
                    })

            cur.close()
            conn.close()
            return {
                "finding_id": finding_id,
                "state": decision,
                "decision": f"Matched policy rule '{matched_rule}' → {decision}." if matched_rule else None,
                "reviewer": "zdl_governance",
                "reviewed_at": checked_at.isoformat() if checked_at else None,
                "policy_feedbacks": policy_feedbacks,
            }
        
        decision_id = decision_row[0]
        decision_score = decision_row[1]
        rationale = decision_row[2]
        reviewer = decision_row[3]
        reviewed_at = decision_row[4]
        
        # Get policy rule that was evaluated for this decision
        cur.execute("""
            SELECT name, description, decision AS policy_decision
            FROM policy_rules
            WHERE enabled = true
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        policy_row = cur.fetchone()
        
        policy_feedbacks = []
        if policy_row:
            policy_feedbacks.append({
                "id": "1",
                "policy_name": policy_row[0],
                "evaluation": policy_row[1],
                "score": 0.95,
                "created_at": reviewed_at.isoformat() if reviewed_at else None
            })
        
        cur.close()
        conn.close()
        
        return {
            "finding_id": finding_id,
            "state": decision_score or "under_review",
            "decision": rationale,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
            "policy_feedbacks": policy_feedbacks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/policy_evaluate_action")
async def policy_evaluate_endpoint(body: PolicyEvalPayload):
    result = policy_evaluate_action(action=body.action, fact_set=body.fact_set)
    return result


@app.post("/v1/finding_create_or_update")
async def finding_upsert_endpoint(body: FindingUpsertPayload):
    # parse optional datetime string
    sla_dt = None
    if body.sla_due_at:
        from datetime import datetime
        sla_dt = datetime.fromisoformat(body.sla_due_at)

    result = finding_create_or_update(
        idempotency_key=body.idempotency_key,
        cve_id=body.cve_id,
        asset_id=body.asset_id,
        status=body.status,
        proposed_severity=body.proposed_severity,
        approved_severity=body.approved_severity,
        exploitability_score=body.exploitability_score,
        exploitability_rationale=body.exploitability_rationale,
        remediation_priority=body.remediation_priority,
        sla_due_at=sla_dt,
        owner_team=body.owner_team,
        decision_state=body.decision_state,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.post("/v1/memory_search_similar")
async def memory_search_endpoint(body: MemorySearchPayload):
    query_vector = body.query_vector
    if not query_vector:
        if not body.query_text:
            raise HTTPException(
                status_code=400,
                detail="Either query_vector or query_text must be provided.",
            )
        try:
            query_vector = embed_text(body.query_text)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=f"Titan embedding failed: {exc}")

    result = memory_search_similar(
        query_vector=query_vector,
        limit=body.limit,
        filters=body.filters,
        similarity_threshold=body.similarity_threshold,
    )
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@app.post("/v1/memory_store")
async def memory_store_endpoint(body: MemoryStorePayload):
    result = memory_store(
        summary=body.summary,
        incident_jsonb=body.incident_jsonb,
        tags=body.tags,
        idempotency_key=body.idempotency_key,
    )
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
