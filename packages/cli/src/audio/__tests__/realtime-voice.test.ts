/**
 * Real-time Voice Pipeline Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { RealtimeVoicePipeline, RealtimeVoiceState } from '../realtime-voice.js';

// Mock dependencies
vi.mock('../deepgram.js', () => ({
  DeepgramClient: vi.fn().mockImplementation(() => ({
    on: vi.fn(),
    off: vi.fn(),
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    isConnected: vi.fn().mockReturnValue(false),
    sendAudio: vi.fn(),
    finishStream: vi.fn(),
  })),
}));

vi.mock('../elevenlabs.js', () => ({
  ElevenLabsClient: vi.fn().mockImplementation(() => ({
    synthesize: vi.fn().mockResolvedValue(new ArrayBuffer(100)),
    synthesizeStream: vi.fn().mockImplementation(async (text, onChunk) => {
      onChunk(new ArrayBuffer(50));
    }),
  })),
  ELEVENLABS_MODELS: {},
}));

vi.mock('../node-wake-word.js', () => ({
  NodeWakeWordDetector: vi.fn().mockImplementation(() => ({
    on: vi.fn(),
    off: vi.fn(),
    start: vi.fn().mockResolvedValue(undefined),
    stop: vi.fn(),
    isActive: vi.fn().mockReturnValue(false),
  })),
}));

describe('RealtimeVoicePipeline', () => {
  let pipeline: RealtimeVoicePipeline;
  let mockRecorder: any;
  let mockPlayer: any;
  let mockConversationClient: any;

  beforeEach(() => {
    pipeline = new RealtimeVoicePipeline({
      wakeWordServerUrl: 'http://localhost:8002',
      deepgramApiKey: 'test-deepgram-key',
      elevenLabsApiKey: 'test-elevenlabs-key',
      elevenLabsVoiceId: 'test-voice-id',
      authToken: 'test-token',
    });

    mockRecorder = {
      start: vi.fn().mockResolvedValue(undefined),
      stop: vi.fn().mockResolvedValue(new ArrayBuffer(100)),
      isRecording: vi.fn().mockReturnValue(false),
      onData: vi.fn(),
    };

    mockPlayer = {
      play: vi.fn().mockResolvedValue(undefined),
      stop: vi.fn(),
      isPlaying: vi.fn().mockReturnValue(false),
    };

    mockConversationClient = {
      sendMessage: vi.fn().mockResolvedValue('Hello, I am JARVIS.'),
    };

    pipeline.setRecorder(mockRecorder);
    pipeline.setPlayer(mockPlayer);
    pipeline.setConversationClient(mockConversationClient);
  });

  afterEach(async () => {
    await pipeline.stop();
    vi.clearAllMocks();
  });

  describe('initialization', () => {
    it('should create pipeline with config', () => {
      expect(pipeline).toBeDefined();
      expect(pipeline.getState()).toBe('initializing');
    });

    it('should start in initializing state', () => {
      expect(pipeline.getState()).toBe('initializing');
    });
  });

  describe('state management', () => {
    it('should emit stateChange events', async () => {
      const stateHandler = vi.fn();
      pipeline.on('stateChange', stateHandler);

      await pipeline.start();

      // Should transition through states
      expect(stateHandler).toHaveBeenCalled();
    });

    it('should transition to wake_word_listening on start', async () => {
      await pipeline.start();
      expect(pipeline.getState()).toBe('wake_word_listening');
    });

    it('should transition to stopped on stop', async () => {
      await pipeline.start();
      await pipeline.stop();
      expect(pipeline.getState()).toBe('stopped');
    });
  });

  describe('component requirements', () => {
    it('should throw if recorder not set', async () => {
      const newPipeline = new RealtimeVoicePipeline({
        wakeWordServerUrl: 'http://localhost:8002',
        deepgramApiKey: 'test-key',
        elevenLabsApiKey: 'test-key',
        elevenLabsVoiceId: 'test-voice',
        authToken: 'test-token',
      });

      newPipeline.setPlayer(mockPlayer);
      newPipeline.setConversationClient(mockConversationClient);

      await expect(newPipeline.start()).rejects.toThrow(
        'Recorder, player, and conversation client must be set'
      );
    });

    it('should throw if player not set', async () => {
      const newPipeline = new RealtimeVoicePipeline({
        wakeWordServerUrl: 'http://localhost:8002',
        deepgramApiKey: 'test-key',
        elevenLabsApiKey: 'test-key',
        elevenLabsVoiceId: 'test-voice',
        authToken: 'test-token',
      });

      newPipeline.setRecorder(mockRecorder);
      newPipeline.setConversationClient(mockConversationClient);

      await expect(newPipeline.start()).rejects.toThrow(
        'Recorder, player, and conversation client must be set'
      );
    });

    it('should throw if conversation client not set', async () => {
      const newPipeline = new RealtimeVoicePipeline({
        wakeWordServerUrl: 'http://localhost:8002',
        deepgramApiKey: 'test-key',
        elevenLabsApiKey: 'test-key',
        elevenLabsVoiceId: 'test-voice',
        authToken: 'test-token',
      });

      newPipeline.setRecorder(mockRecorder);
      newPipeline.setPlayer(mockPlayer);

      await expect(newPipeline.start()).rejects.toThrow(
        'Recorder, player, and conversation client must be set'
      );
    });
  });

  describe('event handling', () => {
    it('should emit wakeWordDetected event', async () => {
      const handler = vi.fn();
      pipeline.on('wakeWordDetected', handler);

      const detection = {
        wakeWord: 'hey_jarvis',
        confidence: 0.9,
        timestamp: Date.now() / 1000,
      };

      pipeline.emit('wakeWordDetected', detection);
      expect(handler).toHaveBeenCalledWith(detection);
    });

    it('should emit transcriptPartial event', () => {
      const handler = vi.fn();
      pipeline.on('transcriptPartial', handler);

      pipeline.emit('transcriptPartial', 'Hello');
      expect(handler).toHaveBeenCalledWith('Hello');
    });

    it('should emit transcriptFinal event', () => {
      const handler = vi.fn();
      pipeline.on('transcriptFinal', handler);

      pipeline.emit('transcriptFinal', 'Hello JARVIS');
      expect(handler).toHaveBeenCalledWith('Hello JARVIS');
    });

    it('should emit bargeIn event', () => {
      const handler = vi.fn();
      pipeline.on('bargeIn', handler);

      pipeline.emit('bargeIn');
      expect(handler).toHaveBeenCalled();
    });

    it('should emit turnComplete event', () => {
      const handler = vi.fn();
      pipeline.on('turnComplete', handler);

      const turn = {
        userText: 'Hello',
        assistantText: 'Hi there',
        startTime: Date.now() - 1000,
        endTime: Date.now(),
        transcriptionLatencyMs: 500,
        ttsLatencyMs: 300,
      };

      pipeline.emit('turnComplete', turn);
      expect(handler).toHaveBeenCalledWith(turn);
    });
  });

  describe('latency tracking', () => {
    it('should track latency metrics', async () => {
      await pipeline.start();
      const metrics = pipeline.getLatencyMetrics();

      expect(metrics).toBeDefined();
      expect(metrics).toHaveProperty('overall');
    });
  });
});

describe('RealtimeVoiceConfig', () => {
  it('should use default values for optional config', () => {
    const pipeline = new RealtimeVoicePipeline({
      wakeWordServerUrl: 'http://localhost:8002',
      deepgramApiKey: 'test-key',
      elevenLabsApiKey: 'test-key',
      elevenLabsVoiceId: 'test-voice',
      authToken: 'test-token',
    });

    // Pipeline should be created with defaults
    expect(pipeline).toBeDefined();
  });

  it('should accept custom config values', () => {
    const pipeline = new RealtimeVoicePipeline({
      wakeWordServerUrl: 'http://localhost:8002',
      wakeWordThreshold: 0.7,
      deepgramApiKey: 'test-key',
      sttLanguage: 'en-GB',
      sttModel: 'nova-2-general',
      elevenLabsApiKey: 'test-key',
      elevenLabsVoiceId: 'test-voice',
      ttsModelId: 'eleven_multilingual_v2',
      silenceDurationMs: 1500,
      energyThreshold: 0.02,
      autoReturnToWakeWord: false,
      enableBargeIn: false,
      conversationTimeoutMs: 60000,
      authToken: 'test-token',
    });

    expect(pipeline).toBeDefined();
  });
});

describe('Voice Pipeline States', () => {
  const validStates: RealtimeVoiceState[] = [
    'initializing',
    'wake_word_listening',
    'active_listening',
    'processing',
    'speaking',
    'error',
    'stopped',
  ];

  it('should have all expected states defined', () => {
    validStates.forEach((state) => {
      expect(typeof state).toBe('string');
    });
  });
});
