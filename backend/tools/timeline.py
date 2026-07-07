"""
Tool: timeline_append_event

Append immutable audit events to action_timeline. Enforces append-only semantics
over zero-day librarian agent actions, human decisions, and system mutations.
Used by agents to record operational decisions and by governance to prove compliance.
"""
import json
import psycopg
from typing import Any, Optional
from datetime import datetime
from .contracts import TimelineAppendRequest

from .db import get_psycopg_conn


def timeline_append_event(
    finding_id: Optional[str],
    actor_type: str,
    actor_id: str,
    action: str,
    target_table: Optional[str],
    target_id: Optional[str],
    payload_json: dict,
) -> dict[str, Any]:
    """
    Append an immutable audit event into action_timeline.

    Returns {event_id, created_at, success, error}.
    """
    conn = get_psycopg_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO action_timeline
                (finding_id, actor_type, actor_id, action, target_table, target_id, payload_json)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s)
            RETURNING event_id, created_at
            """,
            (
                finding_id,
                actor_type,
                actor_id,
                action,
                target_table,
                target_id,
                json.dumps(payload_json) if payload_json is not None else None,
            ),
        )
        row = cur.fetchone()
        return {
            "event_id": str(row[0]),
            "created_at": row[1].isoformat(),
            "success": True,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
