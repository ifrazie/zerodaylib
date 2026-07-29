<#
.SYNOPSIS
    Bring up the full Zero Day Librarian stack locally for testing (Windows/PowerShell).

.DESCRIPTION
    Starts the FastAPI backend (uvicorn) on http://127.0.0.1:8000 and the
    Next.js frontend (next dev) on http://localhost:3000. The backend uses
    COCKROACH_URL from agentcore/.env.local to talk to CockroachDB Cloud.

.PARAMETER BackendOnly
    Start only the backend.

.PARAMETER FrontendOnly
    Start only the frontend.

.PARAMETER NoInstall
    Skip dependency installation.

.PARAMETER Clean
    Wipe the frontend .next/out cache before starting (fixes stale
    "missing generateStaticParams()" errors after editing route exports).

.PARAMETER ExtraSeed
    Also apply backend/db/seed_extra_findings.sql. Additive and idempotent:
    fills the dashboard table with a fuller spread of findings for demos and
    screenshots, without touching the base camera-ready scenario.

.EXAMPLE
    ./scripts/dev.ps1
    ./scripts/dev.ps1 -BackendOnly
    ./scripts/dev.ps1 -Clean
    ./scripts/dev.ps1 -ExtraSeed
#>
[CmdletBinding()]
param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoInstall,
    [switch]$Clean,
    [switch]$ExtraSeed
)

$ErrorActionPreference = "Stop"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir     = Split-Path -Parent $ScriptDir
$BackendDir  = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$EnvFile     = Join-Path $RootDir "agentcore/.env.local"
$LogDir      = Join-Path $RootDir ".dev-logs"

$BackendHost = "127.0.0.1"
$BackendPort = 8000
$FrontendPort = 3000

$RunBackend  = -not $FrontendOnly
$RunFrontend = -not $BackendOnly
$DoInstall   = -not $NoInstall

function Info($m) { Write-Host "[dev] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[dev] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[dev] $m" -ForegroundColor Yellow }
function Err($m)  { Write-Host "[dev] $m" -ForegroundColor Red }

# --- Load COCKROACH_URL ------------------------------------------------------
if (-not $env:COCKROACH_URL) {
    if (Test-Path $EnvFile) {
        Info "Loading COCKROACH_URL from $EnvFile"
        $line = Select-String -Path $EnvFile -Pattern '^COCKROACH_URL=' | Select-Object -First 1
        if ($line) {
            $val = $line.Line -replace '^COCKROACH_URL=', '' -replace '^"', '' -replace '"$', ''
            $env:COCKROACH_URL = $val
        }
    }
}
if ($env:COCKROACH_URL) { Ok "COCKROACH_URL is set." }
else { Warn "COCKROACH_URL not set; backend falls back to local insecure node." }

# --- Populate ZDL_GIT_COMMIT for the /api/system sidebar footer --------------
if (-not $env:ZDL_GIT_COMMIT) {
  try {
    $commit = (git -C $RootDir rev-parse --short HEAD 2>$null)
    if ($commit) { $env:ZDL_GIT_COMMIT = $commit; Info "ZDL_GIT_COMMIT=$commit" }
  } catch { }
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$script:Procs = @()

# --- Backend -----------------------------------------------------------------
function Start-Backend {
    Info "Preparing backend..."
    $venv = Join-Path $BackendDir ".venv"
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
    if (-not $python) { Err "No python interpreter found."; return }

    if ($DoInstall -and -not (Test-Path $venv)) {
        Info "Creating virtualenv at backend/.venv"
        & $python.Source -m venv $venv
    }

    $vpy = Join-Path $venv "Scripts/python.exe"
    if (-not (Test-Path $vpy)) { $vpy = $python.Source }

    if ($DoInstall) {
        Info "Installing backend dependencies..."
        & $vpy -m pip install --quiet --upgrade pip
        & $vpy -m pip install --quiet -r (Join-Path $BackendDir "requirements.txt")
        Ok "Backend dependencies ready."
    }

    # Optionally apply the additive "fuller table" seed. Additive and idempotent
    # (ON CONFLICT DO NOTHING with stable idempotency keys), so it is safe to
    # re-run and never touches the base camera-ready scenario. Applied via the
    # backend's own psycopg connection (no cockroach CLI dependency).
    if ($ExtraSeed) {
        Info "Applying extra findings seed (backend/db/seed_extra_findings.sql)..."
        $env:EXTRA_SEED_SQL = Join-Path $BackendDir "db/seed_extra_findings.sql"
        $py = @'
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))
from tools.db import get_psycopg_conn
with open(os.environ["EXTRA_SEED_SQL"], "r", encoding="utf-8") as f:
    sql = f.read()
conn = get_psycopg_conn()
conn.execute(sql)
conn.close()
print("extra-seed-ok")
'@
        $py | & $vpy -
        if ($LASTEXITCODE -eq 0) {
            Ok "Extra findings seed applied."
        } else {
            Warn "Extra findings seed failed (see backend output above)."
        }
    }

    # Backfill any semantic_memory rows missing a real Titan embedding. Safe
    # to re-run: rows that already have embedded_at set are skipped (see
    # backend/db/seed_embed.py). Requires AWS credentials with
    # bedrock:InvokeModel on amazon.titan-embed-text-v2:0; a failure here is
    # non-fatal for local dev.
    Info "Refreshing unembedded semantic_memory rows with Titan vectors..."
    & $vpy -m backend.db.seed_embed
    if ($LASTEXITCODE -eq 0) {
        Ok "Semantic memory embeddings are up to date."
    } else {
        Warn "seed_embed failed (missing AWS credentials?) - vector search may return unembedded rows."
    }

    Info "Starting backend on http://${BackendHost}:${BackendPort} (log: .dev-logs/backend.log)"
    $out = Join-Path $LogDir "backend.log"
    $p = Start-Process -FilePath $vpy `
        -ArgumentList @("-m","uvicorn","main:app","--host",$BackendHost,"--port",$BackendPort,"--reload") `
        -WorkingDirectory $BackendDir `
        -RedirectStandardOutput $out -RedirectStandardError (Join-Path $LogDir "backend.err.log") `
        -NoNewWindow -PassThru
    $script:Procs += $p
}

# --- Frontend ----------------------------------------------------------------
function Start-Frontend {
    Info "Preparing frontend..."
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npm) { Err "npm not found; cannot start frontend."; return }

    if ($DoInstall -and -not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Info "Installing frontend dependencies (npm install)..."
        Push-Location $FrontendDir; & npm install --silent; Pop-Location
        Ok "Frontend dependencies ready."
    }

    # Optionally wipe the Next.js build cache. next dev caches route metadata and
    # does not hot-reload changes to generateStaticParams/dynamicParams, which
    # surfaces as "missing generateStaticParams()" under output: 'export'.
    if ($Clean) {
        Info "Cleaning frontend build cache (.next, out)..."
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $FrontendDir ".next")
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $FrontendDir "out")
        Ok "Frontend cache cleared."
    }

    $fenv = Join-Path $FrontendDir ".env.local"
    if (-not (Test-Path $fenv) -or -not (Select-String -Path $fenv -Pattern '^NEXT_PUBLIC_API_BASE_URL=' -Quiet)) {
        Info "Writing frontend/.env.local with NEXT_PUBLIC_API_BASE_URL"
        Add-Content -Path $fenv -Value "NEXT_PUBLIC_API_BASE_URL=http://${BackendHost}:${BackendPort}"
    }

    Info "Starting frontend on http://localhost:${FrontendPort} (log: .dev-logs/frontend.log)"
    $out = Join-Path $LogDir "frontend.log"
    $p = Start-Process -FilePath "npm.cmd" `
        -ArgumentList @("run","dev","--","--port",$FrontendPort) `
        -WorkingDirectory $FrontendDir `
        -RedirectStandardOutput $out -RedirectStandardError (Join-Path $LogDir "frontend.err.log") `
        -NoNewWindow -PassThru
    $script:Procs += $p
}

function Wait-ForHttp($url, $name, $tries = 40) {
    Info "Waiting for $name at $url ..."
    for ($i = 0; $i -lt $tries; $i++) {
        try {
            Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null
            Ok "$name is up."; return $true
        } catch { Start-Sleep -Seconds 1 }
    }
    Warn "$name did not respond after ${tries}s (check .dev-logs/$name.log)."
    return $false
}

# --- Cleanup on Ctrl-C -------------------------------------------------------
$cleanup = {
    Write-Host ""
    Write-Host "[dev] Shutting down..." -ForegroundColor Cyan
    foreach ($p in $script:Procs) {
        if ($p -and -not $p.HasExited) {
            try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {}
        }
    }
    # uvicorn --reload and next dev spawn detached worker children that outlive
    # the launcher. Free the ports by killing whichever process is listening.
    foreach ($port in @($BackendPort, $FrontendPort)) {
        try {
            Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
        } catch {}
    }
    Write-Host "[dev] Stopped." -ForegroundColor Green
}

try {
    if ($RunBackend)  { Start-Backend }
    if ($RunFrontend) { Start-Frontend }

    if ($RunBackend)  { Wait-ForHttp "http://${BackendHost}:${BackendPort}/api/findings" "backend" 40 | Out-Null }
    if ($RunFrontend) { Wait-ForHttp "http://localhost:${FrontendPort}" "frontend" 60 | Out-Null }

    Write-Host ""
    Ok "Stack is running:"
    if ($RunBackend)  { Write-Host "   Backend API : http://${BackendHost}:${BackendPort}  (docs at /docs)" }
    if ($RunFrontend) { Write-Host "   Frontend UI : http://localhost:${FrontendPort}" }
    Write-Host "   Logs        : $LogDir/"
    Write-Host ""
    Info "Press Ctrl-C to stop."

    while ($true) {
        Start-Sleep -Seconds 1
        $alive = $script:Procs | Where-Object { $_ -and -not $_.HasExited }
        if (-not $alive) { Warn "All processes exited."; break }
    }
}
finally {
    & $cleanup
}
