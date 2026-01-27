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
- SQLite (mobile offline storage)

### Local AI Services
- **Ollama** - Local LLM (llama3.2) for conversation
- **Whisper** - Local speech-to-text transcription
- **pyttsx3** - Local text-to-speech synthesis

## Common Commands

```bash
# Install dependencies
bun install

# Build all packages
bun run build

# Run tests
bun run test                 # TypeScript tests
pytest                       # Python tests

# Start infrastructure (PostgreSQL, Redis)
docker-compose -f docker-compose.dev.yml up -d

# Start Ollama (local LLM)
brew services start ollama
ollama pull llama3.2

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

## Agent Routing System

JARVIS features intelligent agent routing that automatically selects specialized experts based on user intent. The system includes 130 agent definitions across 10 categories.

### How It Works
1. User sends a message
2. LLM-based intent classifier analyzes the request
3. Best-matching agent is selected (or default JARVIS for general queries)
4. JARVIS seamlessly introduces the specialist: "Allow me to consult our Python specialist..."
5. Response is generated with agent expertise
6. Session caching keeps context for follow-up questions

### Agent Categories
- **Core Development** - Backend, frontend, mobile, API design
- **Language Specialists** - Python, TypeScript, Rust, Go, Java, etc.
- **Infrastructure** - DevOps, SRE, cloud, Kubernetes, Terraform
- **Quality & Security** - Testing, code review, security auditing
- **Data & AI** - ML, data science, NLP, LLM architecture
- **Developer Experience** - CLI tools, documentation, refactoring
- **Specialized Domains** - Blockchain, IoT, game dev, fintech
- **Business & Product** - Product management, UX, project management
- **Meta & Orchestration** - Multi-agent coordination, workflows
- **Research & Analysis** - Market research, competitive analysis

### User Commands
- "Ask the Python expert about..." - Explicit agent request
- "Consult the security specialist" - Force specific routing
- "What specialists are available?" - List all agents

### Configuration
```bash
AGENT_ROUTING_ENABLED=true          # Enable/disable routing
AGENT_CONFIDENCE_THRESHOLD=0.6      # Min confidence for agent selection
AGENT_SESSION_TTL_SECONDS=3600      # Session cache duration
AGENT_TOPIC_CHANGE_THRESHOLD=0.7    # Threshold for topic change detection
```

### API Endpoints
- `GET /agents` - List all agents
- `GET /agents/categories` - List agent categories
- `GET /agents/{agent_id}` - Get agent details
- `GET /agents/search?q=python` - Search agents
- `POST /agents/reload` - Hot-reload agent definitions

## Key Files

- `/packages/core/src/api/client.ts` - WebSocket and REST client
- `/packages/core/src/state/store.ts` - Zustand state management
- `/packages/core/src/services/voice.ts` - Voice service abstraction
- `/services/conversation-service/src/main.py` - Core conversation orchestration
- `/services/conversation-service/src/bedrock_client.py` - LLM client (Ollama/OpenAI)
- `/services/conversation-service/src/prompts.py` - JARVIS personality prompts
- `/services/conversation-service/src/agents/` - Agent routing module
- `/services/conversation-service/agents/` - Agent definition files (130 agents)
- `/services/voice-processing/src/transcribe.py` - Whisper speech-to-text
- `/services/voice-processing/src/polly.py` - pyttsx3 text-to-speech

## Testing

- TypeScript: vitest (`bun run test`)
- Python: pytest (`pytest services/<service-name>`)

## Environment Variables

### Local LLM Configuration
```bash
LLM_PROVIDER=ollama                    # "ollama" or "openai"
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Local Voice Configuration
```bash
WHISPER_MODEL=base                     # Whisper model size
WHISPER_DEVICE=cpu                     # "cpu" or "cuda"
TTS_ENGINE=pyttsx3
TTS_RATE=150
```

### External API Keys
- `OPENWEATHER_API_KEY` - OpenWeatherMap
- `NEWSAPI_KEY` - NewsAPI
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - Google Calendar OAuth
- `OPENAI_API_KEY` - (Optional) For OpenAI as LLM provider
