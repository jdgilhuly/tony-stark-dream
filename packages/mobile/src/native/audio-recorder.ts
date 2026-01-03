/**
 * React Native Audio Recorder Implementation
 * Provides voice recording capabilities for JARVIS mobile app
 */

import AudioRecorderPlayer, {
  AudioEncoderAndroidType,
  AudioSourceAndroidType,
  AVEncoderAudioQualityIOSType,
  AVEncodingOption,
  OutputFormatAndroidType,
} from 'react-native-audio-recorder-player';
import { Platform, PermissionsAndroid } from 'react-native';
import { check, request, PERMISSIONS, RESULTS } from 'react-native-permissions';

export interface RecordingOptions {
  sampleRate?: number;
  channels?: number;
  bitRate?: number;
  onProgress?: (currentPosition: number, currentMetering?: number) => void;
}

export interface RecordingResult {
  path: string;
  duration: number;
}

class NativeAudioRecorder {
  private recorder: AudioRecorderPlayer;
  private isRecording: boolean = false;
  private recordingPath: string | null = null;

  constructor() {
    this.recorder = new AudioRecorderPlayer();
    this.recorder.setSubscriptionDuration(0.1); // 100ms updates
  }

  async checkPermissions(): Promise<boolean> {
    if (Platform.OS === 'android') {
      const granted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
        {
          title: 'JARVIS Microphone Permission',
          message: 'JARVIS needs access to your microphone for voice commands.',
          buttonNeutral: 'Ask Me Later',
          buttonNegative: 'Cancel',
          buttonPositive: 'OK',
        }
      );
      return granted === PermissionsAndroid.RESULTS.GRANTED;
    } else {
      const result = await check(PERMISSIONS.IOS.MICROPHONE);
      if (result === RESULTS.GRANTED) {
        return true;
      }
      if (result === RESULTS.DENIED) {
        const requestResult = await request(PERMISSIONS.IOS.MICROPHONE);
        return requestResult === RESULTS.GRANTED;
      }
      return false;
    }
  }

  async startRecording(options: RecordingOptions = {}): Promise<void> {
    const hasPermission = await this.checkPermissions();
    if (!hasPermission) {
      throw new Error('Microphone permission denied');
    }

    if (this.isRecording) {
      await this.stopRecording();
    }

    const {
      sampleRate = 16000,
      channels = 1,
      bitRate = 128000,
      onProgress,
    } = options;

    // Configure recording settings
    const audioSet = {
      AudioEncoderAndroid: AudioEncoderAndroidType.AAC,
      AudioSourceAndroid: AudioSourceAndroidType.MIC,
      AVEncoderAudioQualityKeyIOS: AVEncoderAudioQualityIOSType.high,
      AVNumberOfChannelsKeyIOS: channels,
      AVFormatIDKeyIOS: AVEncodingOption.aac,
      OutputFormatAndroid: OutputFormatAndroidType.AAC_ADTS,
      AudioSamplingRateAndroid: sampleRate,
      AudioBitRateAndroid: bitRate,
    };

    // Add progress listener
    if (onProgress) {
      this.recorder.addRecordBackListener((e) => {
        onProgress(e.currentPosition, e.currentMetering);
      });
    }

    // Start recording
    const path = await this.recorder.startRecorder(undefined, audioSet, true);
    this.recordingPath = path;
    this.isRecording = true;

    console.log('Recording started:', path);
  }

  async stopRecording(): Promise<RecordingResult> {
    if (!this.isRecording) {
      throw new Error('No active recording');
    }

    const result = await this.recorder.stopRecorder();
    this.recorder.removeRecordBackListener();
    this.isRecording = false;

    const duration = await this.getRecordingDuration();

    console.log('Recording stopped:', result);

    return {
      path: result,
      duration,
    };
  }

  async cancelRecording(): Promise<void> {
    if (this.isRecording) {
      await this.recorder.stopRecorder();
      this.recorder.removeRecordBackListener();
      this.isRecording = false;
      this.recordingPath = null;
    }
  }

  private async getRecordingDuration(): Promise<number> {
    // Duration is tracked during recording
    return 0; // Will be updated by progress callback
  }

  getIsRecording(): boolean {
    return this.isRecording;
  }

  getRecordingPath(): string | null {
    return this.recordingPath;
  }
}

// Audio Player for playback
class NativeAudioPlayer {
  private player: AudioRecorderPlayer;
  private isPlaying: boolean = false;

  constructor() {
    this.player = new AudioRecorderPlayer();
  }

  async play(
    path: string,
    onProgress?: (currentPosition: number, duration: number) => void,
    onFinished?: () => void
  ): Promise<void> {
    if (this.isPlaying) {
      await this.stop();
    }

    if (onProgress) {
      this.player.addPlayBackListener((e) => {
        onProgress(e.currentPosition, e.duration);

        if (e.currentPosition >= e.duration) {
          this.stop();
          onFinished?.();
        }
      });
    }

    await this.player.startPlayer(path);
    this.isPlaying = true;
  }

  async pause(): Promise<void> {
    if (this.isPlaying) {
      await this.player.pausePlayer();
    }
  }

  async resume(): Promise<void> {
    await this.player.resumePlayer();
  }

  async stop(): Promise<void> {
    if (this.isPlaying) {
      await this.player.stopPlayer();
      this.player.removePlayBackListener();
      this.isPlaying = false;
    }
  }

  async seekTo(position: number): Promise<void> {
    await this.player.seekToPlayer(position);
  }

  async setVolume(volume: number): Promise<void> {
    await this.player.setVolume(Math.max(0, Math.min(1, volume)));
  }

  getIsPlaying(): boolean {
    return this.isPlaying;
  }
}

// Singleton instances
export const audioRecorder = new NativeAudioRecorder();
export const audioPlayer = new NativeAudioPlayer();

// Helper function to convert audio file to base64 for API upload
export async function getAudioBase64(path: string): Promise<string> {
  const RNFS = require('react-native-fs');
  const base64 = await RNFS.readFile(path, 'base64');
  return base64;
}

// Helper to create FormData for audio upload
export function createAudioFormData(path: string, filename: string = 'audio.aac'): FormData {
  const formData = new FormData();
  formData.append('audio', {
    uri: Platform.OS === 'android' ? path : path.replace('file://', ''),
    type: 'audio/aac',
    name: filename,
  } as any);
  return formData;
}
