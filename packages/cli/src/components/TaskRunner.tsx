import React, { useState, useEffect, useCallback } from 'react';
import { Box, Text, Spinner } from 'ink';
import axios from 'axios';

interface TaskRunnerProps {
  serverUrl: string;
  tokens: { accessToken: string; refreshToken: string };
  task: string;
  taskType: 'do' | 'code' | 'research' | 'automation';
  options?: Record<string, any>;
  onComplete?: (result: any) => void;
  onError?: (error: Error) => void;
}

type Status = 'idle' | 'running' | 'completed' | 'failed';

interface TaskResult {
  success: boolean;
  result?: any;
  error?: string;
}

export const TaskRunner: React.FC<TaskRunnerProps> = ({
  serverUrl,
  tokens,
  task,
  taskType,
  options = {},
  onComplete,
  onError,
}) => {
  const [status, setStatus] = useState<Status>('idle');
  const [result, setResult] = useState<TaskResult | null>(null);
  const [startTime, setStartTime] = useState<number>(0);
  const [elapsed, setElapsed] = useState<number>(0);

  const executeTask = useCallback(async () => {
    setStatus('running');
    setStartTime(Date.now());

    try {
      let endpoint = '/orchestration/do';
      let payload: any = { task };

      switch (taskType) {
        case 'code':
          endpoint = '/orchestration/code-task';
          payload = {
            task,
            working_directory: options.workingDirectory || '.',
            use_git: options.useGit !== false,
          };
          break;
        case 'research':
          endpoint = '/orchestration/research-task';
          payload = {
            topic: task,
            depth: options.depth || 'moderate',
            include_sources: options.includeSources !== false,
            save_to_memory: options.saveToMemory !== false,
          };
          break;
        case 'automation':
          endpoint = '/orchestration/automation-task';
          payload = {
            description: task,
            url: options.url,
            steps: options.steps,
          };
          break;
        default:
          // 'do' - natural language task
          payload = { task };
      }

      const response = await axios.post(
        `${serverUrl}${endpoint}`,
        payload,
        {
          headers: {
            Authorization: `Bearer ${tokens.accessToken}`,
            'Content-Type': 'application/json',
          },
          timeout: 600000, // 10 min timeout
        }
      );

      const taskResult: TaskResult = {
        success: response.data.success !== false,
        result: response.data.data || response.data,
      };

      setResult(taskResult);
      setStatus('completed');
      onComplete?.(taskResult);
    } catch (error: any) {
      const taskResult: TaskResult = {
        success: false,
        error: error.response?.data?.error?.message || error.message,
      };
      setResult(taskResult);
      setStatus('failed');
      onError?.(error);
    }
  }, [serverUrl, tokens, task, taskType, options, onComplete, onError]);

  useEffect(() => {
    executeTask();
  }, [executeTask]);

  useEffect(() => {
    if (status === 'running') {
      const interval = setInterval(() => {
        setElapsed(Date.now() - startTime);
      }, 100);
      return () => clearInterval(interval);
    }
  }, [status, startTime]);

  const formatElapsed = (ms: number): string => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${seconds}.${Math.floor((ms % 1000) / 100)}s`;
  };

  const getStatusIcon = (): React.ReactNode => {
    switch (status) {
      case 'running':
        return <Spinner type="dots" />;
      case 'completed':
        return <Text color="green">✓</Text>;
      case 'failed':
        return <Text color="red">✗</Text>;
      default:
        return <Text color="gray">○</Text>;
    }
  };

  const getStatusColor = (): string => {
    switch (status) {
      case 'running':
        return 'cyan';
      case 'completed':
        return 'green';
      case 'failed':
        return 'red';
      default:
        return 'gray';
    }
  };

  return (
    <Box flexDirection="column" padding={1}>
      <Box>
        <Text bold color="yellow">
          JARVIS Task Runner
        </Text>
      </Box>

      <Box marginTop={1}>
        <Text color="gray">Task: </Text>
        <Text>{task}</Text>
      </Box>

      <Box marginTop={1}>
        {getStatusIcon()}
        <Text color={getStatusColor()}>
          {' '}
          {status === 'running'
            ? `Executing... (${formatElapsed(elapsed)})`
            : status === 'completed'
            ? `Completed in ${formatElapsed(elapsed)}`
            : status === 'failed'
            ? 'Failed'
            : 'Idle'}
        </Text>
      </Box>

      {result && (
        <Box marginTop={1} flexDirection="column">
          {result.success ? (
            <>
              <Text color="green" bold>
                Result:
              </Text>
              <Box marginTop={1} paddingLeft={2}>
                <Text>
                  {typeof result.result === 'string'
                    ? result.result
                    : JSON.stringify(result.result, null, 2)}
                </Text>
              </Box>
            </>
          ) : (
            <>
              <Text color="red" bold>
                Error:
              </Text>
              <Box marginTop={1} paddingLeft={2}>
                <Text color="red">{result.error}</Text>
              </Box>
            </>
          )}
        </Box>
      )}

      {status !== 'running' && (
        <Box marginTop={2}>
          <Text color="gray" dimColor>
            Press Ctrl+C to exit
          </Text>
        </Box>
      )}
    </Box>
  );
};
