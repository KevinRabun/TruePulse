#!/bin/bash
# TruePulse Backend Validation Script
# Runs all CI checks locally before pushing
# Usage: ./scripts/validate.sh [--fix] [--quick]

set -e

FIX=false
QUICK=false
FAILED=false

for arg in "$@"; do
    case $arg in
        --fix) FIX=true ;;
        --quick) QUICK=true ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

step() { echo -e "\n${CYAN}▶ $1${NC}"; }
pass() { echo -e "  ${GREEN}✓ $1${NC}"; }
fail() { echo -e "  ${RED}✗ $1${NC}"; FAILED=true; }
skip() { echo -e "  ${YELLOW}⊘ $1 (skipped)${NC}"; }

# Navigate to backend directory
cd "$(dirname "$0")/.."

echo -e "${NC}🔍 TruePulse Backend Validation"
echo "================================"

# 1. Ruff Linter
step "Ruff Linter"
if $FIX; then
    if python -m ruff check . --fix; then pass "Linter (fixed)"; else fail "Linter (fix failed)"; fi
else
    if python -m ruff check .; then pass "Linter"; else fail "Linter - run with --fix to auto-fix"; fi
fi

# 2. Ruff Formatter
step "Ruff Formatter"
if $FIX; then
    if python -m ruff format .; then pass "Formatter (fixed)"; else fail "Formatter (fix failed)"; fi
else
    if python -m ruff format --check .; then pass "Formatter"; else fail "Formatter - run with --fix to auto-fix"; fi
fi

# 3. MyPy Type Checking
step "MyPy Type Checking"
if $QUICK; then
    skip "MyPy (quick mode)"
else
    if python -m mypy . --ignore-missing-imports --exclude tests/ --exclude scripts/ --explicit-package-bases; then
        pass "MyPy"
    else
        fail "MyPy type errors found"
    fi
fi

# 4. Unit Tests
step "Unit Tests"
if python -m pytest tests/ -v --tb=short -q; then pass "Tests"; else fail "Tests failed"; fi

# Summary
echo ""
echo "================================"
if $FAILED; then
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo -e "${YELLOW}Fix issues before pushing.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ ALL CHECKS PASSED${NC}"
    echo "Ready to commit and push."
    exit 0
fi
