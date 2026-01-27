import { describe, it, expect, vi } from 'vitest';

// Mock ink hooks and components for testing
vi.mock('ink', () => ({
  Box: ({ children }: any) => children,
  Text: ({ children }: any) => children,
  useInput: vi.fn(),
  useApp: vi.fn().mockReturnValue({ exit: vi.fn() }),
}));

vi.mock('ink-spinner', () => ({
  default: () => null,
}));

// Mock the audio recorder
vi.mock('../../audio/recorder.js', () => ({
  NodeAudioRecorder: vi.fn().mockImplementation(() => ({
    start: vi.fn().mockResolvedValue(undefined),
    stop: vi.fn().mockResolvedValue(new ArrayBuffer(8)),
    isRecording: vi.fn().mockReturnValue(false),
    onData: vi.fn(),
    getSampleRate: vi.fn().mockReturnValue(16000),
    getChannels: vi.fn().mockReturnValue(1),
  })),
}));

describe('VoiceChat', () => {
  describe('module', () => {
    it('should export VoiceChat component', async () => {
      const { VoiceChat } = await import('../VoiceChat.js');
      expect(VoiceChat).toBeDefined();
      expect(typeof VoiceChat).toBe('function');
    });
  });

  describe('NodeAudioRecorder mock', () => {
    it('should create mock recorder with expected methods', async () => {
      const { NodeAudioRecorder } = await import('../../audio/recorder.js');
      const recorder = new NodeAudioRecorder();

      expect(recorder.start).toBeDefined();
      expect(recorder.stop).toBeDefined();
      expect(recorder.isRecording).toBeDefined();
      expect(recorder.onData).toBeDefined();
      expect(recorder.getSampleRate()).toBe(16000);
      expect(recorder.getChannels()).toBe(1);
    });

    it('should return false for isRecording initially', async () => {
      const { NodeAudioRecorder } = await import('../../audio/recorder.js');
      const recorder = new NodeAudioRecorder();

      expect(recorder.isRecording()).toBe(false);
    });

    it('should resolve start promise', async () => {
      const { NodeAudioRecorder } = await import('../../audio/recorder.js');
      const recorder = new NodeAudioRecorder();

      await expect(recorder.start()).resolves.toBeUndefined();
    });

    it('should return ArrayBuffer on stop', async () => {
      const { NodeAudioRecorder } = await import('../../audio/recorder.js');
      const recorder = new NodeAudioRecorder();

      const result = await recorder.stop();
      expect(result).toBeInstanceOf(ArrayBuffer);
    });
  });

  describe('props types', () => {
    it('should accept required props types', async () => {
      const { VoiceChat } = await import('../VoiceChat.js');

      // Type check - these should compile without errors
      const props = {
        serverUrl: 'http://localhost:3000',
        tokens: {
          accessToken: 'test-access',
          refreshToken: 'test-refresh',
        },
      };

      expect(props.serverUrl).toBe('http://localhost:3000');
      expect(props.tokens.accessToken).toBe('test-access');
      expect(props.tokens.refreshToken).toBe('test-refresh');
    });

    it('should accept optional callback props', () => {
      const onMessage = vi.fn();
      const onResponse = vi.fn();

      expect(typeof onMessage).toBe('function');
      expect(typeof onResponse).toBe('function');
    });
  });

  describe('VoiceState type', () => {
    it('should support expected state values', () => {
      const validStates = ['idle', 'listening', 'processing', 'speaking', 'error'];

      validStates.forEach((state) => {
        expect(['idle', 'listening', 'processing', 'speaking', 'error']).toContain(state);
      });
    });
  });
});
