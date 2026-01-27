/**
 * Voice Pipeline Tests (Barge-In Support)
 * Following TDD: Red → Green → Refactor
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VoicePipeline, VoicePipelineConfig, VoicePipelineState } from '../voice-pipeline.js';

describe('VoicePipeline', () => {
  let pipeline: VoicePipeline;
  let mockRecorder: any;
  let mockPlayer: any;
  let mockDeepgram: any;
  let mockElevenLabs: any;

  beforeEach(() => {
    mockRecorder = {
      start: vi.fn().mockResolvedValue(undefined),
      stop: vi.fn().mockResolvedValue(new ArrayBuffer(1024)),
      isRecording: vi.fn().mockReturnValue(false),
      onData: vi.fn(),
    };

    mockPlayer = {
      play: vi.fn().mockResolvedValue(undefined),
      stop: vi.fn(),
      isPlaying: vi.fn().mockReturnValue(false),
    };

    mockDeepgram = {
      connect: vi.fn().mockResolvedValue(undefined),
      disconnect: vi.fn(),
      sendAudio: vi.fn(),
      on: vi.fn(),
      off: vi.fn(),
      isConnected: vi.fn().mockReturnValue(true),
    };

    mockElevenLabs = {
      synthesize: vi.fn().mockResolvedValue(new ArrayBuffer(1024)),
      synthesizeStream: vi.fn(),
    };

    pipeline = new VoicePipeline({
      recorder: mockRecorder,
      player: mockPlayer,
      sttClient: mockDeepgram,
      ttsClient: mockElevenLabs,
    });
  });

  afterEach(() => {
    pipeline.stop();
  });

  describe('State Management', () => {
    it('should start in idle state', () => {
      expect(pipeline.getState()).toBe('idle');
    });

    it('should transition to listening when started', async () => {
      await pipeline.startListening();

      expect(pipeline.getState()).toBe('listening');
      expect(mockRecorder.start).toHaveBeenCalled();
    });

    it('should transition to processing after speech ends', async () => {
      await pipeline.startListening();

      // Simulate VAD detecting speech end
      pipeline.handleSpeechEnd();

      expect(pipeline.getState()).toBe('processing');
    });

    it('should transition to speaking when TTS starts', async () => {
      await pipeline.startListening();
      pipeline.handleSpeechEnd();

      // Simulate response received
      await pipeline.speak('Hello');

      expect(pipeline.getState()).toBe('speaking');
    });
  });

  describe('Barge-In Functionality', () => {
    it('should stop TTS playback when user starts speaking', async () => {
      await pipeline.startListening();
      pipeline.handleSpeechEnd();
      await pipeline.speak('Hello');

      expect(pipeline.getState()).toBe('speaking');

      // User starts speaking (barge-in)
      pipeline.handleBargeIn();

      expect(mockPlayer.stop).toHaveBeenCalled();
      expect(pipeline.getState()).toBe('listening');
    });

    it('should emit bargeIn event', async () => {
      const onBargeIn = vi.fn();
      pipeline.on('bargeIn', onBargeIn);

      await pipeline.startListening();
      pipeline.handleSpeechEnd();
      await pipeline.speak('Hello');

      pipeline.handleBargeIn();

      expect(onBargeIn).toHaveBeenCalled();
    });

    it('should clear audio queue on barge-in', async () => {
      await pipeline.startListening();
      pipeline.handleSpeechEnd();
      await pipeline.speak('Hello');

      const queueClearSpy = vi.spyOn(pipeline as any, 'clearAudioQueue');

      pipeline.handleBargeIn();

      expect(queueClearSpy).toHaveBeenCalled();
    });

    it('should resume recording after barge-in', async () => {
      await pipeline.startListening();
      pipeline.handleSpeechEnd();
      await pipeline.speak('Hello');

      mockRecorder.start.mockClear();

      pipeline.handleBargeIn();

      expect(mockRecorder.start).toHaveBeenCalled();
    });
  });

  describe('Events', () => {
    it('should emit stateChange on transitions', async () => {
      const onStateChange = vi.fn();
      pipeline.on('stateChange', onStateChange);

      await pipeline.startListening();

      expect(onStateChange).toHaveBeenCalledWith('listening');
    });

    it('should emit transcript when speech recognized', () => {
      const onTranscript = vi.fn();
      pipeline.on('transcript', onTranscript);

      // Simulate transcript from Deepgram
      pipeline.handleTranscript({ text: 'Hello world', isFinal: true, confidence: 0.95 });

      expect(onTranscript).toHaveBeenCalledWith(
        expect.objectContaining({ text: 'Hello world' })
      );
    });

    it('should emit error on failures', async () => {
      const onError = vi.fn();
      pipeline.on('error', onError);

      mockRecorder.start.mockRejectedValueOnce(new Error('Microphone error'));

      await pipeline.startListening();

      expect(onError).toHaveBeenCalled();
    });
  });

  describe('Stop', () => {
    it('should stop all components', async () => {
      await pipeline.startListening();

      pipeline.stop();

      expect(mockRecorder.stop).toHaveBeenCalled();
      expect(mockPlayer.stop).toHaveBeenCalled();
      expect(mockDeepgram.disconnect).toHaveBeenCalled();
      expect(pipeline.getState()).toBe('idle');
    });

    it('should emit stopped event', async () => {
      const onStopped = vi.fn();
      pipeline.on('stopped', onStopped);

      await pipeline.startListening();
      pipeline.stop();

      expect(onStopped).toHaveBeenCalled();
    });
  });

  describe('Audio Level', () => {
    it('should emit audioLevel events', () => {
      const onAudioLevel = vi.fn();
      pipeline.on('audioLevel', onAudioLevel);

      pipeline.handleAudioLevel(0.5);

      expect(onAudioLevel).toHaveBeenCalledWith(0.5);
    });

    it('should track current audio level', () => {
      pipeline.handleAudioLevel(0.75);

      expect(pipeline.getAudioLevel()).toBe(0.75);
    });
  });
});
