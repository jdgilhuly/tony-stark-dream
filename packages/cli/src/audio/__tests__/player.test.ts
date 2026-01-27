import { describe, it, expect, beforeEach, afterEach, vi, Mock } from 'vitest';

// Mock play-sound before importing
vi.mock('play-sound', () => ({
  default: vi.fn(),
}));

import { NodeAudioPlayer } from '../recorder.js';

describe('NodeAudioPlayer', () => {
  let player: NodeAudioPlayer;
  let mockPlayerInstance: { play: Mock };

  beforeEach(async () => {
    vi.resetAllMocks();

    mockPlayerInstance = {
      play: vi.fn(),
    };

    const playSoundModule = await import('play-sound');
    (playSoundModule.default as Mock).mockReturnValue(mockPlayerInstance);

    player = new NodeAudioPlayer();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('isPlaying', () => {
    it('should return false initially', () => {
      expect(player.isPlaying()).toBe(false);
    });
  });

  describe('play with file path', () => {
    it('should play audio from file path', async () => {
      mockPlayerInstance.play.mockImplementation(
        (filePath: string, callback: (err: Error | null) => void) => {
          callback(null);
        }
      );

      await player.play('/path/to/audio.mp3');

      expect(mockPlayerInstance.play).toHaveBeenCalledWith(
        '/path/to/audio.mp3',
        expect.any(Function)
      );
    });

    it('should reject on playback error', async () => {
      mockPlayerInstance.play.mockImplementation(
        (filePath: string, callback: (err: Error | null) => void) => {
          callback(new Error('Playback failed'));
        }
      );

      await expect(player.play('/path/to/audio.mp3')).rejects.toThrow('Playback failed');
    });

    it('should call onComplete callback after successful playback', async () => {
      const completeCallback = vi.fn();
      player.onComplete(completeCallback);

      mockPlayerInstance.play.mockImplementation(
        (filePath: string, callback: (err: Error | null) => void) => {
          callback(null);
        }
      );

      await player.play('/path/to/audio.mp3');
      expect(completeCallback).toHaveBeenCalled();
    });
  });

  describe('stop', () => {
    it('should not throw when not playing', () => {
      expect(() => player.stop()).not.toThrow();
    });
  });

  describe('pause', () => {
    it('should not throw (not supported)', () => {
      expect(() => player.pause()).not.toThrow();
    });
  });

  describe('resume', () => {
    it('should not throw (not supported)', () => {
      expect(() => player.resume()).not.toThrow();
    });
  });

  describe('setVolume', () => {
    it('should clamp volume to max 1', () => {
      expect(() => player.setVolume(1.5)).not.toThrow();
    });

    it('should clamp volume to min 0', () => {
      expect(() => player.setVolume(-0.5)).not.toThrow();
    });

    it('should accept valid volume', () => {
      expect(() => player.setVolume(0.5)).not.toThrow();
    });
  });

  describe('onComplete callback', () => {
    it('should invoke callback after successful playback', async () => {
      const completeCallback = vi.fn();
      player.onComplete(completeCallback);

      mockPlayerInstance.play.mockImplementation(
        (filePath: string, callback: (err: Error | null) => void) => {
          callback(null);
        }
      );

      await player.play('/path/to/audio.mp3');
      expect(completeCallback).toHaveBeenCalled();
    });

    it('should not invoke callback on error', async () => {
      const completeCallback = vi.fn();
      player.onComplete(completeCallback);

      mockPlayerInstance.play.mockImplementation(
        (filePath: string, callback: (err: Error | null) => void) => {
          callback(new Error('Playback failed'));
        }
      );

      await expect(player.play('/path/to/audio.mp3')).rejects.toThrow();
      expect(completeCallback).not.toHaveBeenCalled();
    });
  });
});
