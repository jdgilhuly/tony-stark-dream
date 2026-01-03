/**
 * Cache Manager - Handles caching strategies with TTL management
 */

import type { StorageAdapter } from '../adapters/interfaces.js';

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
  key: string;
}

export interface CacheOptions {
  defaultTtl: number;
  maxEntries: number;
  cleanupInterval: number;
}

export class CacheManager {
  private storage: StorageAdapter;
  private options: CacheOptions;
  private memoryCache: Map<string, CacheEntry<unknown>> = new Map();
  private cleanupTimer?: NodeJS.Timeout;

  constructor(storage: StorageAdapter, options: Partial<CacheOptions> = {}) {
    this.storage = storage;
    this.options = {
      defaultTtl: options.defaultTtl ?? 300000, // 5 minutes
      maxEntries: options.maxEntries ?? 1000,
      cleanupInterval: options.cleanupInterval ?? 60000, // 1 minute
    };

    this.startCleanup();
  }

  async get<T>(key: string): Promise<T | null> {
    // Check memory cache first
    const memEntry = this.memoryCache.get(key) as CacheEntry<T> | undefined;
    if (memEntry && !this.isExpired(memEntry)) {
      return memEntry.data;
    }

    // Check persistent storage
    try {
      const stored = await this.storage.get<CacheEntry<T>>(this.storageKey(key));
      if (stored && !this.isExpired(stored)) {
        // Restore to memory cache
        this.memoryCache.set(key, stored);
        return stored.data;
      }
    } catch {
      // Storage error, return null
    }

    return null;
  }

  async set<T>(key: string, data: T, ttl?: number): Promise<void> {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl: ttl ?? this.options.defaultTtl,
      key,
    };

    // Enforce max entries
    if (this.memoryCache.size >= this.options.maxEntries) {
      this.evictOldest();
    }

    this.memoryCache.set(key, entry);

    // Persist to storage
    try {
      await this.storage.set(this.storageKey(key), entry);
    } catch {
      // Storage error, cache only in memory
    }
  }

  async delete(key: string): Promise<void> {
    this.memoryCache.delete(key);
    try {
      await this.storage.remove(this.storageKey(key));
    } catch {
      // Ignore storage errors
    }
  }

  async clear(): Promise<void> {
    this.memoryCache.clear();
    try {
      const keys = await this.storage.keys();
      const cacheKeys = keys.filter(k => k.startsWith('cache:'));
      await Promise.all(cacheKeys.map(k => this.storage.remove(k)));
    } catch {
      // Ignore storage errors
    }
  }

  async has(key: string): Promise<boolean> {
    const value = await this.get(key);
    return value !== null;
  }

  private isExpired(entry: CacheEntry<unknown>): boolean {
    return Date.now() - entry.timestamp > entry.ttl;
  }

  private storageKey(key: string): string {
    return `cache:${key}`;
  }

  private evictOldest(): void {
    let oldestKey: string | null = null;
    let oldestTime = Infinity;

    for (const [key, entry] of this.memoryCache) {
      if (entry.timestamp < oldestTime) {
        oldestTime = entry.timestamp;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      this.memoryCache.delete(oldestKey);
    }
  }

  private startCleanup(): void {
    this.cleanupTimer = setInterval(() => {
      const now = Date.now();
      for (const [key, entry] of this.memoryCache) {
        if (this.isExpired(entry)) {
          this.memoryCache.delete(key);
        }
      }
    }, this.options.cleanupInterval);
  }

  dispose(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
    }
    this.memoryCache.clear();
  }
}

// Predefined TTL values
export const CacheTTL = {
  SHORT: 60000,       // 1 minute
  MEDIUM: 300000,     // 5 minutes
  LONG: 1800000,      // 30 minutes
  HOUR: 3600000,      // 1 hour
  DAY: 86400000,      // 24 hours
} as const;
