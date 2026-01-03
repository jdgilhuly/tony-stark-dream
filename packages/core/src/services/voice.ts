import type {
  AudioRecorderAdapter,
  AudioPlayerAdapter,
  SpeechToTextAdapter,
  TextToSpeechAdapter,
  WakeWordAdapter,
} from '../adapters/interfaces.js';
import type { VoiceConfig, TranscriptionResult } from '../types/index.js';

export interface VoiceServiceConfig {
  audioRecorder: AudioRecorderAdapter;
  audioPlayer: AudioPlayerAdapter;
  speechToText: SpeechToTextAdapter;
  textToSpeech: TextToSpeechAdapter;
  wakeWord?: WakeWordAdapter;
}

export type VoiceServiceEvent =
  | { type: 'wake_word_detected' }
  | { type: 'listening_started' }
  | { type: 'listening_stopped' }
  | { type: 'transcription_partial'; result: TranscriptionResult }
  | { type: 'transcription_final'; result: TranscriptionResult }
  | { type: 'speaking_started'; text: string }
  | { type: 'speaking_stopped' }
  | { type: 'error'; error: Error };

type VoiceServiceEventHandler = (event: VoiceServiceEvent) => void;

export class VoiceService {
  private adapters: VoiceServiceConfig;
  private config: VoiceConfig;
  private eventHandlers: Set<VoiceServiceEventHandler> = new Set();
  private isActive = false;

  constructor(adapters: VoiceServiceConfig, config?: Partial<VoiceConfig>) {
    this.adapters = adapters;
    this.config = {
      enabled: config?.enabled ?? true,
      wakeWord: config?.wakeWord ?? 'jarvis',
      language: config?.language ?? 'en-US',
      voice: config?.voice ?? 'Brian',
      speakingRate: config?.speakingRate ?? 1.0,
    };

    this.setupWakeWordDetection();
  }

  private setupWakeWordDetection(): void {
    if (this.adapters.wakeWord) {
      this.adapters.wakeWord.onDetected(() => {
        this.emit({ type: 'wake_word_detected' });
        if (this.config.enabled) {
          this.startListening();
        }
      });
    }
  }

  async startWakeWordDetection(): Promise<void> {
    if (!this.adapters.wakeWord) {
      throw new Error('Wake word adapter not configured');
    }
    await this.adapters.wakeWord.start(this.config.wakeWord);
    this.isActive = true;
  }

  stopWakeWordDetection(): void {
    this.adapters.wakeWord?.stop();
    this.isActive = false;
  }

  async startListening(): Promise<void> {
    try {
      await this.adapters.audioRecorder.start();
      await this.adapters.speechToText.startStreaming(this.config);

      // Set up partial result handling
      this.adapters.speechToText.onPartialResult?.((result) => {
        this.emit({ type: 'transcription_partial', result });
      });

      this.emit({ type: 'listening_started' });
    } catch (error) {
      this.emit({ type: 'error', error: error instanceof Error ? error : new Error(String(error)) });
      throw error;
    }
  }

  async stopListening(): Promise<TranscriptionResult> {
    try {
      const audioData = await this.adapters.audioRecorder.stop();
      const result = await this.adapters.speechToText.stopStreaming();

      this.emit({ type: 'listening_stopped' });
      this.emit({ type: 'transcription_final', result });

      return result;
    } catch (error) {
      this.emit({ type: 'error', error: error instanceof Error ? error : new Error(String(error)) });
      throw error;
    }
  }

  async transcribe(audioData: ArrayBuffer): Promise<TranscriptionResult> {
    try {
      return await this.adapters.speechToText.transcribe(audioData);
    } catch (error) {
      this.emit({ type: 'error', error: error instanceof Error ? error : new Error(String(error)) });
      throw error;
    }
  }

  async speak(text: string): Promise<void> {
    try {
      this.emit({ type: 'speaking_started', text });
      await this.adapters.textToSpeech.speak(text, this.config);
      this.emit({ type: 'speaking_stopped' });
    } catch (error) {
      this.emit({ type: 'error', error: error instanceof Error ? error : new Error(String(error)) });
      throw error;
    }
  }

  stopSpeaking(): void {
    this.adapters.textToSpeech.stop();
    this.adapters.audioPlayer.stop();
    this.emit({ type: 'speaking_stopped' });
  }

  async getAvailableVoices(): Promise<string[]> {
    return this.adapters.textToSpeech.getAvailableVoices();
  }

  setConfig(config: Partial<VoiceConfig>): void {
    this.config = { ...this.config, ...config };
  }

  getConfig(): VoiceConfig {
    return { ...this.config };
  }

  isListening(): boolean {
    return this.adapters.audioRecorder.isRecording();
  }

  isSpeaking(): boolean {
    return this.adapters.textToSpeech.isSpeaking();
  }

  isWakeWordActive(): boolean {
    return this.isActive && (this.adapters.wakeWord?.isListening() ?? false);
  }

  on(handler: VoiceServiceEventHandler): () => void {
    this.eventHandlers.add(handler);
    return () => {
      this.eventHandlers.delete(handler);
    };
  }

  private emit(event: VoiceServiceEvent): void {
    this.eventHandlers.forEach((handler) => handler(event));
  }

  dispose(): void {
    this.stopWakeWordDetection();
    this.stopSpeaking();
    if (this.adapters.audioRecorder.isRecording()) {
      this.adapters.audioRecorder.stop();
    }
    this.eventHandlers.clear();
  }
}

export const createVoiceService = (
  adapters: VoiceServiceConfig,
  config?: Partial<VoiceConfig>
): VoiceService => {
  return new VoiceService(adapters, config);
};
