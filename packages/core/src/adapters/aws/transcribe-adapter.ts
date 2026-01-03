/**
 * AWS Transcribe adapter for speech-to-text.
 */

import type {
  SpeechToTextAdapter,
} from '../interfaces.js';
import type { TranscriptionResult, VoiceConfig } from '../../types/index.js';

export interface TranscribeAdapterConfig {
  apiUrl: string;
  getToken: () => Promise<string>;
}

interface TranscribeWebSocketMessage {
  type: 'partial' | 'final' | 'error';
  text?: string;
  confidence?: number;
  error?: string;
}

export class AWSTranscribeAdapter implements SpeechToTextAdapter {
  private config: TranscribeAdapterConfig;
  private ws: WebSocket | null = null;
  private partialCallback: ((result: TranscriptionResult) => void) | null = null;
  private finalResult: TranscriptionResult | null = null;
  private resolveStop: ((result: TranscriptionResult) => void) | null = null;
  private streaming = false;

  constructor(config: TranscribeAdapterConfig) {
    this.config = config;
  }

  async startStreaming(voiceConfig?: Partial<VoiceConfig>): Promise<void> {
    if (this.streaming) {
      throw new Error('Already streaming');
    }

    const token = await this.config.getToken();
    const language = voiceConfig?.language || 'en-US';

    return new Promise((resolve, reject) => {
      const wsUrl = `${this.config.apiUrl.replace('http', 'ws')}/ws/voice?token=${token}`;

      this.ws = new WebSocket(wsUrl);
      this.finalResult = null;

      this.ws.onopen = () => {
        this.streaming = true;
        // Send start command
        this.ws?.send(JSON.stringify({
          type: 'start',
          language_code: language,
        }));
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: TranscribeWebSocketMessage = JSON.parse(event.data);

          if (message.type === 'partial' && message.text) {
            const result: TranscriptionResult = {
              text: message.text,
              confidence: message.confidence ?? 0,
              isFinal: false,
            };
            this.partialCallback?.(result);
          } else if (message.type === 'final' && message.text) {
            this.finalResult = {
              text: message.text,
              confidence: message.confidence ?? 1,
              isFinal: true,
            };
          } else if (message.type === 'error') {
            console.error('Transcription error:', message.error);
          }
        } catch {
          // Handle binary audio data or invalid JSON
        }
      };

      this.ws.onerror = (error) => {
        this.streaming = false;
        reject(new Error('WebSocket connection failed'));
      };

      this.ws.onclose = () => {
        this.streaming = false;
        if (this.resolveStop && this.finalResult) {
          this.resolveStop(this.finalResult);
          this.resolveStop = null;
        }
      };
    });
  }

  async stopStreaming(): Promise<TranscriptionResult> {
    if (!this.streaming || !this.ws) {
      return { text: '', confidence: 0, isFinal: true };
    }

    return new Promise((resolve) => {
      this.resolveStop = resolve;

      // Send stop command
      this.ws?.send(JSON.stringify({ type: 'stop' }));

      // Timeout fallback
      setTimeout(() => {
        if (this.resolveStop) {
          this.resolveStop(this.finalResult || { text: '', confidence: 0, isFinal: true });
          this.resolveStop = null;
        }
        this.ws?.close();
      }, 5000);
    });
  }

  async transcribe(audioData: ArrayBuffer): Promise<TranscriptionResult> {
    const token = await this.config.getToken();

    const formData = new FormData();
    formData.append('audio', new Blob([audioData], { type: 'audio/wav' }));

    const response = await fetch(`${this.config.apiUrl}/transcribe`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Transcription failed: ${response.statusText}`);
    }

    const data = await response.json();

    return {
      text: data.text || '',
      confidence: data.confidence || 0,
      isFinal: true,
    };
  }

  onPartialResult(callback: (result: TranscriptionResult) => void): void {
    this.partialCallback = callback;
  }

  isStreaming(): boolean {
    return this.streaming;
  }

  /**
   * Send audio chunk for real-time transcription.
   */
  sendAudioChunk(chunk: ArrayBuffer): void {
    if (this.ws && this.streaming) {
      this.ws.send(chunk);
    }
  }
}

export function createTranscribeAdapter(config: TranscribeAdapterConfig): AWSTranscribeAdapter {
  return new AWSTranscribeAdapter(config);
}
