/**
 * ElevenLabs Text-to-Speech Client
 * Handles TTS synthesis via ElevenLabs API
 */

export interface ElevenLabsConfig {
  apiKey: string;
  voiceId: string;
  modelId?: string;
  stability?: number;
  similarityBoost?: number;
  style?: number;
  useSpeakerBoost?: boolean;
  outputFormat?: string;
}

interface VoiceSettings {
  stability: number;
  similarity_boost: number;
  style?: number;
  use_speaker_boost?: boolean;
}

const DEFAULT_CONFIG = {
  modelId: 'eleven_turbo_v2_5',  // Use turbo model for lower latency
  stability: 0.5,
  similarityBoost: 0.75,
  style: 0,
  useSpeakerBoost: true,
  outputFormat: 'mp3_22050_32',  // Lower quality for faster streaming
};

// Available models with their characteristics
export const ELEVENLABS_MODELS = {
  'eleven_turbo_v2_5': {
    name: 'Turbo v2.5',
    description: 'Fastest model, ~300ms latency',
    languages: ['en'],
  },
  'eleven_multilingual_v2': {
    name: 'Multilingual v2',
    description: 'High quality, 29 languages',
    languages: ['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'hi', 'ar', 'zh', 'ja', 'ko'],
  },
  'eleven_monolingual_v1': {
    name: 'Monolingual v1',
    description: 'Original English model',
    languages: ['en'],
  },
} as const;

export class ElevenLabsClient {
  private config: Required<ElevenLabsConfig>;

  constructor(config: ElevenLabsConfig) {
    this.config = {
      apiKey: config.apiKey,
      voiceId: config.voiceId,
      modelId: config.modelId ?? DEFAULT_CONFIG.modelId,
      stability: config.stability ?? DEFAULT_CONFIG.stability,
      similarityBoost: config.similarityBoost ?? DEFAULT_CONFIG.similarityBoost,
      style: config.style ?? DEFAULT_CONFIG.style,
      useSpeakerBoost: config.useSpeakerBoost ?? DEFAULT_CONFIG.useSpeakerBoost,
      outputFormat: config.outputFormat ?? DEFAULT_CONFIG.outputFormat,
    };
  }

  getConfig(): Required<ElevenLabsConfig> {
    return { ...this.config };
  }

  setVoiceId(voiceId: string): void {
    this.config.voiceId = voiceId;
  }

  async synthesize(text: string): Promise<ArrayBuffer> {
    const url = this.buildUrl(false);
    const body = this.buildRequestBody(text);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'xi-api-key': this.config.apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`ElevenLabs API error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    return response.arrayBuffer();
  }

  async synthesizeStream(
    text: string,
    onChunk: (chunk: ArrayBuffer) => void
  ): Promise<void> {
    const url = this.buildUrl(true);
    const body = this.buildRequestBody(text);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'xi-api-key': this.config.apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`ElevenLabs API error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    if (!response.body) {
      throw new Error('No response body for streaming');
    }

    const reader = response.body.getReader();

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      if (value) {
        onChunk(value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength));
      }
    }
  }

  private buildUrl(stream: boolean): string {
    const baseUrl = 'https://api.elevenlabs.io/v1/text-to-speech';
    const endpoint = stream ? 'stream' : '';
    const path = endpoint ? `${this.config.voiceId}/${endpoint}` : this.config.voiceId;
    const params = new URLSearchParams({
      output_format: this.config.outputFormat,
    });

    return `${baseUrl}/${path}?${params.toString()}`;
  }

  private buildRequestBody(text: string): {
    text: string;
    model_id: string;
    voice_settings: VoiceSettings;
  } {
    return {
      text,
      model_id: this.config.modelId,
      voice_settings: {
        stability: this.config.stability,
        similarity_boost: this.config.similarityBoost,
        style: this.config.style,
        use_speaker_boost: this.config.useSpeakerBoost,
      },
    };
  }

  /**
   * WebSocket-based streaming for lowest latency.
   * Supports real-time text input and audio output.
   */
  async synthesizeWebSocket(
    textGenerator: AsyncGenerator<string, void, unknown>,
    onChunk: (chunk: ArrayBuffer) => void,
    onComplete?: () => void
  ): Promise<void> {
    const WebSocket = (await import('ws')).default;
    const wsUrl = `wss://api.elevenlabs.io/v1/text-to-speech/${this.config.voiceId}/stream-input?model_id=${this.config.modelId}`;

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(wsUrl);

      ws.on('open', async () => {
        // Send initial configuration
        ws.send(JSON.stringify({
          text: ' ',
          voice_settings: {
            stability: this.config.stability,
            similarity_boost: this.config.similarityBoost,
          },
          xi_api_key: this.config.apiKey,
        }));

        // Stream text chunks
        try {
          for await (const textChunk of textGenerator) {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({
                text: textChunk,
                try_trigger_generation: true,
              }));
            }
          }

          // Signal end of text
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              text: '',
            }));
          }
        } catch (error) {
          reject(error);
          ws.close();
        }
      });

      ws.on('message', (data: Buffer) => {
        try {
          const message = JSON.parse(data.toString());

          if (message.audio) {
            // Decode base64 audio
            const audioBuffer = Buffer.from(message.audio, 'base64');
            onChunk(audioBuffer.buffer.slice(audioBuffer.byteOffset, audioBuffer.byteOffset + audioBuffer.byteLength));
          }

          if (message.isFinal) {
            onComplete?.();
            ws.close();
            resolve();
          }
        } catch {
          // Binary audio data
          onChunk(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength));
        }
      });

      ws.on('error', (error) => {
        reject(error);
      });

      ws.on('close', () => {
        resolve();
      });
    });
  }

  /**
   * Synthesize with input streaming - send text as it's generated
   * for lowest possible latency.
   */
  async synthesizeInputStreaming(
    text: string,
    onChunk: (chunk: ArrayBuffer) => void
  ): Promise<void> {
    const url = `https://api.elevenlabs.io/v1/text-to-speech/${this.config.voiceId}/stream-input?model_id=${this.config.modelId}&output_format=${this.config.outputFormat}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'xi-api-key': this.config.apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        voice_settings: {
          stability: this.config.stability,
          similarity_boost: this.config.similarityBoost,
          style: this.config.style,
          use_speaker_boost: this.config.useSpeakerBoost,
        },
        generation_config: {
          chunk_length_schedule: [120, 160, 250, 290], // Optimize for low latency
        },
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`ElevenLabs API error: ${response.status} - ${errorText}`);
    }

    if (!response.body) {
      throw new Error('No response body');
    }

    const reader = response.body.getReader();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value) {
        onChunk(value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength));
      }
    }
  }

  /**
   * Get available voices.
   */
  async getVoices(): Promise<Array<{ voice_id: string; name: string; category: string }>> {
    const response = await fetch('https://api.elevenlabs.io/v1/voices', {
      headers: {
        'xi-api-key': this.config.apiKey,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get voices: ${response.statusText}`);
    }

    const data = await response.json();
    return data.voices;
  }
}
