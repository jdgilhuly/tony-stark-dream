import React, { useState, useEffect, useCallback } from 'react';
import { Box, Text, useInput, useApp } from 'ink';
import Spinner from 'ink-spinner';
import { NodeAudioRecorder } from '../audio/recorder.js';

type AudioRecorder = NodeAudioRecorder;

interface VoiceChatProps {
  serverUrl: string;
  tokens: { accessToken: string; refreshToken: string };
  onMessage?: (message: string) => void;
  onResponse?: (response: string) => void;
}

type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking' | 'error';

export function VoiceChat({ serverUrl, tokens, onMessage, onResponse }: VoiceChatProps) {
  const { exit } = useApp();
  const [state, setState] = useState<VoiceState>('idle');
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [recorder, setRecorder] = useState<AudioRecorder | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);

  useEffect(() => {
    const rec = new NodeAudioRecorder();
    setRecorder(rec);
    return () => {
      rec.stop();
    };
  }, []);

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

  const renderAudioLevel = () => {
    const bars = Math.round(audioLevel * 20);
    return '█'.repeat(bars) + '░'.repeat(20 - bars);
  };

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
            <Text> {renderAudioLevel()}</Text>
          </>
        )}
        {state === 'processing' && (
          <Text color="yellow">
            <Spinner type="dots" /> Processing...
          </Text>
        )}
        {state === 'speaking' && (
          <Text color="blue">
            <Spinner type="dots" /> Speaking...
          </Text>
        )}
        {state === 'error' && <Text color="red">Error: {error}</Text>}
      </Box>

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
