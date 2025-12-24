# TruePulse Local Development Setup Script for Windows
# Run this after cloning the repository

Write-Host "🚀 TruePulse Local Development Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Check prerequisites
Write-Host "`n📋 Checking prerequisites..." -ForegroundColor Yellow

try { python --version | Out-Null } catch { Write-Host "❌ Python 3 is required but not installed." -ForegroundColor Red; exit 1 }
try { node --version | Out-Null } catch { Write-Host "❌ Node.js is required but not installed." -ForegroundColor Red; exit 1 }
try { docker --version | Out-Null } catch { Write-Host "⚠️ Docker is recommended but not installed." -ForegroundColor Yellow }

Write-Host "✅ Prerequisites check passed" -ForegroundColor Green

# Backend setup
Write-Host "`n🐍 Setting up Backend..." -ForegroundColor Yellow
Push-Location src/backend

if (-not (Test-Path ".venv")) {
    Write-Host "   Creating Python virtual environment..."
    python -m venv .venv
}

Write-Host "   Activating virtual environment..."
& .venv/Scripts/Activate.ps1

Write-Host "   Installing dependencies..."
pip install -r requirements.txt -q
pip install -r requirements-dev.txt -q

# Copy .env.example if .env doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "   Creating .env from .env.example..."
    Copy-Item .env.example .env
    Write-Host "   ⚠️ Please edit .env with your actual configuration values" -ForegroundColor Yellow
}

Write-Host "✅ Backend setup complete" -ForegroundColor Green

# Pre-commit setup
Write-Host "`n🪝 Setting up pre-commit hooks..." -ForegroundColor Yellow
Pop-Location
pip install pre-commit -q
pre-commit install
Write-Host "✅ Pre-commit hooks installed" -ForegroundColor Green

# Frontend setup
Write-Host "`n⚛️ Setting up Frontend..." -ForegroundColor Yellow
Push-Location src/frontend

Write-Host "   Installing npm packages..."
npm ci

# Copy .env.example if .env.local doesn't exist
if (-not (Test-Path ".env.local")) {
    if (Test-Path ".env.example") {
        Write-Host "   Creating .env.local from .env.example..."
        Copy-Item .env.example .env.local
    } else {
        Write-Host "   Creating default .env.local..."
        "NEXT_PUBLIC_API_URL=http://localhost:8000" | Out-File -Encoding UTF8 .env.local
    }
}

Write-Host "✅ Frontend setup complete" -ForegroundColor Green
Pop-Location

# Instructions
Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "🎉 Setup Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 1: Use Docker Compose (recommended)" -ForegroundColor White
Write-Host "  docker compose up -d"
Write-Host ""
Write-Host "Option 2: Run services manually" -ForegroundColor White
Write-Host ""
Write-Host "  Backend:" -ForegroundColor Cyan
Write-Host "    cd src/backend"
Write-Host "    .venv\Scripts\Activate.ps1"
Write-Host "    uvicorn main:app --reload"
Write-Host ""
Write-Host "  Frontend:" -ForegroundColor Cyan
Write-Host "    cd src/frontend"
Write-Host "    npm run dev"
Write-Host ""
Write-Host "Option 3: Run tests" -ForegroundColor White
Write-Host ""
Write-Host "  Backend tests:" -ForegroundColor Cyan
Write-Host "    cd src/backend; pytest"
Write-Host ""
Write-Host "  Frontend tests:" -ForegroundColor Cyan
Write-Host "    cd src/frontend; npm test"
Write-Host ""
