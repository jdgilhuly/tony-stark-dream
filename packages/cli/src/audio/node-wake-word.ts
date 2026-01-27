/**
 * Node.js Wake Word Detection
 *
 * Provides always-on wake word detection for the CLI using native audio capture.
 * Uses the voice processing service for actual detection.
 */

import { EventEmitter } from 'events';
import { spawn, ChildProcess } from 'child_process';
import WebSocket from 'ws';

export interface NodeWakeWordConfig {
  serverUrl: string;
  token: string;
  sampleRate?: number;
  threshold?: number;
  refractoryPeriodMs?: number;
  wakeWords?: string[];
}

export interface WakeWordDetection {
  wakeWord: string;
  confidence: number;
  timestamp: number;
}

type WakeWordEvents = {
  detected: [WakeWordDetection];
  started: [];
  stopped: [];
  error: [Error];
  listening: [boolean];
};

/**
 * Node.js wake word detector using native audio capture.
 *
 * Uses sox/rec for audio capture and streams to the voice processing service.
 */
export class NodeWakeWordDetector extends EventEmitter<WakeWordEvents> {
  private config: Required<NodeWakeWordConfig>;
  private isListening = false;
  private audioProcess: ChildProcess | null = null;
  private ws: WebSocket | null = null;
  private lastActivationTime = 0;
  private reconnectAttempts = 0;
  private readonly MAX_RECONNECT_ATTEMPTS = 5;

  constructor(config: NodeWakeWordConfig) {
    super();
    this.config = {
      sampleRate: 16000,
      threshold: 0.5,
      refractoryPeriodMs: 2000,
      wakeWords: ['hey_jarvis', 'jarvis'],
      ...config,
    };
  }

  /**
   * Start listening for wake words.
   */
  async start(): Promise<void> {
    if (this.isListening) {
      return;
    }

    try {
      // Start audio capture
      this.startAudioCapture();

      // Connect to wake word service
      await this.connectToService();

      this.isListening = true;
      this.emit('started');
      this.emit('listening', true);

      console.log('Wake word detection active. Say "Hey JARVIS" to activate.');
    } catch (error) {
      this.cleanup();
      throw error;
    }
  }

  /**
   * Stop listening for wake words.
   */
  stop(): void {
    if (!this.isListening) {
      return;
    }

    this.cleanup();
    this.isListening = false;
    this.emit('stopped');
    this.emit('listening', false);
  }

  /**
   * Check if actively listening.
   */
  isActive(): boolean {
    return this.isListening;
  }

  private startAudioCapture(): void {
    // Use sox/rec for cross-platform audio capture
    // rec is part of sox and available on macOS, Linux, Windows
    const args = [
      '-q', // Quiet mode
      '-t', 'raw', // Raw format
      '-b', '16', // 16-bit
      '-e', 'signed-integer', // Signed integers
      '-c', '1', // Mono
      '-r', String(this.config.sampleRate), // Sample rate
      '-', // Output to stdout
    ];

    try {
      // Try 'rec' first (sox recording utility)
      this.audioProcess = spawn('rec', args, {
        stdio: ['ignore', 'pipe', 'ignore'],
      });
    } catch {
      // Fall back to sox with input device
      try {
        this.audioProcess = spawn('sox', ['-d', ...args], {
          stdio: ['ignore', 'pipe', 'ignore'],
        });
      } catch (error) {
        throw new Error(
          'Audio capture not available. Install sox: brew install sox (macOS) or apt install sox (Linux)'
        );
      }
    }

    this.audioProcess.on('error', (error) => {
      this.emit('error', new Error(`Audio capture error: ${error.message}`));
    });

    this.audioProcess.on('exit', (code) => {
      if (this.isListening && code !== 0) {
        this.emit('error', new Error(`Audio capture exited with code ${code}`));
      }
    });

    // Stream audio to WebSocket
    this.audioProcess.stdout?.on('data', (chunk: Buffer) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(chunk);
      }
    });
  }

  private async connectToService(): Promise<void> {
    const wsUrl = this.config.serverUrl
      .replace('http://', 'ws://')
      .replace('https://', 'wss://');

    return new Promise((resolve, reject) => {
      const url = `${wsUrl}/ws/wake-word?token=${this.config.token}`;

      this.ws = new WebSocket(url);

      const timeout = setTimeout(() => {
        reject(new Error('Connection timeout'));
        this.ws?.close();
      }, 5000);

      this.ws.on('open', () => {
        clearTimeout(timeout);
        this.reconnectAttempts = 0;

        // Send configuration
        this.ws?.send(
          JSON.stringify({
            type: 'config',
            threshold: this.config.threshold,
            wake_words: this.config.wakeWords,
          })
        );

        resolve();
      });

      this.ws.on('error', (error) => {
        clearTimeout(timeout);
        reject(error);
      });

      this.ws.on('message', (data: Buffer) => {
        this.handleMessage(data);
      });

      this.ws.on('close', () => {
        if (this.isListening) {
          this.handleDisconnect();
        }
      });
    });
  }

  private handleMessage(data: Buffer): void {
    try {
      const message = JSON.parse(data.toString());

      switch (message.type) {
        case 'wake_word_detected':
          this.handleDetection({
            wakeWord: message.wake_word,
            confidence: message.confidence,
            timestamp: message.timestamp,
          });
          break;

        case 'error':
          this.emit('error', new Error(message.message));
          break;

        case 'config_updated':
          // Configuration acknowledged
          break;
      }
    } catch (error) {
      // Non-JSON message, ignore
    }
  }

  private handleDetection(detection: WakeWordDetection): void {
    // Check refractory period
    const now = Date.now();
    if (now - this.lastActivationTime < this.config.refractoryPeriodMs) {
      return;
    }

    // Check threshold
    if (detection.confidence < this.config.threshold) {
      return;
    }

    this.lastActivationTime = now;
    this.emit('detected', detection);
  }

  private async handleDisconnect(): Promise<void> {
    if (this.reconnectAttempts >= this.MAX_RECONNECT_ATTEMPTS) {
      this.emit('error', new Error('Max reconnection attempts reached'));
      this.stop();
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

    console.log(`Reconnecting to wake word service in ${delay}ms...`);

    await new Promise((resolve) => setTimeout(resolve, delay));

    try {
      await this.connectToService();
    } catch {
      this.handleDisconnect();
    }
  }

  private cleanup(): void {
    if (this.audioProcess) {
      this.audioProcess.kill();
      this.audioProcess = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Update detection threshold.
   */
  setThreshold(threshold: number): void {
    this.config.threshold = Math.max(0, Math.min(1, threshold));
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: 'config',
          threshold: this.config.threshold,
        })
      );
    }
  }

  /**
   * Update refractory period.
   */
  setRefractoryPeriod(periodMs: number): void {
    this.config.refractoryPeriodMs = Math.max(0, periodMs);
  }
}

/**
 * Simple local wake word detector using energy-based detection.
 * Used as fallback when service is unavailable.
 */
export class LocalWakeWordDetector extends EventEmitter<WakeWordEvents> {
  private isListening = false;
  private audioProcess: ChildProcess | null = null;
  private lastActivationTime = 0;
  private energyHistory: number[] = [];
  private readonly HISTORY_SIZE = 30;
  private readonly SPIKE_THRESHOLD = 2.5;
  private refractoryPeriodMs: number;

  constructor(refractoryPeriodMs = 2000) {
    super();
    this.refractoryPeriodMs = refractoryPeriodMs;
  }

  async start(): Promise<void> {
    if (this.isListening) {
      return;
    }

    // Start audio capture
    const args = ['-q', '-t', 'raw', '-b', '16', '-e', 'signed-integer', '-c', '1', '-r', '16000', '-'];

    try {
      this.audioProcess = spawn('rec', args, {
        stdio: ['ignore', 'pipe', 'ignore'],
      });
    } catch {
      this.audioProcess = spawn('sox', ['-d', ...args], {
        stdio: ['ignore', 'pipe', 'ignore'],
      });
    }

    this.audioProcess.stdout?.on('data', (chunk: Buffer) => {
      this.processAudio(chunk);
    });

    this.audioProcess.on('error', (error) => {
      this.emit('error', error);
    });

    this.isListening = true;
    this.emit('started');
    this.emit('listening', true);
  }

  stop(): void {
    if (this.audioProcess) {
      this.audioProcess.kill();
      this.audioProcess = null;
    }

    this.isListening = false;
    this.energyHistory = [];
    this.emit('stopped');
    this.emit('listening', false);
  }

  isActive(): boolean {
    return this.isListening;
  }

  private processAudio(chunk: Buffer): void {
    // Convert to samples
    const samples = new Int16Array(
      chunk.buffer.slice(chunk.byteOffset, chunk.byteOffset + chunk.byteLength)
    );

    // Calculate RMS energy
    let sumSquares = 0;
    for (let i = 0; i < samples.length; i++) {
      const normalized = samples[i] / 32768;
      sumSquares += normalized * normalized;
    }
    const energy = Math.sqrt(sumSquares / samples.length);

    // Update history
    this.energyHistory.push(energy);
    if (this.energyHistory.length > this.HISTORY_SIZE) {
      this.energyHistory.shift();
    }

    // Need enough history
    if (this.energyHistory.length < this.HISTORY_SIZE) {
      return;
    }

    // Calculate average and look for spike
    const avgEnergy =
      this.energyHistory.slice(0, -3).reduce((a, b) => a + b, 0) /
      (this.energyHistory.length - 3);

    const recentMax = Math.max(...this.energyHistory.slice(-3));

    // Check for energy spike
    if (recentMax > avgEnergy * this.SPIKE_THRESHOLD && avgEnergy > 0.005) {
      const now = Date.now();
      if (now - this.lastActivationTime < this.refractoryPeriodMs) {
        return;
      }

      this.lastActivationTime = now;
      this.emit('detected', {
        wakeWord: 'hey_jarvis',
        confidence: 0.6,
        timestamp: now / 1000,
      });
    }
  }
}
