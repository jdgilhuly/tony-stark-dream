/**
 * Mock Audio Recorder for Testing
 * Simulates audio recording without requiring microphone hardware
 */

import type { AudioRecorderAdapter } from '@jarvis/core';
import * as fs from 'fs';

export interface MockRecorderOptions {
  sampleRate?: number;
  channels?: number;
  audioFile?: string;
  audioData?: ArrayBuffer;
  chunkSize?: number;
  chunkIntervalMs?: number;
  autoStopMs?: number;
}

export class MockAudioRecorder implements AudioRecorderAdapter {
  private recording: boolean = false;
  private audioBuffer: Buffer[] = [];
  private dataCallback?: (data: ArrayBuffer) => void;
  private options: Required<Omit<MockRecorderOptions, 'audioFile' | 'audioData'>> & Pick<MockRecorderOptions, 'audioFile' | 'audioData'>;
  private streamInterval?: ReturnType<typeof setInterval>;
  private autoStopTimeout?: ReturnType<typeof setTimeout>;
  private sourceData?: Buffer;
  private streamPosition: number = 0;

  constructor(options: MockRecorderOptions = {}) {
    this.options = {
      sampleRate: options.sampleRate ?? 16000,
      channels: options.channels ?? 1,
      chunkSize: options.chunkSize ?? 4096,
      chunkIntervalMs: options.chunkIntervalMs ?? 100,
      autoStopMs: options.autoStopMs ?? 0,
      audioFile: options.audioFile,
      audioData: options.audioData,
    };
  }

  async start(): Promise<void> {
    if (this.recording) {
      throw new Error('Already recording');
    }

    this.audioBuffer = [];
    this.recording = true;
    this.streamPosition = 0;

    // Load source audio if provided
    if (this.options.audioFile) {
      this.sourceData = fs.readFileSync(this.options.audioFile);
    } else if (this.options.audioData) {
      this.sourceData = Buffer.from(this.options.audioData);
    } else {
      // Generate silent audio data for testing
      const silentDuration = this.options.autoStopMs || 3000;
      const bytesPerSecond = this.options.sampleRate * this.options.channels * 2; // 16-bit audio
      const totalBytes = Math.floor((silentDuration / 1000) * bytesPerSecond);
      this.sourceData = Buffer.alloc(totalBytes);
    }

    // Stream audio in chunks to simulate real recording
    this.streamInterval = setInterval(() => {
      if (!this.recording || !this.sourceData) {
        return;
      }

      const remaining = this.sourceData.length - this.streamPosition;
      if (remaining <= 0) {
        // Reached end of source data
        if (this.options.autoStopMs > 0) {
          this.stopInternal();
        }
        return;
      }

      const chunkSize = Math.min(this.options.chunkSize, remaining);
      const chunk = this.sourceData.subarray(this.streamPosition, this.streamPosition + chunkSize);
      this.streamPosition += chunkSize;

      this.audioBuffer.push(Buffer.from(chunk));

      if (this.dataCallback) {
        const arrayBuffer = new ArrayBuffer(chunk.byteLength);
        new Uint8Array(arrayBuffer).set(new Uint8Array(chunk));
        this.dataCallback(arrayBuffer);
      }
    }, this.options.chunkIntervalMs);

    // Auto-stop after specified duration
    if (this.options.autoStopMs > 0) {
      this.autoStopTimeout = setTimeout(() => {
        this.stopInternal();
      }, this.options.autoStopMs);
    }
  }

  private stopInternal(): void {
    if (this.streamInterval) {
      clearInterval(this.streamInterval);
      this.streamInterval = undefined;
    }
    if (this.autoStopTimeout) {
      clearTimeout(this.autoStopTimeout);
      this.autoStopTimeout = undefined;
    }
    this.recording = false;
  }

  async stop(): Promise<ArrayBuffer> {
    if (!this.recording) {
      return new ArrayBuffer(0);
    }

    this.stopInternal();

    // Combine all chunks into a single buffer
    const totalLength = this.audioBuffer.reduce((acc, chunk) => acc + chunk.length, 0);
    const combined = Buffer.concat(this.audioBuffer, totalLength);

    this.audioBuffer = [];
    this.sourceData = undefined;
    this.streamPosition = 0;

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

  /**
   * Set audio data to stream (useful for testing with specific audio)
   */
  setAudioData(data: ArrayBuffer): void {
    this.options.audioData = data;
  }

  /**
   * Load audio from file for streaming
   */
  loadAudioFile(filePath: string): void {
    this.options.audioFile = filePath;
  }
}
