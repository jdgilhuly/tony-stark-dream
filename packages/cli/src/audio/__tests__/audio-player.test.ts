import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { EventEmitter } from 'events';
import { PassThrough } from 'stream';

// Create a factory for mock speaker that properly emits events
function createMockSpeaker() {
  const emitter = new EventEmitter();
  const mockSpeaker = Object.assign(emitter, {
    close: vi.fn((flush: boolean) => {
      // Emit close event synchronously for testing
      process.nextTick(() => emitter.emit('close'));
    }),
    write: vi.fn().mockReturnValue(true),
    end: vi.fn(() => {
      process.nextTick(() => emitter.emit('close'));
    }),
  });

  // Make it writable stream compatible
  (mockSpeaker as any).writable = true;
  (mockSpeaker as any).cork = vi.fn();
  (mockSpeaker as any).uncork = vi.fn();
  (mockSpeaker as any).destroy = vi.fn();
  (mockSpeaker as any).destroyed = false;
  (mockSpeaker as any).setDefaultEncoding = vi.fn();

  return mockSpeaker;
}

// Mock Speaker
vi.mock('speaker', () => {
  return {
    default: vi.fn().mockImplementation(() => createMockSpeaker()),
  };
});

import { AudioPlayer, VoiceOutput, Mp3Player, getVoiceOutput } from '../player.js';

describe('AudioPlayer', () => {
  let player: AudioPlayer;

  beforeEach(() => {
    vi.resetAllMocks();
    player = new AudioPlayer();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('constructor', () => {
    it('should create player with default options', () => {
      expect(player.playing).toBe(false);
    });

    it('should create player with custom options', () => {
      const customPlayer = new AudioPlayer({
        sampleRate: 44100,
        channels: 2,
        bitDepth: 24,
      });
      expect(customPlayer.playing).toBe(false);
    });
  });

  describe('playing property', () => {
    it('should return false initially', () => {
      expect(player.playing).toBe(false);
    });
  });

  describe('playPcm', () => {
    it('should return a PlaybackResult', async () => {
      const audioData = Buffer.from([0, 0, 0, 0]);
      const result = await player.playPcm(audioData);

      expect(result).toHaveProperty('success');
    });

    it('should set playing to false after playback resolves', async () => {
      const audioData = Buffer.from([0, 0, 0, 0]);
      await player.playPcm(audioData);

      expect(player.playing).toBe(false);
    });
  });

  describe('playStream', () => {
    it('should return a PlaybackResult', async () => {
      const stream = new PassThrough();
      stream.end(Buffer.from([0, 0, 0, 0]));

      const result = await player.playStream(stream);

      expect(result).toHaveProperty('success');
    });
  });

  describe('stop', () => {
    it('should not throw when not playing', async () => {
      await expect(player.stop()).resolves.not.toThrow();
    });

    it('should resolve when called on idle player', async () => {
      const result = await player.stop();
      expect(result).toBeUndefined();
    });
  });
});

describe('VoiceOutput', () => {
  let voiceOutput: VoiceOutput;

  beforeEach(() => {
    vi.resetAllMocks();
    voiceOutput = new VoiceOutput();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('queue management', () => {
    it('should start with empty queue', () => {
      expect(voiceOutput.queueLength).toBe(0);
    });

    it('should not be playing initially', () => {
      expect(voiceOutput.isPlaying).toBe(false);
    });
  });

  describe('enqueue', () => {
    it('should not throw when adding audio', () => {
      expect(() => voiceOutput.enqueue(Buffer.from([1, 2, 3]))).not.toThrow();
    });
  });

  describe('clear', () => {
    it('should clear the queue', async () => {
      voiceOutput.enqueue(Buffer.from([1, 2, 3]));
      await voiceOutput.clear();
      expect(voiceOutput.queueLength).toBe(0);
    });

    it('should not throw when clearing empty queue', async () => {
      await expect(voiceOutput.clear()).resolves.not.toThrow();
    });
  });

  describe('speakNow', () => {
    it('should return a PlaybackResult', async () => {
      const result = await voiceOutput.speakNow(Buffer.from([4, 5, 6]));
      expect(result).toHaveProperty('success');
    });
  });

  describe('isPlaying', () => {
    it('should return false when not playing', () => {
      expect(voiceOutput.isPlaying).toBe(false);
    });
  });

  describe('queueLength', () => {
    it('should return 0 for empty queue', () => {
      expect(voiceOutput.queueLength).toBe(0);
    });
  });
});

describe('Mp3Player', () => {
  let mp3Player: Mp3Player;

  beforeEach(() => {
    vi.resetAllMocks();
    mp3Player = new Mp3Player();
  });

  describe('playing property', () => {
    it('should return false initially', () => {
      expect(mp3Player.playing).toBe(false);
    });
  });

  describe('play without lame decoder', () => {
    it('should return error result when lame is not available', async () => {
      const result = await mp3Player.play(Buffer.from([1, 2, 3]));
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('stop', () => {
    it('should not throw when not playing', async () => {
      await expect(mp3Player.stop()).resolves.not.toThrow();
    });
  });
});

describe('getVoiceOutput', () => {
  it('should return a VoiceOutput instance', () => {
    const output = getVoiceOutput();
    expect(output).toBeInstanceOf(VoiceOutput);
  });

  it('should return the same singleton instance', () => {
    const output1 = getVoiceOutput();
    const output2 = getVoiceOutput();
    expect(output1).toBe(output2);
  });
});
