import React, { useState, useEffect, useCallback } from 'react';
import { Box, Text } from 'ink';
import Spinner from 'ink-spinner';
import axios from 'axios';

interface ResearchViewerProps {
  serverUrl: string;
  tokens: { accessToken: string; refreshToken: string };
  topic: string;
  depth?: 'shallow' | 'moderate' | 'deep';
  includeSources?: boolean;
  saveToMemory?: boolean;
  onComplete?: (result: any) => void;
  onError?: (error: Error) => void;
}

interface Source {
  url: string;
  title: string;
  snippet?: string;
}

interface ResearchResult {
  topic: string;
  summary: string;
  key_findings: string[];
  sources: Source[];
  timestamp: string;
}

export const ResearchViewer: React.FC<ResearchViewerProps> = ({
  serverUrl,
  tokens,
  topic,
  depth = 'moderate',
  includeSources = true,
  saveToMemory = true,
  onComplete,
  onError,
}) => {
  const [status, setStatus] = useState<'idle' | 'searching' | 'extracting' | 'synthesizing' | 'done' | 'error'>('idle');
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [startTime, setStartTime] = useState<number>(0);
  const [elapsed, setElapsed] = useState<number>(0);

  const conductResearch = useCallback(async () => {
    setStatus('searching');
    setStartTime(Date.now());

    try {
      const response = await axios.post(
        `${serverUrl}/research/research`,
        {
          topic,
          depth,
          include_sources: includeSources,
          save_to_memory: saveToMemory,
        },
        {
          headers: {
            Authorization: `Bearer ${tokens.accessToken}`,
            'Content-Type': 'application/json',
          },
          timeout: 300000, // 5 min timeout for research
        }
      );

      const researchResult = response.data.data || response.data;
      setResult(researchResult);
      setStatus('done');
      onComplete?.(researchResult);
    } catch (err: any) {
      setError(err.response?.data?.error?.message || err.message);
      setStatus('error');
      onError?.(err);
    }
  }, [serverUrl, tokens, topic, depth, includeSources, saveToMemory, onComplete, onError]);

  useEffect(() => {
    conductResearch();
  }, [conductResearch]);

  useEffect(() => {
    if (status !== 'done' && status !== 'error') {
      const interval = setInterval(() => {
        setElapsed(Date.now() - startTime);

        // Update status phases based on elapsed time
        if (elapsed > 2000 && status === 'searching') {
          setStatus('extracting');
        } else if (elapsed > 10000 && status === 'extracting') {
          setStatus('synthesizing');
        }
      }, 100);
      return () => clearInterval(interval);
    }
  }, [status, startTime, elapsed]);

  const formatElapsed = (ms: number): string => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${seconds}.${Math.floor((ms % 1000) / 100)}s`;
  };

  const getDepthLabel = (): string => {
    switch (depth) {
      case 'shallow': return '3 sources';
      case 'deep': return '10 sources';
      default: return '5 sources';
    }
  };

  if (status === 'error') {
    return (
      <Box flexDirection="column" padding={1}>
        <Text color="red" bold>Research Failed</Text>
        <Text color="red">{error}</Text>
        <Box marginTop={1}>
          <Text color="gray" dimColor>Press Ctrl+C to exit</Text>
        </Box>
      </Box>
    );
  }

  if (status !== 'done') {
    return (
      <Box flexDirection="column" padding={1}>
        <Text bold color="yellow">JARVIS Research</Text>
        <Box marginTop={1}>
          <Text color="gray">Topic: </Text>
          <Text>{topic}</Text>
        </Box>
        <Box>
          <Text color="gray">Depth: </Text>
          <Text>{depth} ({getDepthLabel()})</Text>
        </Box>

        <Box marginTop={2} flexDirection="column">
          <Box>
            {status === 'searching' ? <Spinner type="dots" /> : <Text color="green">✓</Text>}
            <Text color={status === 'searching' ? 'cyan' : 'gray'}> Searching the web...</Text>
          </Box>
          <Box>
            {status === 'extracting' ? <Spinner type="dots" /> :
             status === 'searching' ? <Text color="gray">○</Text> : <Text color="green">✓</Text>}
            <Text color={status === 'extracting' ? 'cyan' : 'gray'}> Extracting content...</Text>
          </Box>
          <Box>
            {status === 'synthesizing' ? <Spinner type="dots" /> : <Text color="gray">○</Text>}
            <Text color={status === 'synthesizing' ? 'cyan' : 'gray'}> Synthesizing findings...</Text>
          </Box>
        </Box>

        <Box marginTop={1}>
          <Text color="gray" dimColor>Elapsed: {formatElapsed(elapsed)}</Text>
        </Box>
      </Box>
    );
  }

  if (!result) return null;

  return (
    <Box flexDirection="column" padding={1}>
      <Text bold color="yellow">JARVIS Research Complete</Text>
      <Box marginTop={1}>
        <Text color="gray">Topic: </Text>
        <Text bold>{result.topic}</Text>
      </Box>
      <Box>
        <Text color="gray">Completed in: {formatElapsed(elapsed)}</Text>
      </Box>

      <Box marginTop={2} flexDirection="column">
        <Text bold color="cyan">Summary:</Text>
        <Box marginTop={1} paddingLeft={2}>
          <Text wrap="wrap">{result.summary}</Text>
        </Box>
      </Box>

      {result.key_findings && result.key_findings.length > 0 && (
        <Box marginTop={2} flexDirection="column">
          <Text bold color="cyan">Key Findings:</Text>
          {result.key_findings.map((finding, index) => (
            <Box key={index} marginTop={1} paddingLeft={2}>
              <Text color="green">• </Text>
              <Text wrap="wrap">{finding}</Text>
            </Box>
          ))}
        </Box>
      )}

      {includeSources && result.sources && result.sources.length > 0 && (
        <Box marginTop={2} flexDirection="column">
          <Text bold color="cyan">Sources:</Text>
          {result.sources.map((source, index) => (
            <Box key={index} marginTop={1} paddingLeft={2} flexDirection="column">
              <Text color="blue">{index + 1}. {source.title}</Text>
              <Text color="gray" dimColor>   {source.url}</Text>
            </Box>
          ))}
        </Box>
      )}

      {saveToMemory && (
        <Box marginTop={2}>
          <Text color="green">✓ Research saved to memory</Text>
        </Box>
      )}

      <Box marginTop={2}>
        <Text color="gray" dimColor>Press Ctrl+C to exit</Text>
      </Box>
    </Box>
  );
};
