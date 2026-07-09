<#
.SYNOPSIS
    Build the ZDL frontend read API Lambda package (zdl-api-handler.zip) on Windows.

.DESCRIPTION
    Packages the FastAPI app (backend/main.py) + Mangum entrypoint (api_lambda.py)
    + embedding client + tools/ + certs/ together with ARM64 wheels for
    fastapi / mangum / pydantic into dist/zdl-api-handler.zip.

    Building ARM64 wheels requires Docker + Linux, which is cleanest under WSL.
    This script therefore delegates to the bash builder:

        wsl bash backend/package_api_lambda.sh

    Run it directly in WSL/Linux/macOS instead if you prefer.

.EXAMPLE
    ./backend/package_api_lambda.ps1
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir

function Info($m) { Write-Host "[package-api] $m" -ForegroundColor Cyan }

Info "The API Lambda requires ARM64 Linux wheels (Docker). Delegating to WSL bash builder..."
Info "If this fails, run in WSL/Linux/macOS: bash backend/package_api_lambda.sh"

$relScript = "backend/package_api_lambda.sh"
Push-Location $RootDir
try {
    wsl bash $relScript
} finally {
    Pop-Location
}
