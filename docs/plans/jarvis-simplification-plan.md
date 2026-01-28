# JARVIS Simplification Plan

## Project Overview

Simplify JARVIS from a 10+ microservice architecture down to a single TypeScript CLI application that wraps Claude Code. Users interact with JARVIS via text or voice (push-to-talk), and JARVIS invokes Claude Code using the `-p` flag to execute tasks in the current working directory. The entire system will be containerized in a single Docker image.

**Before:** 10 microservices, PostgreSQL, Redis, complex agent routing
**After:** 1 CLI application, markdown file for session memory, Claude Code as the backend

---

## Functional Requirements

### Core Features

- **Text Chat Interface**
  - Interactive REPL loop in terminal
  - User types messages, JARVIS responds
  - Maintains JARVIS persona in all responses
  - Session history displayed in terminal

- **Voice Interface (Push-to-Talk)**
  - User presses key (e.g., `Space`) to start recording
  - Release key to stop and process
  - Local Whisper for speech-to-text transcription
  - Local TTS (pyttsx3 on Linux, `say` on macOS) for spoken responses
  - Visual indicator showing recording state

- **Claude Code Integration**
  - Execute `claude -p "system_prompt + user_message"` for each interaction
  - Capture stdout/stderr from Claude Code
  - Display formatted response to user
  - Pass conversation context via the prompt

- **Session Memory**
  - Store conversation in `.jarvis-session.md` in current directory
  - Markdown format with timestamps and speaker labels
  - Load previous session on startup if file exists
  - Include last N messages in Claude Code prompt for context
  - Clear session with `/clear` command

- **JARVIS Persona**
  - System prompt establishing JARVIS identity
  - Formal British butler personality
  - References to "Sir" or user's preferred title
  - Maintains helpful, witty, intelligent demeanor

### User Commands

| Command | Description |
|---------|-------------|
| `/voice` | Toggle voice mode on/off |
| `/clear` | Clear session history |
| `/history` | Show full conversation history |
| `/help` | Show available commands |
| `/exit` or `Ctrl+C` | Exit JARVIS |

---

## Non-Functional Requirements

### Performance
- Response time: < 2 seconds for text input to Claude Code execution start
- Voice transcription: < 3 seconds for typical utterance
- TTS playback: Start within 500ms of response completion

### Security
- No external API calls except Claude Code's own API
- Session files stored locally only
- No credentials stored (relies on user's Claude Code auth)

### Scalability
- Single-user CLI tool (no multi-tenancy)
- Memory-efficient (stream Claude Code output)

### Reliability
- Graceful handling of Claude Code failures
- Timeout handling for voice recording
- Clear error messages

### Usability
- Works out-of-the-box with minimal config
- Color-coded terminal output
- Clear recording state indicators
- Accessible keyboard shortcuts

---

## Technical Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────┐
│                    JARVIS CLI                         │
│                   (TypeScript)                        │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   Text UI   │  │  Voice UI   │  │   Session   │  │
│  │    (Ink)    │  │ (Push-Talk) │  │   Manager   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │
│         │                │                │          │
│         └────────────────┼────────────────┘          │
│                          │                           │
│                  ┌───────▼───────┐                   │
│                  │  Orchestrator │                   │
│                  └───────┬───────┘                   │
│                          │                           │
│         ┌────────────────┼────────────────┐         │
│         │                │                │         │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐ │
│  │  Whisper    │  │ Claude Code │  │    TTS      │ │
│  │  (Local)    │  │  Executor   │  │  (Local)    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└──────────────────────────────────────────────────────┘
                          │
                          │ spawn process
                          ▼
              ┌─────────────────────┐
              │    Claude Code      │
              │   (claude -p ...)   │
              └─────────────────────┘
                          │
                          │ operates on
                          ▼
              ┌─────────────────────┐
              │  Current Directory  │
              │   (User's codebase) │
              └─────────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| Runtime | Node.js 20+ / Bun |
| Language | TypeScript 5+ |
| CLI Framework | Ink (React for terminal) |
| Voice Recording | node-record-lpcm16 |
| Speech-to-Text | Whisper.cpp (local) |
| Text-to-Speech | pyttsx3 (Linux) / say (macOS) |
| Claude Integration | Child process spawn |
| Container | Docker (single image) |

### File Structure

```
jarvis-simple/
├── src/
│   ├── index.ts              # Entry point
│   ├── components/
│   │   ├── App.tsx           # Main Ink component
│   │   ├── ChatInput.tsx     # Text input component
│   │   ├── MessageList.tsx   # Display messages
│   │   └── VoiceIndicator.tsx # Recording state UI
│   ├── services/
│   │   ├── claude.ts         # Claude Code executor
│   │   ├── session.ts        # Session file manager
│   │   ├── voice.ts          # Voice recording
│   │   ├── whisper.ts        # Speech-to-text
│   │   └── tts.ts            # Text-to-speech
│   ├── prompts/
│   │   └── jarvis.ts         # JARVIS system prompt
│   └── types.ts              # TypeScript interfaces
├── Dockerfile
├── package.json
├── tsconfig.json
└── README.md
```

---

## User Flows

### Flow 1: Text Conversation

```
1. User starts JARVIS: `jarvis` or `docker run jarvis`
2. JARVIS loads any existing .jarvis-session.md
3. JARVIS displays welcome message
4. User types: "Help me refactor this function"
5. JARVIS builds prompt:
   - System prompt (JARVIS persona)
   - Last 5 messages from session
   - Current user message
6. JARVIS executes: claude -p "<combined_prompt>"
7. Claude Code response is captured
8. Response is displayed with JARVIS formatting
9. Both messages appended to .jarvis-session.md
10. Loop continues until /exit
```

### Flow 2: Voice Conversation

```
1. User types `/voice` to enable voice mode
2. Visual indicator shows "Voice Mode Active"
3. User presses and holds Space
4. Visual indicator shows "Recording..."
5. User speaks: "What does this config file do?"
6. User releases Space
7. Audio is transcribed via local Whisper
8. Transcribed text displayed
9. Same flow as text (steps 5-9 above)
10. Response is spoken via TTS
11. Response also displayed in terminal
```

### Flow 3: Session Management

```
1. User has been chatting for 20 messages
2. User types `/history`
3. Full session displayed (scrollable)
4. User types `/clear`
5. JARVIS asks confirmation: "Clear session history, Sir?"
6. User confirms
7. .jarvis-session.md is deleted
8. Fresh session begins
```

---

## Data Model

### Session File Format (`.jarvis-session.md`)

```markdown
# JARVIS Session
Started: 2024-01-15 10:30:00

---

## 10:30:00 - User
Help me understand the auth flow in this codebase

---

## 10:30:15 - JARVIS
Certainly, Sir. Based on my analysis of the codebase...

[Claude Code's response here]

---

## 10:31:00 - User
Can you add rate limiting to the login endpoint?

---

## 10:31:20 - JARVIS
Of course, Sir. I shall implement rate limiting...

[Response continues]
```

### Message Interface

```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  voiceInput?: boolean;  // Was this from voice?
}

interface Session {
  startedAt: Date;
  messages: Message[];
  voiceModeActive: boolean;
}
```

---

## API Design

This is a CLI tool, not a service with an API. However, the internal interfaces are:

### Claude Code Executor

```typescript
interface ClaudeExecutor {
  // Execute Claude Code with prompt
  execute(prompt: string, options?: ExecuteOptions): Promise<string>;
}

interface ExecuteOptions {
  timeout?: number;      // Max execution time (default: 120s)
  cwd?: string;          // Working directory (default: process.cwd())
}
```

### Session Manager

```typescript
interface SessionManager {
  load(): Promise<Session | null>;
  save(session: Session): Promise<void>;
  clear(): Promise<void>;
  getContextMessages(count: number): Message[];
}
```

### Voice Service

```typescript
interface VoiceService {
  startRecording(): void;
  stopRecording(): Promise<Buffer>;
  transcribe(audio: Buffer): Promise<string>;
  speak(text: string): Promise<void>;
}
```

---

## Non-Goals / Out of Scope

The following features from the original JARVIS will NOT be included:

- **Agent routing system** - No 130 specialized agents, just JARVIS
- **Multi-user support** - Single-user CLI only
- **Web/Mobile clients** - CLI only
- **Database persistence** - Markdown files only
- **Redis caching** - No external services
- **API Gateway** - No HTTP server
- **Weather/News/Calendar integration** - No external APIs
- **Wake word detection** - Push-to-talk only
- **Briefing service** - No scheduled features
- **Notification service** - No push notifications
- **Task management system** - Claude Code handles tasks directly
- **User profile service** - Minimal config only
- **OAuth/Authentication** - Relies on Claude Code's auth
- **Streaming responses** - Wait for full response (simpler)
- **WebSocket connections** - Not needed for CLI

---

## Implementation Plan

### Phase 1: Core CLI (MVP)
1. Set up TypeScript project with Ink
2. Implement Claude Code executor (`claude -p`)
3. Create JARVIS system prompt
4. Build basic text chat UI
5. Implement session file (markdown) persistence
6. Add basic commands (/help, /clear, /exit)

### Phase 2: Voice Support
1. Integrate node-record-lpcm16 for audio capture
2. Set up local Whisper for transcription
3. Implement push-to-talk with Space key
4. Add TTS output (platform-specific)
5. Voice mode toggle command

### Phase 3: Docker
1. Create Dockerfile with all dependencies
2. Include Whisper model in image
3. Handle audio device passthrough
4. Test on Linux and macOS
5. Publish to Docker Hub (optional)

### Phase 4: Polish
1. Improve error handling
2. Add color themes
3. Configuration file support
4. README and documentation
5. Final testing

---

## Docker Considerations

### Base Image
```dockerfile
FROM node:20-slim

# Install audio dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    portaudio19-dev \
    python3 \
    python3-pip \
    && pip3 install pyttsx3

# Install Whisper.cpp
RUN git clone https://github.com/ggerganov/whisper.cpp && \
    cd whisper.cpp && make && \
    ./models/download-ggml-model.sh base.en

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code
```

### Audio Passthrough
For voice to work in Docker:
```bash
# Linux
docker run -it --device /dev/snd jarvis

# macOS (requires PulseAudio)
docker run -it -e PULSE_SERVER=docker.for.mac.localhost jarvis
```

---

## Success Criteria

1. User can start JARVIS and have a text conversation
2. Claude Code executes tasks in the current directory
3. Conversation persists in .jarvis-session.md
4. Voice input/output works with push-to-talk
5. Single Docker container runs the entire system
6. No external services required (besides Claude Code's API)
