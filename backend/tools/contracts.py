"""
Tool contracts and reusable business logic for Zero Day Librarian.

These modules implement the core operations that agents invoke via the gateway.
The same code is used:
- locally: by a FastAPI service for testing/iterating
- remotely: wrapped in an AWS Lambda MCP handler (zdl-tools-handler)

Contracts are: timeline_append_event, policy_evaluate_action, finding_create_or_update.
"""
from typing import TypedDict, Literal, Optional, Any
from datetime import datetime
import uuid

# --- Shared types and constants ---

# Map closely to zDL database schemas
class TimelineAppendRequest(TypedDict):
    finding_id: Optional[uuid.UUID]  # optional; nullable per schema
    actor_type: str
    actor_id: str
    action: str
    target_table: Optional[str]
    target_id: Optional[str]
    payload_json: dict[str, Any]

class PolicyEvalRequest(TypedDict):
    action: str
    fact_set: dict[str, Any]  # unstructured facts for predicate matching

class FindingUpsertRequest(TypedDict):
    idempotency_key: str
    cve_id: Optional[str]
    asset_id: Optional[uuid.UUID]
    status: Optional[str]
    proposed_severity: Optional[str]
    approved_severity: Optional[str]
    exploitability_score: Optional[float]
    exploitability_rationale: Optional[str]
    remediation_priority: Optional[str]
    sla_due_at: Optional[datetime]
    owner_team: Optional[str]
    decision_state: Optional[str]

# Decision outcomes from policy ( presidio + hackathon safety posture )
DecisionScore = Literal["allow", "deny", "manual_review"]

RulePredicate = dict[str, Any]  # atomic predicate unit
RuleSet = list[dict[str, Any]]  # list of {name, predicate, decision, rationale, enabled}
