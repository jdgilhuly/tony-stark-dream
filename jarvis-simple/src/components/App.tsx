import React, { useState, useEffect, useCallback } from 'react';
import { Box, Text, useApp, useInput, useStdin } from 'ink';
import TextInput from 'ink-text-input';
import { MessageList } from './MessageList.js';
import { VoiceIndicator } from './VoiceIndicator.js';
import { SessionManager } from '../services/session.js';
import { claudeExecutor } from '../services/claude.js';
import { voiceService } from '../services/voice.js';
import { buildPrompt } from '../prompts/jarvis.js';
import type { Message, VoiceState } from '../types.js';

export function App() {
  const { exit } = useApp();
  const { isRawModeSupported, setRawMode } = useStdin();

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [sessionManager] = useState(() => new SessionManager());
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  // Load existing session on startup
  useEffect(() => {
    async function init() {
      const existing = await sessionManager.load();
      if (existing) {
        setMessages(sessionManager.getMessages());
      }
      setInitialized(true);
    }
    init();
  }, [sessionManager]);

  const processMessage = useCallback(async (userMessage: string, isVoice = false) => {
    if (!userMessage.trim() || isProcessing) return;

    setIsProcessing(true);
    setError(null);

    // Add user message
    const userMsg = sessionManager.addMessage('user', userMessage, isVoice);
    setMessages((prev) => [...prev, userMsg]);

    try {
      // Build prompt with conversation context
      const context = sessionManager.getContextMessages(5);
      const prompt = buildPrompt(userMessage, context.slice(0, -1)); // Exclude current message from context

      // Execute Claude Code
      const response = await claudeExecutor.execute(prompt);

      // Add assistant response
      const assistantMsg = sessionManager.addMessage('assistant', response);
      setMessages((prev) => [...prev, assistantMsg]);

      // Save session
      await sessionManager.save();

      // Speak response if voice mode
      if (voiceEnabled && response) {
        setVoiceState('speaking');
        await voiceService.speak(response);
        setVoiceState('idle');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);

      // Add error as assistant message
      const errorResponse = `I apologize, Sir. I encountered an error: ${errorMessage}`;
      const assistantMsg = sessionManager.addMessage('assistant', errorResponse);
      setMessages((prev) => [...prev, assistantMsg]);
      await sessionManager.save();
    } finally {
      setIsProcessing(false);
    }
  }, [sessionManager, isProcessing, voiceEnabled]);

  const handleCommand = useCallback(async (cmd: string) => {
    const command = cmd.toLowerCase().trim();

    switch (command) {
      case '/help':
        setMessages((prev) => [
          ...prev,
          {
            id: 'help',
            role: 'assistant',
            content: `Available commands:
/voice - Toggle voice mode (push-to-talk with Space)
/clear - Clear conversation history
/history - Show full conversation
/help - Show this help
/exit - Exit JARVIS

When voice mode is enabled, hold Space to record.`,
            timestamp: new Date(),
          },
        ]);
        return true;

      case '/voice':
        if (!isRawModeSupported) {
          setMessages((prev) => [
            ...prev,
            {
              id: 'voice-error',
              role: 'assistant',
              content: 'I apologize, Sir, but voice mode is not supported in this terminal environment.',
              timestamp: new Date(),
            },
          ]);
          return true;
        }
        setVoiceEnabled((prev) => !prev);
        if (setRawMode) {
          setRawMode(!voiceEnabled);
        }
        setMessages((prev) => [
          ...prev,
          {
            id: 'voice-toggle',
            role: 'assistant',
            content: voiceEnabled
              ? 'Voice mode disabled, Sir.'
              : 'Voice mode enabled, Sir. Hold Space to speak.',
            timestamp: new Date(),
          },
        ]);
        return true;

      case '/clear':
        await sessionManager.clear();
        setMessages([
          {
            id: 'cleared',
            role: 'assistant',
            content: 'Session cleared, Sir. How may I assist you?',
            timestamp: new Date(),
          },
        ]);
        return true;

      case '/history':
        const history = sessionManager.getMessages();
        const historyText = history.length > 0
          ? `Conversation history (${history.length} messages):\n\n${history
              .map((m) => `[${m.timestamp.toLocaleTimeString()}] ${m.role === 'user' ? 'You' : 'JARVIS'}: ${m.content}`)
              .join('\n\n')}`
          : 'No conversation history yet, Sir.';
        setMessages((prev) => [
          ...prev,
          {
            id: 'history',
            role: 'assistant',
            content: historyText,
            timestamp: new Date(),
          },
        ]);
        return true;

      case '/exit':
        exit();
        return true;

      default:
        return false;
    }
  }, [sessionManager, exit, voiceEnabled, setRawMode, isRawModeSupported]);

  const handleSubmit = useCallback(async (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;

    setInput('');

    // Check for commands
    if (trimmed.startsWith('/')) {
      const handled = await handleCommand(trimmed);
      if (handled) return;
    }

    // Process as regular message
    await processMessage(trimmed);
  }, [handleCommand, processMessage]);

  // Handle keyboard input for voice mode
  useInput(async (input, key) => {
    if (key.ctrl && input === 'c') {
      exit();
      return;
    }

    if (voiceEnabled && input === ' ' && !isProcessing) {
      if (voiceState === 'idle') {
        // Start recording
        setVoiceState('recording');
        await voiceService.startRecording();
      }
    }
  }, { isActive: voiceEnabled && isRawModeSupported });

  // Handle space key release for voice
  useEffect(() => {
    if (!voiceEnabled) return;

    const handleKeyUp = async () => {
      if (voiceState === 'recording') {
        setVoiceState('transcribing');
        const audio = await voiceService.stopRecording();

        if (audio.length > 0) {
          try {
            const transcription = await voiceService.transcribe(audio);
            if (transcription.trim()) {
              setVoiceState('idle');
              await processMessage(transcription, true);
            } else {
              setVoiceState('idle');
            }
          } catch (err) {
            setError('Transcription failed. Is Whisper installed?');
            setVoiceState('idle');
          }
        } else {
          setVoiceState('idle');
        }
      }
    };

    // This is a simplified approach - in production you'd want proper key release detection
    const timer = setInterval(() => {
      if (voiceState === 'recording' && !voiceService.isCurrentlyRecording()) {
        // Recording stopped externally
        setVoiceState('idle');
      }
    }, 100);

    return () => clearInterval(timer);
  }, [voiceEnabled, voiceState, processMessage]);

  if (!initialized) {
    return (
      <Box>
        <Text color="yellow">Initializing JARVIS...</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" padding={1}>
      {/* Header */}
      <Box marginBottom={1}>
        <Text bold color="blue">
          J.A.R.V.I.S. - Just A Rather Very Intelligent System
        </Text>
      </Box>
      <Box marginBottom={1}>
        <Text color="gray">Type /help for commands. Ctrl+C to exit.</Text>
      </Box>

      {/* Messages */}
      <MessageList messages={messages} />

      {/* Voice indicator */}
      <VoiceIndicator state={voiceState} voiceEnabled={voiceEnabled} />

      {/* Error display */}
      {error && (
        <Box marginBottom={1}>
          <Text color="red">Error: {error}</Text>
        </Box>
      )}

      {/* Input */}
      {isProcessing ? (
        <Box>
          <Text color="yellow">Processing...</Text>
        </Box>
      ) : (
        <Box>
          <Text color="cyan" bold>{'> '}</Text>
          <TextInput
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            placeholder="Ask JARVIS anything..."
          />
        </Box>
      )}
    </Box>
  );
}
