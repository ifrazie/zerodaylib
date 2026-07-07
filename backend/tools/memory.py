"""
Tool: memory_search_similar

Search semantic_memory for prior incidents similar to the current context.
This tool uses CockroachDB's distributed vector index (idx_memory_embedding)
to perform efficient nearest-neighbor search over 1024-dimensional Titan Text
v2 embeddings.

Intended for agents retrieving historical context and learning from prior
decisions or governance outcomes. By retrieving relevant prior cases,
agents can apply pattern recognition and avoid repeating the same mistakes.
Uses L2 distance over the VECTOR(1024) column; most similar matches have
the smallest distances. similarity_score = 1 / (1 + distance) is computed in
SQL so it can be used both for display and for threshold filtering.
"""
import psycopg
from typing import Any, Optional

from .db import get_psycopg_conn


def memory_search_similar(
    query_vector: list[float],
    limit: int = 3,
    filters: Optional[dict] = None,
    similarity_threshold: float = 0.0,
) -> dict[str, Any]:
    """
    Search for K nearest neighbors in semantic_memory.

    Params
      query_vector: A 1024-dim float list (Bedrock Titan Text v2 embedding).
      limit: Max results (1-10), default 3.
      filters: Optional flat k/v constraints on incident fields (e.g.,
               {"cve_id":"CVE-2024-1234"}). Only rows matching these are
               candidates, applied before vector ranking.
      similarity_threshold: Optional minimum similarity_score (0-1). Rows
               below this threshold are excluded from matches. Default 0.0
               (no filtering).

    Returns
      {
        matches: list[{memory_id, incident_jsonb, summary, tags, distance,
                        similarity_score}],
        limit: int,
        total_unfiltered: int (count of rows matching filters, before vector
                               ordering and before similarity_threshold),
        success: bool,
      }
    """
    if limit < 1 or limit > 10:
        limit = 3
    if similarity_threshold < 0.0 or similarity_threshold > 1.0:
        similarity_threshold = 0.0

    conn = get_psycopg_conn()
    cur = conn.cursor()

    try:
        qvec_expr = f"('[' || array_to_string(ARRAY{list(query_vector)}, ',') || ']')::VECTOR(1024)"

        where_clauses = []
        filter_args = []
        if filters:
            for k, v in filters.items():
                where_clauses.append(f"incident_jsonb->>'{k}' = %s")
                filter_args.append(str(v))

        where = "" if not where_clauses else "WHERE " + " AND ".join(where_clauses)

        # Total rows matching filters before vector ordering (unaffected by
        # similarity_threshold, which is a vector-ranking concern).
        count_sql = f"SELECT count(*) FROM semantic_memory {where}"
        cur.execute(count_sql, filter_args)
        total_unfiltered = cur.fetchone()[0]

        # Compute distance once in the CTE; derive similarity_score from it
        # in the outer query so both are available without recomputing the
        # vector distance twice.
        knn_sql = (
            "WITH ranked AS ("
            f"  SELECT memory_id, incident_jsonb, summary, tags,"
            f"         embedding <-> {qvec_expr} AS distance"
            f"  FROM semantic_memory {where}"
            ")"
            " SELECT memory_id, incident_jsonb, summary, tags, distance,"
            "        1.0 / (1.0 + distance) AS similarity_score"
            " FROM ranked"
            " WHERE 1.0 / (1.0 + distance) >= %s"
            " ORDER BY distance"
            " LIMIT %s"
        )
        cur.execute(knn_sql, (*filter_args, similarity_threshold, limit))
        rows = cur.fetchall()

        matches = []
        for mid, incident_jsonb, summary, tags, dist, score in rows:
            matches.append({
                "memory_id": str(mid),
                "incident_jsonb": incident_jsonb,
                "summary": summary,
                "tags": tags,
                "distance": float(dist),
                "similarity_score": float(score),
            })

        return {
            "matches": matches,
            "limit": limit,
            "total_unfiltered": total_unfiltered,
            "success": True,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()
