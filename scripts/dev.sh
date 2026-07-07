#!/usr/bin/env bash
#
# dev.sh — Bring up the full Zero Day Librarian stack locally for testing.
#
# Starts:
#   - FastAPI backend  (uvicorn) on http://127.0.0.1:8000
#   - Next.js frontend (next dev) on http://127.0.0.1:3000
#
# The backend talks to the live CockroachDB Cloud `zdl_db` using COCKROACH_URL
# from agentcore/.env.local. Nothing is torn down in the database.
#
# Usage:
#   ./scripts/dev.sh            # install deps if needed, start both, stream logs
#   ./scripts/dev.sh --backend  # backend only
#   ./scripts/dev.sh --frontend # frontend only
#   ./scripts/dev.sh --no-install  # skip dependency install
#
# Press Ctrl-C to stop everything.

set -euo pipefail

# --- Resolve paths -----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
ENV_FILE="$ROOT_DIR/agentcore/.env.local"
LOG_DIR="$ROOT_DIR/.dev-logs"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8000"
FRONTEND_PORT="3000"

RUN_BACKEND=1
RUN_FRONTEND=1
DO_INSTALL=1

for arg in "$@"; do
  case "$arg" in
    --backend)    RUN_FRONTEND=0 ;;
    --frontend)   RUN_BACKEND=0 ;;
    --no-install) DO_INSTALL=0 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

# --- Pretty logging ----------------------------------------------------------
c_reset=$'\033[0m'; c_blue=$'\033[34m'; c_green=$'\033[32m'; c_yellow=$'\033[33m'; c_red=$'\033[31m'
info()  { echo "${c_blue}[dev]${c_reset} $*"; }
ok()    { echo "${c_green}[dev]${c_reset} $*"; }
warn()  { echo "${c_yellow}[dev]${c_reset} $*"; }
err()   { echo "${c_red}[dev]${c_reset} $*" >&2; }

# --- Pick a python interpreter ----------------------------------------------
PYTHON=""
for cand in python python3 py; do
  if command -v "$cand" >/dev/null 2>&1; then PYTHON="$cand"; break; fi
done
if [ -z "$PYTHON" ]; then err "No python interpreter found on PATH."; exit 1; fi

# --- Load COCKROACH_URL from agentcore/.env.local ----------------------------
if [ -z "${COCKROACH_URL:-}" ]; then
  if [ -f "$ENV_FILE" ]; then
    info "Loading COCKROACH_URL from $ENV_FILE"
    # Extract the value, strip surrounding quotes.
    line="$(grep -E '^COCKROACH_URL=' "$ENV_FILE" | head -n1 || true)"
    if [ -n "$line" ]; then
      COCKROACH_URL="${line#COCKROACH_URL=}"
      COCKROACH_URL="${COCKROACH_URL%\"}"; COCKROACH_URL="${COCKROACH_URL#\"}"
      export COCKROACH_URL
    fi
  fi
fi
if [ -z "${COCKROACH_URL:-}" ]; then
  warn "COCKROACH_URL not set and not found in $ENV_FILE."
  warn "Backend will fall back to postgresql://root@localhost:26257/zdl_db (local insecure node)."
else
  ok "COCKROACH_URL is set."
fi

mkdir -p "$LOG_DIR"
PIDS=()

cleanup() {
  echo ""
  info "Shutting down..."
  for pid in "${PIDS[@]:-}"; do
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  # Best-effort kill of direct child process trees.
  pkill -P $$ 2>/dev/null || true

  # uvicorn --reload and next dev spawn detached worker children that do not
  # die with the launcher. On Windows (Git Bash) fall back to freeing the
  # ports by PID; on POSIX use pkill patterns.
  if command -v powershell >/dev/null 2>&1; then
    for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
      powershell -NoProfile -Command "
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
          ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }
      " 2>/dev/null || true
    done
  else
    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "next-server" 2>/dev/null || true
  fi
  ok "Stopped."
}
trap cleanup EXIT INT TERM

# --- Backend setup + start ---------------------------------------------------
start_backend() {
  info "Preparing backend..."
  local venv="$BACKEND_DIR/.venv"
  local vpy

  if [ "$DO_INSTALL" -eq 1 ]; then
    if [ ! -d "$venv" ]; then
      info "Creating virtualenv at backend/.venv"
      "$PYTHON" -m venv "$venv"
    fi
  fi

  # Resolve the venv python (Windows uses Scripts/, POSIX uses bin/).
  if [ -x "$venv/Scripts/python.exe" ]; then
    vpy="$venv/Scripts/python.exe"
  elif [ -x "$venv/bin/python" ]; then
    vpy="$venv/bin/python"
  else
    warn "No venv python found; using system $PYTHON"
    vpy="$PYTHON"
  fi

  if [ "$DO_INSTALL" -eq 1 ]; then
    info "Installing backend dependencies..."
    "$vpy" -m pip install --quiet --upgrade pip
    "$vpy" -m pip install --quiet -r "$BACKEND_DIR/requirements.txt"
    ok "Backend dependencies ready."
  fi

  # Quick DB connectivity check (non-fatal).
  info "Checking database connectivity..."
  if COCKROACH_URL="${COCKROACH_URL:-}" "$vpy" - <<'PYEOF'
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))
try:
    from tools.db import get_psycopg_conn
    conn = get_psycopg_conn()
    conn.execute("SELECT 1")
    conn.close()
    print("db-ok")
except Exception as e:
    print(f"db-fail: {e}")
    sys.exit(3)
PYEOF
  then
    ok "Database reachable."
  else
    warn "Database check failed — backend will still start but API calls may error."
  fi

  # Backfill any semantic_memory rows missing a real Titan embedding. Safe to
  # re-run: rows that already have embedded_at set are skipped (see
  # backend/db/seed_embed.py). Requires AWS credentials with bedrock:InvokeModel
  # on amazon.titan-embed-text-v2:0; failures here are non-fatal for local dev.
  info "Refreshing unembedded semantic_memory rows with Titan vectors..."
  if COCKROACH_URL="${COCKROACH_URL:-}" "$vpy" -m backend.db.seed_embed 2>>"$LOG_DIR/backend.err.log"; then
    ok "Semantic memory embeddings are up to date."
  else
    warn "seed_embed failed (missing AWS credentials?) — vector search may return unembedded rows."
  fi

  info "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT (log: .dev-logs/backend.log)"
  (
    cd "$BACKEND_DIR"
    COCKROACH_URL="${COCKROACH_URL:-}" exec "$vpy" -m uvicorn main:app \
      --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload
  ) > "$LOG_DIR/backend.log" 2>&1 &
  PIDS+=("$!")
}

# --- Frontend setup + start --------------------------------------------------
start_frontend() {
  info "Preparing frontend..."
  if ! command -v npm >/dev/null 2>&1; then
    err "npm not found on PATH; cannot start frontend."
    return 1
  fi

  if [ "$DO_INSTALL" -eq 1 ] && [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    info "Installing frontend dependencies (npm install)..."
    (cd "$FRONTEND_DIR" && npm install --silent)
    ok "Frontend dependencies ready."
  fi

  # Ensure the API base URL points at our backend.
  local fenv="$FRONTEND_DIR/.env.local"
  if [ ! -f "$fenv" ] || ! grep -q '^NEXT_PUBLIC_API_BASE_URL=' "$fenv" 2>/dev/null; then
    info "Writing frontend/.env.local with NEXT_PUBLIC_API_BASE_URL"
    echo "NEXT_PUBLIC_API_BASE_URL=http://$BACKEND_HOST:$BACKEND_PORT" >> "$fenv"
  fi

  info "Starting frontend on http://localhost:$FRONTEND_PORT (log: .dev-logs/frontend.log)"
  (
    cd "$FRONTEND_DIR"
    exec npm run dev -- --port "$FRONTEND_PORT"
  ) > "$LOG_DIR/frontend.log" 2>&1 &
  PIDS+=("$!")
}

# --- Health checks -----------------------------------------------------------
wait_for_http() {
  local url="$1" name="$2" tries="${3:-30}"
  info "Waiting for $name at $url ..."
  for ((i=1; i<=tries; i++)); do
    if command -v curl >/dev/null 2>&1 && curl -sf -o /dev/null "$url"; then
      ok "$name is up."
      return 0
    fi
    sleep 1
  done
  warn "$name did not respond after ${tries}s (check .dev-logs/${name}.log)."
  return 1
}

# --- Orchestrate -------------------------------------------------------------
[ "$RUN_BACKEND" -eq 1 ]  && start_backend
[ "$RUN_FRONTEND" -eq 1 ] && start_frontend

if [ "$RUN_BACKEND" -eq 1 ]; then
  wait_for_http "http://$BACKEND_HOST:$BACKEND_PORT/api/findings" "backend" 40 || true
fi
if [ "$RUN_FRONTEND" -eq 1 ]; then
  wait_for_http "http://localhost:$FRONTEND_PORT" "frontend" 60 || true
fi

echo ""
ok "Stack is running:"
[ "$RUN_BACKEND" -eq 1 ]  && echo "   Backend API : http://$BACKEND_HOST:$BACKEND_PORT  (docs at /docs)"
[ "$RUN_FRONTEND" -eq 1 ] && echo "   Frontend UI : http://localhost:$FRONTEND_PORT"
echo "   Logs        : $LOG_DIR/"
echo ""
info "Press Ctrl-C to stop."

# Wait on all background jobs; cleanup runs via trap on exit.
wait
