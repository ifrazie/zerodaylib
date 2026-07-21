"""
Utility to get a psycopg connection to CockroachDB Cloud (zdl_db) with sane defaults.
Reads from env variables: COCKROACH_URL, COCKROACH_USER, COCKROACH_PASSWORD.
Fallback to local dev defaults for dev/testing.
"""
import os
from pathlib import Path
from typing import Any
import psycopg

# Bundled CockroachDB Cloud CA cert (downloaded from the cluster cert endpoint).
_BUNDLED_CA = Path(__file__).resolve().parents[1] / "certs" / "cc-ca.crt"


def _normalize_url(url: str) -> str:
    """Ensure verify-full connections have a usable root cert.

    CockroachDB Cloud serves certificates chained to a cluster CA. libpq
    (psycopg) needs a root cert to verify them. Resolution order:
      1. sslrootcert already present in the URL -> leave as-is
      2. COCKROACH_SSLROOTCERT env var -> use that path
      3. bundled backend/certs/cc-ca.crt -> use that
      4. fall back to the OS trust store (sslrootcert=system)
    """
    if "sslmode=verify-full" not in url or "sslrootcert=" in url:
        return url

    rootcert = os.environ.get("COCKROACH_SSLROOTCERT")
    if not rootcert and _BUNDLED_CA.exists():
        rootcert = str(_BUNDLED_CA)
    if not rootcert:
        rootcert = "system"

    sep = "&" if "?" in url else "?"
    return f"{url}{sep}sslrootcert={rootcert}"


def get_psycopg_conn() -> psycopg.Connection[Any]:
    """Return a psycopg connection to zdl_db in CockroachDB Cloud (AWS us-east-1)."""
    url = os.environ.get("COCKROACH_URL") or "postgresql://root@localhost:26257/zdl_db?sslmode=require"
    url = _normalize_url(url)

    conn = psycopg.connect(
        conninfo=url,
        autocommit=True,  # CRDB needs autocommit unless explicit transactions
        connect_timeout=10,  # fail fast on an unreachable host instead of hanging forever
    )
    return conn
