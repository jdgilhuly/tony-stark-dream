import React, { useState, useCallback, useEffect } from 'react';
import { Box, Text, useApp, useInput } from 'ink';
import TextInput from 'ink-text-input';
import Spinner from 'ink-spinner';
import { createApiClient, type AuthTokens } from '@jarvis/core';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface AppProps {
  serverUrl: string;
  tokens: AuthTokens;
}

export const App: React.FC<AppProps> = ({ serverUrl, tokens }) => {
  const { exit } = useApp();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  const client = React.useMemo(() => {
    const c = createApiClient({ baseUrl: serverUrl });
    c.setTokens(tokens);
    return c;
  }, [serverUrl, tokens]);

  // Initial greeting
  useEffect(() => {
    if (!isInitialized) {
      setIsInitialized(true);
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: 'Good day, sir. JARVIS at your service. How may I assist you today?',
          timestamp: new Date(),
        },
      ]);
    }
  }, [isInitialized]);

  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      exit();
    }
  });

  const handleSubmit = useCallback(async (value: string) => {
    if (!value.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: value,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await client.sendMessage({
        message: value,
        conversationId: conversationId ?? undefined,
      });

      if (response.success && response.data) {
        setConversationId(response.data.conversationId);
        setMessages((prev) => [
          ...prev,
          {
            id: response.data!.message.id,
            role: 'assistant',
            content: response.data!.message.content,
            timestamp: new Date(response.data!.message.timestamp),
          },
        ]);
      } else {
        setError(response.error?.message ?? 'Failed to get response');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  }, [client, conversationId, isLoading]);

  return (
    <Box flexDirection="column" padding={1}>
      {/* Header */}
      <Box marginBottom={1}>
        <Text bold color="cyan">
          ╔═══════════════════════════════════════════════════════════╗
        </Text>
      </Box>
      <Box marginBottom={1}>
        <Text bold color="cyan">
          ║  J.A.R.V.I.S. - Just A Rather Very Intelligent System     ║
        </Text>
      </Box>
      <Box marginBottom={1}>
        <Text bold color="cyan">
          ╚═══════════════════════════════════════════════════════════╝
        </Text>
      </Box>

      {/* Messages */}
      <Box flexDirection="column" marginBottom={1}>
        {messages.slice(-10).map((msg) => (
          <Box key={msg.id} marginBottom={1}>
            <Text color={msg.role === 'user' ? 'green' : 'blue'}>
              {msg.role === 'user' ? '> You: ' : '> JARVIS: '}
            </Text>
            <Text wrap="wrap">{msg.content}</Text>
          </Box>
        ))}
      </Box>

      {/* Loading indicator */}
      {isLoading && (
        <Box marginBottom={1}>
          <Text color="yellow">
            <Spinner type="dots" />
            {' JARVIS is thinking...'}
          </Text>
        </Box>
      )}

      {/* Error display */}
      {error && (
        <Box marginBottom={1}>
          <Text color="red">Error: {error}</Text>
        </Box>
      )}

      {/* Input */}
      <Box>
        <Text color="green">{`> `}</Text>
        <TextInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          placeholder="Type your message..."
        />
      </Box>

      {/* Help text */}
      <Box marginTop={1}>
        <Text dimColor>Press Ctrl+C to exit</Text>
      </Box>
    </Box>
  );
};
