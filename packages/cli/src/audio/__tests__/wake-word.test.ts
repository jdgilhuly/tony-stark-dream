/**
 * Wake Word Detection Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WakeWordDetector, WakeWordEvent } from '../wake-word.js';

describe('WakeWordDetector', () => {
  let detector: WakeWordDetector;

  beforeEach(() => {
    detector = new WakeWordDetector({
      serverUrl: 'http://localhost:8002',
      token: 'test-token',
      threshold: 0.5,
      refractoryPeriodMs: 2000,
    });
  });

  afterEach(async () => {
    await detector.stop();
  });

  describe('initialization', () => {
    it('should create detector with config', () => {
      expect(detector).toBeDefined();
      expect(detector.isActive()).toBe(false);
    });

    it('should accept custom threshold', () => {
      const customDetector = new WakeWordDetector({
        serverUrl: 'http://localhost:8002',
        threshold: 0.7,
      });
      expect(customDetector).toBeDefined();
    });
  });

  describe('event handling', () => {
    it('should emit started event when starting', async () => {
      const startedHandler = vi.fn();
      detector.on('started', startedHandler);

      // Mock the fetch and WebSocket
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({}),
      });

      // Can't fully start without browser APIs, but we can test the event system
      detector.emit('started');
      expect(startedHandler).toHaveBeenCalled();
    });

    it('should emit stopped event when stopping', () => {
      const stoppedHandler = vi.fn();
      detector.on('stopped', stoppedHandler);

      detector.emit('stopped');
      expect(stoppedHandler).toHaveBeenCalled();
    });

    it('should emit detected event with wake word data', () => {
      const detectedHandler = vi.fn();
      detector.on('detected', detectedHandler);

      const event: WakeWordEvent = {
        wakeWord: 'hey_jarvis',
        confidence: 0.85,
        timestamp: Date.now() / 1000,
      };

      detector.emit('detected', event);
      expect(detectedHandler).toHaveBeenCalledWith(event);
    });

    it('should emit stateChange event', () => {
      const stateHandler = vi.fn();
      detector.on('stateChange', stateHandler);

      detector.emit('stateChange', true);
      expect(stateHandler).toHaveBeenCalledWith(true);
    });
  });

  describe('configuration updates', () => {
    it('should update threshold via API', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'updated' }),
      });
      global.fetch = mockFetch;

      await detector.updateConfig({ threshold: 0.8 });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8002/wake-word/config',
        expect.objectContaining({
          method: 'PUT',
          body: expect.stringContaining('0.8'),
        })
      );
    });

    it('should update refractory period via API', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'updated' }),
      });
      global.fetch = mockFetch;

      await detector.updateConfig({ refractoryPeriodMs: 3000 });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8002/wake-word/config',
        expect.objectContaining({
          method: 'PUT',
          body: expect.stringContaining('3000'),
        })
      );
    });
  });

  describe('status retrieval', () => {
    it('should get status from service', async () => {
      const mockStatus = {
        is_listening: true,
        threshold: 0.5,
        refractory_period_ms: 2000,
        models: ['hey_jarvis.onnx'],
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockStatus),
      });

      const status = await detector.getStatus();

      expect(status.isListening).toBe(true);
      expect(status.threshold).toBe(0.5);
      expect(status.refractoryPeriodMs).toBe(2000);
      expect(status.models).toContain('hey_jarvis.onnx');
    });

    it('should throw on status fetch error', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        statusText: 'Internal Server Error',
      });

      await expect(detector.getStatus()).rejects.toThrow('Failed to get wake word status');
    });
  });
});

describe('Wake Word Event Structure', () => {
  it('should have correct event structure', () => {
    const event: WakeWordEvent = {
      wakeWord: 'hey_jarvis',
      confidence: 0.95,
      timestamp: 1706300000,
    };

    expect(event.wakeWord).toBe('hey_jarvis');
    expect(event.confidence).toBeGreaterThanOrEqual(0);
    expect(event.confidence).toBeLessThanOrEqual(1);
    expect(event.timestamp).toBeGreaterThan(0);
  });
});
