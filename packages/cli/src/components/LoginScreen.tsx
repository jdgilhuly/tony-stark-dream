import React, { useState, useCallback } from 'react';
import { Box, Text, useApp } from 'ink';
import TextInput from 'ink-text-input';
import Spinner from 'ink-spinner';
import { createApiClient, type AuthTokens } from '@jarvis/core';

interface LoginScreenProps {
  serverUrl: string;
  onSuccess: (tokens: AuthTokens) => void;
}

type LoginStep = 'password' | 'loading' | 'success' | 'error';

export const LoginScreen: React.FC<LoginScreenProps> = ({ serverUrl, onSuccess }) => {
  const { exit } = useApp();
  const [step, setStep] = useState<LoginStep>('password');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const client = React.useMemo(() => createApiClient({ baseUrl: serverUrl }), [serverUrl]);

  const handleLogin = useCallback(async (loginPassword: string) => {
    setStep('loading');
    setError(null);

    try {
      const response = await client.login(loginPassword);

      if (response.success && response.data) {
        onSuccess(response.data.tokens);
        setStep('success');
        setTimeout(() => exit(), 1500);
      } else if (response.error?.code === 'INVALID_CREDENTIALS') {
        setError('Invalid password. Press Enter to try again.');
        setStep('error');
      } else if (response.error?.code === 'CONFIG_ERROR') {
        setError('Server not configured. Ensure JARVIS_PASSWORD is set on the server.');
        setStep('error');
      } else {
        setError(response.error?.message ?? 'Login failed');
        setStep('error');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
      setStep('error');
    }
  }, [client, onSuccess, exit]);

  const handlePasswordSubmit = useCallback((value: string) => {
    setPassword(value);
    handleLogin(value);
  }, [handleLogin]);

  const handleRetry = useCallback(() => {
    setPassword('');
    setStep('password');
  }, []);

  return (
    <Box flexDirection="column" padding={1}>
      <Box marginBottom={1}>
        <Text bold color="cyan">
          JARVIS Authentication
        </Text>
      </Box>

      {step === 'password' && (
        <Box flexDirection="column">
          <Text>Enter your JARVIS password to continue</Text>
          <Box marginTop={1}>
            <Text>Password: </Text>
            <TextInput
              value={password}
              onChange={setPassword}
              onSubmit={handlePasswordSubmit}
              mask="*"
              placeholder="Enter password"
            />
          </Box>
        </Box>
      )}

      {step === 'loading' && (
        <Box>
          <Text color="yellow">
            <Spinner type="dots" />
            {' Authenticating...'}
          </Text>
        </Box>
      )}

      {step === 'success' && (
        <Box flexDirection="column">
          <Text color="green">Authentication successful!</Text>
          <Text>Welcome to JARVIS, sir.</Text>
        </Box>
      )}

      {step === 'error' && (
        <Box flexDirection="column">
          <Text color="red">Error: {error}</Text>
          <Box marginTop={1}>
            <Text>Press Enter to retry: </Text>
            <TextInput
              value=""
              onChange={() => {}}
              onSubmit={handleRetry}
              placeholder=""
            />
          </Box>
        </Box>
      )}
    </Box>
  );
};
