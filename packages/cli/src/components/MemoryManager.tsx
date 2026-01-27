import React, { useState, useEffect, useCallback } from 'react';
import { Box, Text, useInput } from 'ink';
import Spinner from 'ink-spinner';
import axios from 'axios';

interface MemoryManagerProps {
  serverUrl: string;
  tokens: { accessToken: string; refreshToken: string };
  mode: 'remember' | 'recall';
  content?: string;  // For remember mode
  query?: string;    // For recall mode
  options?: {
    memoryType?: string;
    importance?: number;
    limit?: number;
  };
  onComplete?: (result: any) => void;
  onError?: (error: Error) => void;
}

interface Memory {
  id: string;
  content: string;
  memory_type: string;
  importance: number;
  created_at: string;
  relevance?: number;
}

export const MemoryManager: React.FC<MemoryManagerProps> = ({
  serverUrl,
  tokens,
  mode,
  content,
  query,
  options = {},
  onComplete,
  onError,
}) => {
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');
  const [memories, setMemories] = useState<Memory[]>([]);
  const [storedMemory, setStoredMemory] = useState<Memory | null>(null);
  const [error, setError] = useState<string | null>(null);

  const storeMemory = useCallback(async () => {
    if (!content) return;

    setStatus('loading');
    try {
      const response = await axios.post(
        `${serverUrl}/memory/store`,
        {
          content,
          memory_type: options.memoryType || 'fact',
          importance: options.importance || 0.5,
        },
        {
          headers: {
            Authorization: `Bearer ${tokens.accessToken}`,
            'Content-Type': 'application/json',
          },
          timeout: 30000,
        }
      );

      setStoredMemory(response.data.data || response.data);
      setStatus('done');
      onComplete?.(response.data);
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.message);
      setStatus('error');
      onError?.(err);
    }
  }, [serverUrl, tokens, content, options, onComplete, onError]);

  const recallMemories = useCallback(async () => {
    if (!query) return;

    setStatus('loading');
    try {
      const response = await axios.get(
        `${serverUrl}/memory/recall`,
        {
          params: {
            query,
            limit: options.limit || 5,
          },
          headers: {
            Authorization: `Bearer ${tokens.accessToken}`,
          },
          timeout: 30000,
        }
      );

      const results = response.data.data?.memories || response.data.memories || [];
      setMemories(results);
      setStatus('done');
      onComplete?.(results);
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.message);
      setStatus('error');
      onError?.(err);
    }
  }, [serverUrl, tokens, query, options, onComplete, onError]);

  useEffect(() => {
    if (mode === 'remember') {
      storeMemory();
    } else {
      recallMemories();
    }
  }, [mode, storeMemory, recallMemories]);

  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  const getImportanceColor = (importance: number): string => {
    if (importance >= 0.8) return 'red';
    if (importance >= 0.6) return 'yellow';
    if (importance >= 0.4) return 'cyan';
    return 'gray';
  };

  if (status === 'loading') {
    return (
      <Box padding={1}>
        <Spinner type="dots" />
        <Text> {mode === 'remember' ? 'Storing memory...' : 'Searching memories...'}</Text>
      </Box>
    );
  }

  if (status === 'error') {
    return (
      <Box flexDirection="column" padding={1}>
        <Text color="red" bold>Error:</Text>
        <Text color="red">{error}</Text>
        <Box marginTop={1}>
          <Text color="gray" dimColor>Press Ctrl+C to exit</Text>
        </Box>
      </Box>
    );
  }

  if (mode === 'remember' && storedMemory) {
    return (
      <Box flexDirection="column" padding={1}>
        <Text color="green" bold>✓ Memory Stored</Text>
        <Box marginTop={1} flexDirection="column">
          <Text color="gray">ID: {storedMemory.id}</Text>
          <Text color="gray">Type: {storedMemory.memory_type}</Text>
          <Text color="gray">Content: {storedMemory.content}</Text>
        </Box>
        <Box marginTop={1}>
          <Text color="gray" dimColor>Press Ctrl+C to exit</Text>
        </Box>
      </Box>
    );
  }

  if (mode === 'recall') {
    return (
      <Box flexDirection="column" padding={1}>
        <Text bold color="yellow">JARVIS Memory Recall</Text>
        <Box marginTop={1}>
          <Text color="gray">Query: "{query}"</Text>
        </Box>

        {memories.length === 0 ? (
          <Box marginTop={1}>
            <Text color="gray">No memories found matching your query.</Text>
          </Box>
        ) : (
          <Box marginTop={1} flexDirection="column">
            <Text color="cyan">{memories.length} memories found:</Text>

            {memories.map((memory, index) => (
              <Box
                key={memory.id}
                marginTop={1}
                flexDirection="column"
                borderStyle="round"
                borderColor="gray"
                paddingX={1}
              >
                <Box>
                  <Text color="gray">{index + 1}. </Text>
                  <Text color={getImportanceColor(memory.importance)}>
                    [{memory.memory_type}]
                  </Text>
                  {memory.relevance && (
                    <Text color="green"> {Math.round(memory.relevance * 100)}% match</Text>
                  )}
                </Box>
                <Box paddingLeft={2} marginTop={1}>
                  <Text>{memory.content}</Text>
                </Box>
                <Box paddingLeft={2}>
                  <Text color="gray" dimColor>
                    {formatDate(memory.created_at)} | Importance: {memory.importance}
                  </Text>
                </Box>
              </Box>
            ))}
          </Box>
        )}

        <Box marginTop={2}>
          <Text color="gray" dimColor>Press Ctrl+C to exit</Text>
        </Box>
      </Box>
    );
  }

  return null;
};
