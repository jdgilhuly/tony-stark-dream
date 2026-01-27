/**
 * Latency Tracker
 * Measures and tracks latency across the voice pipeline
 */

export interface LatencyMetrics {
  stt: number;
  conversation: number;
  tts: number;
  total: number;
  timeToFirstByte: number;
}

export interface LatencyStatistics {
  avgTotal: number;
  minTotal: number;
  maxTotal: number;
  cycleCount: number;
  avgStt: number;
  avgConversation: number;
  avgTts: number;
}

type Phase = 'stt' | 'conversation' | 'tts';

type EventCallback<T = void> = T extends void ? () => void : (data: T) => void;

interface EventMap {
  latencyWarning: LatencyMetrics;
  cycleComplete: LatencyMetrics;
}

export class LatencyTracker {
  private phaseStartTimes: Map<Phase, number> = new Map();
  private currentMetrics: LatencyMetrics = this.createEmptyMetrics();
  private cycleStartTime: number | null = null;
  private history: LatencyMetrics[] = [];
  private targetLatency = 500; // Default 500ms target
  private eventListeners: Map<keyof EventMap, Set<EventCallback<any>>> = new Map();

  on<K extends keyof EventMap>(event: K, callback: EventCallback<EventMap[K]>): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);
  }

  off<K extends keyof EventMap>(event: K, callback: EventCallback<EventMap[K]>): void {
    this.eventListeners.get(event)?.delete(callback);
  }

  private emit<K extends keyof EventMap>(event: K, data: EventMap[K]): void {
    this.eventListeners.get(event)?.forEach((callback) => {
      (callback as EventCallback<EventMap[K]>)(data);
    });
  }

  private createEmptyMetrics(): LatencyMetrics {
    return {
      stt: 0,
      conversation: 0,
      tts: 0,
      total: 0,
      timeToFirstByte: 0,
    };
  }

  startPhase(phase: Phase): void {
    this.phaseStartTimes.set(phase, Date.now());
  }

  endPhase(phase: Phase): void {
    const startTime = this.phaseStartTimes.get(phase);
    if (startTime) {
      const duration = Date.now() - startTime;
      this.currentMetrics[phase] = duration;
      this.phaseStartTimes.delete(phase);
    }
  }

  startCycle(): void {
    this.cycleStartTime = Date.now();
    this.currentMetrics = this.createEmptyMetrics();
  }

  endCycle(): void {
    if (this.cycleStartTime) {
      this.currentMetrics.total = Date.now() - this.cycleStartTime;
      this.history.push({ ...this.currentMetrics });

      this.emit('cycleComplete', this.currentMetrics);

      if (this.currentMetrics.total > this.targetLatency) {
        this.emit('latencyWarning', this.currentMetrics);
      }

      this.cycleStartTime = null;
    }
  }

  markFirstByte(): void {
    if (this.cycleStartTime) {
      this.currentMetrics.timeToFirstByte = Date.now() - this.cycleStartTime;
    }
  }

  getMetrics(): LatencyMetrics {
    return { ...this.currentMetrics };
  }

  getStatistics(): LatencyStatistics {
    if (this.history.length === 0) {
      return {
        avgTotal: 0,
        minTotal: 0,
        maxTotal: 0,
        cycleCount: 0,
        avgStt: 0,
        avgConversation: 0,
        avgTts: 0,
      };
    }

    const totals = this.history.map((m) => m.total);
    const sttValues = this.history.map((m) => m.stt);
    const convValues = this.history.map((m) => m.conversation);
    const ttsValues = this.history.map((m) => m.tts);

    return {
      avgTotal: this.average(totals),
      minTotal: Math.min(...totals),
      maxTotal: Math.max(...totals),
      cycleCount: this.history.length,
      avgStt: this.average(sttValues),
      avgConversation: this.average(convValues),
      avgTts: this.average(ttsValues),
    };
  }

  private average(values: number[]): number {
    if (values.length === 0) return 0;
    return values.reduce((a, b) => a + b, 0) / values.length;
  }

  setTargetLatency(ms: number): void {
    this.targetLatency = ms;
  }

  isUnderTarget(): boolean {
    if (this.history.length === 0) return true;
    const latest = this.history[this.history.length - 1];
    return latest.total <= this.targetLatency;
  }

  reset(): void {
    this.history = [];
    this.currentMetrics = this.createEmptyMetrics();
    this.cycleStartTime = null;
    this.phaseStartTimes.clear();
  }
}
