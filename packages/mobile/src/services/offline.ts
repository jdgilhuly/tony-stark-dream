import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { apiClient } from './api';

interface QueueItem {
  id: string;
  type: string;
  payload: any;
  timestamp: number;
  retries: number;
}

const QUEUE_KEY = '@jarvis/offline_queue';
const MAX_RETRIES = 3;

class OfflineQueue {
  private isProcessing = false;

  constructor() {
    // Listen for network changes
    NetInfo.addEventListener((state) => {
      if (state.isConnected) {
        this.processQueue();
      }
    });
  }

  async add(item: Omit<QueueItem, 'id' | 'timestamp' | 'retries'>): Promise<void> {
    try {
      const queue = await this.getQueue();
      const newItem: QueueItem = {
        ...item,
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        timestamp: Date.now(),
        retries: 0,
      };
      queue.push(newItem);
      await this.saveQueue(queue);
      console.log('Added to offline queue:', newItem.type);
    } catch (error) {
      console.error('Failed to add to offline queue:', error);
    }
  }

  async getQueue(): Promise<QueueItem[]> {
    try {
      const stored = await AsyncStorage.getItem(QUEUE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Failed to get offline queue:', error);
      return [];
    }
  }

  private async saveQueue(queue: QueueItem[]): Promise<void> {
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  }

  async processQueue(): Promise<void> {
    if (this.isProcessing) return;

    const netInfo = await NetInfo.fetch();
    if (!netInfo.isConnected) return;

    this.isProcessing = true;
    console.log('Processing offline queue...');

    try {
      const queue = await this.getQueue();
      const remaining: QueueItem[] = [];

      for (const item of queue) {
        try {
          await this.processItem(item);
          console.log('Processed queued item:', item.type);
        } catch (error) {
          console.error('Failed to process queued item:', item.type, error);
          item.retries++;
          if (item.retries < MAX_RETRIES) {
            remaining.push(item);
          } else {
            console.log('Max retries reached, discarding:', item.type);
          }
        }
      }

      await this.saveQueue(remaining);
    } finally {
      this.isProcessing = false;
    }
  }

  private async processItem(item: QueueItem): Promise<void> {
    switch (item.type) {
      case 'message':
        await apiClient.post('/conversation/message', item.payload);
        break;
      case 'task':
        await apiClient.post('/tasks', item.payload);
        break;
      case 'settings':
        await apiClient.patch('/user/preferences', item.payload);
        break;
      default:
        console.warn('Unknown queue item type:', item.type);
    }
  }

  async clear(): Promise<void> {
    await AsyncStorage.removeItem(QUEUE_KEY);
  }

  async getCount(): Promise<number> {
    const queue = await this.getQueue();
    return queue.length;
  }
}

export const offlineQueue = new OfflineQueue();
