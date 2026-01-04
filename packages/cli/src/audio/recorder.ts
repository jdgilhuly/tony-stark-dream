/**
 * CLI Audio Recording Adapter
 * Uses node-record-lpcm16 for microphone input
 */

import type { AudioRecorderAdapter } from '@jarvis/core';

interface RecordingOptions {
  sampleRate: number;
  channels: number;
  threshold: number;
  silence: string;
  recorder: string;
}

export class NodeAudioRecorder implements AudioRecorderAdapter {
  private recording: boolean = false;
  private audioBuffer: Buffer[] = [];
  private recordInstance: any = null;
  private dataCallback?: (data: ArrayBuffer) => void;
  private options: RecordingOptions;

  constructor(options: Partial<RecordingOptions> = {}) {
    this.options = {
      sampleRate: options.sampleRate ?? 16000,
      channels: options.channels ?? 1,
      threshold: options.threshold ?? 0.5,
      silence: options.silence ?? '1.0',
      recorder: options.recorder ?? 'sox', // sox, rec, or arecord
    };
  }

  async start(): Promise<void> {
    if (this.recording) {
      throw new Error('Already recording');
    }

    // Dynamic import to avoid issues in environments without the package
    const record = await import('node-record-lpcm16');

    this.audioBuffer = [];
    this.recording = true;

    this.recordInstance = record.record({
      sampleRate: this.options.sampleRate,
      channels: this.options.channels,
      threshold: this.options.threshold,
      silence: this.options.silence,
      recorder: this.options.recorder,
      audioType: 'raw',
    });

    const stream = this.recordInstance.stream();

    stream.on('data', (chunk: Buffer) => {
      this.audioBuffer.push(chunk);

      if (this.dataCallback) {
        // Copy to a new ArrayBuffer to ensure it's not SharedArrayBuffer
        const arrayBuffer = new ArrayBuffer(chunk.byteLength);
        new Uint8Array(arrayBuffer).set(new Uint8Array(chunk.buffer, chunk.byteOffset, chunk.byteLength));
        this.dataCallback(arrayBuffer);
      }
    });

    stream.on('error', (err: Error) => {
      console.error('Recording error:', err);
      this.recording = false;
    });
  }

  async stop(): Promise<ArrayBuffer> {
    if (!this.recording || !this.recordInstance) {
      return new ArrayBuffer(0);
    }

    this.recording = false;
    this.recordInstance.stop();

    // Combine all chunks into a single buffer
    const totalLength = this.audioBuffer.reduce((acc, chunk) => acc + chunk.length, 0);
    const combined = Buffer.concat(this.audioBuffer, totalLength);

    this.audioBuffer = [];
    this.recordInstance = null;

    return combined.buffer.slice(combined.byteOffset, combined.byteOffset + combined.byteLength);
  }

  isRecording(): boolean {
    return this.recording;
  }

  onData(callback: (data: ArrayBuffer) => void): void {
    this.dataCallback = callback;
  }

  getSampleRate(): number {
    return this.options.sampleRate;
  }

  getChannels(): number {
    return this.options.channels;
  }
}

/**
 * Simple audio player using play-sound
 */
export class NodeAudioPlayer {
  private playing: boolean = false;
  private player: any = null;
  private completeCallback?: () => void;
  private volume: number = 1.0;

  async play(audioData: ArrayBuffer | string): Promise<void> {
    if (this.playing) {
      this.stop();
    }

    const playSound = await import('play-sound');
    this.player = playSound.default();
    this.playing = true;

    return new Promise((resolve, reject) => {
      if (typeof audioData === 'string') {
        // Play from file path
        this.player.play(audioData, (err: Error | null) => {
          this.playing = false;
          if (err) {
            reject(err);
          } else {
            this.completeCallback?.();
            resolve();
          }
        });
      } else {
        // For ArrayBuffer, we need to save to temp file first
        const fs = require('fs');
        const os = require('os');
        const path = require('path');

        const tempFile = path.join(os.tmpdir(), `jarvis-audio-${Date.now()}.mp3`);
        fs.writeFileSync(tempFile, Buffer.from(audioData));

        this.player.play(tempFile, (err: Error | null) => {
          this.playing = false;
          // Clean up temp file
          try {
            fs.unlinkSync(tempFile);
          } catch {}

          if (err) {
            reject(err);
          } else {
            this.completeCallback?.();
            resolve();
          }
        });
      }
    });
  }

  stop(): void {
    if (this.player && this.playing) {
      // Note: play-sound doesn't have a built-in stop method
      // We'd need to track the child process and kill it
      this.playing = false;
    }
  }

  pause(): void {
    // Not supported by play-sound
  }

  resume(): void {
    // Not supported by play-sound
  }

  isPlaying(): boolean {
    return this.playing;
  }

  setVolume(volume: number): void {
    this.volume = Math.max(0, Math.min(1, volume));
  }

  onComplete(callback: () => void): void {
    this.completeCallback = callback;
  }
}

/**
 * Factory function to create CLI platform adapters
 */
export async function createCliAudioAdapters() {
  return {
    recorder: new NodeAudioRecorder(),
    player: new NodeAudioPlayer(),
  };
}
