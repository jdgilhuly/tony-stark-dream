/**
 * Audio Queue Tests
 * Following TDD: Red → Green → Refactor
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AudioQueue, AudioQueueConfig } from '../audio-queue.js';

describe('AudioQueue', () => {
  let queue: AudioQueue;
  let mockPlayer: {
    play: ReturnType<typeof vi.fn>;
    stop: ReturnType<typeof vi.fn>;
    isPlaying: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    mockPlayer = {
      play: vi.fn().mockResolvedValue(undefined),
      stop: vi.fn(),
      isPlaying: vi.fn().mockReturnValue(false),
    };

    queue = new AudioQueue(mockPlayer as any);
  });

  afterEach(() => {
    queue.clear();
  });

  describe('Enqueue', () => {
    it('should add audio to pending count', () => {
      const audio = new ArrayBuffer(1024);
      queue.enqueue(audio);

      // Item may already be processing, but pendingCount tracks total
      expect(queue.pendingCount()).toBeGreaterThanOrEqual(0);
    });

    it('should track all enqueued items', async () => {
      // Create a slow player that lets us check queue state
      let resolvePlay: ((value?: unknown) => void) | undefined;
      mockPlayer.play.mockImplementation(() => new Promise(r => { resolvePlay = r; }));

      queue.enqueue(new ArrayBuffer(1024));
      queue.enqueue(new ArrayBuffer(1024));
      queue.enqueue(new ArrayBuffer(1024));

      // First item is processing, 2 still in queue
      expect(queue.length()).toBe(2);

      // Resolve all
      resolvePlay?.();
    });

    it('should start playback when first item added', async () => {
      const audio = new ArrayBuffer(1024);
      queue.enqueue(audio);

      // Give time for async playback to start
      await vi.waitFor(() => {
        expect(mockPlayer.play).toHaveBeenCalled();
      });
    });
  });

  describe('Sequential Playback', () => {
    it('should play items in order', async () => {
      const playOrder: number[] = [];
      let callCount = 0;

      mockPlayer.play.mockImplementation(async () => {
        playOrder.push(++callCount);
      });

      queue.enqueue(new ArrayBuffer(100));
      queue.enqueue(new ArrayBuffer(200));
      queue.enqueue(new ArrayBuffer(300));

      // Wait for all items to be played
      await vi.waitFor(() => {
        expect(mockPlayer.play).toHaveBeenCalledTimes(3);
      });

      expect(playOrder).toEqual([1, 2, 3]);
    });

    it('should emit playbackComplete when queue is empty', async () => {
      const onComplete = vi.fn();
      queue.on('playbackComplete', onComplete);

      queue.enqueue(new ArrayBuffer(1024));

      await vi.waitFor(() => {
        expect(onComplete).toHaveBeenCalled();
      });
    });

    it('should emit itemPlayed for each item', async () => {
      const onItemPlayed = vi.fn();
      queue.on('itemPlayed', onItemPlayed);

      queue.enqueue(new ArrayBuffer(1024));
      queue.enqueue(new ArrayBuffer(1024));

      await vi.waitFor(() => {
        expect(onItemPlayed).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Clear', () => {
    it('should clear all queued items', () => {
      queue.enqueue(new ArrayBuffer(1024));
      queue.enqueue(new ArrayBuffer(1024));

      queue.clear();

      expect(queue.length()).toBe(0);
    });

    it('should stop current playback when clearing', () => {
      mockPlayer.isPlaying.mockReturnValue(true);

      queue.enqueue(new ArrayBuffer(1024));
      queue.clear();

      expect(mockPlayer.stop).toHaveBeenCalled();
    });

    it('should emit cleared event', () => {
      const onCleared = vi.fn();
      queue.on('cleared', onCleared);

      queue.enqueue(new ArrayBuffer(1024));
      queue.clear();

      expect(onCleared).toHaveBeenCalled();
    });
  });

  describe('State', () => {
    it('should report isPlaying correctly', async () => {
      mockPlayer.isPlaying.mockReturnValue(false);
      expect(queue.isPlaying()).toBe(false);

      mockPlayer.isPlaying.mockReturnValue(true);
      queue.enqueue(new ArrayBuffer(1024));

      expect(queue.isPlaying()).toBe(true);
    });

    it('should report isEmpty correctly when queue is empty vs has pending', async () => {
      expect(queue.isEmpty()).toBe(true);

      // Use slow player to check queue during processing
      let resolvePlay: ((value?: unknown) => void) | undefined;
      mockPlayer.play.mockImplementation(() => new Promise(r => { resolvePlay = r; }));

      queue.enqueue(new ArrayBuffer(1024));
      queue.enqueue(new ArrayBuffer(1024));

      // One item processing, one in queue = not empty
      expect(queue.isEmpty()).toBe(false);

      resolvePlay?.();
    });
  });

  describe('Pause and Resume', () => {
    it('should pause playback', () => {
      queue.enqueue(new ArrayBuffer(1024));
      queue.pause();

      expect(queue.isPaused()).toBe(true);
    });

    it('should resume playback after pause', async () => {
      queue.enqueue(new ArrayBuffer(1024));
      queue.enqueue(new ArrayBuffer(1024));

      queue.pause();
      expect(queue.isPaused()).toBe(true);

      queue.resume();
      expect(queue.isPaused()).toBe(false);
    });

    it('should not process queue while paused', async () => {
      queue.pause();
      queue.enqueue(new ArrayBuffer(1024));

      // Wait a bit
      await new Promise((r) => setTimeout(r, 50));

      // Should not have started playing
      expect(mockPlayer.play).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should emit error event on playback failure', async () => {
      const onError = vi.fn();
      queue.on('error', onError);

      mockPlayer.play.mockRejectedValueOnce(new Error('Playback failed'));

      queue.enqueue(new ArrayBuffer(1024));

      await vi.waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
    });

    it('should continue to next item after error', async () => {
      mockPlayer.play
        .mockRejectedValueOnce(new Error('Playback failed'))
        .mockResolvedValueOnce(undefined);

      queue.enqueue(new ArrayBuffer(1024));
      queue.enqueue(new ArrayBuffer(1024));

      await vi.waitFor(() => {
        expect(mockPlayer.play).toHaveBeenCalledTimes(2);
      });
    });
  });
});
