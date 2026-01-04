#!/bin/bash

# JARVIS Development Helper Script
# Provides shortcuts for common development tasks

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

show_help() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║  J.A.R.V.I.S. Development Helper                          ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Usage: ./scripts/dev.sh <command>"
    echo ""
    echo "Commands:"
    echo "  ${GREEN}infra${NC}          Start infrastructure (PostgreSQL, Redis, LocalStack)"
    echo "  ${GREEN}infra-down${NC}     Stop infrastructure"
    echo "  ${GREEN}api${NC}            Start API Gateway (port 3000)"
    echo "  ${GREEN}conversation${NC}   Start Conversation Service (port 8001)"
    echo "  ${GREEN}voice${NC}          Start Voice Processing Service (port 8002)"
    echo "  ${GREEN}weather${NC}        Start Weather Service (port 8003)"
    echo "  ${GREEN}news${NC}           Start News Service (port 8004)"
    echo "  ${GREEN}briefing${NC}       Start Briefing Service (port 8005)"
    echo "  ${GREEN}calendar${NC}       Start Calendar Service (port 8006)"
    echo "  ${GREEN}tasks${NC}          Start Task Execution Service (port 8007)"
    echo "  ${GREEN}notify${NC}         Start Notification Service (port 8008)"
    echo "  ${GREEN}profile${NC}        Start User Profile Service (port 8009)"
    echo "  ${GREEN}cli${NC}            Start CLI in development mode"
    echo "  ${GREEN}all${NC}            Start all services with Docker Compose"
    echo "  ${GREEN}logs${NC}           Show logs from Docker Compose"
    echo "  ${GREEN}migrate${NC}        Run database migrations"
    echo "  ${GREEN}clean${NC}          Clean build artifacts"
    echo "  ${GREEN}build${NC}          Build all TypeScript packages"
    echo ""
}

start_python_service() {
    local service_name=$1
    local port=$2
    local service_dir="services/$service_name"

    if [ ! -d "$service_dir" ]; then
        echo -e "${RED}Service directory not found: $service_dir${NC}"
        exit 1
    fi

    cd "$service_dir"

    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -q -r requirements.txt
    else
        source .venv/bin/activate
    fi

    echo -e "${GREEN}Starting $service_name on port $port...${NC}"
    uvicorn src.main:app --reload --host 0.0.0.0 --port "$port"
}

start_node_service() {
    local service_name=$1
    local service_dir="services/$service_name"

    if [ ! -d "$service_dir" ]; then
        echo -e "${RED}Service directory not found: $service_dir${NC}"
        exit 1
    fi

    cd "$service_dir"
    echo -e "${GREEN}Starting $service_name...${NC}"
    bun run dev
}

case "${1:-help}" in
    infra)
        echo -e "${BLUE}Starting infrastructure services...${NC}"
        docker-compose -f docker-compose.dev.yml up -d
        echo -e "${GREEN}Infrastructure started!${NC}"
        echo "  PostgreSQL: localhost:5432"
        echo "  Redis: localhost:6379"
        echo "  LocalStack: localhost:4566"
        ;;

    infra-down)
        echo -e "${BLUE}Stopping infrastructure services...${NC}"
        docker-compose -f docker-compose.dev.yml down
        echo -e "${GREEN}Infrastructure stopped!${NC}"
        ;;

    api)
        cd services/api-gateway
        echo -e "${GREEN}Starting API Gateway on port 3000...${NC}"
        bun run dev
        ;;

    conversation)
        start_python_service "conversation-service" 8001
        ;;

    voice)
        start_python_service "voice-processing" 8002
        ;;

    weather)
        start_python_service "weather-service" 8003
        ;;

    news)
        start_python_service "news-service" 8004
        ;;

    briefing)
        start_python_service "briefing-service" 8005
        ;;

    calendar)
        start_node_service "calendar-service"
        ;;

    tasks)
        start_python_service "task-execution" 8007
        ;;

    notify)
        start_python_service "notification-service" 8008
        ;;

    profile)
        start_python_service "user-profile" 8009
        ;;

    cli)
        cd packages/cli
        echo -e "${GREEN}Starting CLI in development mode...${NC}"
        bun run dev
        ;;

    all)
        echo -e "${BLUE}Starting all services with Docker Compose...${NC}"
        docker-compose up
        ;;

    logs)
        docker-compose logs -f
        ;;

    migrate)
        echo -e "${BLUE}Running database migrations...${NC}"
        ./scripts/migrate.sh
        ;;

    clean)
        echo -e "${BLUE}Cleaning build artifacts...${NC}"
        bun run clean
        echo -e "${GREEN}Clean complete!${NC}"
        ;;

    build)
        echo -e "${BLUE}Building all TypeScript packages...${NC}"
        bun run build
        echo -e "${GREEN}Build complete!${NC}"
        ;;

    help|--help|-h)
        show_help
        ;;

    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac
