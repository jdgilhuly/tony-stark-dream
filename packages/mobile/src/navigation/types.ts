/**
 * Navigation type definitions for JARVIS Mobile.
 */

import type { NavigatorScreenParams } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';
import type { CompositeScreenProps } from '@react-navigation/native';

/**
 * Root stack navigator params.
 */
export type RootStackParamList = {
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
  Onboarding: undefined;
  Settings: undefined;
  ConversationDetail: { conversationId: string };
  VoiceCall: { conversationId?: string };
  BriefingDetail: { briefingId: string };
  TaskDetail: { taskId: string };
  CalendarEventDetail: { eventId: string };
};

/**
 * Auth stack navigator params.
 */
export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
  ResetPassword: { token: string };
};

/**
 * Main tab navigator params.
 */
export type MainTabParamList = {
  Chat: undefined;
  Dashboard: undefined;
  Briefing: undefined;
  Profile: undefined;
};

/**
 * Chat stack navigator params (nested in Chat tab).
 */
export type ChatStackParamList = {
  ConversationList: undefined;
  Conversation: { conversationId: string };
  NewConversation: undefined;
};

/**
 * Dashboard stack navigator params (nested in Dashboard tab).
 */
export type DashboardStackParamList = {
  DashboardHome: undefined;
  Weather: undefined;
  Calendar: undefined;
  Tasks: undefined;
  News: undefined;
};

/**
 * Screen props types for type-safe navigation.
 */

// Root stack screens
export type RootStackScreenProps<T extends keyof RootStackParamList> =
  NativeStackScreenProps<RootStackParamList, T>;

// Auth stack screens
export type AuthStackScreenProps<T extends keyof AuthStackParamList> =
  CompositeScreenProps<
    NativeStackScreenProps<AuthStackParamList, T>,
    RootStackScreenProps<keyof RootStackParamList>
  >;

// Main tab screens
export type MainTabScreenProps<T extends keyof MainTabParamList> =
  CompositeScreenProps<
    BottomTabScreenProps<MainTabParamList, T>,
    RootStackScreenProps<keyof RootStackParamList>
  >;

// Chat stack screens
export type ChatStackScreenProps<T extends keyof ChatStackParamList> =
  CompositeScreenProps<
    NativeStackScreenProps<ChatStackParamList, T>,
    MainTabScreenProps<'Chat'>
  >;

// Dashboard stack screens
export type DashboardStackScreenProps<T extends keyof DashboardStackParamList> =
  CompositeScreenProps<
    NativeStackScreenProps<DashboardStackParamList, T>,
    MainTabScreenProps<'Dashboard'>
  >;

/**
 * Navigation prop type for use in components.
 */
export type NavigationProp = RootStackScreenProps<keyof RootStackParamList>['navigation'];

/**
 * Declare global navigation types for useNavigation hook.
 */
declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
