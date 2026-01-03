import type {
  ApiResponse,
  AuthTokens,
  ConnectionConfig,
  ConversationRequest,
  ConversationResponse,
  User,
  WebSocketMessage,
  WebSocketStatus,
} from '../types/index.js';

type WebSocketEventHandler<T = unknown> = (message: WebSocketMessage<T>) => void;

export class JarvisApiClient {
  private config: ConnectionConfig;
  private tokens: AuthTokens | null = null;
  private ws: WebSocket | null = null;
  private wsStatus: WebSocketStatus = 'disconnected';
  private wsReconnectAttempts = 0;
  private eventHandlers: Map<string, Set<WebSocketEventHandler>> = new Map();
  private pendingRequests: Map<string, { resolve: (value: unknown) => void; reject: (error: Error) => void }> = new Map();

  constructor(config: Partial<ConnectionConfig> = {}) {
    this.config = {
      baseUrl: config.baseUrl ?? 'http://localhost:3000',
      wsUrl: config.wsUrl ?? 'ws://localhost:3000',
      timeout: config.timeout ?? 30000,
      retryAttempts: config.retryAttempts ?? 3,
      retryDelay: config.retryDelay ?? 1000,
    };
  }

  // Authentication
  async login(email: string, password: string): Promise<ApiResponse<{ user: User; tokens: AuthTokens }>> {
    const response = await this.post<{ user: User; tokens: AuthTokens }>('/auth/login', { email, password });
    if (response.success && response.data) {
      this.tokens = response.data.tokens;
    }
    return response;
  }

  async refreshToken(): Promise<ApiResponse<AuthTokens>> {
    if (!this.tokens?.refreshToken) {
      return { success: false, error: { code: 'NO_REFRESH_TOKEN', message: 'No refresh token available' } };
    }
    const response = await this.post<AuthTokens>('/auth/refresh', { refreshToken: this.tokens.refreshToken });
    if (response.success && response.data) {
      this.tokens = response.data;
    }
    return response;
  }

  setTokens(tokens: AuthTokens): void {
    this.tokens = tokens;
  }

  clearTokens(): void {
    this.tokens = null;
  }

  // Conversation API
  async sendMessage(request: ConversationRequest): Promise<ApiResponse<ConversationResponse>> {
    return this.post<ConversationResponse>('/conversation/message', request);
  }

  async getConversationHistory(conversationId: string): Promise<ApiResponse<ConversationResponse[]>> {
    return this.get<ConversationResponse[]>(`/conversation/${conversationId}/history`);
  }

  // User API
  async getProfile(): Promise<ApiResponse<User>> {
    return this.get<User>('/user/profile');
  }

  async updateProfile(updates: Partial<User>): Promise<ApiResponse<User>> {
    return this.put<User>('/user/profile', updates);
  }

  // HTTP Methods
  private async request<T>(method: string, path: string, body?: unknown): Promise<ApiResponse<T>> {
    const url = `${this.config.baseUrl}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.tokens?.accessToken) {
      headers['Authorization'] = `Bearer ${this.tokens.accessToken}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      const data = await response.json() as ApiResponse<T>;

      if (!response.ok) {
        return {
          success: false,
          error: data.error ?? { code: 'HTTP_ERROR', message: `HTTP ${response.status}` },
        };
      }

      return data;
    } catch (error) {
      clearTimeout(timeoutId);
      const message = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        error: { code: 'NETWORK_ERROR', message },
      };
    }
  }

  private async get<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>('GET', path);
  }

  private async post<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>('POST', path, body);
  }

  private async put<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', path, body);
  }

  // WebSocket Methods
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.wsStatus = 'connecting';
    const wsUrl = this.tokens?.accessToken
      ? `${this.config.wsUrl}?token=${this.tokens.accessToken}`
      : this.config.wsUrl;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.wsStatus = 'connected';
      this.wsReconnectAttempts = 0;
      this.emit('connection', { status: 'connected' });
    };

    this.ws.onclose = () => {
      this.wsStatus = 'disconnected';
      this.emit('connection', { status: 'disconnected' });
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      this.wsStatus = 'error';
      this.emit('error', { error });
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data as string) as WebSocketMessage;

        // Handle response to pending request
        if (message.correlationId && this.pendingRequests.has(message.correlationId)) {
          const { resolve } = this.pendingRequests.get(message.correlationId)!;
          this.pendingRequests.delete(message.correlationId);
          resolve(message.payload);
          return;
        }

        // Emit to event handlers
        this.emit(message.type, message.payload);
      } catch {
        console.error('Failed to parse WebSocket message');
      }
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.wsStatus = 'disconnected';
  }

  private attemptReconnect(): void {
    if (this.wsReconnectAttempts >= this.config.retryAttempts) {
      this.emit('reconnect_failed', {});
      return;
    }

    this.wsStatus = 'reconnecting';
    this.wsReconnectAttempts++;

    setTimeout(() => {
      this.connect();
    }, this.config.retryDelay * this.wsReconnectAttempts);
  }

  send<T>(type: string, payload: T): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }

    const message: WebSocketMessage<T> = {
      type,
      payload,
      timestamp: new Date(),
    };

    this.ws.send(JSON.stringify(message));
  }

  async sendAndWait<T, R>(type: string, payload: T, timeout = 30000): Promise<R> {
    return new Promise((resolve, reject) => {
      const correlationId = crypto.randomUUID();

      const timeoutId = setTimeout(() => {
        this.pendingRequests.delete(correlationId);
        reject(new Error('Request timeout'));
      }, timeout);

      this.pendingRequests.set(correlationId, {
        resolve: (value) => {
          clearTimeout(timeoutId);
          resolve(value as R);
        },
        reject: (error) => {
          clearTimeout(timeoutId);
          reject(error);
        },
      });

      const message: WebSocketMessage<T> = {
        type,
        payload,
        timestamp: new Date(),
        correlationId,
      };

      this.ws?.send(JSON.stringify(message));
    });
  }

  on<T>(event: string, handler: WebSocketEventHandler<T>): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler as WebSocketEventHandler);

    return () => {
      this.eventHandlers.get(event)?.delete(handler as WebSocketEventHandler);
    };
  }

  private emit<T>(event: string, payload: T): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      const message: WebSocketMessage<T> = {
        type: event,
        payload,
        timestamp: new Date(),
      };
      handlers.forEach(handler => handler(message));
    }
  }

  getStatus(): WebSocketStatus {
    return this.wsStatus;
  }
}

export const createApiClient = (config?: Partial<ConnectionConfig>): JarvisApiClient => {
  return new JarvisApiClient(config);
};
