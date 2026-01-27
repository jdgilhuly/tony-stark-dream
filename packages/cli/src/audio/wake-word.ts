/**
 * Wake Word Detection Client
 *
 * Provides always-on listening for "Hey JARVIS" wake word detection.
 * Integrates with the voice processing service for wake word events.
 */

import { EventEmitter } from 'events';

export interface WakeWordConfig {
  serverUrl: string;
  threshold?: number;
  refractoryPeriodMs?: number;
  token?: string;
}

export interface WakeWordEvent {
  wakeWord: string;
  confidence: number;
  timestamp: number;
}

export interface WakeWordStatus {
  isListening: boolean;
  threshold: number;
  refractoryPeriodMs: number;
  models: string[];
}

type WakeWordEventMap = {
  detected: [WakeWordEvent];
  started: [];
  stopped: [];
  error: [Error];
  stateChange: [boolean];
};

/**
 * Local wake word detector using WebAudio API and simple energy detection.
 * For production, connects to the Python service with openWakeWord.
 */
export class WakeWordDetector extends EventEmitter<WakeWordEventMap> {
  private config: WakeWordConfig;
  private isListening = false;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private lastActivationTime = 0;
  private ws: WebSocket | null = null;

  // Simple phrase detection state
  private energyHistory: number[] = [];
  private readonly ENERGY_HISTORY_SIZE = 30;
  private readonly ENERGY_SPIKE_THRESHOLD = 2.5;

  constructor(config: WakeWordConfig) {
    super();
    this.config = {
      threshold: 0.5,
      refractoryPeriodMs: 2000,
      ...config,
    };
  }

  /**
   * Start wake word detection using microphone input.
   */
  async start(): Promise<void> {
    if (this.isListening) {
      return;
    }

    try {
      // Try to connect to the Python service WebSocket
      await this.connectToService();

      // Start local audio capture for streaming to service
      await this.startAudioCapture();

      this.isListening = true;
      this.emit('started');
      this.emit('stateChange', true);
    } catch (error) {
      this.emit('error', error instanceof Error ? error : new Error(String(error)));
      throw error;
    }
  }

  /**
   * Stop wake word detection.
   */
  async stop(): Promise<void> {
    if (!this.isListening) {
      return;
    }

    this.stopAudioCapture();
    this.disconnectFromService();

    this.isListening = false;
    this.emit('stopped');
    this.emit('stateChange', false);
  }

  /**
   * Check if detector is currently listening.
   */
  isActive(): boolean {
    return this.isListening;
  }

  /**
   * Get current status from the service.
   */
  async getStatus(): Promise<WakeWordStatus> {
    const response = await fetch(`${this.config.serverUrl}/wake-word/status`, {
      headers: {
        Authorization: `Bearer ${this.config.token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get wake word status: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      isListening: data.is_listening,
      threshold: data.threshold,
      refractoryPeriodMs: data.refractory_period_ms,
      models: data.models,
    };
  }

  /**
   * Update wake word configuration.
   */
  async updateConfig(updates: Partial<Pick<WakeWordConfig, 'threshold' | 'refractoryPeriodMs'>>): Promise<void> {
    const response = await fetch(`${this.config.serverUrl}/wake-word/config`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.config.token}`,
      },
      body: JSON.stringify({
        threshold: updates.threshold,
        refractory_period_ms: updates.refractoryPeriodMs,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to update wake word config: ${response.statusText}`);
    }

    if (updates.threshold !== undefined) {
      this.config.threshold = updates.threshold;
    }
    if (updates.refractoryPeriodMs !== undefined) {
      this.config.refractoryPeriodMs = updates.refractoryPeriodMs;
    }
  }

  private async connectToService(): Promise<void> {
    const wsUrl = this.config.serverUrl
      .replace('http://', 'ws://')
      .replace('https://', 'wss://');

    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(`${wsUrl}/ws/wake-word?token=${this.config.token}`);

      this.ws.onopen = () => {
        resolve();
      };

      this.ws.onerror = (error) => {
        // Fall back to local detection if service unavailable
        console.warn('Wake word service unavailable, using local detection');
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'wake_word_detected') {
            this.handleDetection({
              wakeWord: data.wake_word,
              confidence: data.confidence,
              timestamp: data.timestamp,
            });
          }
        } catch (e) {
          console.error('Failed to parse wake word message:', e);
        }
      };

      this.ws.onclose = () => {
        this.ws = null;
      };

      // Timeout after 2 seconds
      setTimeout(() => {
        if (this.ws?.readyState !== WebSocket.OPEN) {
          resolve(); // Fall back to local
        }
      }, 2000);
    });
  }

  private disconnectFromService(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private async startAudioCapture(): Promise<void> {
    // Skip audio capture in Node.js environment (will be handled differently)
    if (typeof window === 'undefined' || typeof navigator === 'undefined') {
      // In Node.js, we'll use a different audio capture method
      return;
    }

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      this.audioContext = new AudioContext({ sampleRate: 16000 });
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Use ScriptProcessor for audio processing (deprecated but widely supported)
      this.processor = this.audioContext.createScriptProcessor(1024, 1, 1);
      this.processor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        this.processAudioChunk(inputData);
      };

      source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);
    } catch (error) {
      console.warn('Failed to start audio capture:', error);
      // Continue without audio - service might handle it
    }
  }

  private stopAudioCapture(): void {
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    this.energyHistory = [];
  }

  private processAudioChunk(audioData: Float32Array): void {
    // If connected to service, stream audio
    if (this.ws?.readyState === WebSocket.OPEN) {
      // Convert to Int16 for transmission
      const int16Data = new Int16Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        int16Data[i] = Math.max(-32768, Math.min(32767, audioData[i] * 32768));
      }
      this.ws.send(int16Data.buffer);
      return;
    }

    // Local fallback: simple energy-based detection
    this.localWakeWordDetection(audioData);
  }

  private localWakeWordDetection(audioData: Float32Array): void {
    // Calculate RMS energy
    let sumSquares = 0;
    for (let i = 0; i < audioData.length; i++) {
      sumSquares += audioData[i] * audioData[i];
    }
    const energy = Math.sqrt(sumSquares / audioData.length);

    // Update history
    this.energyHistory.push(energy);
    if (this.energyHistory.length > this.ENERGY_HISTORY_SIZE) {
      this.energyHistory.shift();
    }

    // Need enough history
    if (this.energyHistory.length < this.ENERGY_HISTORY_SIZE) {
      return;
    }

    // Calculate average and look for spike
    const avgEnergy =
      this.energyHistory.slice(0, -3).reduce((a, b) => a + b, 0) /
      (this.energyHistory.length - 3);

    const recentMax = Math.max(...this.energyHistory.slice(-3));

    // Check for energy spike (simple wake word proxy)
    if (recentMax > avgEnergy * this.ENERGY_SPIKE_THRESHOLD && avgEnergy > 0.005) {
      // Check refractory period
      const now = Date.now();
      if (now - this.lastActivationTime < (this.config.refractoryPeriodMs || 2000)) {
        return;
      }

      this.lastActivationTime = now;

      // Emit detection (this is a fallback - not as accurate as openWakeWord)
      this.handleDetection({
        wakeWord: 'hey_jarvis',
        confidence: 0.6, // Lower confidence for local detection
        timestamp: now / 1000,
      });
    }
  }

  private handleDetection(event: WakeWordEvent): void {
    // Check refractory period
    const now = Date.now();
    if (now - this.lastActivationTime < (this.config.refractoryPeriodMs || 2000)) {
      return;
    }

    // Check threshold
    if (event.confidence < (this.config.threshold || 0.5)) {
      return;
    }

    this.lastActivationTime = now;
    this.emit('detected', event);
  }
}

/**
 * Create a wake word detector with default configuration.
 */
export function createWakeWordDetector(
  serverUrl: string,
  token?: string
): WakeWordDetector {
  return new WakeWordDetector({
    serverUrl,
    token,
    threshold: 0.5,
    refractoryPeriodMs: 2000,
  });
}
