import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';

interface Weather {
  temperature: number;
  condition: string;
  humidity: number;
  wind: number;
  icon?: string;
}

interface WeatherWidgetProps {
  weather?: Weather;
}

const getWeatherIcon = (condition?: string): string => {
  if (!condition) return 'cloud';
  const lower = condition.toLowerCase();
  if (lower.includes('sun') || lower.includes('clear')) return 'sunny';
  if (lower.includes('cloud')) return 'cloudy';
  if (lower.includes('rain')) return 'rainy';
  if (lower.includes('snow')) return 'snow';
  if (lower.includes('thunder')) return 'thunderstorm';
  return 'partly-sunny';
};

export function WeatherWidget({ weather }: WeatherWidgetProps) {
  if (!weather) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Icon name="partly-sunny" size={20} color="#00D9FF" />
          <Text style={styles.title}>Weather</Text>
        </View>
        <View style={styles.placeholder}>
          <Text style={styles.placeholderText}>Weather data unavailable</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Icon name="partly-sunny" size={20} color="#00D9FF" />
        <Text style={styles.title}>Weather</Text>
      </View>

      <View style={styles.content}>
        <View style={styles.mainInfo}>
          <Icon name={getWeatherIcon(weather.condition)} size={48} color="#00D9FF" />
          <Text style={styles.temperature}>{weather.temperature}°</Text>
        </View>

        <Text style={styles.condition}>{weather.condition}</Text>

        <View style={styles.details}>
          <View style={styles.detailItem}>
            <Icon name="water" size={16} color="#888" />
            <Text style={styles.detailText}>{weather.humidity}%</Text>
          </View>
          <View style={styles.detailItem}>
            <Icon name="speedometer" size={16} color="#888" />
            <Text style={styles.detailText}>{weather.wind} mph</Text>
          </View>
        </View>
      </View>
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
    alignItems: 'center',
  },
  mainInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  temperature: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#FFF',
    marginLeft: 12,
  },
  condition: {
    color: '#888',
    fontSize: 16,
    marginBottom: 12,
  },
  details: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 24,
  },
  detailItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  detailText: {
    color: '#888',
    marginLeft: 4,
  },
  placeholder: {
    padding: 20,
    alignItems: 'center',
  },
  placeholderText: {
    color: '#666',
    fontStyle: 'italic',
  },
});
