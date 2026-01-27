/**
 * Audio Queue for Sequential Playback
 * Manages a queue of audio buffers for TTS playback
 */

export interface AudioQueueConfig {
  autoPlay?: boolean;
}

interface AudioPlayer {
  play(audio: ArrayBuffer): Promise<void>;
  stop(): void;
  isPlaying(): boolean;
}

type EventCallback<T = void> = T extends void ? () => void : (data: T) => void;

interface EventMap {
  playbackComplete: void;
  itemPlayed: void;
  cleared: void;
  error: Error;
}

export class AudioQueue {
  private queue: ArrayBuffer[] = [];
  private player: AudioPlayer;
  private playing = false;
  private paused = false;
  private processing = false;
  private totalEnqueued = 0;
  private totalProcessed = 0;
  private eventListeners: Map<keyof EventMap, Set<EventCallback<any>>> = new Map();

  constructor(player: AudioPlayer) {
    this.player = player;
  }

  on<K extends keyof EventMap>(event: K, callback: EventCallback<EventMap[K]>): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);
  }

  off<K extends keyof EventMap>(event: K, callback: EventCallback<EventMap[K]>): void {
    this.eventListeners.get(event)?.delete(callback);
  }

  private emit<K extends keyof EventMap>(event: K, data?: EventMap[K]): void {
    this.eventListeners.get(event)?.forEach((callback) => {
      if (data !== undefined) {
        (callback as EventCallback<EventMap[K]>)(data);
      } else {
        (callback as EventCallback<void>)();
      }
    });
  }

  enqueue(audio: ArrayBuffer): void {
    this.queue.push(audio);
    this.totalEnqueued++;
    this.playing = true;

    if (!this.processing && !this.paused) {
      this.processQueue();
    }
  }

  private async processQueue(): Promise<void> {
    if (this.processing || this.paused) {
      return;
    }

    this.processing = true;

    while (this.queue.length > 0 && !this.paused) {
      const audio = this.queue.shift()!;

      try {
        await this.player.play(audio);
        this.totalProcessed++;
        this.emit('itemPlayed');
      } catch (error) {
        this.totalProcessed++;
        this.emit('error', error instanceof Error ? error : new Error(String(error)));
      }
    }

    this.processing = false;
    this.playing = false;

    if (this.queue.length === 0 && !this.paused) {
      this.emit('playbackComplete');
    }
  }

  clear(): void {
    this.queue = [];
    this.totalEnqueued = 0;
    this.totalProcessed = 0;

    if (this.player.isPlaying()) {
      this.player.stop();
    }

    this.playing = false;
    this.emit('cleared');
  }

  pause(): void {
    this.paused = true;
  }

  resume(): void {
    this.paused = false;

    if (this.queue.length > 0 && !this.processing) {
      this.processQueue();
    }
  }

  isPlaying(): boolean {
    return this.playing || this.player.isPlaying();
  }

  isPaused(): boolean {
    return this.paused;
  }

  isEmpty(): boolean {
    return this.queue.length === 0;
  }

  length(): number {
    return this.queue.length;
  }

  pendingCount(): number {
    return this.totalEnqueued - this.totalProcessed;
  }
}
