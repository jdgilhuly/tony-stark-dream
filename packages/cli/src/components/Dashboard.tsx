import React, { useState, useEffect } from 'react';
import { Box, Text, useApp, useInput } from 'ink';
import Spinner from 'ink-spinner';
import type { AuthTokens, DailyBriefing, WeatherInfo, CalendarEvent, NewsItem } from '@jarvis/core';

interface DashboardProps {
  serverUrl: string;
  tokens: AuthTokens;
}

interface DashboardData {
  weather?: WeatherInfo;
  calendar?: CalendarEvent[];
  news?: NewsItem[];
  briefing?: DailyBriefing;
}

export const Dashboard: React.FC<DashboardProps> = ({ serverUrl, tokens }) => {
  const { exit } = useApp();
  const [data, setData] = useState<DashboardData>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [activeSection, setActiveSection] = useState<'weather' | 'calendar' | 'news' | 'briefing'>('briefing');

  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      exit();
    }
    if (input === 'r') {
      fetchData();
    }
    if (input === 'w') setActiveSection('weather');
    if (input === 'c') setActiveSection('calendar');
    if (input === 'n') setActiveSection('news');
    if (input === 'b') setActiveSection('briefing');
    if (key.leftArrow) {
      const sections: Array<typeof activeSection> = ['briefing', 'weather', 'calendar', 'news'];
      const idx = sections.indexOf(activeSection);
      setActiveSection(sections[(idx - 1 + sections.length) % sections.length]);
    }
    if (key.rightArrow) {
      const sections: Array<typeof activeSection> = ['briefing', 'weather', 'calendar', 'news'];
      const idx = sections.indexOf(activeSection);
      setActiveSection(sections[(idx + 1) % sections.length]);
    }
  });

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const headers = {
        'Authorization': `Bearer ${tokens.accessToken}`,
        'Content-Type': 'application/json',
      };

      // Fetch briefing (which includes weather, calendar, news)
      const briefingRes = await fetch(`${serverUrl}/briefing/daily`, { headers });
      if (briefingRes.ok) {
        const briefingData = await briefingRes.json();
        if (briefingData.success && briefingData.data) {
          setData({
            briefing: briefingData.data,
            weather: briefingData.data.weather,
            calendar: briefingData.data.calendar,
            news: briefingData.data.news,
          });
        }
      } else {
        setError('Failed to fetch briefing data');
      }

      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Refresh every 5 minutes
    const interval = setInterval(fetchData, 300000);
    return () => clearInterval(interval);
  }, []);

  if (isLoading && !data.briefing) {
    return (
      <Box padding={1}>
        <Text color="yellow">
          <Spinner type="dots" />
          {' Loading dashboard, sir...'}
        </Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" padding={1}>
      {/* Header */}
      <Box marginBottom={1}>
        <Text bold color="cyan">
          ═══════════════════════════════════════════════════════════════
        </Text>
      </Box>
      <Box marginBottom={1} justifyContent="space-between">
        <Text bold color="cyan">{'  '}JARVIS Dashboard</Text>
        <Text dimColor>
          {lastUpdated ? `Updated: ${lastUpdated.toLocaleTimeString()}` : ''}
          {isLoading ? ' (refreshing...)' : ''}
        </Text>
      </Box>
      <Box marginBottom={1}>
        <Text bold color="cyan">
          ═══════════════════════════════════════════════════════════════
        </Text>
      </Box>

      {/* Navigation */}
      <Box marginBottom={1}>
        <Text>
          {'  '}
          <Text color={activeSection === 'briefing' ? 'green' : 'white'} bold={activeSection === 'briefing'}>
            [B]riefing
          </Text>
          {'  '}
          <Text color={activeSection === 'weather' ? 'green' : 'white'} bold={activeSection === 'weather'}>
            [W]eather
          </Text>
          {'  '}
          <Text color={activeSection === 'calendar' ? 'green' : 'white'} bold={activeSection === 'calendar'}>
            [C]alendar
          </Text>
          {'  '}
          <Text color={activeSection === 'news' ? 'green' : 'white'} bold={activeSection === 'news'}>
            [N]ews
          </Text>
        </Text>
      </Box>

      {error && (
        <Box marginBottom={1}>
          <Text color="red">Error: {error}</Text>
        </Box>
      )}

      {/* Content based on active section */}
      <Box flexDirection="column" borderStyle="single" paddingX={1} paddingY={1}>
        {activeSection === 'briefing' && (
          <BriefingSection briefing={data.briefing} />
        )}
        {activeSection === 'weather' && (
          <WeatherSection weather={data.weather} />
        )}
        {activeSection === 'calendar' && (
          <CalendarSection events={data.calendar} />
        )}
        {activeSection === 'news' && (
          <NewsSection news={data.news} />
        )}
      </Box>

      {/* Footer */}
      <Box marginTop={1}>
        <Text dimColor>
          [R] Refresh | [←/→] Navigate | Ctrl+C to exit
        </Text>
      </Box>
    </Box>
  );
};

const BriefingSection: React.FC<{ briefing?: DailyBriefing }> = ({ briefing }) => {
  if (!briefing) {
    return <Text dimColor>No briefing available. Press R to refresh.</Text>;
  }

  return (
    <Box flexDirection="column">
      <Text bold color="blue">{briefing.summary}</Text>
    </Box>
  );
};

const WeatherSection: React.FC<{ weather?: WeatherInfo }> = ({ weather }) => {
  if (!weather) {
    return <Text dimColor>Weather data not available.</Text>;
  }

  return (
    <Box flexDirection="column">
      <Text bold color="yellow">☀ Weather - {weather.location}</Text>
      <Box marginTop={1}>
        <Box flexDirection="column" marginRight={4}>
          <Text>Current</Text>
          <Text bold>{weather.current.temperature}°</Text>
          <Text>{weather.current.condition}</Text>
        </Box>
        <Box flexDirection="column" marginRight={4}>
          <Text>Humidity</Text>
          <Text bold>{weather.current.humidity}%</Text>
        </Box>
        <Box flexDirection="column">
          <Text>Wind</Text>
          <Text bold>{weather.current.windSpeed} mph</Text>
        </Box>
      </Box>
      {weather.forecast && weather.forecast.length > 0 && (
        <Box flexDirection="column" marginTop={1}>
          <Text bold>Forecast:</Text>
          {weather.forecast.slice(0, 3).map((day, i) => (
            <Text key={i}>
              {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}: {day.high}°/{day.low}° - {day.condition}
            </Text>
          ))}
        </Box>
      )}
    </Box>
  );
};

const CalendarSection: React.FC<{ events?: CalendarEvent[] }> = ({ events }) => {
  if (!events || events.length === 0) {
    return <Text dimColor>No events scheduled for today.</Text>;
  }

  return (
    <Box flexDirection="column">
      <Text bold color="green">📅 Today's Schedule</Text>
      <Box flexDirection="column" marginTop={1}>
        {events.map((event) => (
          <Box key={event.id} marginBottom={1}>
            <Text color="cyan">
              {new Date(event.startTime).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
            </Text>
            <Text> - </Text>
            <Text bold>{event.title}</Text>
            {event.location && <Text dimColor> @ {event.location}</Text>}
          </Box>
        ))}
      </Box>
    </Box>
  );
};

const NewsSection: React.FC<{ news?: NewsItem[] }> = ({ news }) => {
  if (!news || news.length === 0) {
    return <Text dimColor>No news available.</Text>;
  }

  return (
    <Box flexDirection="column">
      <Text bold color="magenta">📰 Headlines</Text>
      <Box flexDirection="column" marginTop={1}>
        {news.slice(0, 5).map((item, i) => (
          <Box key={item.id || i} marginBottom={1}>
            <Text>• </Text>
            <Text bold>{item.title}</Text>
            <Text dimColor> ({item.source})</Text>
          </Box>
        ))}
      </Box>
    </Box>
  );
};
