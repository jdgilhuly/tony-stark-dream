/**
 * Voice Pipeline
 * Orchestrates STT, TTS, VAD, and audio queue with barge-in support
 */

import { AudioQueue } from './audio-queue.js';

export type VoicePipelineState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error';

export interface VoicePipelineConfig {
  recorder: AudioRecorder;
  player: AudioPlayer;
  sttClient: STTClient;
  ttsClient: TTSClient;
}

interface AudioRecorder {
  start(): Promise<void>;
  stop(): Promise<ArrayBuffer>;
  isRecording(): boolean;
  onData(callback: (data: ArrayBuffer) => void): void;
}

interface AudioPlayer {
  play(audio: ArrayBuffer): Promise<void>;
  stop(): void;
  isPlaying(): boolean;
}

interface STTClient {
  connect(): Promise<void>;
  disconnect(): void;
  sendAudio(audio: ArrayBuffer): void;
  on(event: string, callback: (...args: any[]) => void): void;
  off(event: string, callback: (...args: any[]) => void): void;
  isConnected(): boolean;
}

interface TTSClient {
  synthesize(text: string): Promise<ArrayBuffer>;
  synthesizeStream?(text: string, onChunk: (chunk: ArrayBuffer) => void): Promise<void>;
}

export interface TranscriptData {
  text: string;
  isFinal: boolean;
  confidence: number;
}

type EventCallback<T = void> = T extends void ? () => void : (data: T) => void;

interface EventMap {
  stateChange: VoicePipelineState;
  transcript: TranscriptData;
  bargeIn: void;
  error: Error;
  stopped: void;
  audioLevel: number;
}

export class VoicePipeline {
  private state: VoicePipelineState = 'idle';
  private recorder: AudioRecorder;
  private player: AudioPlayer;
  private sttClient: STTClient;
  private ttsClient: TTSClient;
  private audioQueue: AudioQueue;
  private currentAudioLevel = 0;
  private eventListeners: Map<keyof EventMap, Set<EventCallback<any>>> = new Map();

  constructor(config: VoicePipelineConfig) {
    this.recorder = config.recorder;
    this.player = config.player;
    this.sttClient = config.sttClient;
    this.ttsClient = config.ttsClient;
    this.audioQueue = new AudioQueue(this.player);
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

  private setState(newState: VoicePipelineState): void {
    this.state = newState;
    this.emit('stateChange', newState);
  }

  getState(): VoicePipelineState {
    return this.state;
  }

  getAudioLevel(): number {
    return this.currentAudioLevel;
  }

  async startListening(): Promise<void> {
    try {
      // Connect STT if not connected
      if (!this.sttClient.isConnected()) {
        await this.sttClient.connect();
      }

      // Start recording
      await this.recorder.start();

      // Stream audio to STT
      this.recorder.onData((data) => {
        this.sttClient.sendAudio(data);
      });

      this.setState('listening');
    } catch (error) {
      this.setState('error');
      this.emit('error', error instanceof Error ? error : new Error(String(error)));
    }
  }

  handleSpeechEnd(): void {
    this.recorder.stop();
    this.setState('processing');
  }

  async speak(text: string): Promise<void> {
    try {
      const audioData = await this.ttsClient.synthesize(text);
      this.audioQueue.enqueue(audioData);
      this.setState('speaking');
    } catch (error) {
      this.emit('error', error instanceof Error ? error : new Error(String(error)));
    }
  }

  handleBargeIn(): void {
    // Stop current playback
    this.player.stop();

    // Clear queue
    this.clearAudioQueue();

    // Emit event
    this.emit('bargeIn');

    // Resume listening
    this.setState('listening');
    this.recorder.start().catch((err) => {
      this.emit('error', err instanceof Error ? err : new Error(String(err)));
    });
  }

  handleTranscript(transcript: TranscriptData): void {
    this.emit('transcript', transcript);
  }

  handleAudioLevel(level: number): void {
    this.currentAudioLevel = level;
    this.emit('audioLevel', level);
  }

  private clearAudioQueue(): void {
    this.audioQueue.clear();
  }

  stop(): void {
    // Stop all components
    this.recorder.stop();
    this.player.stop();
    this.sttClient.disconnect();
    this.audioQueue.clear();

    this.setState('idle');
    this.emit('stopped');
  }
}
