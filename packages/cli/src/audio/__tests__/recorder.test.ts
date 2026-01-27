import { describe, it, expect, beforeEach, afterEach, vi, Mock } from 'vitest';
import { EventEmitter } from 'events';

// Create mock function for record - needs to be hoisted
const mockRecordFn = vi.fn();

// Mock node-record-lpcm16 before importing the module
// Handle both CommonJS default export and named export patterns
vi.mock('node-record-lpcm16', () => {
  return {
    default: mockRecordFn,
    record: mockRecordFn,
  };
});

// Mock play-sound before importing
vi.mock('play-sound', () => ({
  default: vi.fn(),
}));

import { NodeAudioRecorder, NodeAudioPlayer } from '../recorder.js';

describe('NodeAudioRecorder', () => {
  let recorder: NodeAudioRecorder;
  let mockStream: EventEmitter;
  let mockRecordInstance: { stream: Mock; stop: Mock };

  beforeEach(async () => {
    vi.resetAllMocks();

    // Create mock stream
    mockStream = new EventEmitter();

    // Create mock record instance
    mockRecordInstance = {
      stream: vi.fn().mockReturnValue(mockStream),
      stop: vi.fn(),
    };

    // Setup the mock - mockRecordFn is used by both default and record exports
    mockRecordFn.mockReturnValue(mockRecordInstance);

    recorder = new NodeAudioRecorder();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('constructor', () => {
    it('should create recorder with default options', () => {
      expect(recorder.getSampleRate()).toBe(16000);
      expect(recorder.getChannels()).toBe(1);
    });

    it('should create recorder with custom options', () => {
      const customRecorder = new NodeAudioRecorder({
        sampleRate: 44100,
        channels: 2,
      });
      expect(customRecorder.getSampleRate()).toBe(44100);
      expect(customRecorder.getChannels()).toBe(2);
    });
  });

  describe('isRecording', () => {
    it('should return false initially', () => {
      expect(recorder.isRecording()).toBe(false);
    });

    it('should return true after start', async () => {
      await recorder.start();
      expect(recorder.isRecording()).toBe(true);
    });

    it('should return false after stop', async () => {
      await recorder.start();
      await recorder.stop();
      expect(recorder.isRecording()).toBe(false);
    });
  });

  describe('start', () => {
    it('should start recording with correct options', async () => {
      await recorder.start();

      // mockRecordFn is used by the module (as default export)
      expect(mockRecordFn).toHaveBeenCalledWith({
        sampleRate: 16000,
        channels: 1,
        threshold: 0.5,
        silence: '1.0',
        recorder: 'sox',
        audioType: 'raw',
      });
    });

    it('should throw if already recording', async () => {
      await recorder.start();
      await expect(recorder.start()).rejects.toThrow('Already recording');
    });
  });

  describe('stop', () => {
    it('should return empty ArrayBuffer if not recording', async () => {
      const result = await recorder.stop();
      expect(result.byteLength).toBe(0);
    });

    it('should return combined audio buffer', async () => {
      await recorder.start();

      // Simulate audio data arriving
      const chunk1 = Buffer.from([1, 2, 3, 4]);
      const chunk2 = Buffer.from([5, 6, 7, 8]);
      mockStream.emit('data', chunk1);
      mockStream.emit('data', chunk2);

      const result = await recorder.stop();

      expect(result.byteLength).toBe(8);
      expect(mockRecordInstance.stop).toHaveBeenCalled();
    });

    it('should clear buffer after stop', async () => {
      await recorder.start();
      mockStream.emit('data', Buffer.from([1, 2, 3, 4]));
      await recorder.stop();

      // Second stop should return empty
      const result = await recorder.stop();
      expect(result.byteLength).toBe(0);
    });
  });

  describe('onData callback', () => {
    it('should invoke callback for each chunk', async () => {
      const dataCallback = vi.fn();
      recorder.onData(dataCallback);

      await recorder.start();

      const chunk = Buffer.from([1, 2, 3, 4]);
      mockStream.emit('data', chunk);

      expect(dataCallback).toHaveBeenCalledTimes(1);
      expect(dataCallback).toHaveBeenCalledWith(expect.any(ArrayBuffer));
    });

    it('should copy data to new ArrayBuffer', async () => {
      const receivedBuffers: ArrayBuffer[] = [];
      recorder.onData((data) => receivedBuffers.push(data));

      await recorder.start();
      mockStream.emit('data', Buffer.from([1, 2, 3, 4]));

      expect(receivedBuffers[0]).toBeInstanceOf(ArrayBuffer);
      expect(receivedBuffers[0].byteLength).toBe(4);
    });
  });

  describe('error handling', () => {
    it('should handle stream errors', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      await recorder.start();
      mockStream.emit('error', new Error('Test error'));

      expect(consoleSpy).toHaveBeenCalled();
      expect(recorder.isRecording()).toBe(false);

      consoleSpy.mockRestore();
    });
  });

  describe('getSampleRate', () => {
    it('should return configured sample rate', () => {
      expect(recorder.getSampleRate()).toBe(16000);
    });
  });

  describe('getChannels', () => {
    it('should return configured channels', () => {
      expect(recorder.getChannels()).toBe(1);
    });
  });
});
