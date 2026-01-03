/**
 * Push Notification Service for JARVIS Mobile App
 * Handles Firebase Cloud Messaging and local notifications
 */

import { Platform } from 'react-native';
import PushNotification, { Importance } from 'react-native-push-notification';
import PushNotificationIOS from '@react-native-community/push-notification-ios';
import { apiClient } from './api';

// Notification channel IDs
const CHANNELS = {
  DEFAULT: 'jarvis-default',
  BRIEFING: 'jarvis-briefing',
  REMINDERS: 'jarvis-reminders',
  URGENT: 'jarvis-urgent',
};

class NotificationService {
  private initialized: boolean = false;
  private deviceToken: string | null = null;

  async initialize(): Promise<void> {
    if (this.initialized) return;

    // Create notification channels for Android
    this.createChannels();

    // Configure push notifications
    PushNotification.configure({
      // Called when Token is generated
      onRegister: (token) => {
        console.log('Push notification token:', token);
        this.deviceToken = token.token;
        this.registerDevice(token.token, token.os);
      },

      // Called when a notification is received
      onNotification: (notification) => {
        console.log('Notification received:', notification);
        this.handleNotification(notification);

        // Required on iOS
        if (Platform.OS === 'ios') {
          notification.finish(PushNotificationIOS.FetchResult.NoData);
        }
      },

      // Called when a notification action is pressed
      onAction: (notification) => {
        console.log('Notification action:', notification.action);
        this.handleAction(notification);
      },

      // Called when registration fails
      onRegistrationError: (error) => {
        console.error('Push notification registration error:', error);
      },

      // iOS permissions
      permissions: {
        alert: true,
        badge: true,
        sound: true,
      },

      // Should the initial notification be popped automatically
      popInitialNotification: true,

      // Request permissions on iOS
      requestPermissions: Platform.OS === 'ios',
    });

    this.initialized = true;
  }

  private createChannels(): void {
    // Default channel
    PushNotification.createChannel(
      {
        channelId: CHANNELS.DEFAULT,
        channelName: 'JARVIS Notifications',
        channelDescription: 'General notifications from JARVIS',
        playSound: true,
        soundName: 'default',
        importance: Importance.DEFAULT,
        vibrate: true,
      },
      (created) => console.log(`Channel ${CHANNELS.DEFAULT} created:`, created)
    );

    // Briefing channel
    PushNotification.createChannel(
      {
        channelId: CHANNELS.BRIEFING,
        channelName: 'Daily Briefings',
        channelDescription: 'Your daily briefing notifications',
        playSound: true,
        soundName: 'default',
        importance: Importance.HIGH,
        vibrate: true,
      },
      (created) => console.log(`Channel ${CHANNELS.BRIEFING} created:`, created)
    );

    // Reminders channel
    PushNotification.createChannel(
      {
        channelId: CHANNELS.REMINDERS,
        channelName: 'Reminders',
        channelDescription: 'Task and event reminders',
        playSound: true,
        soundName: 'default',
        importance: Importance.HIGH,
        vibrate: true,
      },
      (created) => console.log(`Channel ${CHANNELS.REMINDERS} created:`, created)
    );

    // Urgent channel
    PushNotification.createChannel(
      {
        channelId: CHANNELS.URGENT,
        channelName: 'Urgent Notifications',
        channelDescription: 'High priority notifications',
        playSound: true,
        soundName: 'default',
        importance: Importance.HIGH,
        vibrate: true,
      },
      (created) => console.log(`Channel ${CHANNELS.URGENT} created:`, created)
    );
  }

  private async registerDevice(token: string, platform: string): Promise<void> {
    try {
      await apiClient.post('/notifications/devices', {
        token,
        platform: platform.toLowerCase(),
      });
      console.log('Device registered for push notifications');
    } catch (error) {
      console.error('Failed to register device:', error);
    }
  }

  private handleNotification(notification: any): void {
    const { data, title, message } = notification;

    // Handle different notification types
    switch (data?.type) {
      case 'briefing':
        // Navigate to briefing screen
        break;
      case 'reminder':
        // Show reminder
        break;
      case 'task_update':
        // Update task state
        break;
      default:
        // Default handling
        break;
    }
  }

  private handleAction(notification: any): void {
    const { action, data } = notification;

    switch (action) {
      case 'mark_read':
        this.markAsRead(data?.notificationId);
        break;
      case 'dismiss':
        // Just dismiss
        break;
      case 'open':
        // Navigate to relevant screen
        break;
    }
  }

  async markAsRead(notificationId: string): Promise<void> {
    try {
      await apiClient.post(`/notifications/${notificationId}/read`);
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
    }
  }

  // Local notification methods
  showLocalNotification(
    title: string,
    message: string,
    options: {
      channelId?: string;
      data?: object;
      playSound?: boolean;
      vibrate?: boolean;
    } = {}
  ): void {
    PushNotification.localNotification({
      channelId: options.channelId || CHANNELS.DEFAULT,
      title,
      message,
      userInfo: options.data,
      playSound: options.playSound ?? true,
      vibrate: options.vibrate ?? true,
      priority: 'high',
      visibility: 'public',
    });
  }

  scheduleLocalNotification(
    title: string,
    message: string,
    date: Date,
    options: {
      channelId?: string;
      data?: object;
      repeatType?: 'day' | 'week' | 'month';
    } = {}
  ): void {
    PushNotification.localNotificationSchedule({
      channelId: options.channelId || CHANNELS.REMINDERS,
      title,
      message,
      date,
      userInfo: options.data,
      repeatType: options.repeatType,
      allowWhileIdle: true,
    });
  }

  cancelAllNotifications(): void {
    PushNotification.cancelAllLocalNotifications();
  }

  cancelNotification(id: string): void {
    PushNotification.cancelLocalNotification(id);
  }

  async getScheduledNotifications(): Promise<any[]> {
    return new Promise((resolve) => {
      PushNotification.getScheduledLocalNotifications((notifications) => {
        resolve(notifications);
      });
    });
  }

  // Request permissions (iOS)
  async requestPermissions(): Promise<boolean> {
    if (Platform.OS === 'ios') {
      const permissions = await PushNotification.requestPermissions(['alert', 'badge', 'sound']);
      return permissions.alert || permissions.badge || permissions.sound;
    }
    return true;
  }

  // Check if permissions are granted
  async checkPermissions(): Promise<boolean> {
    return new Promise((resolve) => {
      PushNotification.checkPermissions((permissions) => {
        resolve(permissions.alert || permissions.badge || permissions.sound);
      });
    });
  }

  // Get badge count (iOS)
  async getBadgeCount(): Promise<number> {
    if (Platform.OS === 'ios') {
      return new Promise((resolve) => {
        PushNotificationIOS.getApplicationIconBadgeNumber((count) => {
          resolve(count);
        });
      });
    }
    return 0;
  }

  // Set badge count (iOS)
  setBadgeCount(count: number): void {
    if (Platform.OS === 'ios') {
      PushNotificationIOS.setApplicationIconBadgeNumber(count);
    }
  }

  // Get device token
  getDeviceToken(): string | null {
    return this.deviceToken;
  }

  // Unregister device
  async unregisterDevice(): Promise<void> {
    if (this.deviceToken) {
      try {
        await apiClient.delete(`/notifications/devices/${this.deviceToken}`);
        this.deviceToken = null;
      } catch (error) {
        console.error('Failed to unregister device:', error);
      }
    }
  }
}

// Singleton instance
export const notificationService = new NotificationService();
