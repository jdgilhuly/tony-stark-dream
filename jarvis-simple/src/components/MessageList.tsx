import React from 'react';
import { Box, Text } from 'ink';
import type { Message } from '../types.js';

interface MessageListProps {
  messages: Message[];
  maxDisplay?: number;
}

export function MessageList({ messages, maxDisplay = 20 }: MessageListProps) {
  const displayMessages = messages.slice(-maxDisplay);

  return (
    <Box flexDirection="column" marginBottom={1}>
      {displayMessages.map((msg) => (
        <Box key={msg.id} flexDirection="column" marginBottom={1}>
          <Box>
            <Text bold color={msg.role === 'user' ? 'cyan' : 'yellow'}>
              {msg.role === 'user' ? 'You' : 'JARVIS'}
              {msg.voiceInput && ' (voice)'}:
            </Text>
          </Box>
          <Box marginLeft={2}>
            <Text>{msg.content}</Text>
          </Box>
        </Box>
      ))}
    </Box>
  );
}
