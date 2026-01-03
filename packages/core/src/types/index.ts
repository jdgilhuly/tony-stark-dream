// User types
export interface User {
  id: string;
  email: string;
  name: string;
  preferredTitle: string;
  timezone: string;
  preferences: UserPreferences;
  createdAt: Date;
  updatedAt: Date;
}

export interface UserPreferences {
  voiceEnabled: boolean;
  wakeWord: string;
  preferredVoice: string;
  briefingTime: string;
  newsCategories: string[];
  temperatureUnit: 'celsius' | 'fahrenheit';
}

// Conversation types
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: MessageMetadata;
}

export interface MessageMetadata {
  audioUrl?: string;
  duration?: number;
  transcriptionConfidence?: number;
  tokens?: number;
}

export interface Conversation {
  id: string;
  userId: string;
  messages: Message[];
  startedAt: Date;
  lastMessageAt: Date;
  summary?: string;
}

export interface ConversationRequest {
  message: string;
  conversationId?: string;
  audioData?: ArrayBuffer;
  contextHints?: string[];
}

export interface ConversationResponse {
  id: string;
  conversationId: string;
  message: Message;
  audioUrl?: string;
  suggestedActions?: SuggestedAction[];
}

export interface SuggestedAction {
  label: string;
  action: string;
  parameters?: Record<string, unknown>;
}

// Briefing types
export interface DailyBriefing {
  id: string;
  userId: string;
  generatedAt: Date;
  summary: string;
  weather: WeatherInfo;
  news: NewsItem[];
  calendar: CalendarEvent[];
  tasks: TaskItem[];
}

export interface WeatherInfo {
  location: string;
  current: {
    temperature: number;
    condition: string;
    humidity: number;
    windSpeed: number;
  };
  forecast: WeatherForecast[];
}

export interface WeatherForecast {
  date: Date;
  high: number;
  low: number;
  condition: string;
  precipitationChance: number;
}

export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  source: string;
  url: string;
  category: string;
  publishedAt: Date;
}

export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  startTime: Date;
  endTime: Date;
  location?: string;
  isAllDay: boolean;
  attendees?: string[];
}

export interface TaskItem {
  id: string;
  title: string;
  description?: string;
  dueDate?: Date;
  priority: 'low' | 'medium' | 'high';
  status: 'pending' | 'in_progress' | 'completed';
}

// Voice types
export interface VoiceConfig {
  enabled: boolean;
  wakeWord: string;
  language: string;
  voice: string;
  speakingRate: number;
}

export interface TranscriptionResult {
  text: string;
  confidence: number;
  isFinal: boolean;
  alternatives?: Array<{ text: string; confidence: number }>;
}

export interface SynthesisResult {
  audioData: ArrayBuffer;
  contentType: string;
  text: string;
  duration: number;
}

// API types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  metadata?: ResponseMetadata;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ResponseMetadata {
  requestId: string;
  timestamp: Date;
  processingTime: number;
}

// Auth types
export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: Date;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  tokens: AuthTokens | null;
}

// WebSocket types
export interface WebSocketMessage<T = unknown> {
  type: string;
  payload: T;
  timestamp: Date;
  correlationId?: string;
}

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error';

// Connection types
export interface ConnectionConfig {
  baseUrl: string;
  wsUrl: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
}
