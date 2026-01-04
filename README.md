# JARVIS - Just A Rather Very Intelligent System

> *"Good morning, sir. Systems initialized and ready."*

A personal AI assistant inspired by Tony Stark's JARVIS from Iron Man. Your intelligent companion for daily tasks, updates, and conversational interaction.

## Status: Implementation Complete

All core features have been implemented and the system is ready for deployment.

## Features

- **Voice Interface**: Natural speech interaction via AWS Transcribe (STT) and Polly Neural "Brian" voice (TTS)
- **Text Interface**: Full conversation support in CLI and mobile
- **Daily Briefings**: Personalized summaries of weather, news, calendar, and tasks
- **Task Management**: Create, schedule, and automate tasks with cron support
- **Multi-Platform**: CLI tool and React Native mobile app with 70% shared code
- **Offline Support**: SQLite storage with sync queue for mobile
- **Push Notifications**: Real-time updates via WebSocket and Firebase
- **JARVIS Personality**: British butler demeanor with characteristic wit

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Clients                                  │
├─────────────────────┬───────────────────────────────────────────┤
│   CLI (Ink/Node)    │         Mobile (React Native)             │
├─────────────────────┴───────────────────────────────────────────┤
│                    @jarvis/core (shared)                         │
│         API Client │ State (Zustand) │ Voice │ Adapters          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (:3000)                         │
│              Express │ JWT Auth │ WebSocket                      │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Conversation   │ │ Voice Processing│ │    Briefing     │
│    (:8001)      │ │    (:8002)      │ │    (:8005)      │
│  Claude/Bedrock │ │Transcribe/Polly │ │  LLM Summary    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    Weather      │ │      News       │ │    Calendar     │
│    (:8003)      │ │    (:8004)      │ │    (:8006)      │
│ OpenWeatherMap  │ │    NewsAPI      │ │ Google Calendar │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Task Execution  │ │  Notification   │ │  User Profile   │
│    (:8007)      │ │    (:8008)      │ │    (:8009)      │
│   APScheduler   │ │ WebSocket/Push  │ │  Preferences    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
│     PostgreSQL │ Redis │ DynamoDB │ S3                           │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- pnpm 9+
- Docker & Docker Compose

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tony-stark-dream.git
cd tony-stark-dream

# Run setup script (installs dependencies, builds packages, starts infrastructure)
./scripts/setup.sh

# Or manually:
pnpm install
pnpm build
docker-compose -f docker-compose.dev.yml up -d
```

### Configuration

Copy the environment template and add your API keys:

```bash
cp .env.example .env
```

Required API keys:
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - AWS credentials for Bedrock, Transcribe, Polly
- `OPENWEATHER_API_KEY` - OpenWeatherMap API key
- `NEWSAPI_KEY` - NewsAPI key
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - Google Calendar OAuth

### Running Services

```bash
# Start all services with Docker Compose
docker-compose up

# Or use the dev helper script for individual services
./scripts/dev.sh infra      # Start PostgreSQL, Redis, LocalStack
./scripts/dev.sh api        # Start API Gateway
./scripts/dev.sh conversation  # Start Conversation Service
./scripts/dev.sh all        # Start everything
```

### Using the CLI

```bash
# Login
pnpm --filter @jarvis/cli dev login

# Start conversation
pnpm --filter @jarvis/cli dev chat

# Voice mode
pnpm --filter @jarvis/cli dev voice

# Get daily briefing
pnpm --filter @jarvis/cli dev briefing

# Open dashboard
pnpm --filter @jarvis/cli dev dashboard
```

## Project Structure

```
jarvis/
├── packages/
│   ├── core/           # Shared TypeScript library
│   │   ├── api/        # API client with WebSocket
│   │   ├── state/      # Zustand stores
│   │   ├── services/   # Voice service abstraction
│   │   ├── adapters/   # Platform adapters (AWS)
│   │   └── cache/      # Offline queue, sync manager
│   ├── cli/            # Terminal UI (Ink)
│   │   ├── components/ # Dashboard, Chat, Briefing
│   │   └── audio/      # Recording and playback
│   └── mobile/         # React Native app
│       ├── screens/    # App screens
│       ├── components/ # UI widgets
│       ├── stores/     # Zustand stores
│       └── services/   # API, SQLite, notifications
├── services/
│   ├── api-gateway/        # Express gateway (:3000)
│   ├── conversation-service/ # FastAPI + Bedrock (:8001)
│   ├── voice-processing/   # FastAPI + Transcribe/Polly (:8002)
│   ├── weather-service/    # FastAPI + OpenWeatherMap (:8003)
│   ├── news-service/       # FastAPI + NewsAPI (:8004)
│   ├── briefing-service/   # FastAPI + LLM summarization (:8005)
│   ├── calendar-service/   # Express + Google Calendar (:8006)
│   ├── task-execution/     # FastAPI + APScheduler (:8007)
│   ├── notification-service/ # FastAPI + WebSocket (:8008)
│   └── user-profile/       # FastAPI + preferences (:8009)
├── infrastructure/
│   ├── terraform/      # AWS infrastructure as code
│   └── migrations/     # PostgreSQL schema
├── scripts/
│   ├── setup.sh        # Initial setup
│   ├── dev.sh          # Development helper
│   └── migrate.sh      # Database migrations
├── docker-compose.yml      # Full stack
├── docker-compose.dev.yml  # Infrastructure only
└── .github/workflows/      # CI/CD pipelines
```

## Example Interactions

```
JARVIS: Good morning, sir. Systems initialized and ready.
        How may I assist you today?

You: What's on my schedule today?

JARVIS: You have 3 meetings scheduled today, sir. Your first
        engagement is at 9:00 AM with the engineering team,
        followed by a product review at 11:30, and a one-on-one
        with Ms. Chen at 3:00 PM. Shall I provide more details
        on any of these?

You: What's the weather like?

JARVIS: Current conditions show 72°F with clear skies and
        light winds from the northwest. Perfect weather for
        your afternoon, sir. The forecast suggests similar
        conditions throughout the day.

You: Give me my daily briefing

JARVIS: Certainly, sir. Here's your briefing for today:

        Weather: Clear skies, high of 75°F

        Calendar: 3 meetings scheduled, first at 9:00 AM

        News Headlines:
        - Tech sector sees record gains...
        - New breakthrough in renewable energy...

        Tasks: 2 items due today
        - Review Q3 reports (high priority)
        - Send project update to stakeholders

        Will there be anything else, sir?
```

## Testing

```bash
# TypeScript tests
pnpm test

# Python tests
pytest

# Specific service
pytest services/conversation-service
```

## Deployment

The project includes Terraform infrastructure for AWS deployment:

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

This provisions:
- ECS Fargate cluster with all services
- RDS PostgreSQL database
- ElastiCache Redis cluster
- DynamoDB tables
- S3 buckets for audio storage
- ALB for load balancing
- CloudWatch logging

## Technology Stack

| Category | Technology |
|----------|------------|
| Backend | Python 3.11 (FastAPI), Node.js 20 (Express) |
| AI/ML | AWS Bedrock (Claude), Transcribe, Polly Neural |
| Database | PostgreSQL 15, Redis 7, DynamoDB |
| CLI | Node.js, Ink (React for terminal) |
| Mobile | React Native, Zustand, SQLite |
| Infrastructure | Docker, Terraform, AWS ECS Fargate |
| CI/CD | GitHub Actions |

## Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests.

## License

MIT License - see LICENSE file for details.

---

*"Sometimes you gotta run before you can walk."* - Tony Stark

**Building the future, one line of code at a time.**
