import React, { useState, useCallback } from 'react';
import { Box, Text, useApp } from 'ink';
import TextInput from 'ink-text-input';
import Spinner from 'ink-spinner';
import { createApiClient, type AuthTokens } from '@jarvis/core';

interface LoginScreenProps {
  serverUrl: string;
  onSuccess: (tokens: AuthTokens) => void;
}

type LoginStep = 'email' | 'password' | 'loading' | 'success' | 'error' | 'register_name';

export const LoginScreen: React.FC<LoginScreenProps> = ({ serverUrl, onSuccess }) => {
  const { exit } = useApp();
  const [step, setStep] = useState<LoginStep>('email');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isNewUser, setIsNewUser] = useState(false);

  const client = React.useMemo(() => createApiClient({ baseUrl: serverUrl }), [serverUrl]);

  const handleLogin = useCallback(async (loginEmail: string, loginPassword: string) => {
    setStep('loading');
    setError(null);

    try {
      const response = await client.login(loginEmail, loginPassword);

      if (response.success && response.data) {
        onSuccess(response.data.tokens);
        setStep('success');
        setTimeout(() => exit(), 1500);
      } else if (response.error?.code === 'INVALID_CREDENTIALS') {
        setError('Invalid email or password. Press Enter to try again or type "register" to create an account.');
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

  const handleRegister = useCallback(async () => {
    setStep('loading');
    setError(null);

    try {
      // Use fetch directly for registration since client doesn't have register method
      const response = await fetch(`${serverUrl}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name }),
      });

      const data = await response.json() as {
        success: boolean;
        data?: { tokens: { accessToken: string; refreshToken: string; expiresAt: string } };
        error?: { message: string }
      };

      if (data.success && data.data) {
        const tokens: AuthTokens = {
          ...data.data.tokens,
          expiresAt: new Date(data.data.tokens.expiresAt),
        };
        onSuccess(tokens);
        setStep('success');
        setTimeout(() => exit(), 1500);
      } else {
        setError(data.error?.message ?? 'Registration failed');
        setStep('error');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
      setStep('error');
    }
  }, [serverUrl, email, password, name, onSuccess, exit]);

  const handleEmailSubmit = useCallback((value: string) => {
    setEmail(value);
    setStep('password');
  }, []);

  const handlePasswordSubmit = useCallback((value: string) => {
    setPassword(value);
    if (isNewUser) {
      setStep('register_name');
    } else {
      handleLogin();
    }
  }, [isNewUser, handleLogin]);

  const handleNameSubmit = useCallback((value: string) => {
    setName(value);
    handleRegister();
  }, [handleRegister]);

  const handleErrorInput = useCallback((value: string) => {
    if (value.toLowerCase() === 'register') {
      setIsNewUser(true);
      setStep('email');
      setEmail('');
      setPassword('');
    } else {
      setStep('email');
      setEmail('');
      setPassword('');
    }
  }, []);

  return (
    <Box flexDirection="column" padding={1}>
      <Box marginBottom={1}>
        <Text bold color="cyan">
          JARVIS Authentication
        </Text>
      </Box>

      {step === 'email' && (
        <Box flexDirection="column">
          <Text>{isNewUser ? 'Create your account' : 'Please login to continue'}</Text>
          <Box marginTop={1}>
            <Text>Email: </Text>
            <TextInput
              value={email}
              onChange={setEmail}
              onSubmit={handleEmailSubmit}
              placeholder="your@email.com"
            />
          </Box>
        </Box>
      )}

      {step === 'password' && (
        <Box flexDirection="column">
          <Text>Email: {email}</Text>
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

      {step === 'register_name' && (
        <Box flexDirection="column">
          <Text>Email: {email}</Text>
          <Box marginTop={1}>
            <Text>Name: </Text>
            <TextInput
              value={name}
              onChange={setName}
              onSubmit={handleNameSubmit}
              placeholder="Your name"
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
            <TextInput
              value=""
              onChange={() => {}}
              onSubmit={handleErrorInput}
              placeholder="Press Enter to retry..."
            />
          </Box>
        </Box>
      )}
    </Box>
  );
};
