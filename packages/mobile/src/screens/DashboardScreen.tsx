import React, { useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useBriefingStore } from '../stores/briefing';
import { WeatherWidget } from '../components/WeatherWidget';
import { CalendarWidget } from '../components/CalendarWidget';
import { TasksWidget } from '../components/TasksWidget';

export function DashboardScreen({ navigation }: any) {
  const { briefing, isLoading, error, fetchBriefing } = useBriefingStore();

  useEffect(() => {
    fetchBriefing();
  }, [fetchBriefing]);

  const onRefresh = useCallback(() => {
    fetchBriefing();
  }, [fetchBriefing]);

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={isLoading}
          onRefresh={onRefresh}
          tintColor="#00D9FF"
          colors={['#00D9FF']}
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.jarvisIcon}>
          <Icon name="pulse" size={32} color="#00D9FF" />
        </View>
        <Text style={styles.greeting}>{getGreeting()}, sir.</Text>
        <Text style={styles.subGreeting}>
          I'm at your service. All systems operational.
        </Text>
      </View>

      {/* Quick Actions */}
      <View style={styles.quickActions}>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate('Chat')}
        >
          <Icon name="mic" size={24} color="#00D9FF" />
          <Text style={styles.actionText}>Voice</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate('Briefing')}
        >
          <Icon name="newspaper" size={24} color="#00D9FF" />
          <Text style={styles.actionText}>Briefing</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate('Chat')}
        >
          <Icon name="chatbubbles" size={24} color="#00D9FF" />
          <Text style={styles.actionText}>Chat</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate('Settings')}
        >
          <Icon name="settings" size={24} color="#00D9FF" />
          <Text style={styles.actionText}>Settings</Text>
        </TouchableOpacity>
      </View>

      {/* Widgets */}
      <View style={styles.widgets}>
        <WeatherWidget weather={briefing?.weather} />
        <CalendarWidget events={briefing?.calendar} />
        <TasksWidget tasks={briefing?.tasks} />
      </View>

      {/* Error State */}
      {error && (
        <View style={styles.errorContainer}>
          <Icon name="alert-circle" size={24} color="#FF6B6B" />
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={onRefresh}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
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
  header: {
    alignItems: 'center',
    marginBottom: 24,
    paddingTop: 8,
  },
  jarvisIcon: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#1A1A2E',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 2,
    borderColor: '#00D9FF',
  },
  greeting: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#FFF',
    marginBottom: 4,
  },
  subGreeting: {
    fontSize: 14,
    color: '#888',
  },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  actionButton: {
    flex: 1,
    backgroundColor: '#1A1A2E',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginHorizontal: 4,
    borderWidth: 1,
    borderColor: '#2A2A3E',
  },
  actionText: {
    color: '#FFF',
    fontSize: 12,
    marginTop: 8,
  },
  widgets: {
    gap: 16,
  },
  errorContainer: {
    backgroundColor: '#2A1A1A',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 16,
    borderWidth: 1,
    borderColor: '#FF6B6B',
  },
  errorText: {
    color: '#FF6B6B',
    marginTop: 8,
    textAlign: 'center',
  },
  retryButton: {
    marginTop: 12,
    paddingHorizontal: 24,
    paddingVertical: 8,
    backgroundColor: '#FF6B6B',
    borderRadius: 8,
  },
  retryText: {
    color: '#FFF',
    fontWeight: 'bold',
  },
});
