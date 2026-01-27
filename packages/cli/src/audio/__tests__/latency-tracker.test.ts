/**
 * Latency Tracker Tests
 * Following TDD: Red → Green → Refactor
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { LatencyTracker, LatencyMetrics } from '../latency-tracker.js';

describe('LatencyTracker', () => {
  let tracker: LatencyTracker;

  beforeEach(() => {
    vi.useFakeTimers();
    tracker = new LatencyTracker();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Phase Tracking', () => {
    it('should track speech-to-text latency', () => {
      tracker.startPhase('stt');
      vi.advanceTimersByTime(150);
      tracker.endPhase('stt');

      const metrics = tracker.getMetrics();
      expect(metrics.stt).toBe(150);
    });

    it('should track conversation latency', () => {
      tracker.startPhase('conversation');
      vi.advanceTimersByTime(200);
      tracker.endPhase('conversation');

      const metrics = tracker.getMetrics();
      expect(metrics.conversation).toBe(200);
    });

    it('should track text-to-speech latency', () => {
      tracker.startPhase('tts');
      vi.advanceTimersByTime(100);
      tracker.endPhase('tts');

      const metrics = tracker.getMetrics();
      expect(metrics.tts).toBe(100);
    });
  });

  describe('Full Cycle', () => {
    it('should track end-to-end latency', () => {
      tracker.startCycle();
      vi.advanceTimersByTime(500);
      tracker.endCycle();

      const metrics = tracker.getMetrics();
      expect(metrics.total).toBe(500);
    });

    it('should calculate time to first byte', () => {
      tracker.startCycle();
      vi.advanceTimersByTime(300);
      tracker.markFirstByte();

      const metrics = tracker.getMetrics();
      expect(metrics.timeToFirstByte).toBe(300);
    });
  });

  describe('Statistics', () => {
    it('should calculate average latency', () => {
      // First cycle
      tracker.startCycle();
      vi.advanceTimersByTime(400);
      tracker.endCycle();

      // Second cycle
      tracker.startCycle();
      vi.advanceTimersByTime(600);
      tracker.endCycle();

      const stats = tracker.getStatistics();
      expect(stats.avgTotal).toBe(500);
    });

    it('should track min and max latency', () => {
      tracker.startCycle();
      vi.advanceTimersByTime(300);
      tracker.endCycle();

      tracker.startCycle();
      vi.advanceTimersByTime(700);
      tracker.endCycle();

      tracker.startCycle();
      vi.advanceTimersByTime(500);
      tracker.endCycle();

      const stats = tracker.getStatistics();
      expect(stats.minTotal).toBe(300);
      expect(stats.maxTotal).toBe(700);
    });

    it('should count total cycles', () => {
      tracker.startCycle();
      tracker.endCycle();
      tracker.startCycle();
      tracker.endCycle();
      tracker.startCycle();
      tracker.endCycle();

      const stats = tracker.getStatistics();
      expect(stats.cycleCount).toBe(3);
    });
  });

  describe('Reset', () => {
    it('should reset all metrics', () => {
      tracker.startCycle();
      vi.advanceTimersByTime(500);
      tracker.endCycle();

      tracker.reset();

      const stats = tracker.getStatistics();
      expect(stats.cycleCount).toBe(0);
      expect(stats.avgTotal).toBe(0);
    });
  });

  describe('Target Threshold', () => {
    it('should report if under target latency', () => {
      tracker.setTargetLatency(500);

      tracker.startCycle();
      vi.advanceTimersByTime(400);
      tracker.endCycle();

      expect(tracker.isUnderTarget()).toBe(true);
    });

    it('should report if over target latency', () => {
      tracker.setTargetLatency(500);

      tracker.startCycle();
      vi.advanceTimersByTime(600);
      tracker.endCycle();

      expect(tracker.isUnderTarget()).toBe(false);
    });

    it('should emit warning when over target', () => {
      const onWarning = vi.fn();
      tracker.on('latencyWarning', onWarning);
      tracker.setTargetLatency(500);

      tracker.startCycle();
      vi.advanceTimersByTime(600);
      tracker.endCycle();

      expect(onWarning).toHaveBeenCalled();
    });
  });
});
