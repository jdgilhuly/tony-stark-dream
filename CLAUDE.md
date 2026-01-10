# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JARVIS (Just A Rather Very Intelligent System) is a personal AI assistant inspired by Tony Stark's JARVIS from Iron Man. The system provides voice and text interaction, daily briefings, task management, and calendar integration across CLI and mobile platforms.

## Development Status

**Implementation Complete** - All core features have been implemented and the system is ready for deployment.

## Architecture

### Monorepo Structure
- **packages/core** - Shared TypeScript library (API client, state management, voice service, adapters)
- **packages/cli** - Terminal UI built with Ink (React for terminal)
- **packages/mobile** - React Native mobile application

### Backend Services (10 microservices)
| Service | Port | Technology |
|---------|------|------------|
| api-gateway | 3000 | Express/TypeScript |
| conversation-service | 8001 | FastAPI/Python |
| voice-processing | 8002 | FastAPI/Python |
| weather-service | 8003 | FastAPI/Python |
| news-service | 8004 | FastAPI/Python |
| briefing-service | 8005 | FastAPI/Python |
| calendar-service | 8006 | Express/TypeScript |
| task-execution | 8007 | FastAPI/Python |
| notification-service | 8008 | FastAPI/Python |
| user-profile | 8009 | FastAPI/Python |

### Data Layer
- PostgreSQL (user data, conversations)
- Redis (caching, sessions)
- DynamoDB (high-throughput key-value)
- SQLite (mobile offline storage)
- S3 (audio file storage)

## Common Commands

```bash
# Install dependencies
bun install

# Build all packages
bun run build

# Run tests
bun run test                 # TypeScript tests
pytest                       # Python tests

# Start infrastructure (PostgreSQL, Redis, LocalStack)
docker-compose -f docker-compose.dev.yml up -d

# Start all services
docker-compose up

# CLI commands
bun run --filter @jarvis/cli dev login      # Login
bun run --filter @jarvis/cli dev chat       # Start conversation
bun run --filter @jarvis/cli dev voice      # Voice mode
bun run --filter @jarvis/cli dev briefing   # Daily briefing
bun run --filter @jarvis/cli dev dashboard  # Open dashboard

# Development helper script
./scripts/dev.sh infra       # Start infrastructure only
./scripts/dev.sh api         # Start API gateway
./scripts/dev.sh all         # Start everything
```

## Key Files

- `/packages/core/src/api/client.ts` - WebSocket and REST client
- `/packages/core/src/state/store.ts` - Zustand state management
- `/packages/core/src/services/voice.ts` - Voice service abstraction
- `/services/conversation-service/src/main.py` - Core conversation orchestration
- `/services/conversation-service/src/prompts.py` - JARVIS personality prompts
- `/infrastructure/terraform/main.tf` - AWS infrastructure as code

## Testing

- TypeScript: vitest (`bun run test`)
- Python: pytest (`pytest services/<service-name>`)

## Environment Variables

Required API keys (see `.env.example`):
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - AWS credentials
- `OPENWEATHER_API_KEY` - OpenWeatherMap
- `NEWSAPI_KEY` - NewsAPI
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - Google Calendar OAuth
