# JARVIS Implementation Plan

## Overview
Build a complete personal AI assistant system inspired by Tony Stark's JARVIS with voice+text interface, CLI+mobile clients, daily briefing capabilities, and AWS ECS/EKS deployment.

## Architecture Summary

### Backend (AWS ECS/EKS)
**Microservices Architecture** with 10 core services:
- API Gateway (Node.js/Express) - Single entry point, JWT auth
- Conversation Service (Python/FastAPI) - Core NLP orchestration with Claude 3.5 Sonnet via AWS Bedrock
- Voice Processing Service (Python/FastAPI) - AWS Transcribe (STT) + AWS Polly (TTS)
- Briefing Service (Python/FastAPI) - Aggregates news/weather/calendar
- News/Weather/Calendar Services (Python/Node.js) - External API integrations
- User Profile Service (Node.js/Go) - User data and preferences
- Task Execution Service (Python) - Command execution and automation
- Notification Service (Node.js) - Push notifications and WebSockets

**AWS Services Stack:**
- Compute: ECS Fargate (start) → EKS (later)
- AI/ML: AWS Bedrock (Claude), Transcribe, Polly
- Database: RDS PostgreSQL (user data, conversations), DynamoDB (sessions), ElastiCache Redis (cache)
- Storage: S3 (audio files, logs)
- Networking: ALB, API Gateway, VPC
- Monitoring: CloudWatch, X-Ray

### Voice & NLP Pipeline
**Voice Recognition:** AWS Transcribe Streaming (300-500ms latency)
**LLM:** Claude 3.5 Sonnet via AWS Bedrock ($3/$15 per million tokens) for main queries, GPT-4o-mini for simple queries
**TTS:** AWS Polly Neural "Brian" voice ($16/1M characters)
**Memory System:** 3-tier architecture
  - Short-term: Redis (last 10-20 exchanges, 24hr TTL)
  - Working memory: PostgreSQL (last 7 days, summarized)
  - Long-term: Vector DB (semantic search via Pinecone/OpenSearch)

**End-to-end latency target:** 2-3 seconds from speech end to response start

### Client Applications (70% Code Reuse)
**Shared Core (TypeScript):** API client, state management (Zustand), conversation logic, caching
**CLI Tool:** Node.js + Ink (React for terminal), node-record-lpcm16 (voice), Porcupine (wake word)
**Mobile App:** React Native, react-native-audio-recorder-player, react-native-tts, Firebase push notifications

**Communication:** WebSocket-first (real-time) with REST fallback

## Implementation Phases

### Phase 1: Backend Foundation (Weeks 1-2)
**Infrastructure:**
- Set up AWS VPC, ECS cluster, RDS PostgreSQL, DynamoDB, ElastiCache Redis, S3 buckets
- Configure ALB, security groups, IAM roles
- Set up CI/CD pipeline (CodePipeline/GitHub Actions)

**Services:**
- Implement API Gateway service with JWT authentication
- Implement User Profile Service (CRUD operations)
- Set up service discovery (AWS Cloud Map)

**Critical Files:**
- `/infrastructure/terraform/main.tf` - Core AWS infrastructure (VPC, ECS, RDS, DynamoDB, ALB, security groups)
- `/infrastructure/terraform/ecs.tf` - ECS cluster, task definitions, services
- `/services/api-gateway/src/server.js` - Express API gateway with routing and auth
- `/services/user-profile/src/main.py` - User service with PostgreSQL integration

### Phase 2: Core Conversation System (Weeks 3-4)
**Backend:**
- Implement Conversation Service with AWS Bedrock integration
- Session management with DynamoDB
- Conversation history storage in PostgreSQL
- Redis caching layer

**Client:**
- Set up monorepo (pnpm workspaces)
- Implement shared core API client (WebSocket + REST)
- Build state management (Zustand)
- Create CLI MVP with text-based conversation
- Create React Native project with basic conversation screen

**Critical Files:**
- `/services/conversation-service/src/main.py` - Core conversation orchestration, LLM integration, context management
- `/packages/core/src/api/client.ts` - WebSocket and REST client with reconnection logic
- `/packages/core/src/state/store.ts` - Zustand state management with conversation slices
- `/packages/cli/src/index.tsx` - Ink-based CLI entry point with terminal UI
- `/packages/mobile/src/App.tsx` - React Native app with navigation setup

### Phase 3: Voice Processing (Weeks 5-6)
**Backend:**
- Implement Voice Processing Service
- AWS Transcribe integration (streaming API)
- AWS Polly integration (Neural TTS)
- S3 audio storage and retrieval

**Client:**
- Voice service abstraction in shared core
- CLI: node-record-lpcm16 recording + play-sound playback
- Mobile: react-native-audio-recorder-player + TTS
- Wake word detection (Porcupine) on both platforms

**Critical Files:**
- `/services/voice-processing/src/voice_handler.py` - Transcribe/Polly integration, audio streaming
- `/packages/core/src/services/voice.ts` - Voice service abstraction with platform adapters
- `/packages/core/src/adapters/interfaces.ts` - AudioRecorder, AudioPlayer, StorageAdapter interfaces
- `/packages/cli/src/audio/recorder.ts` - Node.js audio recording implementation
- `/packages/mobile/src/native/audio-recorder.ts` - React Native audio implementation

### Phase 4: External Integrations (Weeks 7-8)
**Backend Services:**
- Weather Service (OpenWeatherMap API)
- News Service (NewsAPI)
- Calendar Service (Google Calendar API, Microsoft Graph)
- OAuth token management

**Integration:**
- API key management (AWS Secrets Manager)
- Caching strategies (Redis 30min weather, 1hr news, 15min calendar)
- Error handling and circuit breakers

**Critical Files:**
- `/services/weather-service/src/main.py` - OpenWeatherMap integration with Redis caching
- `/services/news-service/src/main.py` - NewsAPI integration
- `/services/calendar-service/src/main.js` - Google Calendar OAuth and event retrieval
- `/services/conversation-service/src/integrations.py` - Service-to-service communication

### Phase 5: Daily Briefing System (Weeks 9-10)
**Backend:**
- Briefing Service aggregating weather/news/calendar
- Scheduled generation via EventBridge
- LLM-based summarization and personalization
- DynamoDB briefing cache

**Client:**
- Dashboard views (CLI + mobile)
- Daily briefing display
- Push notifications for mobile

**Critical Files:**
- `/services/briefing-service/src/briefing_generator.py` - Data aggregation and LLM summarization
- `/packages/cli/src/components/Dashboard.tsx` - CLI dashboard with weather/calendar widgets
- `/packages/mobile/src/screens/DashboardScreen.tsx` - Mobile dashboard
- `/packages/mobile/src/screens/BriefingScreen.tsx` - Full briefing view

### Phase 6: Offline Support & Polish (Weeks 11-12)
**Features:**
- Offline queue implementation
- SQLite conversation storage (mobile)
- Background sync
- Performance optimization (caching, streaming, parallel processing)
- JARVIS personality refinement (system prompts, SSML)

**Critical Files:**
- `/packages/core/src/cache/offline-queue.ts` - Optimistic updates and sync queue
- `/packages/core/src/cache/manager.ts` - Cache strategies and TTL management
- `/packages/mobile/src/services/sqlite.ts` - Local conversation storage
- `/services/conversation-service/src/prompts.py` - JARVIS personality system prompts

## JARVIS Personality System

**Core Identity:**
- Professional British butler demeanor
- Intelligent, capable, loyal
- Subtle dry wit and understatement
- Address user as "sir" or preferred title
- Use phrases: "I'm afraid...", "Certainly, sir", "Might I suggest..."

**System Prompt Structure:**
```
1. Core identity and traits
2. Speech patterns and examples
3. Current context (time, location, weather, calendar)
4. Recent conversation history (last 3-5 exchanges)
5. User profile and preferences
6. Response guidelines
```

**Response Quality Measures:**
- Transcription accuracy > 95%
- Response relevance > 4.5/5
- Personality consistency > 4.5/5
- End-to-end latency < 3.5s (p95)

## Cost Estimation

**Development Environment:** ~$30-50/month
- Lambda instead of ECS
- DynamoDB instead of RDS
- GPT-4o-mini for most queries

**Production (1-10 users):** ~$230-300/month
- ECS Fargate compute: ~$660
- Databases (RDS + DynamoDB + Redis): ~$178
- AI/ML (Bedrock, Transcribe, Polly): ~$150
- External APIs: ~$89
- Networking and other: ~$140

**Optimization strategies:**
- Query routing (simple queries to cheaper models)
- Aggressive caching (Redis)
- Reserved Instances for production

## Critical Success Factors

1. **Low Latency:** Voice conversation must feel natural (2-3s response time)
2. **Personality Consistency:** JARVIS must maintain character across all interactions
3. **Reliability:** 99.9% uptime, robust reconnection logic
4. **Code Reuse:** 70% shared code between CLI and mobile
5. **Offline Support:** Core features work without connectivity

## Technology Stack Summary

**Backend:**
- Python 3.11+ with FastAPI (AI services)
- Node.js 20+ with Express (I/O services)
- Docker for containerization
- Terraform for infrastructure as code

**AI/ML:**
- AWS Bedrock (Claude 3.5 Sonnet, GPT-4o-mini)
- AWS Transcribe (speech-to-text)
- AWS Polly Neural (text-to-speech)
- Pinecone or Amazon OpenSearch (vector embeddings)

**Database:**
- PostgreSQL 15+ (structured data)
- Redis 7+ (caching, sessions)
- DynamoDB (high-throughput key-value)

**Clients:**
- TypeScript 5+ (shared core, CLI, mobile)
- Node.js 20+ with Ink (CLI)
- React Native 0.73+ (mobile)

## Next Steps After Approval

1. Set up AWS account and configure credentials
2. Initialize monorepo structure with pnpm workspaces
3. Create Terraform infrastructure files
4. Implement Phase 1: Backend Foundation
5. Begin parallel development of CLI and mobile clients
6. Iterate on JARVIS personality and voice quality

## External Dependencies to Obtain

- AWS account with appropriate service limits
- OpenAI/Anthropic API keys (for Bedrock)
- NewsAPI key (free tier: 100 req/day)
- OpenWeatherMap API key (free tier: 1000 calls/day)
- Google Calendar API credentials (OAuth setup)
- Picovoice Porcupine license for wake word detection

---

**Estimated Timeline:** 12 weeks for MVP with all core features
**Team Size:** 1-2 developers
**Risk Areas:** Voice latency optimization, LLM cost management, OAuth integration complexity
