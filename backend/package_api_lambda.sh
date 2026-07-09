#!/usr/bin/env bash
#
# backend/package_api_lambda.sh
#
# Build the deployment artifact for the ZDL frontend read API Lambda
# (zdl-api-handler), which serves the FastAPI app (backend/main.py) via Mangum
# behind API Gateway / CloudFront `/api/*`.
#
#   dist/zdl-api-handler.zip — self-contained handler: app code + FastAPI +
#                              Mangum + pydantic (ARM64 wheels). psycopg comes
#                              from the shared layer (dist/zdl-tools-layer.zip),
#                              boto3 from the Lambda runtime.
#
# Deps are installed as manylinux_2_28 aarch64 wheels so they run on the Lambda
# python3.12 ARM64 (Amazon Linux 2023) runtime. Docker is required.
#
# Usage:
#   cd <repo-root>
#   bash backend/package_api_lambda.sh
#
# Prerequisites:
#   - Docker (for ARM64 wheel install)
#   - python3 (for sha256)
#   - zip (optional; falls back to python zipfile)
#
# Output (relative to repo root):
#   dist/zdl-api-handler.zip
#   dist/api-handler-sha256.txt

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$SCRIPT_DIR"
DIST_DIR="$ROOT_DIR/dist"

info()  { echo "[package-api] $*"; }
ok()    { echo "[package-api] ✓ $*"; }
err()   { echo "[package-api] ✗ $*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || err "Docker is required to build ARM64 wheels. Install Docker and retry."

mkdir -p "$DIST_DIR"

BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

info "Installing API dependencies (ARM64 wheels) ..."
# fastapi, mangum, pydantic (+ their transitive deps) as aarch64 wheels.
# psycopg and boto3 are intentionally excluded (layer + runtime provide them).
docker run --rm --platform linux/arm64 \
  -v "$BUILD_DIR:/out" \
  python:3.12-slim-bookworm \
  pip install --quiet \
    "fastapi>=0.110" \
    "mangum>=0.17" \
    "pydantic>=2.6" \
    --platform manylinux_2_28_aarch64 \
    --only-binary=:all: \
    --target /out

info "Copying application code ..."
# HTTP entrypoint + FastAPI app + embedding client at the zip root.
cp "$BACKEND_DIR/api_lambda.py" "$BUILD_DIR/"
cp "$BACKEND_DIR/main.py"       "$BUILD_DIR/"
cp "$BACKEND_DIR/embed.py"      "$BUILD_DIR/"
[ -f "$BACKEND_DIR/__init__.py" ] && cp "$BACKEND_DIR/__init__.py" "$BUILD_DIR/" || true

# tools/ package (exclude caches, embed_titan, tests)
mkdir -p "$BUILD_DIR/tools"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --quiet \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='embed_titan.py' \
    --exclude='tests/' \
    "$BACKEND_DIR/tools/" "$BUILD_DIR/tools/"
else
  cp -r "$BACKEND_DIR/tools/"* "$BUILD_DIR/tools/"
  find "$BUILD_DIR/tools" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
  find "$BUILD_DIR/tools" -name '*.pyc' -delete 2>/dev/null || true
fi

# CA cert bundled at the path tools/db.py resolves:
# Path(__file__).resolve().parents[1] / "certs" / "cc-ca.crt" → zip-root/certs/
CERT_SRC="$BACKEND_DIR/certs/cc-ca.crt"
if [ -f "$CERT_SRC" ]; then
  mkdir -p "$BUILD_DIR/certs"
  cp "$CERT_SRC" "$BUILD_DIR/certs/cc-ca.crt"
  ok "Bundled certs/cc-ca.crt"
else
  info "Warning: backend/certs/cc-ca.crt not found — set COCKROACH_SSLROOTCERT in the Lambda env."
fi

API_ZIP="$DIST_DIR/zdl-api-handler.zip"
rm -f "$API_ZIP"
if command -v zip >/dev/null 2>&1; then
  (cd "$BUILD_DIR" && zip -qr "$API_ZIP" .)
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
" "$BUILD_DIR" "$API_ZIP"
fi

SHA=$(python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$API_ZIP")
echo "$SHA  zdl-api-handler.zip" > "$DIST_DIR/api-handler-sha256.txt"
ok "API handler zip: $API_ZIP  (sha256: ${SHA:0:16}...)"

echo ""
ok "Artifacts in $DIST_DIR:"
ls -lh "$DIST_DIR"/*.zip 2>/dev/null || true
