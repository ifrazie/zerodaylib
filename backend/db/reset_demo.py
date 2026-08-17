"""
backend/db/reset_demo.py — Reset the three demo-target findings to their known
pre-remediation baseline so the remediation-agent demo is repeatable.

Before each demo take, the remediation agent will have mutated the DB state of a
few findings (status / decision_state) and appended REMEDIATION_EXECUTED audit
rows to action_timeline. This script re-asserts the baseline for those three
findings and removes their remediation audit events, so every take starts from
the same place.

Idempotent: running it when nothing has changed simply re-asserts the baseline
(the UPDATEs are absolute, and the DELETE is a no-op when there are no
REMEDIATION_EXECUTED rows). Safe to run repeatedly.

Usage:
    python -m backend.db.reset_demo      # from repo root
    python backend/db/reset_demo.py      # direct

Requires:
    COCKROACH_URL — CockroachDB connection string. If unset, it is loaded from
    agentcore/.env.local (a line of the form COCKROACH_URL="postgresql://...").
    This mirrors how scripts/dev.sh resolves the URL. Connection + TLS handling
    is reused from backend/tools/db.py (get_psycopg_conn).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import psycopg

# Allow running as a standalone script (python backend/db/reset_demo.py) as well
# as a module (python -m backend.db.reset_demo). When run directly, the repo root
# is not on sys.path, so the `backend.tools.db` import would fail; add it here.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.tools.db import get_psycopg_conn  # noqa: E402

# Repo-relative path to the env file scripts/dev.sh loads COCKROACH_URL from.
_ENV_FILE = _REPO_ROOT / "agentcore" / ".env.local"

# The three designated demo-target findings and their required baseline state.
# (finding_id, baseline_status, baseline_decision_state)
_DEMO_BASELINE: list[tuple[str, str, str]] = [
    ("f0000000-0000-4000-8000-000000000005", "investigating", "allow"),
    ("f0000000-0000-4000-8000-000000000006", "new", "allow"),
    ("f0000000-0000-4000-8000-000000000007", "new", "allow"),
]

_DEMO_FINDING_IDS: list[str] = [row[0] for row in _DEMO_BASELINE]

# Remediation audit events for these findings must be cleared before each take.
_REMEDIATION_ACTION = "REMEDIATION_EXECUTED"


def _load_cockroach_url_from_env_file() -> None:
    """Populate COCKROACH_URL from agentcore/.env.local if not already in env.

    Mirrors scripts/dev.sh: find the `COCKROACH_URL=` line, strip surrounding
    double quotes, and export it. No-op if COCKROACH_URL is already set or the
    file does not exist.
    """
    if os.environ.get("COCKROACH_URL"):
        return
    if not _ENV_FILE.exists():
        return
    for raw_line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("COCKROACH_URL="):
            continue
        value = line[len("COCKROACH_URL="):].strip()
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        if value:
            os.environ["COCKROACH_URL"] = value
        return


def reset_demo_findings(conn: psycopg.Connection[Any]) -> tuple[dict[str, int], int]:
    """Re-assert the demo baseline in a single transaction.

    UPDATEs each of the three findings to its baseline status + decision_state
    (stamping updated_at = now()), then DELETEs any REMEDIATION_EXECUTED rows in
    action_timeline for those findings.

    Returns (updated_per_finding, timeline_rows_deleted), where
    updated_per_finding maps finding_id -> rows updated (0 or 1).
    """
    updated_per_finding: dict[str, int] = {}

    # get_psycopg_conn() returns an autocommit connection; wrap the mutations in
    # an explicit transaction block so all resets commit atomically.
    with conn.transaction():
        cur = conn.cursor()
        for finding_id, status, decision_state in _DEMO_BASELINE:
            cur.execute(
                "UPDATE findings "
                "SET status = %s, decision_state = %s, updated_at = now() "
                "WHERE finding_id = %s",
                (status, decision_state, finding_id),
            )
            updated_per_finding[finding_id] = cur.rowcount

        cur.execute(
            "DELETE FROM action_timeline "
            "WHERE finding_id = ANY(%s) AND action = %s",
            (_DEMO_FINDING_IDS, _REMEDIATION_ACTION),
        )
        timeline_deleted = cur.rowcount

    return updated_per_finding, timeline_deleted


def reset_demo() -> None:
    """CLI entry point: reset the three demo findings to their baseline."""
    _load_cockroach_url_from_env_file()
    if not os.environ.get("COCKROACH_URL"):
        print(
            "ERROR: COCKROACH_URL is not set and was not found in "
            f"{_ENV_FILE}.\n"
            "Set COCKROACH_URL (or add a COCKROACH_URL=\"postgresql://...\" line "
            "to agentcore/.env.local) and re-run.",
            file=sys.stderr,
        )
        sys.exit(1)

    conn = get_psycopg_conn()
    try:
        updated_per_finding, timeline_deleted = reset_demo_findings(conn)
    finally:
        conn.close()

    print("Demo reset complete. Baseline re-asserted for 3 finding(s):")
    for finding_id, status, decision_state in _DEMO_BASELINE:
        rows = updated_per_finding.get(finding_id, 0)
        note = "" if rows else "  (WARNING: no such finding_id in DB)"
        print(
            f"  {finding_id} -> status={status!r}, decision_state={decision_state!r} "
            f"({rows} row updated){note}"
        )
    print(
        f"Deleted {timeline_deleted} {_REMEDIATION_ACTION} timeline row(s) "
        "for those findings."
    )


if __name__ == "__main__":
    reset_demo()
