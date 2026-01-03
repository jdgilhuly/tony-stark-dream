/**
 * Sync Manager - Coordinates offline/online synchronization.
 */

import type { StorageAdapter } from '../adapters/interfaces.js';
import { OfflineQueue, type QueuedAction } from './offline-queue.js';

export interface SyncStatus {
  isOnline: boolean;
  isSyncing: boolean;
  lastSyncAt: number | null;
  pendingCount: number;
  failedCount: number;
  syncErrors: string[];
}

export interface SyncableEntity {
  id: string;
  updatedAt: number;
  syncedAt?: number;
  isLocal?: boolean;
}

export interface ConflictResolution<T> {
  strategy: 'local' | 'remote' | 'merge' | 'manual';
  resolver?: (local: T, remote: T) => T;
}

export type SyncEventType =
  | 'online'
  | 'offline'
  | 'sync_started'
  | 'sync_completed'
  | 'sync_failed'
  | 'conflict_detected'
  | 'entity_synced';

export interface SyncEvent {
  type: SyncEventType;
  timestamp: number;
  data?: unknown;
}

type SyncEventHandler = (event: SyncEvent) => void;

export class SyncManager {
  private storage: StorageAdapter;
  private queue: OfflineQueue;
  private eventHandlers: Set<SyncEventHandler> = new Set();
  private status: SyncStatus;
  private conflictStrategies: Map<string, ConflictResolution<unknown>> = new Map();
  private networkCheckInterval?: NodeJS.Timeout;

  constructor(storage: StorageAdapter, queue: OfflineQueue) {
    this.storage = storage;
    this.queue = queue;
    this.status = {
      isOnline: true,
      isSyncing: false,
      lastSyncAt: null,
      pendingCount: 0,
      failedCount: 0,
      syncErrors: [],
    };
  }

  async initialize(): Promise<void> {
    // Load last sync status
    const savedStatus = await this.storage.get<Partial<SyncStatus>>('sync-status');
    if (savedStatus) {
      this.status.lastSyncAt = savedStatus.lastSyncAt ?? null;
    }

    // Start network monitoring
    this.startNetworkMonitoring();

    // Update counts
    this.updateCounts();
  }

  /**
   * Set conflict resolution strategy for an entity type.
   */
  setConflictStrategy<T>(entityType: string, resolution: ConflictResolution<T>): void {
    this.conflictStrategies.set(entityType, resolution as ConflictResolution<unknown>);
  }

  /**
   * Trigger a full sync.
   */
  async sync(): Promise<void> {
    if (this.status.isSyncing || !this.status.isOnline) {
      return;
    }

    this.status.isSyncing = true;
    this.status.syncErrors = [];
    this.emit({ type: 'sync_started', timestamp: Date.now() });

    try {
      // Process the offline queue
      await this.queue.processQueue();

      // Update status
      this.status.lastSyncAt = Date.now();
      await this.saveStatus();

      this.emit({ type: 'sync_completed', timestamp: Date.now() });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Sync failed';
      this.status.syncErrors.push(errorMessage);
      this.emit({ type: 'sync_failed', timestamp: Date.now(), data: { error: errorMessage } });
    } finally {
      this.status.isSyncing = false;
      this.updateCounts();
    }
  }

  /**
   * Sync a specific entity.
   */
  async syncEntity<T extends SyncableEntity>(
    entityType: string,
    local: T,
    fetchRemote: () => Promise<T | null>,
    saveRemote: (entity: T) => Promise<T>
  ): Promise<T> {
    if (!this.status.isOnline) {
      // Mark as local-only for later sync
      return { ...local, isLocal: true };
    }

    try {
      const remote = await fetchRemote();

      if (!remote) {
        // No remote version, push local
        const saved = await saveRemote(local);
        this.emit({ type: 'entity_synced', timestamp: Date.now(), data: { entityType, id: local.id } });
        return { ...saved, syncedAt: Date.now(), isLocal: false };
      }

      // Check for conflicts
      if (remote.updatedAt > (local.syncedAt || 0) && local.updatedAt > (local.syncedAt || 0)) {
        // Conflict detected
        this.emit({
          type: 'conflict_detected',
          timestamp: Date.now(),
          data: { entityType, id: local.id, local, remote },
        });

        const strategy = this.conflictStrategies.get(entityType);
        const resolved = this.resolveConflict(local, remote, strategy);

        const saved = await saveRemote(resolved);
        return { ...saved, syncedAt: Date.now(), isLocal: false };
      }

      if (local.updatedAt > remote.updatedAt) {
        // Local is newer, push to remote
        const saved = await saveRemote(local);
        this.emit({ type: 'entity_synced', timestamp: Date.now(), data: { entityType, id: local.id } });
        return { ...saved, syncedAt: Date.now(), isLocal: false };
      }

      // Remote is newer or same, use remote
      return { ...remote, syncedAt: Date.now(), isLocal: false };
    } catch (error) {
      // Failed to sync, keep local
      return { ...local, isLocal: true };
    }
  }

  /**
   * Mark the system as online/offline.
   */
  setOnline(online: boolean): void {
    const wasOffline = !this.status.isOnline;
    this.status.isOnline = online;
    this.queue.setOnline(online);

    if (online) {
      this.emit({ type: 'online', timestamp: Date.now() });
      if (wasOffline) {
        // Trigger sync when coming back online
        this.sync();
      }
    } else {
      this.emit({ type: 'offline', timestamp: Date.now() });
    }
  }

  /**
   * Get current sync status.
   */
  getStatus(): SyncStatus {
    this.updateCounts();
    return { ...this.status };
  }

  /**
   * Check if there are pending changes.
   */
  hasPendingChanges(): boolean {
    return this.status.pendingCount > 0;
  }

  /**
   * Subscribe to sync events.
   */
  on(handler: SyncEventHandler): () => void {
    this.eventHandlers.add(handler);
    return () => {
      this.eventHandlers.delete(handler);
    };
  }

  /**
   * Retry all failed sync actions.
   */
  async retryFailed(): Promise<void> {
    await this.queue.retryFailed();
  }

  /**
   * Clear all failed actions.
   */
  async clearFailed(): Promise<void> {
    await this.queue.clearFailed();
    this.updateCounts();
  }

  dispose(): void {
    if (this.networkCheckInterval) {
      clearInterval(this.networkCheckInterval);
    }
    this.queue.dispose();
    this.eventHandlers.clear();
  }

  private resolveConflict<T extends SyncableEntity>(
    local: T,
    remote: T,
    strategy?: ConflictResolution<unknown>
  ): T {
    if (!strategy) {
      // Default: last write wins
      return local.updatedAt > remote.updatedAt ? local : remote;
    }

    switch (strategy.strategy) {
      case 'local':
        return local;
      case 'remote':
        return remote;
      case 'merge':
        if (strategy.resolver) {
          return strategy.resolver(local, remote) as T;
        }
        return local;
      case 'manual':
        // For manual resolution, keep local and mark as conflict
        return { ...local, isLocal: true };
      default:
        return local;
    }
  }

  private updateCounts(): void {
    this.status.pendingCount = this.queue.getPendingCount();
    this.status.failedCount = this.queue.getFailedCount();
  }

  private async saveStatus(): Promise<void> {
    await this.storage.set('sync-status', {
      lastSyncAt: this.status.lastSyncAt,
    });
  }

  private emit(event: SyncEvent): void {
    this.eventHandlers.forEach((handler) => handler(event));
  }

  private startNetworkMonitoring(): void {
    // Check network status periodically
    this.networkCheckInterval = setInterval(async () => {
      try {
        // Try to ping the API
        const response = await fetch('/health', { method: 'HEAD' });
        this.setOnline(response.ok);
      } catch {
        this.setOnline(false);
      }
    }, 30000); // Check every 30 seconds
  }
}

export function createSyncManager(storage: StorageAdapter, queue: OfflineQueue): SyncManager {
  return new SyncManager(storage, queue);
}
