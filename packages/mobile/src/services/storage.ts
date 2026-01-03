import AsyncStorage from '@react-native-async-storage/async-storage';

// Initialize storage - can be used for any setup needed
export async function initializeStorage(): Promise<void> {
  try {
    // Check if this is first launch
    const firstLaunch = await AsyncStorage.getItem('@jarvis/first_launch');
    if (!firstLaunch) {
      // Set default values
      await AsyncStorage.setItem('@jarvis/first_launch', 'false');
      console.log('Storage initialized for first launch');
    }
  } catch (error) {
    console.error('Storage initialization error:', error);
  }
}

// Generic storage helpers
export const storage = {
  async get<T>(key: string): Promise<T | null> {
    try {
      const value = await AsyncStorage.getItem(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error(`Failed to get ${key}:`, error);
      return null;
    }
  },

  async set<T>(key: string, value: T): Promise<void> {
    try {
      await AsyncStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error(`Failed to set ${key}:`, error);
    }
  },

  async remove(key: string): Promise<void> {
    try {
      await AsyncStorage.removeItem(key);
    } catch (error) {
      console.error(`Failed to remove ${key}:`, error);
    }
  },

  async clear(): Promise<void> {
    try {
      await AsyncStorage.clear();
    } catch (error) {
      console.error('Failed to clear storage:', error);
    }
  },

  async getAllKeys(): Promise<readonly string[]> {
    try {
      return await AsyncStorage.getAllKeys();
    } catch (error) {
      console.error('Failed to get all keys:', error);
      return [];
    }
  },
};
