/**
 * Voice Activity Detection (VAD)
 * Detects when speech starts and ends in audio streams
 */

export interface VADConfig {
  energyThreshold: number;
  silenceDurationMs: number;
  speechMinDurationMs: number;
  sampleRate: number;
}

export interface VADEvent {
  type: 'speechStart' | 'speechEnd' | 'silence' | 'level';
  timestamp: number;
  level?: number;
}

type EventCallback<T = void> = T extends void ? () => void : (data: T) => void;

interface EventMap {
  speechStart: void;
  speechEnd: void;
  silence: void;
  level: number;
}

const DEFAULT_CONFIG: VADConfig = {
  energyThreshold: 0.01,
  silenceDurationMs: 500,
  speechMinDurationMs: 100,
  sampleRate: 16000,
};

export class VoiceActivityDetector {
  private config: VADConfig;
  private speaking = false;
  private speechStartTime: number | null = null;
  private silenceStartTime: number | null = null;
  private currentLevel = 0;
  private eventListeners: Map<keyof EventMap, Set<EventCallback<any>>> = new Map();

  constructor(config: Partial<VADConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  on<K extends keyof EventMap>(event: K, callback: EventCallback<EventMap[K]>): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);
  }

  off<K extends keyof EventMap>(event: K, callback: EventCallback<EventMap[K]>): void {
    this.eventListeners.get(event)?.delete(callback);
  }

  private emit<K extends keyof EventMap>(event: K, data?: EventMap[K]): void {
    this.eventListeners.get(event)?.forEach((callback) => {
      if (data !== undefined) {
        (callback as EventCallback<EventMap[K]>)(data);
      } else {
        (callback as EventCallback<void>)();
      }
    });
  }

  processAudio(audioData: ArrayBuffer): void {
    const energy = this.calculateEnergy(audioData);
    this.currentLevel = Math.min(1, energy * 10); // Normalize to 0-1 range

    this.emit('level', this.currentLevel);

    const now = Date.now();
    const isSpeechEnergy = energy >= this.config.energyThreshold;

    if (isSpeechEnergy) {
      // Potential speech detected
      this.silenceStartTime = null;

      if (!this.speaking) {
        if (this.speechStartTime === null) {
          this.speechStartTime = now;
        } else if (now - this.speechStartTime >= this.config.speechMinDurationMs) {
          // Speech confirmed after minimum duration
          this.speaking = true;
          this.emit('speechStart');
        }
      }
    } else {
      // Silence detected
      this.speechStartTime = null;

      if (this.speaking) {
        if (this.silenceStartTime === null) {
          this.silenceStartTime = now;
        } else if (now - this.silenceStartTime >= this.config.silenceDurationMs) {
          // End of speech confirmed after silence duration
          this.speaking = false;
          this.silenceStartTime = null;
          this.emit('speechEnd');
        }
      } else {
        this.emit('silence');
      }
    }
  }

  calculateEnergy(audioData: ArrayBuffer): number {
    const samples = new Int16Array(audioData);

    if (samples.length === 0) {
      return 0;
    }

    // Calculate RMS (Root Mean Square) energy
    let sumSquares = 0;
    for (let i = 0; i < samples.length; i++) {
      const normalized = samples[i] / 32768; // Normalize to -1 to 1 range
      sumSquares += normalized * normalized;
    }

    return Math.sqrt(sumSquares / samples.length);
  }

  isSpeaking(): boolean {
    return this.speaking;
  }

  getAudioLevel(): number {
    return this.currentLevel;
  }

  getConfig(): VADConfig {
    return { ...this.config };
  }

  setEnergyThreshold(threshold: number): void {
    this.config.energyThreshold = threshold;
  }

  setSilenceDuration(durationMs: number): void {
    this.config.silenceDurationMs = durationMs;
  }

  reset(): void {
    this.speaking = false;
    this.speechStartTime = null;
    this.silenceStartTime = null;
    this.currentLevel = 0;
  }
}
