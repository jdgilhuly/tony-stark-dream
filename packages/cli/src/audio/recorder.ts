/**
 * CLI Audio Recording Adapter
 * Uses ffmpeg on macOS (avfoundation) or node-record-lpcm16 on Linux
 */

import type { AudioRecorderAdapter } from '@jarvis/core';
import { spawn, ChildProcess } from 'child_process';

interface RecordingOptions {
  sampleRate: number;
  channels: number;
}

export class NodeAudioRecorder implements AudioRecorderAdapter {
  private recording: boolean = false;
  private audioBuffer: Buffer[] = [];
  private ffmpegProcess: ChildProcess | null = null;
  private recordInstance: any = null;
  private dataCallback?: (data: ArrayBuffer) => void;
  private options: RecordingOptions;
  private useFfmpeg: boolean;

  constructor(options: Partial<RecordingOptions> = {}) {
    // Use ffmpeg on macOS to avoid sox coreaudio buffer overrun issues
    this.useFfmpeg = process.platform === 'darwin';

    this.options = {
      sampleRate: options.sampleRate ?? 48000,
      channels: options.channels ?? 1,
    };
  }

  async start(): Promise<void> {
    if (this.recording) {
      throw new Error('Already recording');
    }

    this.audioBuffer = [];
    this.recording = true;

    if (this.useFfmpeg) {
      await this.startFfmpeg();
    } else {
      await this.startNodeRecord();
    }
  }

  private async startFfmpeg(): Promise<void> {
    // Use ffmpeg with avfoundation on macOS
    // -f avfoundation -i ":0" captures default audio input
    // Output raw PCM s16le to stdout
    this.ffmpegProcess = spawn('ffmpeg', [
      '-f', 'avfoundation',
      '-i', ':0',
      '-ar', this.options.sampleRate.toString(),
      '-ac', this.options.channels.toString(),
      '-f', 's16le',
      '-acodec', 'pcm_s16le',
      'pipe:1'
    ], {
      stdio: ['ignore', 'pipe', 'pipe']
    });

    this.ffmpegProcess.stdout?.on('data', (chunk: Buffer) => {
      this.audioBuffer.push(chunk);

      if (this.dataCallback) {
        const arrayBuffer = new ArrayBuffer(chunk.byteLength);
        new Uint8Array(arrayBuffer).set(new Uint8Array(chunk.buffer, chunk.byteOffset, chunk.byteLength));
        this.dataCallback(arrayBuffer);
      }
    });

    this.ffmpegProcess.stderr?.on('data', (data: Buffer) => {
      // ffmpeg outputs progress to stderr - ignore unless it's an error
      const msg = data.toString();
      if (msg.includes('Error') || msg.includes('error')) {
        console.error('ffmpeg error:', msg);
      }
    });

    this.ffmpegProcess.on('error', (err: Error) => {
      console.error('ffmpeg process error:', err);
      this.recording = false;
    });

    this.ffmpegProcess.on('close', (code: number) => {
      if (code !== 0 && code !== 255 && this.recording) {
        console.error('ffmpeg exited with code:', code);
      }
      this.recording = false;
    });
  }

  private async startNodeRecord(): Promise<void> {
    // Fallback to node-record-lpcm16 on Linux
    const recordModule = await import('node-record-lpcm16');

    let recordFn: (opts: any) => any;
    if (typeof recordModule.record === 'function') {
      recordFn = recordModule.record;
    } else if (recordModule.default && typeof recordModule.default.record === 'function') {
      recordFn = recordModule.default.record;
    } else if (typeof recordModule.default === 'function') {
      recordFn = recordModule.default;
    } else {
      throw new Error('Could not find record function in node-record-lpcm16 module');
    }

    this.recordInstance = recordFn({
      sampleRate: this.options.sampleRate,
      channels: this.options.channels,
      threshold: 0,
      silence: '10.0',
      recorder: 'arecord',
      audioType: 'raw',
    });

    const stream = this.recordInstance.stream();

    stream.on('data', (chunk: Buffer) => {
      this.audioBuffer.push(chunk);

      if (this.dataCallback) {
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
    if (!this.recording) {
      return new ArrayBuffer(0);
    }

    this.recording = false;

    if (this.useFfmpeg && this.ffmpegProcess) {
      // Send SIGINT to ffmpeg to stop gracefully
      this.ffmpegProcess.kill('SIGINT');

      // Wait a bit for any remaining data
      await new Promise(resolve => setTimeout(resolve, 100));

      this.ffmpegProcess = null;
    } else if (this.recordInstance) {
      this.recordInstance.stop();
      this.recordInstance = null;
    }

    // Combine all chunks into a single buffer
    const totalLength = this.audioBuffer.reduce((acc, chunk) => acc + chunk.length, 0);
    const combined = Buffer.concat(this.audioBuffer, totalLength);

    this.audioBuffer = [];

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
