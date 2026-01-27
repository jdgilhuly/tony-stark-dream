import React from 'react';
import { Box, Text } from 'ink';
import type { VoiceState } from '../types.js';

interface VoiceIndicatorProps {
  state: VoiceState;
  voiceEnabled: boolean;
}

export function VoiceIndicator({ state, voiceEnabled }: VoiceIndicatorProps) {
  if (!voiceEnabled) return null;

  const getStatusText = () => {
    switch (state) {
      case 'recording':
        return { text: 'Recording... (release Space to stop)', color: 'red' as const };
      case 'transcribing':
        return { text: 'Transcribing...', color: 'yellow' as const };
      case 'speaking':
        return { text: 'Speaking...', color: 'green' as const };
      default:
        return { text: 'Voice ready (hold Space to talk)', color: 'gray' as const };
    }
  };

  const status = getStatusText();

  return (
    <Box marginBottom={1}>
      <Text color={status.color}>[Voice] {status.text}</Text>
    </Box>
  );
}
