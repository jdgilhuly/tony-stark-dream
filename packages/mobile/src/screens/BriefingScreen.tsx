import React, { useEffect, useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useBriefingStore } from '../stores/briefing';

export function BriefingScreen() {
  const { briefing, isLoading, error, fetchBriefing, playBriefing, isPlaying } = useBriefingStore();
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    weather: true,
    calendar: true,
    news: true,
    tasks: true,
  });

  useEffect(() => {
    fetchBriefing();
  }, [fetchBriefing]);

  const onRefresh = useCallback(() => {
    fetchBriefing();
  }, [fetchBriefing]);

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString([], {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    });
  };

  if (isLoading && !briefing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#00D9FF" />
        <Text style={styles.loadingText}>Preparing your briefing, sir...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={isLoading}
          onRefresh={onRefresh}
          tintColor="#00D9FF"
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Daily Briefing</Text>
        <Text style={styles.date}>{formatDate(new Date())}</Text>
      </View>

      {/* Play Button */}
      <TouchableOpacity
        style={[styles.playButton, isPlaying && styles.playButtonActive]}
        onPress={playBriefing}
        disabled={isPlaying}
      >
        <Icon
          name={isPlaying ? 'pause' : 'play'}
          size={24}
          color="#FFF"
        />
        <Text style={styles.playButtonText}>
          {isPlaying ? 'Playing Briefing...' : 'Play Audio Briefing'}
        </Text>
      </TouchableOpacity>

      {/* Summary */}
      {briefing?.summary && (
        <View style={styles.summaryCard}>
          <Text style={styles.summaryText}>{briefing.summary}</Text>
        </View>
      )}

      {/* Weather Section */}
      <TouchableOpacity
        style={styles.sectionHeader}
        onPress={() => toggleSection('weather')}
      >
        <View style={styles.sectionTitleContainer}>
          <Icon name="partly-sunny" size={20} color="#00D9FF" />
          <Text style={styles.sectionTitle}>Weather</Text>
        </View>
        <Icon
          name={expandedSections.weather ? 'chevron-up' : 'chevron-down'}
          size={20}
          color="#888"
        />
      </TouchableOpacity>
      {expandedSections.weather && briefing?.weather && (
        <View style={styles.sectionContent}>
          <View style={styles.weatherMain}>
            <Text style={styles.weatherTemp}>{briefing.weather.temperature}°</Text>
            <Text style={styles.weatherCondition}>{briefing.weather.condition}</Text>
          </View>
          <View style={styles.weatherDetails}>
            <View style={styles.weatherDetail}>
              <Icon name="water" size={16} color="#888" />
              <Text style={styles.weatherDetailText}>
                {briefing.weather.humidity}% humidity
              </Text>
            </View>
            <View style={styles.weatherDetail}>
              <Icon name="speedometer" size={16} color="#888" />
              <Text style={styles.weatherDetailText}>
                {briefing.weather.wind} mph wind
              </Text>
            </View>
          </View>
        </View>
      )}

      {/* Calendar Section */}
      <TouchableOpacity
        style={styles.sectionHeader}
        onPress={() => toggleSection('calendar')}
      >
        <View style={styles.sectionTitleContainer}>
          <Icon name="calendar" size={20} color="#00D9FF" />
          <Text style={styles.sectionTitle}>Today's Schedule</Text>
        </View>
        <Icon
          name={expandedSections.calendar ? 'chevron-up' : 'chevron-down'}
          size={20}
          color="#888"
        />
      </TouchableOpacity>
      {expandedSections.calendar && (
        <View style={styles.sectionContent}>
          {briefing?.calendar?.length ? (
            briefing.calendar.map((event: any, index: number) => (
              <View key={index} style={styles.eventItem}>
                <Text style={styles.eventTime}>{formatTime(event.start)}</Text>
                <View style={styles.eventDetails}>
                  <Text style={styles.eventTitle}>{event.title}</Text>
                  {event.location && (
                    <Text style={styles.eventLocation}>{event.location}</Text>
                  )}
                </View>
              </View>
            ))
          ) : (
            <Text style={styles.emptyText}>No events scheduled for today, sir.</Text>
          )}
        </View>
      )}

      {/* News Section */}
      <TouchableOpacity
        style={styles.sectionHeader}
        onPress={() => toggleSection('news')}
      >
        <View style={styles.sectionTitleContainer}>
          <Icon name="newspaper" size={20} color="#00D9FF" />
          <Text style={styles.sectionTitle}>Top Headlines</Text>
        </View>
        <Icon
          name={expandedSections.news ? 'chevron-up' : 'chevron-down'}
          size={20}
          color="#888"
        />
      </TouchableOpacity>
      {expandedSections.news && (
        <View style={styles.sectionContent}>
          {briefing?.news?.length ? (
            briefing.news.slice(0, 5).map((article: any, index: number) => (
              <View key={index} style={styles.newsItem}>
                <Text style={styles.newsTitle}>{article.title}</Text>
                <Text style={styles.newsSource}>{article.source}</Text>
              </View>
            ))
          ) : (
            <Text style={styles.emptyText}>No news available.</Text>
          )}
        </View>
      )}

      {/* Tasks Section */}
      <TouchableOpacity
        style={styles.sectionHeader}
        onPress={() => toggleSection('tasks')}
      >
        <View style={styles.sectionTitleContainer}>
          <Icon name="checkbox" size={20} color="#00D9FF" />
          <Text style={styles.sectionTitle}>Pending Tasks</Text>
        </View>
        <Icon
          name={expandedSections.tasks ? 'chevron-up' : 'chevron-down'}
          size={20}
          color="#888"
        />
      </TouchableOpacity>
      {expandedSections.tasks && (
        <View style={styles.sectionContent}>
          {briefing?.tasks?.length ? (
            briefing.tasks.map((task: any, index: number) => (
              <View key={index} style={styles.taskItem}>
                <Icon
                  name={task.completed ? 'checkbox' : 'square-outline'}
                  size={20}
                  color={task.completed ? '#4CAF50' : '#888'}
                />
                <Text
                  style={[
                    styles.taskText,
                    task.completed && styles.taskCompleted,
                  ]}
                >
                  {task.title}
                </Text>
              </View>
            ))
          ) : (
            <Text style={styles.emptyText}>No pending tasks, sir.</Text>
          )}
        </View>
      )}

      {/* Error State */}
      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0A0A0F',
  },
  content: {
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0A0A0F',
  },
  loadingText: {
    color: '#888',
    marginTop: 16,
  },
  header: {
    marginBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFF',
  },
  date: {
    fontSize: 14,
    color: '#888',
    marginTop: 4,
  },
  playButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#00D9FF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  playButtonActive: {
    backgroundColor: '#0099B3',
  },
  playButtonText: {
    color: '#FFF',
    fontWeight: 'bold',
    marginLeft: 8,
    fontSize: 16,
  },
  summaryCard: {
    backgroundColor: '#1A1A2E',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#00D9FF',
  },
  summaryText: {
    color: '#DDD',
    lineHeight: 22,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#1A1A2E',
    padding: 16,
    borderRadius: 12,
    marginBottom: 2,
  },
  sectionTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  sectionTitle: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  sectionContent: {
    backgroundColor: '#151520',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  weatherMain: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: 12,
  },
  weatherTemp: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#FFF',
  },
  weatherCondition: {
    fontSize: 18,
    color: '#888',
    marginLeft: 8,
  },
  weatherDetails: {
    flexDirection: 'row',
    gap: 16,
  },
  weatherDetail: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  weatherDetailText: {
    color: '#888',
    marginLeft: 4,
  },
  eventItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  eventTime: {
    color: '#00D9FF',
    width: 60,
    fontWeight: 'bold',
  },
  eventDetails: {
    flex: 1,
  },
  eventTitle: {
    color: '#FFF',
    fontWeight: '500',
  },
  eventLocation: {
    color: '#888',
    fontSize: 12,
    marginTop: 2,
  },
  newsItem: {
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#2A2A3E',
  },
  newsTitle: {
    color: '#FFF',
    lineHeight: 20,
  },
  newsSource: {
    color: '#888',
    fontSize: 12,
    marginTop: 4,
  },
  taskItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  taskText: {
    color: '#FFF',
    marginLeft: 8,
  },
  taskCompleted: {
    textDecorationLine: 'line-through',
    color: '#888',
  },
  emptyText: {
    color: '#888',
    fontStyle: 'italic',
  },
  errorContainer: {
    backgroundColor: '#2A1A1A',
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
  },
  errorText: {
    color: '#FF6B6B',
    textAlign: 'center',
  },
});
