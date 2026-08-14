# RootCause MCP - Windows PowerShell Setup & Installation Script
# Usage: powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 [-Profile all|clinical|rca] [-Target vscode|claude|cline|all]

[CmdletBinding()]
param(
    [ValidateSet("all", "clinical", "rca")]
    [string]$Profile = "all",

    [ValidateSet("compact", "verbose")]
    [string]$ResponseMode = "compact",

    [ValidateSet("vscode", "claude", "cline", "all")]
    [string]$Target = "all",

    [switch]$SkipTests,
    [switch]$SkipTrial
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "===========================================================================" -ForegroundColor Cyan
Write-Host "🏥 RootCause MCP Server - One-Click Setup & Installer (Windows)" -ForegroundColor Cyan
Write-Host "===========================================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

# 1. Check / Install uv
Write-Host "`n[1/4] Checking uv package manager..." -ForegroundColor Yellow
$UvCmd = Get-Command "uv" -ErrorAction SilentlyContinue

if (-not $UvCmd) {
    $LocalUv = Join-Path $HOME ".local\bin\uv.exe"
    $CargoUv = Join-Path $HOME ".cargo\bin\uv.exe"
    if (Test-Path $LocalUv) {
        $UvPath = $LocalUv
    } elseif (Test-Path $CargoUv) {
        $UvPath = $CargoUv
    } else {
        Write-Host " -> uv not found. Installing uv via official Astral installer..." -ForegroundColor Yellow
        try {
            Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
            $UvPath = Join-Path $HOME ".local\bin\uv.exe"
            if (-not (Test-Path $UvPath)) {
                $UvPath = Join-Path $HOME ".cargo\bin\uv.exe"
            }
        } catch {
            Write-Error "Failed to install uv automatically. Please install uv manually: https://github.com/astral-sh/uv"
        }
    }
} else {
    $UvPath = $UvCmd.Source
}

Write-Host " -> Using uv: $UvPath" -ForegroundColor Green

# 2. Sync Python virtual environment
Write-Host "`n[2/4] Initializing virtual environment & syncing dependencies..." -ForegroundColor Yellow
& $UvPath sync --all-extras
if ($LASTEXITCODE -ne 0) {
    Write-Error "uv sync failed with exit code $LASTEXITCODE"
}
Write-Host " -> Dependencies synchronized successfully." -ForegroundColor Green

# 3. Run Universal Installer Script
Write-Host "`n[3/4] Configuring MCP client harness & host registrations..." -ForegroundColor Yellow
$InstallArgs = @(
    "run",
    "python",
    "scripts/install.py",
    "--profile", $Profile,
    "--response-mode", $ResponseMode,
    "--target", $Target
)

if ($SkipTests) {
    $InstallArgs += "--skip-tests"
}
if ($SkipTrial) {
    $InstallArgs += "--skip-trial"
}

& $UvPath $InstallArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "Installation configuration failed with exit code $LASTEXITCODE"
}

# 4. Summary
Write-Host "`n===========================================================================" -ForegroundColor Cyan
Write-Host "🎉 Setup completed successfully!" -ForegroundColor Green
Write-Host "   Server command: uv run rootcause-mcp" -ForegroundColor Gray
Write-Host "   Profile:        $Profile" -ForegroundColor Gray
Write-Host "   Response Mode:  $ResponseMode" -ForegroundColor Gray
Write-Host "===========================================================================" -ForegroundColor Cyan
