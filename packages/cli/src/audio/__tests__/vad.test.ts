/**
 * Voice Activity Detection (VAD) Tests
 * Following TDD: Red → Green → Refactor
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VoiceActivityDetector, VADConfig, VADEvent } from '../vad.js';

describe('VoiceActivityDetector', () => {
  let vad: VoiceActivityDetector;
  const defaultConfig: VADConfig = {
    energyThreshold: 0.01,
    silenceDurationMs: 500,
    speechMinDurationMs: 100,
    sampleRate: 16000,
  };

  beforeEach(() => {
    vi.useFakeTimers();
    vad = new VoiceActivityDetector(defaultConfig);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Silence Detection', () => {
    it('should detect silence for low energy audio', () => {
      const onSilence = vi.fn();
      vad.on('silence', onSilence);

      // Create a buffer with very low values (near silence)
      const silentBuffer = createAudioBuffer(1024, 0.001);
      vad.processAudio(silentBuffer);

      expect(vad.isSpeaking()).toBe(false);
    });

    it('should detect speech for high energy audio', () => {
      const onSpeechStart = vi.fn();
      vad.on('speechStart', onSpeechStart);

      // Create a buffer with higher values (speech-like)
      const speechBuffer = createAudioBuffer(1024, 0.5);
      vad.processAudio(speechBuffer);

      // Advance time past minimum speech duration and process again
      vi.advanceTimersByTime(150);
      vad.processAudio(speechBuffer);

      expect(vad.isSpeaking()).toBe(true);
      expect(onSpeechStart).toHaveBeenCalled();
    });
  });

  describe('Speech Start Detection', () => {
    it('should emit speechStart when speech begins', () => {
      const onSpeechStart = vi.fn();
      vad.on('speechStart', onSpeechStart);

      // Start with silence
      const silentBuffer = createAudioBuffer(1024, 0.001);
      vad.processAudio(silentBuffer);

      // Then speech
      const speechBuffer = createAudioBuffer(1024, 0.5);
      vad.processAudio(speechBuffer);
      vi.advanceTimersByTime(150);
      vad.processAudio(speechBuffer); // Process again to trigger event

      expect(onSpeechStart).toHaveBeenCalledTimes(1);
    });

    it('should not emit speechStart for brief noise', () => {
      const onSpeechStart = vi.fn();
      vad.on('speechStart', onSpeechStart);

      // Brief high energy followed by silence (less than speechMinDurationMs)
      const speechBuffer = createAudioBuffer(1024, 0.5);
      vad.processAudio(speechBuffer);
      vi.advanceTimersByTime(50); // Less than 100ms minimum

      const silentBuffer = createAudioBuffer(1024, 0.001);
      vad.processAudio(silentBuffer);

      expect(onSpeechStart).not.toHaveBeenCalled();
    });
  });

  describe('Speech End Detection', () => {
    it('should emit speechEnd after silence duration', () => {
      const onSpeechEnd = vi.fn();
      vad.on('speechEnd', onSpeechEnd);

      // Speech - establish first
      const speechBuffer = createAudioBuffer(1024, 0.5);
      vad.processAudio(speechBuffer);
      vi.advanceTimersByTime(200);
      vad.processAudio(speechBuffer); // This triggers speechStart

      // Silence for duration
      const silentBuffer = createAudioBuffer(1024, 0.001);
      vad.processAudio(silentBuffer);
      vi.advanceTimersByTime(600);
      vad.processAudio(silentBuffer); // Process again to trigger speechEnd

      expect(onSpeechEnd).toHaveBeenCalled();
    });

    it('should not emit speechEnd for brief pauses', () => {
      const onSpeechEnd = vi.fn();
      vad.on('speechEnd', onSpeechEnd);

      // Speech - establish first
      const speechBuffer = createAudioBuffer(1024, 0.5);
      vad.processAudio(speechBuffer);
      vi.advanceTimersByTime(200);
      vad.processAudio(speechBuffer);

      // Brief silence
      const silentBuffer = createAudioBuffer(1024, 0.001);
      vad.processAudio(silentBuffer);
      vi.advanceTimersByTime(200); // Less than 500ms

      // Resume speech
      vad.processAudio(speechBuffer);

      expect(onSpeechEnd).not.toHaveBeenCalled();
    });
  });

  describe('Energy Level Calculation', () => {
    it('should calculate RMS energy correctly', () => {
      // Create a buffer with known values
      const buffer = new ArrayBuffer(8);
      const view = new Int16Array(buffer);
      view[0] = 1000;
      view[1] = -1000;
      view[2] = 1000;
      view[3] = -1000;

      const energy = vad.calculateEnergy(buffer);

      // RMS of alternating 1000/-1000 values
      // Normalized: 1000/32768 ≈ 0.0305
      expect(energy).toBeGreaterThan(0.02);
      expect(energy).toBeLessThan(0.04);
    });

    it('should return 0 for silent buffer', () => {
      const buffer = new ArrayBuffer(8);
      const view = new Int16Array(buffer);
      view.fill(0);

      const energy = vad.calculateEnergy(buffer);

      expect(energy).toBe(0);
    });
  });

  describe('Audio Level', () => {
    it('should return current audio level', () => {
      const speechBuffer = createAudioBuffer(1024, 0.5);
      vad.processAudio(speechBuffer);

      const level = vad.getAudioLevel();

      expect(level).toBeGreaterThan(0);
      expect(level).toBeLessThanOrEqual(1);
    });

    it('should emit level event with audio level', () => {
      const onLevel = vi.fn();
      vad.on('level', onLevel);

      const speechBuffer = createAudioBuffer(1024, 0.5);
      vad.processAudio(speechBuffer);

      expect(onLevel).toHaveBeenCalledWith(expect.any(Number));
    });
  });

  describe('Configuration', () => {
    it('should use default config values', () => {
      const vadWithDefaults = new VoiceActivityDetector();

      expect(vadWithDefaults.getConfig().energyThreshold).toBeDefined();
      expect(vadWithDefaults.getConfig().silenceDurationMs).toBeDefined();
    });

    it('should allow updating threshold', () => {
      vad.setEnergyThreshold(0.05);

      expect(vad.getConfig().energyThreshold).toBe(0.05);
    });

    it('should allow updating silence duration', () => {
      vad.setSilenceDuration(1000);

      expect(vad.getConfig().silenceDurationMs).toBe(1000);
    });
  });

  describe('Reset', () => {
    it('should reset state when called', () => {
      // Start speaking
      const speechBuffer = createAudioBuffer(1024, 0.5);
      vad.processAudio(speechBuffer);
      vi.advanceTimersByTime(200);
      vad.processAudio(speechBuffer); // Trigger speechStart

      expect(vad.isSpeaking()).toBe(true);

      // Reset
      vad.reset();

      expect(vad.isSpeaking()).toBe(false);
      expect(vad.getAudioLevel()).toBe(0);
    });
  });
});

// Helper function to create audio buffer with specific amplitude
function createAudioBuffer(samples: number, amplitude: number): ArrayBuffer {
  const buffer = new ArrayBuffer(samples * 2); // 16-bit samples
  const view = new Int16Array(buffer);

  for (let i = 0; i < samples; i++) {
    // Create a simple waveform with given amplitude
    view[i] = Math.round(amplitude * 32767 * Math.sin(i * 0.1));
  }

  return buffer;
}
