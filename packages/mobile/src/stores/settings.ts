import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface SettingsState {
  voiceEnabled: boolean;
  briefingEnabled: boolean;
  briefingTime: string;
  darkMode: boolean;
  notificationsEnabled: boolean;
  weatherLocation: string;
  temperatureUnit: 'celsius' | 'fahrenheit';
  voiceId: string;

  setVoiceEnabled: (enabled: boolean) => void;
  setBriefingEnabled: (enabled: boolean) => void;
  setBriefingTime: (time: string) => void;
  setDarkMode: (enabled: boolean) => void;
  setNotificationsEnabled: (enabled: boolean) => void;
  setWeatherLocation: (location: string) => void;
  setTemperatureUnit: (unit: 'celsius' | 'fahrenheit') => void;
  setVoiceId: (id: string) => void;
  loadSettings: () => Promise<void>;
}

const STORAGE_KEY = '@jarvis/settings';

const defaultSettings = {
  voiceEnabled: true,
  briefingEnabled: true,
  briefingTime: '08:00',
  darkMode: true,
  notificationsEnabled: true,
  weatherLocation: 'New York, NY',
  temperatureUnit: 'fahrenheit' as const,
  voiceId: 'Brian',
};

const persistSettings = async (settings: Partial<SettingsState>) => {
  try {
    const current = await AsyncStorage.getItem(STORAGE_KEY);
    const parsed = current ? JSON.parse(current) : {};
    const updated = { ...parsed, ...settings };
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (error) {
    console.error('Failed to persist settings:', error);
  }
};

export const useSettingsStore = create<SettingsState>((set) => ({
  ...defaultSettings,

  setVoiceEnabled: (voiceEnabled) => {
    set({ voiceEnabled });
    persistSettings({ voiceEnabled });
  },

  setBriefingEnabled: (briefingEnabled) => {
    set({ briefingEnabled });
    persistSettings({ briefingEnabled });
  },

  setBriefingTime: (briefingTime) => {
    set({ briefingTime });
    persistSettings({ briefingTime });
  },

  setDarkMode: (darkMode) => {
    set({ darkMode });
    persistSettings({ darkMode });
  },

  setNotificationsEnabled: (notificationsEnabled) => {
    set({ notificationsEnabled });
    persistSettings({ notificationsEnabled });
  },

  setWeatherLocation: (weatherLocation) => {
    set({ weatherLocation });
    persistSettings({ weatherLocation });
  },

  setTemperatureUnit: (temperatureUnit) => {
    set({ temperatureUnit });
    persistSettings({ temperatureUnit });
  },

  setVoiceId: (voiceId) => {
    set({ voiceId });
    persistSettings({ voiceId });
  },

  loadSettings: async () => {
    try {
      const stored = await AsyncStorage.getItem(STORAGE_KEY);
      if (stored) {
        const settings = JSON.parse(stored);
        set({ ...defaultSettings, ...settings });
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  },
}));
