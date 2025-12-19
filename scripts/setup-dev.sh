#!/bin/bash
# TruePulse Local Development Setup Script
# Run this after cloning the repository

set -e

echo "🚀 TruePulse Local Development Setup"
echo "======================================"

# Check prerequisites
echo "📋 Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "⚠️ Docker is recommended but not installed."; }

echo "✅ Prerequisites check passed"

# Backend setup
echo ""
echo "🐍 Setting up Backend..."
cd src/backend

if [ ! -d ".venv" ]; then
    echo "   Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "   Activating virtual environment..."
source .venv/bin/activate || source .venv/Scripts/activate

echo "   Installing dependencies..."
pip install -r requirements.txt -q
pip install -r requirements-dev.txt -q

# Copy .env.example if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "   Creating .env from .env.example..."
    cp .env.example .env
    echo "   ⚠️ Please edit .env with your actual configuration values"
fi

echo "✅ Backend setup complete"

# Frontend setup
echo ""
echo "⚛️ Setting up Frontend..."
cd ../frontend

echo "   Installing npm packages..."
npm ci

# Copy .env.example if .env doesn't exist
if [ ! -f ".env.local" ]; then
    if [ -f ".env.example" ]; then
        echo "   Creating .env.local from .env.example..."
        cp .env.example .env.local
    else
        echo "   Creating default .env.local..."
        echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
    fi
fi

echo "✅ Frontend setup complete"

# Instructions
echo ""
echo "======================================"
echo "🎉 Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "Option 1: Use Docker Compose (recommended)"
echo "  docker compose up -d"
echo ""
echo "Option 2: Run services manually"
echo ""
echo "  Backend:"
echo "    cd src/backend"
echo "    source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows"
echo "    uvicorn main:app --reload"
echo ""
echo "  Frontend:"
echo "    cd src/frontend"
echo "    npm run dev"
echo ""
echo "Option 3: Run tests"
echo ""
echo "  Backend tests:"
echo "    cd src/backend && pytest"
echo ""
echo "  Frontend tests:"
echo "    cd src/frontend && npm test"
echo ""
