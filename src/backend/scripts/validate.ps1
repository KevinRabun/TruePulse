# TruePulse Backend Validation Script
# Runs all CI checks locally before pushing
# Usage: .\scripts\validate.ps1

param(
    [switch]$Fix,      # Auto-fix linting and formatting issues
    [switch]$Quick     # Skip slower checks (mypy)
)

$ErrorActionPreference = "Continue"
$script:failed = $false

function Write-Step {
    param($msg)
    Write-Host ""
    Write-Host "> $msg" -ForegroundColor Cyan
}

function Write-Pass {
    param($msg)
    Write-Host "  [PASS] $msg" -ForegroundColor Green
}

function Write-Fail {
    param($msg)
    Write-Host "  [FAIL] $msg" -ForegroundColor Red
    $script:failed = $true
}

function Write-Skip {
    param($msg)
    Write-Host "  [SKIP] $msg" -ForegroundColor Yellow
}

# Ensure we're in backend directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Split-Path -Parent $scriptDir
Push-Location $backendDir

Write-Host "TruePulse Backend Validation" -ForegroundColor White
Write-Host "============================" -ForegroundColor White

# 1. Ruff Linter
Write-Step "Ruff Linter"
if ($Fix) {
    python -m ruff check . --fix 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) { Write-Pass "Linter (fixed)" } else { Write-Fail "Linter (fix failed)" }
} else {
    python -m ruff check . 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) { Write-Pass "Linter" } else { Write-Fail "Linter - run with -Fix to auto-fix" }
}

# 2. Ruff Formatter
Write-Step "Ruff Formatter"
if ($Fix) {
    python -m ruff format . 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) { Write-Pass "Formatter (fixed)" } else { Write-Fail "Formatter (fix failed)" }
} else {
    python -m ruff format --check . 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) { Write-Pass "Formatter" } else { Write-Fail "Formatter - run with -Fix to auto-fix" }
}

# 3. MyPy Type Checking
Write-Step "MyPy Type Checking"
if ($Quick) {
    Write-Skip "MyPy (quick mode)"
} else {
    python -m mypy . --ignore-missing-imports --exclude tests/ --exclude scripts/ --explicit-package-bases 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) { Write-Pass "MyPy" } else { Write-Fail "MyPy type errors found" }
}

# 4. Unit Tests
Write-Step "Unit Tests"
python -m pytest tests/ -v --tb=short -q 2>&1 | Out-Host
if ($LASTEXITCODE -eq 0) { Write-Pass "Tests" } else { Write-Fail "Tests failed" }

Pop-Location

# Summary
Write-Host ""
Write-Host "============================" -ForegroundColor White
if ($script:failed) {
    Write-Host "VALIDATION FAILED" -ForegroundColor Red
    Write-Host "Fix issues before pushing." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
    Write-Host "Ready to commit and push." -ForegroundColor White
    exit 0
}
