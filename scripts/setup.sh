#!/bin/bash

# JARVIS Development Setup Script
# This script sets up the development environment for the JARVIS project

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  J.A.R.V.I.S. Development Environment Setup               ║"
echo "║  Just A Rather Very Intelligent System                    ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for required tools
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}✗ $1 is not installed${NC}"
        return 1
    else
        echo -e "${GREEN}✓ $1 is installed${NC}"
        return 0
    fi
}

echo "Checking prerequisites..."
echo ""

MISSING=0

check_command "node" || MISSING=1
check_command "bun" || MISSING=1
check_command "python3" || MISSING=1
check_command "docker" || MISSING=1
check_command "docker-compose" || MISSING=1

echo ""

if [ $MISSING -eq 1 ]; then
    echo -e "${RED}Some prerequisites are missing. Please install them and try again.${NC}"
    echo ""
    echo "Installation guides:"
    echo "  Node.js: https://nodejs.org/"
    echo "  Bun: https://bun.sh/ (curl -fsSL https://bun.sh/install | bash)"
    echo "  Python: https://python.org/"
    echo "  Docker: https://docker.com/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    echo -e "${RED}Node.js version 20 or higher is required (found v$NODE_VERSION)${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -V | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo -e "${YELLOW}Warning: Python 3.11+ is recommended (found $PYTHON_VERSION)${NC}"
fi

echo ""
echo "Installing Node.js dependencies..."
bun install

echo ""
echo "Building TypeScript packages..."
bun run build

echo ""
echo "Setting up Python virtual environments for services..."

# Conversation Service
echo "  Setting up conversation-service..."
cd services/conversation-service
python3 -m venv .venv || true
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
cd ../..

# Voice Processing
echo "  Setting up voice-processing..."
cd services/voice-processing
python3 -m venv .venv || true
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
cd ../..

# Weather Service
echo "  Setting up weather-service..."
cd services/weather-service
python3 -m venv .venv || true
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
cd ../..

# News Service
echo "  Setting up news-service..."
cd services/news-service
python3 -m venv .venv || true
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
cd ../..

# Briefing Service
echo "  Setting up briefing-service..."
cd services/briefing-service
python3 -m venv .venv || true
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
cd ../..

# Task Execution Service
echo "  Setting up task-execution..."
cd services/task-execution
python3 -m venv .venv || true
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
cd ../..

# Notification Service
echo "  Setting up notification-service..."
cd services/notification-service
python3 -m venv .venv || true
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
cd ../..

# User Profile Service
echo "  Setting up user-profile..."
cd services/user-profile
python3 -m venv .venv || true
source .venv/bin/activate
pip install -q -r requirements.txt
deactivate
cd ../..

echo ""
echo "Creating environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}Created .env file from .env.example${NC}"
    echo "Please update .env with your API keys and configuration."
else
    echo -e "${GREEN}.env file already exists${NC}"
fi

echo ""
echo "Starting infrastructure services (PostgreSQL, Redis)..."
docker-compose -f docker-compose.dev.yml up -d

echo ""
echo "Waiting for services to be ready..."
sleep 5

# Check if PostgreSQL is ready
until docker exec jarvis-postgres pg_isready -U jarvis > /dev/null 2>&1; do
    echo "  Waiting for PostgreSQL..."
    sleep 2
done
echo -e "${GREEN}✓ PostgreSQL is ready${NC}"

# Check if Redis is ready
until docker exec jarvis-redis redis-cli ping > /dev/null 2>&1; do
    echo "  Waiting for Redis..."
    sleep 2
done
echo -e "${GREEN}✓ Redis is ready${NC}"

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Setup Complete!                                          ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "Running database migrations..."
if ./scripts/migrate.sh; then
    echo -e "${GREEN}✓ Database migrations complete${NC}"
else
    echo -e "${YELLOW}Warning: Could not run migrations (database may not be ready)${NC}"
fi

echo ""
echo "Next steps:"
echo ""
echo "  1. Update .env with your API keys:"
echo "     - AWS credentials (for Bedrock, Transcribe, Polly)"
echo "     - OpenWeatherMap API key"
echo "     - NewsAPI key"
echo "     - Google Calendar OAuth credentials"
echo ""
echo "  2. Start all services with Docker:"
echo "     docker-compose up"
echo ""
echo "  Or start individual services for development:"
echo ""
echo "  3. Start the API Gateway:"
echo "     pnpm --filter @jarvis/api-gateway dev"
echo ""
echo "  4. Start the Conversation Service:"
echo "     cd services/conversation-service && source .venv/bin/activate && uvicorn src.main:app --reload --port 8001"
echo ""
echo "  5. Run the CLI:"
echo "     pnpm --filter @jarvis/cli dev"
echo ""
echo "  Available CLI Commands:"
echo "     jarvis chat      - Start a conversation"
echo "     jarvis voice     - Voice conversation mode"
echo "     jarvis briefing  - Get your daily briefing"
echo "     jarvis dashboard - Open the dashboard"
echo "     jarvis listen    - Wake word listening mode"
echo ""
echo "Good luck, sir. JARVIS is at your service."
