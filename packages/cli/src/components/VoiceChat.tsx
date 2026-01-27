import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Box, Text, useInput, useApp } from 'ink';
import Spinner from 'ink-spinner';
import type { AudioRecorderAdapter } from '@jarvis/core';
import { NodeAudioRecorder } from '../audio/recorder.js';
import { VoiceActivityDetector } from '../audio/vad.js';

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
      // Wait for user to stop recording
      const audioData = await recorder.stop();

      setState('processing');

      // Send audio to voice processing service for transcription
      const formData = new FormData();
      formData.append('audio', new Blob([audioData], { type: 'audio/wav' }));

      const transcribeResponse = await fetch(`${serverUrl}/api/voice/transcribe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.accessToken}`,
        },
        body: formData,
      });

      if (!transcribeResponse.ok) {
        throw new Error('Transcription failed');
      }

      const transcribeData = await transcribeResponse.json() as { text: string };
      setTranscript(transcribeData.text);
      const text = transcribeData.text;
      onMessage?.(text);

      // Send to conversation service
      const chatResponse = await fetch(`${serverUrl}/api/conversation/message`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: text }),
      });

      if (!chatResponse.ok) {
        throw new Error('Conversation failed');
      }

      const chatData = await chatResponse.json() as { response: string };
      const jarvisResponse = chatData.response;
      setResponse(jarvisResponse);
      onResponse?.(jarvisResponse);

      // Text-to-speech
      setState('speaking');
      const ttsResponse = await fetch(`${serverUrl}/api/voice/synthesize`, {
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

  const stopListening = useCallback(() => {
    recorder?.stop();
    setState('processing');
  }, [recorder]);

  useInput((input, key) => {
    if (key.escape) {
      exit();
    } else if (input === ' ' || key.return) {
      if (state === 'idle') {
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
