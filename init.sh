#!/bin/bash
# Paygent - AI-Powered Multi-Agent Payment Orchestration Platform
# Development Environment Setup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Paygent Development Environment Setup                  ║${NC}"
echo -e "${BLUE}║   AI-Powered Multi-Agent Payment Orchestration Platform        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print step
print_step() {
    echo -e "${GREEN}▶${NC} $1"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to print error
print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Check for uv (Python package manager)
print_step "Checking for uv package manager..."
if ! command_exists uv; then
    print_warning "uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add to current session PATH
    export PATH="$HOME/.local/bin:$PATH"
    if command_exists uv; then
        print_success "uv installed successfully"
    else
        print_error "Failed to install uv. Please install manually: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
else
    print_success "uv is installed ($(uv --version))"
fi

# Check for pnpm (Node.js package manager)
print_step "Checking for pnpm..."
if ! command_exists pnpm; then
    print_warning "pnpm not found. Installing pnpm..."
    if command_exists npm; then
        npm install -g pnpm
        print_success "pnpm installed successfully"
    else
        print_error "npm not found. Please install Node.js 18+ first, then run: npm install -g pnpm"
    fi
else
    print_success "pnpm is installed ($(pnpm --version))"
fi

# Check for Node.js
print_step "Checking for Node.js..."
if ! command_exists node; then
    print_warning "Node.js not found. Please install Node.js 18+ for smart contract development."
else
    NODE_VERSION=$(node --version)
    print_success "Node.js is installed ($NODE_VERSION)"
fi

# Check for Docker (optional)
print_step "Checking for Docker (optional for local development)..."
if ! command_exists docker; then
    print_warning "Docker not found. Docker is optional but recommended for local PostgreSQL and Redis."
else
    print_success "Docker is installed ($(docker --version))"
fi

# Create virtual environment
print_step "Creating Python virtual environment..."
if [ ! -d ".venv" ]; then
    uv venv
    print_success "Virtual environment created"
else
    print_success "Virtual environment already exists"
fi

# Activate virtual environment
print_step "Activating virtual environment..."
source .venv/bin/activate
print_success "Virtual environment activated"

# Install Python dependencies
print_step "Installing Python dependencies..."
if [ -f "pyproject.toml" ]; then
    uv sync
    print_success "Python dependencies installed"
else
    print_warning "pyproject.toml not found. Creating initial project configuration..."
fi

# Install dev dependencies
print_step "Installing development dependencies..."
if [ -f "pyproject.toml" ]; then
    uv sync --dev
    print_success "Development dependencies installed"
fi

# Check for .env file
print_step "Checking environment configuration..."
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    print_warning "Created .env from .env.example - please configure your environment variables"
elif [ ! -f ".env" ]; then
    print_warning "No .env file found. Please create one with required environment variables."
else
    print_success ".env file exists"
fi

# Install Playwright browsers (for E2E testing)
print_step "Installing Playwright browsers for E2E testing..."
if [ -f "pyproject.toml" ]; then
    uv run playwright install chromium 2>/dev/null || print_warning "Playwright not installed or failed to install browsers"
fi

# Install smart contract dependencies
print_step "Checking smart contract dependencies..."
if [ -d "contracts" ] && [ -f "contracts/package.json" ]; then
    cd contracts
    pnpm install
    cd ..
    print_success "Smart contract dependencies installed"
else
    print_warning "contracts directory not set up yet"
fi

# Start local services with Docker (if available)
if command_exists docker && command_exists docker-compose; then
    print_step "Checking Docker services..."
    if [ -f "docker-compose.yml" ]; then
        echo -e "  ${YELLOW}To start local PostgreSQL and Redis:${NC}"
        echo -e "    docker-compose up -d db redis"
    fi
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo -e "  1. Configure your environment variables in ${GREEN}.env${NC}"
echo -e "     Required variables:"
echo -e "       - ANTHROPIC_API_KEY"
echo -e "       - CRONOS_RPC_URL (defaults to testnet)"
echo -e "       - DATABASE_URL (for local dev) or configure Vercel Postgres"
echo ""
echo -e "  2. Start the development server:"
echo -e "     ${GREEN}source .venv/bin/activate${NC}"
echo -e "     ${GREEN}uv run uvicorn src.main:app --reload --port 8000${NC}"
echo ""
echo -e "  3. Access the application:"
echo -e "     - API:        ${BLUE}http://localhost:8000${NC}"
echo -e "     - Swagger UI: ${BLUE}http://localhost:8000/docs${NC}"
echo -e "     - ReDoc:      ${BLUE}http://localhost:8000/redoc${NC}"
echo ""
echo -e "  4. Run tests:"
echo -e "     ${GREEN}uv run pytest${NC}"
echo ""
echo -e "  5. For smart contract development:"
echo -e "     ${GREEN}cd contracts && pnpm exec hardhat compile${NC}"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "For more information, see the README.md file."
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
