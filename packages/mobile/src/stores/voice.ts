import { create } from 'zustand';
import AudioRecorderPlayer from 'react-native-audio-recorder-player';
import { apiClient } from '../services/api';

interface VoiceState {
  isListening: boolean;
  isProcessing: boolean;
  isSpeaking: boolean;
  transcript: string | null;
  audioLevel: number;
  error: string | null;

  startListening: () => Promise<void>;
  stopListening: () => Promise<void>;
  speak: (text: string) => Promise<void>;
  stopSpeaking: () => void;
}

const audioRecorderPlayer = new AudioRecorderPlayer();

export const useVoiceStore = create<VoiceState>((set, get) => ({
  isListening: false,
  isProcessing: false,
  isSpeaking: false,
  transcript: null,
  audioLevel: 0,
  error: null,

  startListening: async () => {
    try {
      set({ isListening: true, transcript: null, error: null });

      // Start recording
      const path = await audioRecorderPlayer.startRecorder();

      // Monitor audio level
      audioRecorderPlayer.addRecordBackListener((e) => {
        const level = e.currentMetering ? Math.abs(e.currentMetering) / 160 : 0;
        set({ audioLevel: Math.min(1, level) });
      });

      console.log('Recording started:', path);
    } catch (error: any) {
      set({
        isListening: false,
        error: error.message || 'Failed to start recording',
      });
    }
  },

  stopListening: async () => {
    try {
      set({ isListening: false, isProcessing: true });

      // Stop recording
      const audioPath = await audioRecorderPlayer.stopRecorder();
      audioRecorderPlayer.removeRecordBackListener();

      // Send audio for transcription
      const formData = new FormData();
      formData.append('audio', {
        uri: audioPath,
        type: 'audio/wav',
        name: 'recording.wav',
      } as any);

      const response = await apiClient.post('/voice/transcribe', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const { text } = response.data;

      set({
        isProcessing: false,
        transcript: text,
      });
    } catch (error: any) {
      set({
        isProcessing: false,
        error: error.message || 'Transcription failed',
      });
    }
  },

  speak: async (text: string) => {
    try {
      set({ isSpeaking: true, error: null });

      // Get synthesized audio from server
      const response = await apiClient.post(
        '/voice/synthesize',
        { text },
        { responseType: 'blob' }
      );

      // Play the audio
      // Note: In a real implementation, we'd need to save the blob
      // to a file and play it with AudioRecorderPlayer
      const audioBlob = response.data;
      const audioPath = `${Date.now()}.mp3`;

      // For now, use TTS library as fallback
      // In production, this would play the server-generated audio
      const Tts = require('react-native-tts').default;
      await Tts.speak(text, {
        iosVoiceId: 'com.apple.ttsbundle.Daniel-compact',
        rate: 0.5,
        pitch: 1.0,
      });

      set({ isSpeaking: false });
    } catch (error: any) {
      // Fallback to local TTS
      try {
        const Tts = require('react-native-tts').default;
        await Tts.speak(text);
      } catch (ttsError) {
        console.error('TTS fallback failed:', ttsError);
      }

      set({
        isSpeaking: false,
        error: error.message || 'Speech synthesis failed',
      });
    }
  },

  stopSpeaking: () => {
    try {
      const Tts = require('react-native-tts').default;
      Tts.stop();
      set({ isSpeaking: false });
    } catch (error) {
      console.error('Failed to stop speaking:', error);
    }
  },
}));
