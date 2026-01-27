/**
 * Real-time Voice Pipeline
 *
 * Integrates wake word detection, streaming STT (Deepgram),
 * streaming TTS (ElevenLabs), and conversation flow management.
 *
 * Flow:
 * 1. Always-on wake word detection ("Hey JARVIS")
 * 2. On detection, activate full listening mode
 * 3. Stream audio to Deepgram for real-time transcription
 * 4. VAD detects end of speech
 * 5. Send transcription to conversation service
 * 6. Stream response audio from ElevenLabs
 * 7. Support barge-in (interrupt during response)
 * 8. Return to wake word detection mode
 */

import { EventEmitter } from 'events';
import { DeepgramClient, TranscriptEvent } from './deepgram.js';
import { ElevenLabsClient } from './elevenlabs.js';
import { VoiceActivityDetector } from './vad.js';
import { AudioQueue } from './audio-queue.js';
import { NodeWakeWordDetector, WakeWordDetection } from './node-wake-word.js';
import { LatencyTracker } from './latency-tracker.js';

export type RealtimeVoiceState =
  | 'initializing'
  | 'wake_word_listening'
  | 'active_listening'
  | 'processing'
  | 'speaking'
  | 'error'
  | 'stopped';

export interface RealtimeVoiceConfig {
  // Wake word settings
  wakeWordServerUrl: string;
  wakeWordThreshold?: number;

  // STT settings
  deepgramApiKey: string;
  sttLanguage?: string;
  sttModel?: string;

  // TTS settings
  elevenLabsApiKey: string;
  elevenLabsVoiceId: string;
  ttsModelId?: string;

  // Voice activity settings
  silenceDurationMs?: number;
  energyThreshold?: number;

  // Behavior settings
  autoReturnToWakeWord?: boolean;
  enableBargeIn?: boolean;
  conversationTimeoutMs?: number;

  // Auth
  authToken: string;
}

export interface ConversationTurn {
  userText: string;
  assistantText?: string;
  startTime: number;
  endTime?: number;
  transcriptionLatencyMs?: number;
  ttsLatencyMs?: number;
}

type RealtimeVoiceEvents = {
  stateChange: [RealtimeVoiceState];
  wakeWordDetected: [WakeWordDetection];
  transcriptPartial: [string];
  transcriptFinal: [string];
  responseStart: [];
  responseChunk: [string];
  responseEnd: [string];
  turnComplete: [ConversationTurn];
  bargeIn: [];
  error: [Error];
  audioLevel: [number];
};

interface AudioRecorder {
  start(): Promise<void>;
  stop(): Promise<ArrayBuffer | void>;
  isRecording(): boolean;
  onData(callback: (data: ArrayBuffer) => void): void;
}

interface AudioPlayer {
  play(audio: ArrayBuffer): Promise<void>;
  stop(): void;
  isPlaying(): boolean;
}

interface ConversationClient {
  sendMessage(text: string): Promise<string>;
  streamMessage?(text: string, onChunk: (chunk: string) => void): Promise<string>;
}

export class RealtimeVoicePipeline extends EventEmitter<RealtimeVoiceEvents> {
  private config: Required<RealtimeVoiceConfig>;
  private state: RealtimeVoiceState = 'initializing';

  // Components
  private wakeWordDetector: NodeWakeWordDetector | null = null;
  private deepgram: DeepgramClient | null = null;
  private elevenLabs: ElevenLabsClient;
  private vad: VoiceActivityDetector;
  private audioQueue: AudioQueue | null = null;
  private latencyTracker: LatencyTracker;

  // External components (injected)
  private recorder: AudioRecorder | null = null;
  private player: AudioPlayer | null = null;
  private conversationClient: ConversationClient | null = null;

  // State tracking
  private currentTranscript = '';
  private currentTurn: ConversationTurn | null = null;
  private conversationTimeout: NodeJS.Timeout | null = null;
  private isProcessing = false;

  constructor(config: RealtimeVoiceConfig) {
    super();
    this.config = {
      wakeWordThreshold: 0.5,
      sttLanguage: 'en-US',
      sttModel: 'nova-2',
      ttsModelId: 'eleven_turbo_v2_5',
      silenceDurationMs: 1000,
      energyThreshold: 0.01,
      autoReturnToWakeWord: true,
      enableBargeIn: true,
      conversationTimeoutMs: 30000,
      ...config,
    };

    // Initialize components
    this.elevenLabs = new ElevenLabsClient({
      apiKey: this.config.elevenLabsApiKey,
      voiceId: this.config.elevenLabsVoiceId,
      modelId: this.config.ttsModelId,
    });

    this.vad = new VoiceActivityDetector({
      silenceDurationMs: this.config.silenceDurationMs,
      energyThreshold: this.config.energyThreshold,
    });

    this.latencyTracker = new LatencyTracker();
  }

  /**
   * Set external recorder component.
   */
  setRecorder(recorder: AudioRecorder): void {
    this.recorder = recorder;
  }

  /**
   * Set external player component.
   */
  setPlayer(player: AudioPlayer): void {
    this.player = player;
    this.audioQueue = new AudioQueue(player);
  }

  /**
   * Set conversation client for LLM interaction.
   */
  setConversationClient(client: ConversationClient): void {
    this.conversationClient = client;
  }

  /**
   * Initialize all components and start the pipeline.
   */
  async start(): Promise<void> {
    if (!this.recorder || !this.player || !this.conversationClient) {
      throw new Error('Recorder, player, and conversation client must be set before starting');
    }

    try {
      this.setState('initializing');

      // Initialize wake word detector
      this.wakeWordDetector = new NodeWakeWordDetector({
        serverUrl: this.config.wakeWordServerUrl,
        token: this.config.authToken,
        threshold: this.config.wakeWordThreshold,
      });

      this.wakeWordDetector.on('detected', (detection) => {
        this.handleWakeWordDetected(detection);
      });

      this.wakeWordDetector.on('error', (error) => {
        console.warn('Wake word detector error:', error.message);
      });

      // Initialize Deepgram
      this.deepgram = new DeepgramClient({
        apiKey: this.config.deepgramApiKey,
        language: this.config.sttLanguage,
        model: this.config.sttModel,
        interimResults: true,
        utteranceEndMs: this.config.silenceDurationMs,
      });

      this.deepgram.on('transcript', (transcript) => {
        this.handleFinalTranscript(transcript);
      });

      this.deepgram.on('partial', (transcript) => {
        this.handlePartialTranscript(transcript);
      });

      this.deepgram.on('error', (error) => {
        console.error('Deepgram error:', error.message);
      });

      // Setup VAD callbacks
      this.vad.on('speechEnd', () => {
        this.handleSpeechEnd();
      });

      this.vad.on('level', (level) => {
        this.emit('audioLevel', level);
      });

      // Start wake word detection
      await this.wakeWordDetector.start();
      this.setState('wake_word_listening');

      console.log('Real-time voice pipeline ready. Say "Hey JARVIS" to activate.');
    } catch (error) {
      this.setState('error');
      throw error;
    }
  }

  /**
   * Stop the pipeline.
   */
  async stop(): Promise<void> {
    this.clearConversationTimeout();

    if (this.wakeWordDetector) {
      this.wakeWordDetector.stop();
    }

    if (this.deepgram) {
      this.deepgram.disconnect();
    }

    if (this.recorder?.isRecording()) {
      await this.recorder.stop();
    }

    if (this.player?.isPlaying()) {
      this.player.stop();
    }

    this.audioQueue?.clear();
    this.setState('stopped');
  }

  /**
   * Get current pipeline state.
   */
  getState(): RealtimeVoiceState {
    return this.state;
  }

  /**
   * Get latency metrics.
   */
  getLatencyMetrics() {
    return this.latencyTracker.getStatistics();
  }

  private setState(newState: RealtimeVoiceState): void {
    const prevState = this.state;
    this.state = newState;
    if (prevState !== newState) {
      this.emit('stateChange', newState);
    }
  }

  private async handleWakeWordDetected(detection: WakeWordDetection): Promise<void> {
    if (this.state !== 'wake_word_listening') {
      return; // Ignore if not in wake word mode
    }

    this.emit('wakeWordDetected', detection);

    // Play activation sound (optional)
    // await this.playActivationSound();

    // Transition to active listening
    await this.startActiveListening();
  }

  private async startActiveListening(): Promise<void> {
    try {
      this.setState('active_listening');
      this.currentTranscript = '';
      this.currentTurn = {
        userText: '',
        startTime: Date.now(),
      };

      // Stop wake word detection while actively listening
      this.wakeWordDetector?.stop();

      // Connect to Deepgram
      if (!this.deepgram?.isConnected()) {
        await this.deepgram?.connect();
      }

      // Start recording and stream to Deepgram
      await this.recorder?.start();
      this.recorder?.onData((data) => {
        // Send to Deepgram
        this.deepgram?.sendAudio(data);

        // Process with VAD
        this.vad.processAudio(data);

        // Check for barge-in during playback
        if (this.config.enableBargeIn && this.state === 'speaking') {
          const energy = this.vad.getAudioLevel();
          if (energy > this.config.energyThreshold * 2) {
            this.handleBargeIn();
          }
        }
      });

      // Set conversation timeout
      this.setConversationTimeout();
    } catch (error) {
      this.setState('error');
      this.emit('error', error instanceof Error ? error : new Error(String(error)));
    }
  }

  private handlePartialTranscript(transcript: TranscriptEvent): void {
    this.currentTranscript = transcript.text;
    this.emit('transcriptPartial', transcript.text);
  }

  private handleFinalTranscript(transcript: TranscriptEvent): void {
    this.currentTranscript = transcript.text;
    this.emit('transcriptFinal', transcript.text);
  }

  private async handleSpeechEnd(): Promise<void> {
    if (this.state !== 'active_listening' || this.isProcessing) {
      return;
    }

    if (!this.currentTranscript.trim()) {
      // No speech detected, return to wake word mode
      await this.returnToWakeWordMode();
      return;
    }

    this.isProcessing = true;
    this.setState('processing');

    // Stop recording
    await this.recorder?.stop();
    this.deepgram?.finishStream();

    // Track transcription latency
    const transcriptionLatency = Date.now() - (this.currentTurn?.startTime || Date.now());
    this.latencyTracker.record('transcription', transcriptionLatency);

    if (this.currentTurn) {
      this.currentTurn.userText = this.currentTranscript;
      this.currentTurn.transcriptionLatencyMs = transcriptionLatency;
    }

    // Send to conversation service
    await this.processUserInput(this.currentTranscript);
  }

  private async processUserInput(text: string): Promise<void> {
    try {
      this.clearConversationTimeout();
      this.emit('responseStart');

      const ttsStartTime = Date.now();
      let fullResponse = '';

      // Check if streaming is supported
      if (this.conversationClient?.streamMessage) {
        // Stream response
        await this.conversationClient.streamMessage(text, async (chunk) => {
          fullResponse += chunk;
          this.emit('responseChunk', chunk);

          // Stream TTS as text comes in
          await this.streamTTS(chunk);
        });
      } else {
        // Non-streaming fallback
        fullResponse = (await this.conversationClient?.sendMessage(text)) || '';

        // Speak full response
        this.setState('speaking');
        await this.speakText(fullResponse);
      }

      // Track TTS latency
      const ttsLatency = Date.now() - ttsStartTime;
      this.latencyTracker.record('tts', ttsLatency);

      if (this.currentTurn) {
        this.currentTurn.assistantText = fullResponse;
        this.currentTurn.ttsLatencyMs = ttsLatency;
        this.currentTurn.endTime = Date.now();
        this.emit('turnComplete', this.currentTurn);
      }

      this.emit('responseEnd', fullResponse);

      // Return to wake word mode if configured
      if (this.config.autoReturnToWakeWord) {
        await this.returnToWakeWordMode();
      } else {
        // Continue conversation mode
        await this.startActiveListening();
      }
    } catch (error) {
      this.setState('error');
      this.emit('error', error instanceof Error ? error : new Error(String(error)));
    } finally {
      this.isProcessing = false;
    }
  }

  private async speakText(text: string): Promise<void> {
    if (!text.trim()) {
      return;
    }

    this.setState('speaking');

    try {
      // Use streaming TTS for lower latency
      await this.elevenLabs.synthesizeStream(text, (chunk) => {
        this.audioQueue?.enqueue(chunk);
      });

      // Wait for playback to complete
      await this.waitForPlaybackComplete();
    } catch (error) {
      console.error('TTS error:', error);
      // Continue even if TTS fails
    }
  }

  private async streamTTS(text: string): Promise<void> {
    if (!text.trim()) {
      return;
    }

    if (this.state !== 'speaking') {
      this.setState('speaking');
    }

    try {
      await this.elevenLabs.synthesizeStream(text, (chunk) => {
        this.audioQueue?.enqueue(chunk);
      });
    } catch (error) {
      console.error('Streaming TTS error:', error);
    }
  }

  private async waitForPlaybackComplete(): Promise<void> {
    return new Promise((resolve) => {
      const check = () => {
        if (!this.player?.isPlaying() && !this.audioQueue?.hasItems()) {
          resolve();
        } else {
          setTimeout(check, 100);
        }
      };
      check();
    });
  }

  private handleBargeIn(): void {
    // Stop current playback
    this.player?.stop();
    this.audioQueue?.clear();

    this.emit('bargeIn');

    // Resume listening
    this.startActiveListening();
  }

  private async returnToWakeWordMode(): Promise<void> {
    // Stop recording if active
    if (this.recorder?.isRecording()) {
      await this.recorder.stop();
    }

    // Disconnect Deepgram to save resources
    this.deepgram?.disconnect();

    // Reset state
    this.currentTranscript = '';
    this.currentTurn = null;
    this.vad.reset();

    // Restart wake word detection
    await this.wakeWordDetector?.start();
    this.setState('wake_word_listening');
  }

  private setConversationTimeout(): void {
    this.clearConversationTimeout();
    this.conversationTimeout = setTimeout(() => {
      console.log('Conversation timeout, returning to wake word mode');
      this.returnToWakeWordMode();
    }, this.config.conversationTimeoutMs);
  }

  private clearConversationTimeout(): void {
    if (this.conversationTimeout) {
      clearTimeout(this.conversationTimeout);
      this.conversationTimeout = null;
    }
  }
}

/**
 * Factory function to create a configured voice pipeline.
 */
export function createRealtimeVoicePipeline(config: RealtimeVoiceConfig): RealtimeVoicePipeline {
  return new RealtimeVoicePipeline(config);
}
