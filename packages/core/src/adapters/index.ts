export type {
  AudioRecorderAdapter,
  AudioPlayerAdapter,
  SpeechToTextAdapter,
  TextToSpeechAdapter,
  WakeWordAdapter,
  StorageAdapter,
  PlatformAdapters,
  CreatePlatformAdapters,
} from './interfaces.js';

// AWS Adapters
export {
  AWSTranscribeAdapter,
  createTranscribeAdapter,
  AWSPollyAdapter,
  createPollyAdapter,
} from './aws/index.js';
export type { TranscribeAdapterConfig, PollyAdapterConfig } from './aws/index.js';
