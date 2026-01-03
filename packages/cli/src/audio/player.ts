/**
 * Audio playback module for CLI.
 * Handles playback of TTS responses using speaker library.
 */

import Speaker from 'speaker';
import { PassThrough, Readable } from 'stream';

export interface AudioPlayerOptions {
  sampleRate?: number;
  channels?: number;
  bitDepth?: number;
}

export interface PlaybackResult {
  success: boolean;
  duration?: number;
  error?: Error;
}

export class AudioPlayer {
  private currentSpeaker: Speaker | null = null;
  private isPlaying = false;
  private options: Required<AudioPlayerOptions>;

  constructor(options: AudioPlayerOptions = {}) {
    this.options = {
      sampleRate: options.sampleRate ?? 22050,
      channels: options.channels ?? 1,
      bitDepth: options.bitDepth ?? 16,
    };
  }

  /**
   * Play raw PCM audio data.
   */
  async playPcm(audioData: Buffer): Promise<PlaybackResult> {
    if (this.isPlaying) {
      await this.stop();
    }

    return new Promise((resolve) => {
      const startTime = Date.now();

      try {
        this.currentSpeaker = new Speaker({
          channels: this.options.channels,
          bitDepth: this.options.bitDepth,
          sampleRate: this.options.sampleRate,
        });

        this.isPlaying = true;

        const stream = new PassThrough();
        stream.end(audioData);

        stream.pipe(this.currentSpeaker);

        this.currentSpeaker.on('close', () => {
          this.isPlaying = false;
          this.currentSpeaker = null;
          resolve({
            success: true,
            duration: Date.now() - startTime,
          });
        });

        this.currentSpeaker.on('error', (err) => {
          this.isPlaying = false;
          this.currentSpeaker = null;
          resolve({
            success: false,
            error: err,
          });
        });
      } catch (error) {
        this.isPlaying = false;
        resolve({
          success: false,
          error: error instanceof Error ? error : new Error(String(error)),
        });
      }
    });
  }

  /**
   * Play audio from a readable stream.
   */
  async playStream(stream: Readable): Promise<PlaybackResult> {
    if (this.isPlaying) {
      await this.stop();
    }

    return new Promise((resolve) => {
      const startTime = Date.now();

      try {
        this.currentSpeaker = new Speaker({
          channels: this.options.channels,
          bitDepth: this.options.bitDepth,
          sampleRate: this.options.sampleRate,
        });

        this.isPlaying = true;

        stream.pipe(this.currentSpeaker);

        this.currentSpeaker.on('close', () => {
          this.isPlaying = false;
          this.currentSpeaker = null;
          resolve({
            success: true,
            duration: Date.now() - startTime,
          });
        });

        this.currentSpeaker.on('error', (err) => {
          this.isPlaying = false;
          this.currentSpeaker = null;
          resolve({
            success: false,
            error: err,
          });
        });
      } catch (error) {
        this.isPlaying = false;
        resolve({
          success: false,
          error: error instanceof Error ? error : new Error(String(error)),
        });
      }
    });
  }

  /**
   * Stop current playback.
   */
  async stop(): Promise<void> {
    if (this.currentSpeaker && this.isPlaying) {
      return new Promise((resolve) => {
        if (this.currentSpeaker) {
          this.currentSpeaker.on('close', () => {
            this.isPlaying = false;
            this.currentSpeaker = null;
            resolve();
          });
          this.currentSpeaker.close(false);
        } else {
          resolve();
        }
      });
    }
  }

  /**
   * Check if audio is currently playing.
   */
  get playing(): boolean {
    return this.isPlaying;
  }
}

/**
 * MP3 audio player using external decoder.
 * For playing MP3 responses from Polly.
 */
export class Mp3Player {
  private player: AudioPlayer;
  private decoder: any = null;

  constructor() {
    this.player = new AudioPlayer({
      sampleRate: 22050,
      channels: 1,
      bitDepth: 16,
    });
  }

  /**
   * Initialize the MP3 decoder (lazy load).
   */
  private async initDecoder(): Promise<any> {
    if (!this.decoder) {
      try {
        // Dynamic import for optional dependency
        const lame = await import('lame');
        this.decoder = new lame.Decoder();
      } catch {
        throw new Error('MP3 decoder not available. Install lame package.');
      }
    }
    return this.decoder;
  }

  /**
   * Play MP3 audio data.
   */
  async play(mp3Data: Buffer): Promise<PlaybackResult> {
    try {
      const decoder = await this.initDecoder();
      const pcmStream = new PassThrough();

      // Create a readable stream from the MP3 buffer
      const inputStream = new PassThrough();
      inputStream.end(mp3Data);

      // Decode MP3 to PCM
      inputStream.pipe(decoder).pipe(pcmStream);

      return await this.player.playStream(pcmStream);
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error : new Error(String(error)),
      };
    }
  }

  /**
   * Stop playback.
   */
  async stop(): Promise<void> {
    await this.player.stop();
  }

  get playing(): boolean {
    return this.player.playing;
  }
}

/**
 * Voice output manager for JARVIS CLI.
 * Handles TTS playback with queuing support.
 */
export class VoiceOutput {
  private player: AudioPlayer;
  private queue: Buffer[] = [];
  private isProcessing = false;

  constructor() {
    this.player = new AudioPlayer({
      sampleRate: 22050,
      channels: 1,
      bitDepth: 16,
    });
  }

  /**
   * Queue audio for playback.
   */
  enqueue(audioData: Buffer): void {
    this.queue.push(audioData);
    this.processQueue();
  }

  /**
   * Process the audio queue.
   */
  private async processQueue(): Promise<void> {
    if (this.isProcessing || this.queue.length === 0) {
      return;
    }

    this.isProcessing = true;

    while (this.queue.length > 0) {
      const audio = this.queue.shift();
      if (audio) {
        await this.player.playPcm(audio);
      }
    }

    this.isProcessing = false;
  }

  /**
   * Clear the queue and stop playback.
   */
  async clear(): Promise<void> {
    this.queue = [];
    await this.player.stop();
  }

  /**
   * Speak immediately, clearing queue.
   */
  async speakNow(audioData: Buffer): Promise<PlaybackResult> {
    await this.clear();
    return this.player.playPcm(audioData);
  }

  get isPlaying(): boolean {
    return this.player.playing || this.isProcessing;
  }

  get queueLength(): number {
    return this.queue.length;
  }
}

// Export singleton instance for convenience
let defaultPlayer: VoiceOutput | null = null;

export function getVoiceOutput(): VoiceOutput {
  if (!defaultPlayer) {
    defaultPlayer = new VoiceOutput();
  }
  return defaultPlayer;
}
