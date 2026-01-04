/**
 * AWS Polly adapter for text-to-speech.
 */

import type { TextToSpeechAdapter } from '../interfaces.js';
import type { SynthesisResult, VoiceConfig } from '../../types/index.js';

export interface PollyAdapterConfig {
  apiUrl: string;
  getToken: () => Promise<string>;
  onAudioData?: (audioData: ArrayBuffer) => Promise<void>;
}

export class AWSPollyAdapter implements TextToSpeechAdapter {
  private config: PollyAdapterConfig;
  private speaking = false;
  private abortController: AbortController | null = null;

  constructor(config: PollyAdapterConfig) {
    this.config = config;
  }

  async synthesize(text: string, voiceConfig?: Partial<VoiceConfig>): Promise<SynthesisResult> {
    const token = await this.config.getToken();
    const voice = voiceConfig?.voice || 'Brian';

    const response = await fetch(`${this.config.apiUrl}/synthesize`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        voice_id: voice,
        output_format: 'mp3',
        use_ssml: false,
      }),
    });

    if (!response.ok) {
      throw new Error(`Synthesis failed: ${response.statusText}`);
    }

    const audioData = await response.arrayBuffer();
    const contentType = response.headers.get('Content-Type') || 'audio/mpeg';
    const characters = parseInt(response.headers.get('X-Characters-Synthesized') || '0', 10);

    return {
      audioData,
      contentType,
      text,
      duration: this.estimateDuration(text),
    };
  }

  async speak(text: string, voiceConfig?: Partial<VoiceConfig>): Promise<void> {
    if (this.speaking) {
      this.stop();
    }

    this.speaking = true;
    this.abortController = new AbortController();

    try {
      const result = await this.synthesize(text, voiceConfig);

      if (this.config.onAudioData) {
        await this.config.onAudioData(result.audioData);
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        throw error;
      }
    } finally {
      this.speaking = false;
      this.abortController = null;
    }
  }

  stop(): void {
    if (this.abortController) {
      this.abortController.abort();
    }
    this.speaking = false;
  }

  isSpeaking(): boolean {
    return this.speaking;
  }

  async getAvailableVoices(): Promise<string[]> {
    const token = await this.config.getToken();

    try {
      const response = await fetch(`${this.config.apiUrl}/voices`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch voices: ${response.statusText}`);
      }

      const voices = await response.json() as { id: string }[];
      return voices.map((v) => v.id);
    } catch {
      // Return default JARVIS-appropriate voices
      return ['Brian', 'Matthew', 'Joanna', 'Amy', 'Emma'];
    }
  }

  /**
   * Estimate audio duration based on text length.
   * Rough estimate: ~150 words per minute, ~5 characters per word.
   */
  private estimateDuration(text: string): number {
    const wordsPerMinute = 150;
    const charsPerWord = 5;
    const wordCount = text.length / charsPerWord;
    const durationMinutes = wordCount / wordsPerMinute;
    return Math.ceil(durationMinutes * 60 * 1000); // milliseconds
  }
}

export function createPollyAdapter(config: PollyAdapterConfig): AWSPollyAdapter {
  return new AWSPollyAdapter(config);
}
