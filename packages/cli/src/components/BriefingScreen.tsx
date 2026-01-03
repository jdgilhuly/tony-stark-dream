import React, { useState, useEffect } from 'react';
import { Box, Text, useApp } from 'ink';
import Spinner from 'ink-spinner';
import type { AuthTokens, DailyBriefing } from '@jarvis/core';

interface BriefingScreenProps {
  serverUrl: string;
  tokens: AuthTokens;
}

export const BriefingScreen: React.FC<BriefingScreenProps> = ({ serverUrl, tokens }) => {
  const { exit } = useApp();
  const [briefing, setBriefing] = useState<DailyBriefing | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBriefing = async () => {
      try {
        const response = await fetch(`${serverUrl}/briefing/daily`, {
          headers: {
            'Authorization': `Bearer ${tokens.accessToken}`,
            'Content-Type': 'application/json',
          },
        });

        const data = await response.json();

        if (data.success && data.data) {
          setBriefing(data.data);
        } else {
          setError(data.error?.message ?? 'Failed to fetch briefing');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Connection failed');
      } finally {
        setIsLoading(false);
      }
    };

    fetchBriefing();
  }, [serverUrl, tokens]);

  if (isLoading) {
    return (
      <Box padding={1}>
        <Text color="yellow">
          <Spinner type="dots" />
          {' Preparing your briefing, sir...'}
        </Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Box padding={1} flexDirection="column">
        <Text color="red">Error: {error}</Text>
        <Text dimColor>Press Ctrl+C to exit</Text>
      </Box>
    );
  }

  if (!briefing) {
    return (
      <Box padding={1}>
        <Text>No briefing data available.</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" padding={1}>
      {/* Header */}
      <Box marginBottom={1}>
        <Text bold color="cyan">
          ═══════════════════════════════════════════════════════════
        </Text>
      </Box>
      <Box marginBottom={1}>
        <Text bold color="cyan">
          {'  '}JARVIS Daily Briefing
        </Text>
      </Box>
      <Box marginBottom={1}>
        <Text bold color="cyan">
          ═══════════════════════════════════════════════════════════
        </Text>
      </Box>

      {/* Summary */}
      <Box marginBottom={1}>
        <Text color="blue">{briefing.summary}</Text>
      </Box>

      {/* Weather */}
      <Box flexDirection="column" marginBottom={1}>
        <Text bold color="yellow">☀ Weather - {briefing.weather.location}</Text>
        <Text>
          {'  '}Current: {briefing.weather.current.temperature}°F, {briefing.weather.current.condition}
        </Text>
        <Text>
          {'  '}Humidity: {briefing.weather.current.humidity}% | Wind: {briefing.weather.current.windSpeed} mph
        </Text>
      </Box>

      {/* Calendar */}
      <Box flexDirection="column" marginBottom={1}>
        <Text bold color="green">📅 Today's Schedule</Text>
        {briefing.calendar.length === 0 ? (
          <Text>{'  '}No events scheduled for today.</Text>
        ) : (
          briefing.calendar.map((event) => (
            <Box key={event.id}>
              <Text>
                {'  '}• {new Date(event.startTime).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                {' - '}
                {event.title}
                {event.location && ` @ ${event.location}`}
              </Text>
            </Box>
          ))
        )}
      </Box>

      {/* News */}
      <Box flexDirection="column" marginBottom={1}>
        <Text bold color="magenta">📰 News Headlines</Text>
        {briefing.news.slice(0, 3).map((item) => (
          <Box key={item.id}>
            <Text>{'  '}• {item.title}</Text>
          </Box>
        ))}
      </Box>

      {/* Tasks */}
      <Box flexDirection="column" marginBottom={1}>
        <Text bold color="red">✓ Pending Tasks</Text>
        {briefing.tasks.filter(t => t.status !== 'completed').length === 0 ? (
          <Text>{'  '}All tasks completed. Well done, sir.</Text>
        ) : (
          briefing.tasks
            .filter(t => t.status !== 'completed')
            .map((task) => (
              <Box key={task.id}>
                <Text>
                  {'  '}[{task.priority.toUpperCase()}] {task.title}
                  {task.dueDate && ` - Due: ${new Date(task.dueDate).toLocaleDateString()}`}
                </Text>
              </Box>
            ))
        )}
      </Box>

      <Box marginTop={1}>
        <Text dimColor>Press Ctrl+C to exit</Text>
      </Box>
    </Box>
  );
};
