import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import { useAuthStore } from '../stores/auth';
import { useSettingsStore } from '../stores/settings';

export function SettingsScreen() {
  const { logout, user } = useAuthStore();
  const {
    voiceEnabled,
    setVoiceEnabled,
    briefingEnabled,
    setBriefingEnabled,
    briefingTime,
    setBriefingTime,
    darkMode,
    setDarkMode,
    notificationsEnabled,
    setNotificationsEnabled,
  } = useSettingsStore();

  const handleLogout = () => {
    Alert.alert(
      'Sign Out',
      'Are you sure you want to sign out, sir?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Sign Out',
          style: 'destructive',
          onPress: logout,
        },
      ]
    );
  };

  const handleClearCache = () => {
    Alert.alert(
      'Clear Cache',
      'This will clear all cached data. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: () => {
            // Clear cache logic
            Alert.alert('Success', 'Cache cleared successfully, sir.');
          },
        },
      ]
    );
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Profile Section */}
      <View style={styles.profileSection}>
        <View style={styles.avatar}>
          <Icon name="person" size={32} color="#00D9FF" />
        </View>
        <View style={styles.profileInfo}>
          <Text style={styles.profileName}>{user?.name || 'User'}</Text>
          <Text style={styles.profileEmail}>{user?.email || 'user@example.com'}</Text>
        </View>
      </View>

      {/* Voice Settings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Voice Settings</Text>

        <View style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="mic" size={20} color="#00D9FF" />
            <Text style={styles.settingLabel}>Voice Input</Text>
          </View>
          <Switch
            value={voiceEnabled}
            onValueChange={setVoiceEnabled}
            trackColor={{ false: '#333', true: '#00D9FF' }}
            thumbColor="#FFF"
          />
        </View>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="volume-high" size={20} color="#00D9FF" />
            <Text style={styles.settingLabel}>Voice Output</Text>
          </View>
          <View style={styles.settingValue}>
            <Text style={styles.settingValueText}>Brian (British)</Text>
            <Icon name="chevron-forward" size={16} color="#888" />
          </View>
        </TouchableOpacity>
      </View>

      {/* Briefing Settings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Daily Briefing</Text>

        <View style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="newspaper" size={20} color="#00D9FF" />
            <Text style={styles.settingLabel}>Daily Briefing</Text>
          </View>
          <Switch
            value={briefingEnabled}
            onValueChange={setBriefingEnabled}
            trackColor={{ false: '#333', true: '#00D9FF' }}
            thumbColor="#FFF"
          />
        </View>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="time" size={20} color="#00D9FF" />
            <Text style={styles.settingLabel}>Briefing Time</Text>
          </View>
          <View style={styles.settingValue}>
            <Text style={styles.settingValueText}>{briefingTime}</Text>
            <Icon name="chevron-forward" size={16} color="#888" />
          </View>
        </TouchableOpacity>
      </View>

      {/* Notification Settings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notifications</Text>

        <View style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="notifications" size={20} color="#00D9FF" />
            <Text style={styles.settingLabel}>Push Notifications</Text>
          </View>
          <Switch
            value={notificationsEnabled}
            onValueChange={setNotificationsEnabled}
            trackColor={{ false: '#333', true: '#00D9FF' }}
            thumbColor="#FFF"
          />
        </View>
      </View>

      {/* Appearance */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Appearance</Text>

        <View style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="moon" size={20} color="#00D9FF" />
            <Text style={styles.settingLabel}>Dark Mode</Text>
          </View>
          <Switch
            value={darkMode}
            onValueChange={setDarkMode}
            trackColor={{ false: '#333', true: '#00D9FF' }}
            thumbColor="#FFF"
          />
        </View>
      </View>

      {/* Integrations */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Integrations</Text>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="calendar" size={20} color="#00D9FF" />
            <Text style={styles.settingLabel}>Google Calendar</Text>
          </View>
          <View style={styles.settingValue}>
            <Text style={[styles.settingValueText, { color: '#4CAF50' }]}>Connected</Text>
            <Icon name="chevron-forward" size={16} color="#888" />
          </View>
        </TouchableOpacity>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="location" size={20} color="#00D9FF" />
            <Text style={styles.settingLabel}>Location</Text>
          </View>
          <View style={styles.settingValue}>
            <Text style={styles.settingValueText}>New York, NY</Text>
            <Icon name="chevron-forward" size={16} color="#888" />
          </View>
        </TouchableOpacity>
      </View>

      {/* Data & Storage */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Data & Storage</Text>

        <TouchableOpacity style={styles.settingItem} onPress={handleClearCache}>
          <View style={styles.settingInfo}>
            <Icon name="trash" size={20} color="#FF6B6B" />
            <Text style={[styles.settingLabel, { color: '#FF6B6B' }]}>Clear Cache</Text>
          </View>
          <Icon name="chevron-forward" size={16} color="#888" />
        </TouchableOpacity>
      </View>

      {/* About */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>

        <View style={styles.settingItem}>
          <View style={styles.settingInfo}>
            <Icon name="information-circle" size={20} color="#00D9FF" />
            <Text style={styles.settingLabel}>Version</Text>
          </View>
          <Text style={styles.settingValueText}>0.1.0</Text>
        </View>
      </View>

      {/* Logout */}
      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Icon name="log-out" size={20} color="#FF6B6B" />
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          J.A.R.V.I.S. - Just A Rather Very Intelligent System
        </Text>
        <Text style={styles.footerText}>At your service, sir.</Text>
      </View>
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
  profileSection: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1A1A2E',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#2A2A3E',
    justifyContent: 'center',
    alignItems: 'center',
  },
  profileInfo: {
    marginLeft: 16,
  },
  profileName: {
    color: '#FFF',
    fontSize: 18,
    fontWeight: 'bold',
  },
  profileEmail: {
    color: '#888',
    marginTop: 2,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    color: '#888',
    fontSize: 12,
    fontWeight: 'bold',
    textTransform: 'uppercase',
    marginBottom: 8,
    marginLeft: 4,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#1A1A2E',
    padding: 16,
    borderRadius: 12,
    marginBottom: 8,
  },
  settingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  settingLabel: {
    color: '#FFF',
    marginLeft: 12,
  },
  settingValue: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  settingValueText: {
    color: '#888',
    marginRight: 4,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#2A1A1A',
    padding: 16,
    borderRadius: 12,
    marginTop: 8,
    borderWidth: 1,
    borderColor: '#FF6B6B',
  },
  logoutText: {
    color: '#FF6B6B',
    fontWeight: 'bold',
    marginLeft: 8,
  },
  footer: {
    alignItems: 'center',
    marginTop: 32,
    paddingBottom: 32,
  },
  footerText: {
    color: '#444',
    fontSize: 12,
  },
});
