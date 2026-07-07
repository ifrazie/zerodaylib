#!/usr/bin/env bash
#
# backend/package_lambda.sh
#
# Build the two deployment artifacts for zdl-tools-handler:
#
#   dist/zdl-tools-layer.zip   — Lambda layer: psycopg[binary] (ARM64) + CA cert
#   dist/zdl-tools-handler.zip — Lambda handler: backend/tools/* + lambda_handler.py
#
# The layer uses a manylinux_2_28 ARM64 wheel so it runs on Amazon Linux 2023
# (Lambda python3.12 ARM64 runtime). Docker is required for the layer build.
# The handler zip is pure-Python and platform-independent.
#
# Usage:
#   cd <repo-root>
#   bash backend/package_lambda.sh          # build both artifacts
#   bash backend/package_lambda.sh --layer  # layer only (slower — needs Docker)
#   bash backend/package_lambda.sh --zip    # handler zip only (fast)
#
# Prerequisites:
#   - Docker (for --layer)
#   - python3 / pip (for --zip)
#   - zip / unzip
#
# Outputs (relative to repo root):
#   dist/zdl-tools-layer.zip
#   dist/zdl-tools-handler.zip
#   dist/layer-sha256.txt
#   dist/handler-sha256.txt

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$SCRIPT_DIR"
DIST_DIR="$ROOT_DIR/dist"

BUILD_LAYER=1
BUILD_ZIP=1

for arg in "$@"; do
  case "$arg" in
    --layer) BUILD_ZIP=0 ;;
    --zip)   BUILD_LAYER=0 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
  esac
done

info()  { echo "[package] $*"; }
ok()    { echo "[package] ✓ $*"; }
err()   { echo "[package] ✗ $*" >&2; exit 1; }

mkdir -p "$DIST_DIR"

# ── LAYER ZIP ────────────────────────────────────────────────────────────────
# psycopg[binary] must be the manylinux_2_28 aarch64 wheel so it runs inside
# the Lambda ARM64 Amazon Linux 2023 runtime without needing libpq headers.
# We use Docker to guarantee the correct platform even on a non-ARM host.
if [ "$BUILD_LAYER" -eq 1 ]; then
  info "Building psycopg layer (requires Docker, ARM64 target) ..."

  command -v docker >/dev/null 2>&1 || err "Docker is required to build the layer. Install Docker and retry."

  LAYER_BUILD_DIR="$(mktemp -d)"
  trap 'rm -rf "$LAYER_BUILD_DIR"' EXIT

  # Lambda layers must place site-packages under python/lib/pythonX.Y/site-packages/
  mkdir -p "$LAYER_BUILD_DIR/python/lib/python3.12/site-packages"

  docker run --rm --platform linux/arm64 \
    -v "$LAYER_BUILD_DIR/python/lib/python3.12/site-packages:/out" \
    python:3.12-slim-bookworm \
    pip install --quiet \
      "psycopg[binary]>=3.1" \
      "psycopg-binary>=3.1" \
      --platform manylinux_2_28_aarch64 \
      --only-binary=:all: \
      --target /out

  # Bundle the CockroachDB Cloud CA cert inside the layer so Lambda finds it
  # via the bundled path resolved in backend/tools/db.py.
  CERT_SRC="$BACKEND_DIR/certs/cc-ca.crt"
  if [ -f "$CERT_SRC" ]; then
    # db.py resolves: Path(__file__).parents[1] / "certs" / "cc-ca.crt"
    # In Lambda the handler is at /var/task/lambda_handler.py and tools/ is at
    # /var/task/tools/ so parents[1] is /var/task — cert goes there.
    CERT_DST="$LAYER_BUILD_DIR/python/lib/python3.12/site-packages/../../../certs/cc-ca.crt"
    # Simpler: bundle the cert in a well-known layer path and set COCKROACH_SSLROOTCERT
    # in the Lambda env instead. We do both: include in layer AND doc the env var.
    mkdir -p "$LAYER_BUILD_DIR/etc/zdl"
    cp "$CERT_SRC" "$LAYER_BUILD_DIR/etc/zdl/cc-ca.crt"
    info "Bundled cc-ca.crt → layer:/etc/zdl/cc-ca.crt (set COCKROACH_SSLROOTCERT=/etc/zdl/cc-ca.crt in Lambda env)"
  else
    info "Warning: backend/certs/cc-ca.crt not found — COCKROACH_SSLROOTCERT will need to be set manually."
  fi

  LAYER_ZIP="$DIST_DIR/zdl-tools-layer.zip"
  rm -f "$LAYER_ZIP"
  if command -v zip >/dev/null 2>&1; then
    (cd "$LAYER_BUILD_DIR" && zip -qr "$LAYER_ZIP" .)
  else
    python3 -c "
import zipfile, os, sys
src, dst = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src):
        for f in files:
            fp = os.path.join(root, f)
            zf.write(fp, os.path.relpath(fp, src))
" "$LAYER_BUILD_DIR" "$LAYER_ZIP"
  fi
  SHA=$(python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$LAYER_ZIP")
  echo "$SHA  zdl-tools-layer.zip" > "$DIST_DIR/layer-sha256.txt"
  ok "Layer zip: $LAYER_ZIP  (sha256: ${SHA:0:16}...)"
fi

# ── HANDLER ZIP ──────────────────────────────────────────────────────────────
# Pure-Python: lambda_handler.py + tools/ package.
# boto3 and psycopg are NOT included here (they come from the layer and the
# Lambda runtime respectively). embed_titan.py is excluded (not needed by handler).
if [ "$BUILD_ZIP" -eq 1 ]; then
  info "Building handler zip ..."

  HANDLER_BUILD_DIR="$(mktemp -d)"
  trap 'rm -rf "$HANDLER_BUILD_DIR"' EXIT

  # lambda_handler.py at root of zip
  cp "$BACKEND_DIR/lambda_handler.py" "$HANDLER_BUILD_DIR/"

  # tools/ package (exclude caches, embed_titan, test files)
  mkdir -p "$HANDLER_BUILD_DIR/tools"
  rsync -a --quiet \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='embed_titan.py' \
    --exclude='tests/' \
    "$BACKEND_DIR/tools/" "$HANDLER_BUILD_DIR/tools/" \
    2>/dev/null || {
      # rsync may not be available on all systems; fall back to cp
      cp -r "$BACKEND_DIR/tools/"* "$HANDLER_BUILD_DIR/tools/"
      find "$HANDLER_BUILD_DIR/tools" -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
      find "$HANDLER_BUILD_DIR/tools" -name '*.pyc' -delete 2>/dev/null || true
    }

  # Bundle the CA cert at the path db.py resolves relative to tools/db.py:
  # Path(__file__).resolve().parents[1] / "certs" / "cc-ca.crt"
  # In the zip: tools/db.py → parents[1] is the zip root → certs/cc-ca.crt
  CERT_SRC="$BACKEND_DIR/certs/cc-ca.crt"
  if [ -f "$CERT_SRC" ]; then
    mkdir -p "$HANDLER_BUILD_DIR/certs"
    cp "$CERT_SRC" "$HANDLER_BUILD_DIR/certs/cc-ca.crt"
    ok "Bundled certs/cc-ca.crt into handler zip"
  fi

  HANDLER_ZIP="$DIST_DIR/zdl-tools-handler.zip"
  rm -f "$HANDLER_ZIP"
  if command -v zip >/dev/null 2>&1; then
    (cd "$HANDLER_BUILD_DIR" && zip -qr "$HANDLER_ZIP" .)
  else
    python3 -c "
import zipfile, os, sys
src, dst = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if f.endswith('.pyc'): continue
            fp = os.path.join(root, f)
            zf.write(fp, os.path.relpath(fp, src))
print('Zipped via python zipfile module')
" "$HANDLER_BUILD_DIR" "$HANDLER_ZIP"
  fi
  SHA=$(python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$HANDLER_ZIP")
  echo "$SHA  zdl-tools-handler.zip" > "$DIST_DIR/handler-sha256.txt"
  ok "Handler zip: $HANDLER_ZIP  (sha256: ${SHA:0:16}...)"

  info "Handler zip contents:"
  python3 -c "
import zipfile, sys
with zipfile.ZipFile(sys.argv[1]) as z:
    for n in sorted(z.namelist()):
        print('  ', n)
" "$HANDLER_ZIP"
fi

echo ""
ok "Artifacts in $DIST_DIR:"
ls -lh "$DIST_DIR"/*.zip 2>/dev/null || true
