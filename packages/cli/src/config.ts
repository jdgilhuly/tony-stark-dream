import Conf from 'conf';

interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
}

interface ConfigSchema {
  serverUrl: string;
  tokens: AuthTokens | null;
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
      return tokens; // Return anyway, let the API handle refresh
    }

    return tokens;
  }

  setTokens(tokens: AuthTokens): void {
    this.config.set('tokens', tokens);
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
