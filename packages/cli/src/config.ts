import Conf from 'conf';
import type { AuthTokens } from '@jarvis/core';

interface StoredAuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
}

interface ConfigSchema {
  serverUrl: string;
  tokens: StoredAuthTokens | null;
  preferences: {
    voiceEnabled: boolean;
    wakeWord: string;
  };
}

export class ConfigManager {
  private config: Conf<ConfigSchema>;

  constructor() {
    this.config = new Conf<ConfigSchema>({
      projectName: 'jarvis-cli',
      defaults: {
        serverUrl: 'http://localhost:3000',
        tokens: null,
        preferences: {
          voiceEnabled: false,
          wakeWord: 'jarvis',
        },
      },
    });
  }

  getTokens(): AuthTokens | null {
    const tokens = this.config.get('tokens');
    if (!tokens) return null;

    // Check if tokens are expired
    const expiresAt = new Date(tokens.expiresAt);
    if (expiresAt <= new Date()) {
      // Token expired, should refresh
      // Return anyway, let the API handle refresh
    }

    return {
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      expiresAt: new Date(tokens.expiresAt),
    };
  }

  setTokens(tokens: AuthTokens): void {
    const storedTokens: StoredAuthTokens = {
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
      expiresAt: tokens.expiresAt instanceof Date ? tokens.expiresAt.toISOString() : tokens.expiresAt,
    };
    this.config.set('tokens', storedTokens);
  }

  clearTokens(): void {
    this.config.delete('tokens');
  }

  get<K extends keyof ConfigSchema>(key: K): ConfigSchema[K] {
    return this.config.get(key);
  }

  set<K extends keyof ConfigSchema>(key: K, value: ConfigSchema[K]): void {
    this.config.set(key, value);
  }

  getAll(): ConfigSchema {
    return this.config.store;
  }
}
