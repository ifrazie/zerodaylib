"""
Tool: policy_evaluate_action

Evaluate requested actions against deterministic policy rules stored in CockroachDB.
Returns allow/deny/manual_review with rationale and the matched rule.
Governance agents use this to gate high-risk mutations and operational state changes.
"""
import json
import psycopg
from typing import Any, Literal, Optional
from .contracts import PolicyEvalRequest, DecisionScore

from .db import get_psycopg_conn


def _rule_matches(predicate: dict, fact_set: dict) -> bool:
    """Deterministic predicate matching (atomic unit)"""
    # Simple key/val match
    if len(predicate) == 1 and all(k not in predicate for k in ("and", "or", "not")):
        key = next(iter(predicate))
        return fact_set.get(key) == predicate[key]

    # Logical gates
    ops = predicate.get("and", []) or predicate.get("or", []) or predicate.get("not")
    if isinstance(ops, list):
        if predicate.get("and"):
            return all(_rule_matches(op, fact_set) for op in ops)
        if predicate.get("or"):
            return any(_rule_matches(op, fact_set) for op in ops)
    # NOT fallback
    not_rule = predicate.get("not")
    if not_rule:
        return not _rule_matches(not_rule, fact_set)
    return True


def policy_evaluate_action(action: str, fact_set: dict) -> dict[str, Any]:
    """
    Evaluate action against policy_rules and return allow/deny/manual_review and rationale.

    Returns: {
        decision: 'allow'|'deny'|'manual_review',
        matched_rule_id: Optional[uuid],
        matched_rule_name: Optional[str],
        rationale: str,
        enabled_many: int,  // total enabled rules
        evaluated: int      // rules that matched predicate
    }
    """
    conn = get_psycopg_conn()
    cur = conn.cursor()

    try:
        # Fetch all enabled rules
        cur.execute("SELECT rule_id, name, predicate_json, decision, rationale FROM policy_rules WHERE enabled = true")
        rules = [
            {
                "rule_id": row[0],
                "name": row[1],
                "predicate": (json.loads(row[2]) if isinstance(row[2], (str, bytes, bytearray)) else (row[2] or {})),
                "decision": row[3],
                "rationale": row[4] or "",
            }
            for row in cur
        ]
        enabled_many = len(rules)

        matched = []
        for r in rules:
            if _rule_matches(r["predicate"], fact_set):
                matched.append(r)
        evaluated = len(matched)

        if not matched:
            # No rule matched -> default posture: deny
            return {
                "decision": "deny",
                "matched_rule_id": None,
                "matched_rule_name": None,
                "rationale": "No policy rule matched; default deny posture.",
                "enabled_many": enabled_many,
                "evaluated": evaluated,
            }

        # Most restrictive decision wins (deny > manual_review > allow) for a
        # deterministic, security-first outcome when multiple rules match.
        severity_rank = {"deny": 0, "manual_review": 1, "allow": 2}
        final = min(matched, key=lambda r: severity_rank.get(r["decision"], 99))
        return {
            "decision": final["decision"],
            "matched_rule_id": str(final["rule_id"]),
            "matched_rule_name": final["name"],
            "rationale": final["rationale"],
            "enabled_many": enabled_many,
            "evaluated": evaluated,
        }
    finally:
        cur.close()
        conn.close()
