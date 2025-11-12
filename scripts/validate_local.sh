#!/bin/bash

# KeyPick Local CI Validation Script
# This script runs the same checks as the GitHub Actions CI pipeline locally
# Run this before committing code to ensure CI will pass
# Uses uv for dependency management and running commands

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Header
echo "================================================"
echo "     KeyPick Local CI Validation Script"
echo "================================================"
echo ""

# Check if uv is installed
print_status "Checking uv installation..."
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed!"
    print_status "Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
print_success "uv is installed: $(uv --version)"

# Check Python version using uv
print_status "Checking Python version..."
PYTHON_VERSION=$(uv run python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ "$PYTHON_VERSION" != "3.12" && "$PYTHON_VERSION" != "3.13" ]]; then
    print_warning "Python version is $PYTHON_VERSION. CI uses 3.12 and 3.13"
    print_status "You can install Python 3.12 with: uv python install 3.12"
fi

# Sync dependencies
print_status "Syncing dependencies with uv..."
uv sync --all-groups
print_success "Dependencies synced"

echo ""
echo "========== LINT CHECKS =========="
echo ""

# 1. Black formatting check
print_status "Running Black formatter check..."
if uv run black --check --diff api/ tests/ --exclude "MediaCrawler|easy-ai-proxy"; then
    print_success "Black formatting check passed"
else
    print_error "Black formatting check failed"
    print_warning "Run 'uv run black api/ tests/' to auto-format"
    exit 1
fi

echo ""

# 2. Ruff linter check
print_status "Running Ruff linter..."
if uv run ruff check api/ tests/ --exclude "MediaCrawler" --exclude "easy-ai-proxy"; then
    print_success "Ruff linter check passed"
else
    print_error "Ruff linter check failed"
    print_warning "Run 'uv run ruff check --fix api/ tests/' to auto-fix some issues"
    exit 1
fi

echo ""

# 3. Ruff formatter check
print_status "Running Ruff formatter check..."
if uv run ruff format --check api/ tests/ --exclude "MediaCrawler" --exclude "easy-ai-proxy"; then
    print_success "Ruff formatter check passed"
else
    print_error "Ruff formatter check failed"
    print_warning "Run 'uv run ruff format api/ tests/' to auto-format"
    exit 1
fi

echo ""

# 4. MyPy type checking
print_status "Running MyPy type checker..."
if uv run mypy api/; then
    print_success "MyPy type check passed"
else
    print_error "MyPy type check failed"
    exit 1
fi

echo ""
echo "========== TEST CHECKS =========="
echo ""

# 5. Check if Redis is running (needed for tests)
print_status "Checking Redis connection..."
if redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is running"
else
    print_warning "Redis is not running. Starting Redis with Docker..."
    docker run -d --name keypick-redis -p 6379:6379 redis:7-alpine > /dev/null 2>&1 || true
    sleep 2
    if redis-cli ping > /dev/null 2>&1; then
        print_success "Redis started successfully"
    else
        print_error "Failed to start Redis. Tests may fail."
    fi
fi

echo ""

# 6. Run pytest with coverage
print_status "Running pytest with coverage..."
export REDIS_URL="redis://localhost:6379/0"

if uv run pytest --cov=api --cov-report=term-missing --cov-report=html; then
    print_success "All tests passed"
    print_status "Coverage report generated in htmlcov/index.html"
else
    print_error "Some tests failed"
    exit 1
fi

echo ""
echo "========== DOCKER BUILD CHECK =========="
echo ""

# 7. Docker build check (optional)
if command -v docker &> /dev/null; then
    print_status "Checking Docker build..."
    if docker build -t keypick:test --target test . > /dev/null 2>&1; then
        print_success "Docker build successful"
    else
        print_warning "Docker build failed (non-critical)"
    fi
else
    print_warning "Docker not installed, skipping build check"
fi

echo ""
echo "================================================"
echo -e "${GREEN}✅ All CI checks passed successfully!${NC}"
echo "================================================"
echo ""
print_status "You can now safely commit your changes."
print_status "Run 'git add . && git commit -m \"your message\"'"
echo ""

# Cleanup
if docker ps -q -f name=keypick-redis > /dev/null 2>&1; then
    print_status "Cleaning up temporary Redis container..."
    docker stop keypick-redis > /dev/null 2>&1
    docker rm keypick-redis > /dev/null 2>&1
fi