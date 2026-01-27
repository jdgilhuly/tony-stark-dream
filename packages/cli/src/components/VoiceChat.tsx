import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Box, Text, useInput, useApp } from 'ink';
import Spinner from 'ink-spinner';
import type { AudioRecorderAdapter } from '@jarvis/core';
import { NodeAudioRecorder } from '../audio/recorder.js';
import { VoiceActivityDetector } from '../audio/vad.js';

// Convert raw PCM to WAV format
function pcmToWav(pcmData: ArrayBuffer, sampleRate: number = 16000, channels: number = 1, bitsPerSample: number = 16): ArrayBuffer {
  const byteRate = sampleRate * channels * (bitsPerSample / 8);
  const blockAlign = channels * (bitsPerSample / 8);
  const dataSize = pcmData.byteLength;
  const headerSize = 44;
  const totalSize = headerSize + dataSize;

  const buffer = new ArrayBuffer(totalSize);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, totalSize - 8, true);
  writeString(view, 8, 'WAVE');

  // fmt chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // chunk size
  view.setUint16(20, 1, true); // audio format (PCM)
  view.setUint16(22, channels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);

  // data chunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataSize, true);

  // Copy PCM data
  new Uint8Array(buffer, headerSize).set(new Uint8Array(pcmData));

  return buffer;
}

function writeString(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

interface VoiceChatProps {
  serverUrl: string;
  tokens: { accessToken: string; refreshToken: string };
  onMessage?: (message: string) => void;
  onResponse?: (response: string) => void;
  recorder?: AudioRecorderAdapter;
}

type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error';

export function VoiceChat({ serverUrl, tokens, onMessage, onResponse, recorder: injectedRecorder }: VoiceChatProps) {
  const { exit } = useApp();
  const [state, setState] = useState<VoiceState>('idle');
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [recorder, setRecorder] = useState<AudioRecorderAdapter | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [partialTranscript, setPartialTranscript] = useState('');
  const [vad] = useState(() => new VoiceActivityDetector());

  useEffect(() => {
    // Use injected recorder if provided, otherwise create a new one
    const rec = injectedRecorder ?? new NodeAudioRecorder();
    setRecorder(rec);

    // Set up VAD level callback
    vad.on('level', (level) => {
      setAudioLevel(level);
    });

    return () => {
      rec.stop();
    };
  }, [vad, injectedRecorder]);

  const startListening = useCallback(async () => {
    if (!recorder) return;

    setState('listening');
    setTranscript('');
    setResponse('');
    setError(null);

    try {
      await recorder.start();
      // Recording is now active - user must press SPACE again to stop
    } catch (err) {
      setState('error');
      setError(err instanceof Error ? err.message : 'Failed to start recording');
    }
  }, [recorder]);

  const stopListening = useCallback(async () => {
    if (!recorder) return;

    try {
      // Stop recording and get the audio data
      const audioData = await recorder.stop();

      if (audioData.byteLength === 0) {
        throw new Error('No audio recorded');
      }

      setState('processing');

      // Convert raw PCM to WAV format using recorder's actual sample rate
      const sampleRate = recorder.getSampleRate?.() ?? 48000;
      const wavData = pcmToWav(audioData, sampleRate, 1, 16);

      // Debug: show audio info
      const durationSecs = audioData.byteLength / (sampleRate * 2); // 16-bit = 2 bytes per sample
      console.log(`[DEBUG] Audio: ${audioData.byteLength} bytes, ${sampleRate}Hz, ~${durationSecs.toFixed(1)}s`);

      // Send audio to voice processing service for transcription
      const formData = new FormData();
      formData.append('audio', new Blob([wavData], { type: 'audio/wav' }), 'recording.wav');

      const transcribeResponse = await fetch(`${serverUrl}/voice/transcribe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.accessToken}`,
        },
        body: formData,
      });

      if (!transcribeResponse.ok) {
        const errorBody = await transcribeResponse.text();
        throw new Error(`Transcription failed: ${transcribeResponse.status} - ${errorBody}`);
      }

      const transcribeData = await transcribeResponse.json() as { text: string };
      const text = transcribeData.text || '';

      if (!text.trim()) {
        throw new Error('No speech detected - please speak clearly and try again');
      }

      setTranscript(text);
      onMessage?.(text);

      // Send to conversation service
      const chatResponse = await fetch(`${serverUrl}/conversation/message`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: text }),
      });

      if (!chatResponse.ok) {
        const errorBody = await chatResponse.text();
        throw new Error(`Conversation failed: ${chatResponse.status} - ${errorBody}`);
      }

      const chatData = await chatResponse.json() as {
        success: boolean;
        data: { message: { content: string } };
      };
      const jarvisResponse = chatData.data.message.content;
      setResponse(jarvisResponse);
      onResponse?.(jarvisResponse);

      // Text-to-speech
      setState('speaking');
      const ttsResponse = await fetch(`${serverUrl}/voice/synthesize`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: jarvisResponse }),
      });

      if (ttsResponse.ok) {
        // In a full implementation, this would play the audio
        // For now, we just display the response
      }

      setState('idle');
    } catch (err) {
      setState('error');
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [recorder, serverUrl, tokens, onMessage, onResponse]);

  useInput((input, key) => {
    if (key.escape) {
      exit();
    } else if (input === ' ' || key.return) {
      if (state === 'idle' || state === 'error') {
        startListening();
      } else if (state === 'listening') {
        stopListening();
      }
    }
  });

  const renderAudioLevel = useMemo(() => {
    const totalBars = 20;
    const filledBars = Math.round(audioLevel * totalBars);
    const emptyBars = totalBars - filledBars;

    // Color-coded level indicator
    let color: string;
    if (audioLevel < 0.3) {
      color = 'green';
    } else if (audioLevel < 0.7) {
      color = 'yellow';
    } else {
      color = 'red';
    }

    return { bars: '█'.repeat(filledBars) + '░'.repeat(emptyBars), color };
  }, [audioLevel]);

  const renderWaveform = useMemo(() => {
    // Create a simple waveform visualization
    const chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
    const level = Math.min(1, audioLevel);
    const idx = Math.floor(level * (chars.length - 1));
    return chars[idx];
  }, [audioLevel]);

  return (
    <Box flexDirection="column" padding={1}>
      <Box marginBottom={1}>
        <Text bold color="cyan">
          ╔══════════════════════════════════════════════════════════════╗
        </Text>
      </Box>
      <Box>
        <Text bold color="cyan">
          ║  J.A.R.V.I.S. Voice Interface                                ║
        </Text>
      </Box>
      <Box marginBottom={1}>
        <Text bold color="cyan">
          ╚══════════════════════════════════════════════════════════════╝
        </Text>
      </Box>

      <Box marginBottom={1}>
        <Text dimColor>
          Press SPACE to {state === 'listening' ? 'stop' : 'start'} speaking, ESC to exit
        </Text>
      </Box>

      <Box marginBottom={1}>
        <Text>Status: </Text>
        {state === 'idle' && <Text color="gray">Ready</Text>}
        {state === 'listening' && (
          <>
            <Text color="green">
              <Spinner type="dots" /> Listening...
            </Text>
            <Text color={renderAudioLevel.color as any}> {renderAudioLevel.bars}</Text>
            <Text> {renderWaveform}</Text>
          </>
        )}
        {state === 'processing' && (
          <Text color="yellow">
            <Spinner type="dots" /> Processing...
          </Text>
        )}
        {state === 'speaking' && (
          <>
            <Text color="blue">
              <Spinner type="dots" /> Speaking...
            </Text>
            <Text dimColor> (Press SPACE to interrupt)</Text>
          </>
        )}
        {state === 'error' && <Text color="red">Error: {error}</Text>}
      </Box>

      {partialTranscript && state === 'listening' && (
        <Box marginBottom={1}>
          <Text dimColor italic>Hearing: {partialTranscript}</Text>
        </Box>
      )}

      {transcript && (
        <Box marginBottom={1}>
          <Text bold>You: </Text>
          <Text>{transcript}</Text>
        </Box>
      )}

      {response && (
        <Box>
          <Text bold color="cyan">JARVIS: </Text>
          <Text>{response}</Text>
        </Box>
      )}
    </Box>
  );
}
