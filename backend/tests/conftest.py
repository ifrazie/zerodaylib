"""Shared pytest fixtures for backend tool tests.

These tests run against the live CockroachDB Cloud `zdl_db` seeded via
backend/db/schema.sql + backend/db/seed.sql. Set COCKROACH_URL in the
environment (loaded from agentcore/.env.local) before running:

    export $(grep '^COCKROACH_URL=' agentcore/.env.local | sed 's/"//g')
    python -m pytest backend/tests -v

Vector-search tests additionally require semantic_memory rows to carry real
Titan embeddings. Run `python -m backend.db.seed_embed` once against the
live cluster before running those tests (scripts/dev.sh and scripts/dev.ps1
do this automatically for local dev).

Test layers
-----------
  test_tools.py          — tool contracts called directly (existing)
  test_lambda_handler.py — Lambda gateway dispatch, called as the gateway does
  test_api.py            — FastAPI HTTP endpoints (via TestClient + api_client)
  test_agent_behavior.py — end-to-end agent runs (opt-in: AGENTCORE_INVOKE=1)
  test_db_invariants.py  — live-schema health-check assertions

The canonical seeded scenario (backend/db/seed.sql) is exposed via the
`seeded_finding_id` and `seeded_finding_key` fixtures so behavioral and API
tests can anchor to a known finding without hard-coding UUIDs in each test.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

from backend.tools.db import get_psycopg_conn

# Canonical seed constants (backend/db/seed.sql).
SEEDED_FINDING_ID = "b2c3d4e5-6f70-48a9-90b1-a2b3c4d5e6f7"
SEEDED_FINDING_KEY = "ingest-CVE-2024-7169-api-prodcolasld-1"
SEEDED_ASSET_ID = "4bf51d97-474c-4244-8806-7c545565915d"
SEEDED_CVE_ID = "CVE-2024-7169"

# Preferred dev-server port for each runtime (matches agentcore's default offset
# from 8080). If a port is already in use the fixture allocates an ephemeral
# replacement so stale listeners from a previous run never block the tests.
_PREFERRED_PORTS = {
    "zdl_supervisorAgent": 8080,
    "zdl_ingestAgent": 8081,
    "zdl_governanceAgent": 8082,
}


def _find_free_port(preferred: int) -> int:
    """Return `preferred` if nothing is actively listening on it, otherwise
    bind an ephemeral port and return that.

    We test by attempting a real TCP connection (not just a bind), which
    correctly detects ports reserved by Windows Hyper-V / dynamic exclusion
    that SO_REUSEADDR bind probes incorrectly report as available.
    """
    def _is_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", port))
                return True  # something accepted the connection
            except (ConnectionRefusedError, TimeoutError, OSError):
                pass
        # Also check via a bind attempt with SO_EXCLUSIVEADDRUSE on Windows
        # to catch kernel-reserved ports that refuse connections but can't be bound.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)  # type: ignore[attr-defined]
            try:
                s.bind(("127.0.0.1", port))
                return False  # exclusive bind succeeded → port is genuinely free
            except OSError:
                return True   # can't bind → port is reserved or in use

    if not _is_in_use(preferred):
        return preferred

    # Preferred port is occupied; let the OS pick an ephemeral one.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session", autouse=True)
def _clear_stale_bedrock_token():
    """Remove AWS_BEARER_TOKEN_BEDROCK if present.

    The agentcore Comet web UI injects a short-lived Bedrock bearer token into
    its process environment, which child processes (including pytest) inherit.
    When this token expires, boto3's Bedrock clients fail with
    'AccessDeniedException: Bearer Token has expired' even for standard IAM
    calls to bedrock-runtime (Titan embedding).

    Unsetting the variable restores normal IAM credential chain resolution,
    which uses the long-lived key in ~/.aws/credentials.
    """
    os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)


@pytest.fixture(scope="session")
def dev_conn():
    """A session-scoped psycopg connection to the seeded zdl_db."""
    if not os.environ.get("COCKROACH_URL"):
        pytest.skip("COCKROACH_URL not set; skipping DB-backed tool tests")
    conn = get_psycopg_conn()
    yield conn
    conn.close()


@pytest.fixture()
def require_embedded_memory(dev_conn):
    """Skip vector-search tests if semantic_memory has no real embeddings yet.

    Guards against the case where schema/seed have been applied but
    `python -m backend.db.seed_embed` has not been run against this cluster.
    """
    count = dev_conn.execute(
        "SELECT count(*) FROM semantic_memory WHERE embedded_at IS NOT NULL"
    ).fetchone()[0]
    if count == 0:
        pytest.skip(
            "No embedded semantic_memory rows; run "
            "'python -m backend.db.seed_embed' against this cluster first."
        )


@pytest.fixture()
def cleanup_test_rows(dev_conn):
    """Remove rows created by tests (idempotency keys / actors prefixed 'test-')."""
    yield
    dev_conn.execute("DELETE FROM action_timeline WHERE actor_id = 'pytest'")
    dev_conn.execute("DELETE FROM findings WHERE idempotency_key LIKE 'test-%'")
    dev_conn.execute("DELETE FROM semantic_memory WHERE idempotency_key LIKE 'test-%'")


# --- Layer 2: FastAPI HTTP client --------------------------------------------

@pytest.fixture(scope="session")
def api_client():
    """A FastAPI TestClient over backend.main.app, backed by the live zdl_db.

    Requires COCKROACH_URL (the app's endpoints call get_psycopg_conn()).
    """
    if not os.environ.get("COCKROACH_URL"):
        pytest.skip("COCKROACH_URL not set; skipping API endpoint tests")
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as client:
        yield client


# --- Layer 3: end-to-end agent invocation via `agentcore dev` ----------------

def _wait_for_dev_server(port: int, timeout: float = 90.0) -> bool:
    """Poll /invocations until the dev server accepts connections.

    The endpoint only accepts POST, so a GET/HEAD returns 405 — that is enough
    to confirm the server is up. Any response code other than a connection error
    counts as ready.
    """
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/invocations"
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True  # 200 (unlikely) also works
        except urllib.error.HTTPError:
            return True  # 405 / 4xx → server is up, wrong method is fine
        except Exception:
            time.sleep(1.0)
    return False


@pytest.fixture()
def agentcore_invoke():
    """Factory that runs a prompt against a locally-started `agentcore dev` server.

    Opt-in: skipped unless AGENTCORE_INVOKE=1. These tests are slow (real LLM
    calls) and route tool calls through the LIVE gateway → Lambda → CockroachDB,
    so they require working AWS credentials and gateway connectivity.

    Usage:
        response_text = agentcore_invoke(runtime="zdl_ingestAgent", prompt="...")

    The dev server for the requested runtime is started once per invocation on a
    free port (falling back from the preferred port if it is occupied), the prompt
    is sent via a second `agentcore dev` subprocess, and the server is torn down
    in fixture teardown. Returns combined stdout+stderr from the invocation.

    Environment: all KEY=VALUE pairs from agentcore/.env.local are merged into
    the subprocess environment so that the gateway URL, COCKROACH_URL, and memory
    IDs are available to the agent code — mirroring what `agentcore dev` normally
    loads from that file.
    """
    if os.environ.get("AGENTCORE_INVOKE") != "1":
        pytest.skip("AGENTCORE_INVOKE != 1; skipping end-to-end agent behavioral tests")

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    servers: list[subprocess.Popen] = []

    def _invoke(runtime: str, prompt: str, timeout: int = 600) -> str:
        port = _find_free_port(_PREFERRED_PORTS[runtime])

        # shell=True is required on Windows for agentcore (a Node.js CLI shim).
        # encoding='utf-8' + errors='replace' avoids cp1252 codec failures from
        # Unicode characters in the agent's streamed output on Windows terminals.
        # Do NOT pass env= here: agentcore dev reads agentcore/.env.local itself
        # (including GATEWAY_*, COCKROACH_URL, and MEMORY_* vars) and injects
        # them into the Python subprocess. Passing an explicit env= would replace
        # the parent environment and break agentcore's own env loading.
        server = subprocess.Popen(
            f"agentcore dev -r {runtime} --logs --no-browser --port {port}",
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            encoding="utf-8",
            errors="replace",
        )
        servers.append(server)

        # Drain the server's stdout until it prints the "Server: http://…" ready
        # line, then fall back to HTTP polling for the actual port bind.
        ready_seen = False
        deadline = time.time() + 30
        while time.time() < deadline:
            line = server.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
            if f"localhost:{port}" in line:
                ready_seen = True
                break

        if not ready_seen:
            raise RuntimeError(
                f"agentcore dev server for {runtime} did not print the ready line "
                f"(expected 'Server: http://localhost:{port}/invocations')"
            )

        if not _wait_for_dev_server(port):
            raise RuntimeError(
                f"agentcore dev server for {runtime} never became reachable on :{port}"
            )

        # Send the prompt to the running dev server.
        # Newlines in the prompt are replaced with spaces — the agent receives
        # the same semantic content. Double-quotes in the prompt are escaped.
        # capture_output=True is incompatible with shell=True on Windows; set
        # PIPE explicitly and decode with utf-8/replace.
        safe_prompt = prompt.replace("\n", " ").replace('"', '\\"')
        result = subprocess.run(
            f'agentcore dev -r {runtime} "{safe_prompt}"',
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return (result.stdout or "") + (result.stderr or "")

    yield _invoke

    for server in servers:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()


@pytest.fixture()
def cleanup_agent_rows(dev_conn):
    """Teardown for behavioral tests: remove agent-created CVEs/memories/events.

    Agent tests seed distinctive CVE ids (CVE-2024-*-TEST) and idempotency keys
    (test-agent-*), plus policy_check events on the seeded finding written during
    the run window. This cleans them all up by default so fair-dolphin stays tidy.
    """
    yield
    dev_conn.execute("DELETE FROM findings WHERE idempotency_key LIKE 'test-agent-%'")
    dev_conn.execute("DELETE FROM findings WHERE cve_id LIKE 'CVE-2024-%-TEST'")
    dev_conn.execute(
        "DELETE FROM semantic_memory WHERE incident_jsonb->>'cve_id' LIKE 'CVE-2024-%-TEST'"
    )
    dev_conn.execute("DELETE FROM semantic_memory WHERE idempotency_key LIKE 'test-agent-%'")
    dev_conn.execute(
        "DELETE FROM action_timeline WHERE finding_id = %s AND actor_id = 'zdl_governance' "
        "AND created_at > now() - INTERVAL '30 minutes'",
        (SEEDED_FINDING_ID,),
    )


@pytest.fixture()
def seeded_finding_id():
    """The canonical seeded finding UUID (backend/db/seed.sql)."""
    return SEEDED_FINDING_ID


@pytest.fixture()
def seeded_finding_key():
    """The canonical seeded finding idempotency_key (backend/db/seed.sql)."""
    return SEEDED_FINDING_KEY
