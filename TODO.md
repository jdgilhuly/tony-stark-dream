# Development Methodology (All Projects)

## Test-Driven Development (TDD)
All code should follow TDD:
1. **Red:** Write a failing test first
2. **Green:** Write minimal code to pass the test
3. **Refactor:** Clean up while keeping tests green

Benefits: Better design, fewer bugs, confident refactoring, living documentation.

## Research with Claude Code Browser
Use Claude Code's browser capabilities to:
- Navigate API documentation and find endpoints
- Understand data structures from source websites
- Explore SDK/library docs for implementation patterns
- Verify current API availability and rate limits

---

# Get Voice Working for Jarvis

## Overview
Enable voice interaction for Jarvis assistant - both speech-to-text input and text-to-speech output.

## Tech Stack
- **STT:** Deepgram (real-time streaming, lowest latency, excellent accuracy)
- **TTS:** ElevenLabs (most natural sounding, ~$0.30/1k chars)

## Architecture
- WebSocket connection for real-time audio streaming
- Voice Activity Detection (VAD) to detect when user stops speaking
- Audio queue for handling TTS responses
- Barge-in support (interrupt TTS when user speaks)

## Tasks
- [ ] Use Claude browser to explore Deepgram docs and WebSocket API
- [ ] Write tests for audio capture and STT integration
- [ ] Implement Deepgram streaming client (TDD)
- [ ] Write tests for VAD behavior
- [ ] Add VAD for automatic speech endpoint detection (TDD)
- [ ] Write tests for TTS playback queue
- [ ] Integrate ElevenLabs TTS (TDD)
- [ ] Write tests for interruption handling
- [ ] Implement barge-in (stop TTS when user speaks) (TDD)
- [ ] Add visual feedback (waveform, listening indicator)
- [ ] Optimize latency (target <500ms response start)
