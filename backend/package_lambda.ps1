<#
.SYNOPSIS
    Build the zdl-tools-handler.zip Lambda deployment package on Windows.

.DESCRIPTION
    Packages lambda_handler.py + backend/tools/* + certs/cc-ca.crt into
    dist/zdl-tools-handler.zip for deployment to AWS Lambda.

    For the psycopg layer (requires Linux ARM64 + Docker), use WSL:
        wsl bash backend/package_lambda.sh --layer

.EXAMPLE
    ./backend/package_lambda.ps1
#>

$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir    = Split-Path -Parent $ScriptDir
$BackendDir = $ScriptDir
$DistDir    = Join-Path $RootDir "dist"

function Info($m) { Write-Host "[package] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[package] $m" -ForegroundColor Green }
function Err($m)  { Write-Host "[package] $m" -ForegroundColor Red; exit 1 }

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

Info "Building handler zip..."

$BuildDir = Join-Path ([System.IO.Path]::GetTempPath()) "zdl-handler-$(Get-Random)"
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

try {
    # lambda_handler.py
    Copy-Item (Join-Path $BackendDir "lambda_handler.py") $BuildDir

    # tools/ (exclude __pycache__, *.pyc, schemas/ is included for reference)
    $ToolsSrc = Join-Path $BackendDir "tools"
    $ToolsDst = Join-Path $BuildDir "tools"
    New-Item -ItemType Directory -Force -Path $ToolsDst | Out-Null
    Get-ChildItem $ToolsSrc -Recurse | Where-Object {
        $_.FullName -notmatch '__pycache__' -and
        $_.Extension -ne '.pyc'
    } | ForEach-Object {
        $Rel = $_.FullName.Substring($ToolsSrc.Length + 1)
        $Dst = Join-Path $ToolsDst $Rel
        $DstDir = Split-Path -Parent $Dst
        New-Item -ItemType Directory -Force -Path $DstDir | Out-Null
        if (-not $_.PSIsContainer) { Copy-Item $_.FullName $Dst }
    }

    # CA cert (bundled so db.py can resolve it without COCKROACH_SSLROOTCERT)
    $CertSrc = Join-Path $BackendDir "certs/cc-ca.crt"
    if (Test-Path $CertSrc) {
        $CertDst = Join-Path $BuildDir "certs"
        New-Item -ItemType Directory -Force -Path $CertDst | Out-Null
        Copy-Item $CertSrc (Join-Path $CertDst "cc-ca.crt")
        Ok "Bundled certs/cc-ca.crt"
    } else {
        Write-Host "[package] Warning: certs/cc-ca.crt not found — set COCKROACH_SSLROOTCERT in Lambda env." -ForegroundColor Yellow
    }

    # Zip via .NET
    $ZipPath = Join-Path $DistDir "zdl-tools-handler.zip"
    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($BuildDir, $ZipPath)

    # SHA256
    $Sha = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLower()
    "$Sha  zdl-tools-handler.zip" | Set-Content (Join-Path $DistDir "handler-sha256.txt")
    Ok "Handler zip: $ZipPath"
    Ok "SHA256: $($Sha.Substring(0,16))..."

    Write-Host ""
    Ok "Contents:"
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $z = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    $z.Entries | Sort-Object FullName | ForEach-Object { Write-Host "   $($_.FullName)" }
    $z.Dispose()

} finally {
    Remove-Item $BuildDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Ok "Done. For the psycopg layer (requires Docker/WSL), run:"
Write-Host "  wsl bash backend/package_lambda.sh --layer" -ForegroundColor Yellow
