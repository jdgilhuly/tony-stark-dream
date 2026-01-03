/**
 * Offline Queue - Handles optimistic updates and sync when back online
 */

import type { StorageAdapter } from '../adapters/interfaces.js';

export interface QueuedAction<T = unknown> {
  id: string;
  type: string;
  payload: T;
  timestamp: number;
  retryCount: number;
  maxRetries: number;
  status: 'pending' | 'processing' | 'failed' | 'completed';
  error?: string;
}

export interface OfflineQueueOptions {
  maxQueueSize: number;
  maxRetries: number;
  retryDelay: number;
  storageKey: string;
}

export type ActionHandler<T = unknown, R = unknown> = (action: QueuedAction<T>) => Promise<R>;

export class OfflineQueue {
  private storage: StorageAdapter;
  private options: OfflineQueueOptions;
  private queue: QueuedAction[] = [];
  private handlers: Map<string, ActionHandler> = new Map();
  private processing = false;
  private online = true;
  private syncTimer?: NodeJS.Timeout;

  constructor(storage: StorageAdapter, options: Partial<OfflineQueueOptions> = {}) {
    this.storage = storage;
    this.options = {
      maxQueueSize: options.maxQueueSize ?? 100,
      maxRetries: options.maxRetries ?? 3,
      retryDelay: options.retryDelay ?? 5000,
      storageKey: options.storageKey ?? 'offline-queue',
    };
  }

  async initialize(): Promise<void> {
    await this.loadFromStorage();
  }

  registerHandler<T, R>(type: string, handler: ActionHandler<T, R>): void {
    this.handlers.set(type, handler as ActionHandler);
  }

  async enqueue<T>(type: string, payload: T): Promise<string> {
    if (this.queue.length >= this.options.maxQueueSize) {
      throw new Error('Queue is full');
    }

    const action: QueuedAction<T> = {
      id: this.generateId(),
      type,
      payload,
      timestamp: Date.now(),
      retryCount: 0,
      maxRetries: this.options.maxRetries,
      status: 'pending',
    };

    this.queue.push(action);
    await this.saveToStorage();

    // Try to process immediately if online
    if (this.online && !this.processing) {
      this.processQueue();
    }

    return action.id;
  }

  async processQueue(): Promise<void> {
    if (this.processing || !this.online) {
      return;
    }

    this.processing = true;

    try {
      const pendingActions = this.queue.filter(a => a.status === 'pending');

      for (const action of pendingActions) {
        const handler = this.handlers.get(action.type);
        if (!handler) {
          action.status = 'failed';
          action.error = `No handler for action type: ${action.type}`;
          continue;
        }

        action.status = 'processing';
        await this.saveToStorage();

        try {
          await handler(action);
          action.status = 'completed';
        } catch (error) {
          action.retryCount++;
          if (action.retryCount >= action.maxRetries) {
            action.status = 'failed';
            action.error = error instanceof Error ? error.message : 'Unknown error';
          } else {
            action.status = 'pending';
          }
        }

        await this.saveToStorage();
      }

      // Remove completed actions
      this.queue = this.queue.filter(a => a.status !== 'completed');
      await this.saveToStorage();
    } finally {
      this.processing = false;
    }

    // Schedule retry for failed/pending actions
    const hasRetryable = this.queue.some(a => a.status === 'pending');
    if (hasRetryable) {
      this.scheduleRetry();
    }
  }

  setOnline(online: boolean): void {
    const wasOffline = !this.online;
    this.online = online;

    if (online && wasOffline) {
      // Coming back online, process queue
      this.processQueue();
    }
  }

  getQueue(): QueuedAction[] {
    return [...this.queue];
  }

  getPendingCount(): number {
    return this.queue.filter(a => a.status === 'pending').length;
  }

  getFailedCount(): number {
    return this.queue.filter(a => a.status === 'failed').length;
  }

  async clearFailed(): Promise<void> {
    this.queue = this.queue.filter(a => a.status !== 'failed');
    await this.saveToStorage();
  }

  async clearAll(): Promise<void> {
    this.queue = [];
    await this.saveToStorage();
  }

  async retryFailed(): Promise<void> {
    for (const action of this.queue) {
      if (action.status === 'failed') {
        action.status = 'pending';
        action.retryCount = 0;
        action.error = undefined;
      }
    }
    await this.saveToStorage();
    this.processQueue();
  }

  private async loadFromStorage(): Promise<void> {
    try {
      const stored = await this.storage.get<QueuedAction[]>(this.options.storageKey);
      if (stored) {
        this.queue = stored;
      }
    } catch {
      // Start with empty queue
      this.queue = [];
    }
  }

  private async saveToStorage(): Promise<void> {
    try {
      await this.storage.set(this.options.storageKey, this.queue);
    } catch {
      // Storage error, queue only in memory
    }
  }

  private scheduleRetry(): void {
    if (this.syncTimer) {
      clearTimeout(this.syncTimer);
    }

    this.syncTimer = setTimeout(() => {
      if (this.online) {
        this.processQueue();
      }
    }, this.options.retryDelay);
  }

  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  dispose(): void {
    if (this.syncTimer) {
      clearTimeout(this.syncTimer);
    }
  }
}

/**
 * Create an optimistic update wrapper
 */
export function createOptimisticUpdate<T, R>(
  queue: OfflineQueue,
  actionType: string,
  optimisticFn: (payload: T) => void,
  rollbackFn: (payload: T, error: Error) => void
): (payload: T) => Promise<string> {
  return async (payload: T) => {
    // Apply optimistic update immediately
    optimisticFn(payload);

    try {
      const actionId = await queue.enqueue(actionType, payload);
      return actionId;
    } catch (error) {
      // Rollback on queue error
      rollbackFn(payload, error instanceof Error ? error : new Error('Unknown error'));
      throw error;
    }
  };
}
