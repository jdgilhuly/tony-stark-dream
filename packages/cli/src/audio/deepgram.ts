/**
 * Deepgram Real-time Speech-to-Text Client
 * Handles WebSocket streaming for real-time transcription
 */

import WebSocket from 'ws';

export interface DeepgramConfig {
  apiKey: string;
  sampleRate?: number;
  channels?: number;
  encoding?: 'linear16' | 'flac' | 'mulaw' | 'amr-nb' | 'amr-wb' | 'opus' | 'speex';
  language?: string;
  model?: string;
  punctuate?: boolean;
  interimResults?: boolean;
  utteranceEndMs?: number;
}

export interface TranscriptEvent {
  text: string;
  confidence: number;
  isFinal: boolean;
  words?: Array<{
    word: string;
    start: number;
    end: number;
    confidence: number;
  }>;
}

type EventCallback<T = void> = T extends void ? () => void : (data: T) => void;

interface EventMap {
  connected: void;
  disconnected: void;
  transcript: TranscriptEvent;
  partial: TranscriptEvent;
  speechStarted: void;
  utteranceEnd: void;
  error: Error;
}

export class DeepgramClient {
  private config: Required<DeepgramConfig>;
  private ws: WebSocket | null = null;
  private connected = false;
  private eventListeners: Map<keyof EventMap, Set<EventCallback<any>>> = new Map();

  constructor(config: DeepgramConfig) {
    this.config = {
      apiKey: config.apiKey,
      sampleRate: config.sampleRate ?? 16000,
      channels: config.channels ?? 1,
      encoding: config.encoding ?? 'linear16',
      language: config.language ?? 'en-US',
      model: config.model ?? 'nova-2',
      punctuate: config.punctuate ?? true,
      interimResults: config.interimResults ?? true,
      utteranceEndMs: config.utteranceEndMs ?? 1000,
    };
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

  private emit<K extends keyof EventMap>(event: K, ...args: EventMap[K] extends void ? [] : [EventMap[K]]): void {
    this.eventListeners.get(event)?.forEach((callback) => {
      if (args.length > 0) {
        (callback as (data: EventMap[K]) => void)(args[0] as EventMap[K]);
      } else {
        (callback as () => void)();
      }
    });
  }

  private buildWebSocketUrl(): string {
    const baseUrl = 'wss://api.deepgram.com/v1/listen';
    const params = new URLSearchParams({
      encoding: this.config.encoding,
      sample_rate: this.config.sampleRate.toString(),
      channels: this.config.channels.toString(),
      language: this.config.language,
      model: this.config.model,
      punctuate: this.config.punctuate.toString(),
      interim_results: this.config.interimResults.toString(),
      utterance_end_ms: this.config.utteranceEndMs.toString(),
    });

    return `${baseUrl}?${params.toString()}`;
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const url = this.buildWebSocketUrl();

      this.ws = new WebSocket(url, {
        headers: {
          Authorization: `Token ${this.config.apiKey}`,
        },
      });

      this.ws.onopen = () => {
        this.connected = true;
        this.emit('connected');
        resolve();
      };

      this.ws.onmessage = (event: any) => {
        const data = typeof event.data === 'string' ? event.data : event.data.toString();
        this.handleMessage(data);
      };

      this.ws.onerror = (event: any) => {
        const error = event instanceof Error ? event : new Error('WebSocket error');
        this.emit('error', error);
        if (!this.connected) {
          reject(error);
        }
      };

      this.ws.onclose = () => {
        this.connected = false;
        this.emit('disconnected');
      };
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.connected = false;
    }
  }

  isConnected(): boolean {
    return this.connected;
  }

  sendAudio(audioData: ArrayBuffer): void {
    if (!this.connected || !this.ws) {
      return;
    }
    this.ws.send(audioData);
  }

  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data);

      switch (message.type) {
        case 'Results':
          this.handleResults(message);
          break;
        case 'SpeechStarted':
          this.emit('speechStarted');
          break;
        case 'UtteranceEnd':
          this.emit('utteranceEnd');
          break;
        case 'Metadata':
          // Connection metadata, can be ignored or logged
          break;
        case 'Error':
          this.emit('error', new Error(message.message || 'Deepgram error'));
          break;
      }
    } catch (error) {
      this.emit('error', error instanceof Error ? error : new Error('Failed to parse message'));
    }
  }

  private handleResults(message: any): void {
    const channel = message.channel;
    if (!channel?.alternatives?.length) {
      return;
    }

    const alternative = channel.alternatives[0];
    const transcript: TranscriptEvent = {
      text: alternative.transcript || '',
      confidence: alternative.confidence || 0,
      isFinal: message.is_final === true,
      words: alternative.words,
    };

    // Skip empty transcripts
    if (!transcript.text.trim()) {
      return;
    }

    if (transcript.isFinal) {
      this.emit('transcript', transcript);
    } else {
      this.emit('partial', transcript);
    }
  }

  // Send a close message to signal end of audio stream
  finishStream(): void {
    if (this.connected && this.ws) {
      // Send empty buffer to signal end of stream
      this.ws.send(JSON.stringify({ type: 'CloseStream' }));
    }
  }
}
