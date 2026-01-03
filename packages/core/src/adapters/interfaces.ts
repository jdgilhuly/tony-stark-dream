import type { TranscriptionResult, SynthesisResult, VoiceConfig } from '../types/index.js';

/**
 * Audio recording adapter interface
 * Implemented differently for CLI (node-record-lpcm16) and mobile (react-native-audio)
 */
export interface AudioRecorderAdapter {
  start(): Promise<void>;
  stop(): Promise<ArrayBuffer>;
  isRecording(): boolean;
  onData?(callback: (data: ArrayBuffer) => void): void;
  getSampleRate(): number;
  getChannels(): number;
}

/**
 * Audio playback adapter interface
 * Implemented differently for CLI (play-sound) and mobile (react-native-audio-player)
 */
export interface AudioPlayerAdapter {
  play(audioData: ArrayBuffer | string): Promise<void>;
  stop(): void;
  pause(): void;
  resume(): void;
  isPlaying(): boolean;
  setVolume(volume: number): void;
  onComplete?(callback: () => void): void;
}

/**
 * Speech-to-text adapter interface
 * Can be backed by AWS Transcribe, Web Speech API, or other providers
 */
export interface SpeechToTextAdapter {
  startStreaming(config?: Partial<VoiceConfig>): Promise<void>;
  stopStreaming(): Promise<TranscriptionResult>;
  transcribe(audioData: ArrayBuffer): Promise<TranscriptionResult>;
  onPartialResult?(callback: (result: TranscriptionResult) => void): void;
  isStreaming(): boolean;
}

/**
 * Text-to-speech adapter interface
 * Can be backed by AWS Polly, device TTS, or other providers
 */
export interface TextToSpeechAdapter {
  synthesize(text: string, config?: Partial<VoiceConfig>): Promise<SynthesisResult>;
  speak(text: string, config?: Partial<VoiceConfig>): Promise<void>;
  stop(): void;
  isSpeaking(): boolean;
  getAvailableVoices(): Promise<string[]>;
}

/**
 * Wake word detection adapter interface
 * Implemented with Porcupine or similar
 */
export interface WakeWordAdapter {
  start(wakeWord: string): Promise<void>;
  stop(): void;
  isListening(): boolean;
  onDetected(callback: () => void): void;
}

/**
 * Local storage adapter interface
 * Implemented differently for Node.js (file system) and mobile (AsyncStorage/SQLite)
 */
export interface StorageAdapter {
  get<T>(key: string): Promise<T | null>;
  set<T>(key: string, value: T): Promise<void>;
  remove(key: string): Promise<void>;
  clear(): Promise<void>;
  keys(): Promise<string[]>;
}

/**
 * Platform-specific services container
 */
export interface PlatformAdapters {
  audioRecorder: AudioRecorderAdapter;
  audioPlayer: AudioPlayerAdapter;
  speechToText: SpeechToTextAdapter;
  textToSpeech: TextToSpeechAdapter;
  wakeWord: WakeWordAdapter;
  storage: StorageAdapter;
}

/**
 * Factory function type for creating platform adapters
 */
export type CreatePlatformAdapters = () => Promise<PlatformAdapters>;
