import { describe, it, expect, beforeEach, vi } from 'vitest';
import { JarvisApiClient, createApiClient } from '../api/client.js';

describe('JarvisApiClient', () => {
  let client: JarvisApiClient;

  beforeEach(() => {
    client = createApiClient({ baseUrl: 'http://localhost:3000' });
    vi.resetAllMocks();
  });

  describe('constructor', () => {
    it('should create client with default config', () => {
      const defaultClient = createApiClient();
      expect(defaultClient).toBeInstanceOf(JarvisApiClient);
    });

    it('should create client with custom config', () => {
      const customClient = createApiClient({
        baseUrl: 'http://custom:4000',
        timeout: 5000,
      });
      expect(customClient).toBeInstanceOf(JarvisApiClient);
    });
  });

  describe('authentication', () => {
    it('should set tokens', () => {
      const tokens = {
        accessToken: 'access-123',
        refreshToken: 'refresh-456',
        expiresAt: new Date(),
      };
      client.setTokens(tokens);
      // Token should be set internally
      expect(() => client.clearTokens()).not.toThrow();
    });

    it('should clear tokens', () => {
      client.setTokens({
        accessToken: 'test',
        refreshToken: 'test',
        expiresAt: new Date(),
      });
      client.clearTokens();
      // Should not throw
      expect(() => client.getStatus()).not.toThrow();
    });
  });

  describe('websocket', () => {
    it('should return disconnected status initially', () => {
      expect(client.getStatus()).toBe('disconnected');
    });

    it('should allow event subscription', () => {
      const handler = vi.fn();
      const unsubscribe = client.on('test', handler);
      expect(typeof unsubscribe).toBe('function');
      unsubscribe();
    });
  });
});
