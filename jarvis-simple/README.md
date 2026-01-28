# JARVIS Simple

A simplified AI assistant powered by Claude Code. Talk to JARVIS via text or voice, and let Claude Code handle the heavy lifting.

## Quick Start

### Local Development

```bash
# Install dependencies
npm install

# Run in development mode
npm run dev

# Or build and run
npm run build
npm start
```

### Docker

```bash
# Build the image
docker build -t jarvis .

# Run (mount your project directory)
docker run -it -v $(pwd):/workspace jarvis

# With audio support (Linux)
docker run -it --device /dev/snd -v $(pwd):/workspace jarvis
```

## Commands

| Command | Description |
|---------|-------------|
| `/voice` | Toggle voice mode (push-to-talk) |
| `/clear` | Clear conversation history |
| `/history` | Show full conversation |
| `/help` | Show available commands |
| `/exit` | Exit JARVIS |

## Voice Mode

When voice mode is enabled:
1. Hold **Space** to start recording
2. Release **Space** to stop and transcribe
3. JARVIS will speak the response

### Voice Requirements

- **macOS**: Built-in `say` command and `rec` (install with `brew install sox`)
- **Linux**: `espeak` for TTS, `arecord` for recording
- **Whisper**: Install [whisper.cpp](https://github.com/ggerganov/whisper.cpp) or [openai-whisper](https://github.com/openai/whisper)

## How It Works

1. You send a message to JARVIS
2. JARVIS builds a prompt with the JARVIS persona + conversation context
3. The prompt is sent to Claude Code via `claude -p`
4. Claude Code executes in your current directory
5. Response is displayed (and spoken if voice mode is on)
6. Conversation is saved to `.jarvis-session.md`

## Session Persistence

Conversations are stored in `.jarvis-session.md` in your current directory. This file is human-readable markdown and persists between sessions.

## Requirements

- Node.js 20+
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)
- Valid Claude Code authentication (run `claude` once to set up)

### For Voice (Optional)

- **macOS**: `brew install sox`
- **Linux**: `apt install sox alsa-utils espeak`
- **Whisper**: See [whisper.cpp](https://github.com/ggerganov/whisper.cpp) installation

## Environment

JARVIS operates in your current working directory. Claude Code will have access to read/write files in that directory.

## License

MIT
