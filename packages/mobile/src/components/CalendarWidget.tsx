import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';

interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  location?: string;
}

interface CalendarWidgetProps {
  events?: CalendarEvent[];
}

export function CalendarWidget({ events }: CalendarWidgetProps) {
  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const upcomingEvents = events?.slice(0, 3) || [];

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Icon name="calendar" size={20} color="#00D9FF" />
        <Text style={styles.title}>Today's Schedule</Text>
      </View>

      <View style={styles.content}>
        {upcomingEvents.length > 0 ? (
          upcomingEvents.map((event, index) => (
            <View key={event.id || index} style={styles.eventItem}>
              <View style={styles.timeContainer}>
                <Text style={styles.eventTime}>{formatTime(event.start)}</Text>
              </View>
              <View style={styles.eventInfo}>
                <Text style={styles.eventTitle} numberOfLines={1}>
                  {event.title}
                </Text>
                {event.location && (
                  <View style={styles.locationContainer}>
                    <Icon name="location-outline" size={12} color="#888" />
                    <Text style={styles.eventLocation} numberOfLines={1}>
                      {event.location}
                    </Text>
                  </View>
                )}
              </View>
            </View>
          ))
        ) : (
          <View style={styles.emptyState}>
            <Icon name="calendar-outline" size={32} color="#444" />
            <Text style={styles.emptyText}>No events today, sir.</Text>
          </View>
        )}
      </View>

      {events && events.length > 3 && (
        <Text style={styles.moreText}>+{events.length - 3} more events</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#1A1A2E',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2A2A3E',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  content: {
    gap: 8,
  },
  eventItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#2A2A3E',
  },
  timeContainer: {
    width: 60,
  },
  eventTime: {
    color: '#00D9FF',
    fontWeight: 'bold',
    fontSize: 13,
  },
  eventInfo: {
    flex: 1,
  },
  eventTitle: {
    color: '#FFF',
    fontSize: 14,
  },
  locationContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 2,
  },
  eventLocation: {
    color: '#888',
    fontSize: 12,
    marginLeft: 4,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  emptyText: {
    color: '#666',
    fontStyle: 'italic',
    marginTop: 8,
  },
  moreText: {
    color: '#00D9FF',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 8,
  },
});
