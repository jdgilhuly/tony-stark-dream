/**
 * ElevenLabs TTS Client Tests
 * Following TDD: Red → Green → Refactor
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ElevenLabsClient, ElevenLabsConfig } from '../elevenlabs.js';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('ElevenLabsClient', () => {
  let client: ElevenLabsClient;
  const testConfig: ElevenLabsConfig = {
    apiKey: 'test-api-key',
    voiceId: 'test-voice-id',
    modelId: 'eleven_monolingual_v1',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    client = new ElevenLabsClient(testConfig);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Configuration', () => {
    it('should use provided config values', () => {
      const config = client.getConfig();

      expect(config.apiKey).toBe('test-api-key');
      expect(config.voiceId).toBe('test-voice-id');
    });

    it('should use default values for optional config', () => {
      const minimalClient = new ElevenLabsClient({
        apiKey: 'test-key',
        voiceId: 'test-voice',
      });

      const config = minimalClient.getConfig();

      expect(config.modelId).toBe('eleven_monolingual_v1');
      expect(config.stability).toBeDefined();
      expect(config.similarityBoost).toBeDefined();
    });

    it('should allow updating voice ID', () => {
      client.setVoiceId('new-voice-id');

      expect(client.getConfig().voiceId).toBe('new-voice-id');
    });
  });

  describe('Text-to-Speech Synthesis', () => {
    it('should call the ElevenLabs API with correct parameters', async () => {
      const mockAudioData = new ArrayBuffer(1024);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(mockAudioData),
      });

      await client.synthesize('Hello world');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('https://api.elevenlabs.io/v1/text-to-speech/test-voice-id'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'xi-api-key': 'test-api-key',
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    it('should include text and voice settings in request body', async () => {
      const mockAudioData = new ArrayBuffer(1024);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(mockAudioData),
      });

      await client.synthesize('Hello world');

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.text).toBe('Hello world');
      expect(body.model_id).toBe('eleven_monolingual_v1');
      expect(body.voice_settings).toBeDefined();
    });

    it('should return audio data on success', async () => {
      const mockAudioData = new ArrayBuffer(1024);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(mockAudioData),
      });

      const result = await client.synthesize('Hello world');

      expect(result).toBe(mockAudioData);
    });

    it('should throw error on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        text: () => Promise.resolve('Invalid API key'),
      });

      await expect(client.synthesize('Hello world')).rejects.toThrow();
    });
  });

  describe('Streaming Synthesis', () => {
    it('should call streaming endpoint when streaming enabled', async () => {
      const mockStream = {
        getReader: () => ({
          read: vi.fn()
            .mockResolvedValueOnce({ done: false, value: new Uint8Array([1, 2, 3]) })
            .mockResolvedValueOnce({ done: true }),
        }),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockStream,
      });

      const chunks: ArrayBuffer[] = [];
      await client.synthesizeStream('Hello world', (chunk) => {
        chunks.push(chunk);
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/stream'),
        expect.any(Object)
      );
    });

    it('should call onChunk for each received chunk', async () => {
      const mockStream = {
        getReader: () => ({
          read: vi.fn()
            .mockResolvedValueOnce({ done: false, value: new Uint8Array([1, 2, 3]) })
            .mockResolvedValueOnce({ done: false, value: new Uint8Array([4, 5, 6]) })
            .mockResolvedValueOnce({ done: true }),
        }),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        body: mockStream,
      });

      const onChunk = vi.fn();
      await client.synthesizeStream('Hello world', onChunk);

      expect(onChunk).toHaveBeenCalledTimes(2);
    });
  });

  describe('Output Format', () => {
    it('should request mp3 format by default', async () => {
      const mockAudioData = new ArrayBuffer(1024);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(mockAudioData),
      });

      await client.synthesize('Hello');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('output_format=mp3_44100_128'),
        expect.any(Object)
      );
    });

    it('should allow setting custom output format', async () => {
      const customClient = new ElevenLabsClient({
        ...testConfig,
        outputFormat: 'pcm_16000',
      });

      const mockAudioData = new ArrayBuffer(1024);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(mockAudioData),
      });

      await customClient.synthesize('Hello');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('output_format=pcm_16000'),
        expect.any(Object)
      );
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(client.synthesize('Hello')).rejects.toThrow('Network error');
    });

    it('should handle rate limiting', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        text: () => Promise.resolve('Rate limit exceeded'),
      });

      await expect(client.synthesize('Hello')).rejects.toThrow();
    });
  });
});
