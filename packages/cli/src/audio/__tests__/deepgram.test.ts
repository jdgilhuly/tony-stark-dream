/**
 * Deepgram STT Client Tests
 * Following TDD: Red → Green → Refactor
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock WebSocket - must be defined before vi.mock
const mockWsInstances: any[] = [];

vi.mock('ws', () => {
  class MockWebSocket {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;

    readyState = 0; // CONNECTING
    onopen: (() => void) | null = null;
    onmessage: ((event: { data: string }) => void) | null = null;
    onerror: ((error: Error) => void) | null = null;
    onclose: (() => void) | null = null;

    send = vi.fn();
    close = vi.fn(() => {
      this.readyState = 3; // CLOSED
      this.onclose?.();
    });

    constructor() {
      mockWsInstances.push(this);
    }

    simulateOpen() {
      this.readyState = 1; // OPEN
      this.onopen?.();
    }

    simulateMessage(data: object) {
      this.onmessage?.({ data: JSON.stringify(data) });
    }

    simulateError(error: Error) {
      this.onerror?.(error);
    }

    simulateClose() {
      this.readyState = 3; // CLOSED
      this.onclose?.();
    }
  }

  return {
    default: MockWebSocket,
    WebSocket: MockWebSocket,
  };
});

import { DeepgramClient, DeepgramConfig, TranscriptEvent } from '../deepgram.js';

describe('DeepgramClient', () => {
  let client: DeepgramClient;
  const testConfig: DeepgramConfig = {
    apiKey: 'test-api-key',
    sampleRate: 16000,
    channels: 1,
    encoding: 'linear16',
    language: 'en-US',
  };

  const getMockWs = () => mockWsInstances[mockWsInstances.length - 1];

  beforeEach(() => {
    vi.clearAllMocks();
    mockWsInstances.length = 0;
    client = new DeepgramClient(testConfig);
  });

  afterEach(() => {
    client.disconnect();
  });

  describe('Connection Lifecycle', () => {
    it('should connect to Deepgram WebSocket', async () => {
      const connectPromise = client.connect();

      // Get the mock WebSocket instance
      const mockWs = getMockWs();
      expect(mockWs).toBeDefined();

      // Simulate connection open
      mockWs.simulateOpen();

      await connectPromise;
      expect(client.isConnected()).toBe(true);
    });

    it('should disconnect cleanly', async () => {
      const connectPromise = client.connect();
      const mockWs = getMockWs();
      mockWs.simulateOpen();
      await connectPromise;

      client.disconnect();

      expect(mockWs.close).toHaveBeenCalled();
      expect(client.isConnected()).toBe(false);
    });

    it('should emit connected event on open', async () => {
      const onConnected = vi.fn();
      client.on('connected', onConnected);

      const connectPromise = client.connect();
      const mockWs = getMockWs();
      mockWs.simulateOpen();
      await connectPromise;

      expect(onConnected).toHaveBeenCalled();
    });

    it('should emit disconnected event on close', async () => {
      const onDisconnected = vi.fn();
      client.on('disconnected', onDisconnected);

      const connectPromise = client.connect();
      const mockWs = getMockWs();
      mockWs.simulateOpen();
      await connectPromise;

      mockWs.simulateClose();

      expect(onDisconnected).toHaveBeenCalled();
    });
  });

  describe('Audio Streaming', () => {
    let mockWs: any;

    beforeEach(async () => {
      const connectPromise = client.connect();
      mockWs = getMockWs();
      mockWs.simulateOpen();
      await connectPromise;
    });

    it('should send audio chunks via WebSocket', () => {
      const audioChunk = new ArrayBuffer(1024);
      client.sendAudio(audioChunk);

      expect(mockWs.send).toHaveBeenCalledWith(audioChunk);
    });

    it('should not send audio when disconnected', () => {
      client.disconnect();

      const audioChunk = new ArrayBuffer(1024);
      client.sendAudio(audioChunk);

      // send was called once during disconnect (close frame), not for audio
      expect(mockWs.send).not.toHaveBeenCalledWith(audioChunk);
    });
  });

  describe('Transcript Events', () => {
    let mockWs: any;

    beforeEach(async () => {
      const connectPromise = client.connect();
      mockWs = getMockWs();
      mockWs.simulateOpen();
      await connectPromise;
    });

    it('should emit transcript event for final transcripts', () => {
      const onTranscript = vi.fn();
      client.on('transcript', onTranscript);

      const transcriptData = {
        type: 'Results',
        channel: {
          alternatives: [
            { transcript: 'Hello world', confidence: 0.95 },
          ],
        },
        is_final: true,
        speech_final: true,
      };

      mockWs.simulateMessage(transcriptData);

      expect(onTranscript).toHaveBeenCalledWith(
        expect.objectContaining({
          text: 'Hello world',
          confidence: 0.95,
          isFinal: true,
        })
      );
    });

    it('should emit partial event for interim results', () => {
      const onPartial = vi.fn();
      client.on('partial', onPartial);

      const partialData = {
        type: 'Results',
        channel: {
          alternatives: [
            { transcript: 'Hello', confidence: 0.8 },
          ],
        },
        is_final: false,
        speech_final: false,
      };

      mockWs.simulateMessage(partialData);

      expect(onPartial).toHaveBeenCalledWith(
        expect.objectContaining({
          text: 'Hello',
          isFinal: false,
        })
      );
    });

    it('should emit speechStarted event', () => {
      const onSpeechStarted = vi.fn();
      client.on('speechStarted', onSpeechStarted);

      const speechStartData = {
        type: 'SpeechStarted',
      };

      mockWs.simulateMessage(speechStartData);

      expect(onSpeechStarted).toHaveBeenCalled();
    });

    it('should emit utteranceEnd event', () => {
      const onUtteranceEnd = vi.fn();
      client.on('utteranceEnd', onUtteranceEnd);

      const utteranceEndData = {
        type: 'UtteranceEnd',
      };

      mockWs.simulateMessage(utteranceEndData);

      expect(onUtteranceEnd).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should emit error event on WebSocket error', async () => {
      const onError = vi.fn();
      client.on('error', onError);

      const connectPromise = client.connect();
      const mockWs = getMockWs();
      mockWs.simulateOpen();
      await connectPromise;

      const testError = new Error('Connection failed');
      mockWs.simulateError(testError);

      expect(onError).toHaveBeenCalledWith(testError);
    });

    it('should handle malformed messages gracefully', async () => {
      const onError = vi.fn();
      client.on('error', onError);

      const connectPromise = client.connect();
      const mockWs = getMockWs();
      mockWs.simulateOpen();
      await connectPromise;

      // Send invalid JSON
      mockWs.onmessage?.({ data: 'not valid json' });

      // Should emit error but not crash
      expect(onError).toHaveBeenCalled();
    });
  });

  describe('Configuration', () => {
    it('should build correct WebSocket URL with params', () => {
      const url = (client as any).buildWebSocketUrl();

      expect(url).toContain('wss://api.deepgram.com/v1/listen');
      expect(url).toContain('encoding=linear16');
      expect(url).toContain('sample_rate=16000');
      expect(url).toContain('channels=1');
      expect(url).toContain('language=en-US');
    });

    it('should include interim_results and utterance_end_ms params', () => {
      const url = (client as any).buildWebSocketUrl();

      expect(url).toContain('interim_results=true');
      expect(url).toContain('utterance_end_ms=1000');
    });
  });
});
