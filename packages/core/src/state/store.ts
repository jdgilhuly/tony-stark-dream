import { createStore } from 'zustand/vanilla';
import type {
  AuthState,
  Conversation,
  DailyBriefing,
  Message,
  User,
  VoiceConfig,
  WebSocketStatus,
} from '../types/index.js';

// Conversation State
export interface ConversationState {
  currentConversation: Conversation | null;
  conversations: Conversation[];
  isLoading: boolean;
  error: string | null;
}

export interface ConversationActions {
  setCurrentConversation: (conversation: Conversation | null) => void;
  addMessage: (message: Message) => void;
  setConversations: (conversations: Conversation[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export type ConversationStore = ConversationState & ConversationActions;

export const createConversationStore = () =>
  createStore<ConversationStore>((set) => ({
    currentConversation: null,
    conversations: [],
    isLoading: false,
    error: null,

    setCurrentConversation: (conversation) =>
      set({ currentConversation: conversation }),

    addMessage: (message) =>
      set((state) => {
        if (!state.currentConversation) return state;
        return {
          currentConversation: {
            ...state.currentConversation,
            messages: [...state.currentConversation.messages, message],
            lastMessageAt: message.timestamp,
          },
        };
      }),

    setConversations: (conversations) => set({ conversations }),

    setLoading: (isLoading) => set({ isLoading }),

    setError: (error) => set({ error }),

    clearError: () => set({ error: null }),
  }));

// Auth State
export interface AuthStoreState extends AuthState {
  isLoading: boolean;
  error: string | null;
}

export interface AuthActions {
  setUser: (user: User | null) => void;
  setAuthenticated: (isAuthenticated: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  logout: () => void;
}

export type AuthStore = AuthStoreState & AuthActions;

export const createAuthStore = () =>
  createStore<AuthStore>((set) => ({
    isAuthenticated: false,
    user: null,
    tokens: null,
    isLoading: false,
    error: null,

    setUser: (user) => set({ user, isAuthenticated: !!user }),

    setAuthenticated: (isAuthenticated) => set({ isAuthenticated }),

    setLoading: (isLoading) => set({ isLoading }),

    setError: (error) => set({ error }),

    logout: () =>
      set({
        isAuthenticated: false,
        user: null,
        tokens: null,
        error: null,
      }),
  }));

// Voice State
export interface VoiceState {
  config: VoiceConfig;
  isListening: boolean;
  isSpeaking: boolean;
  isProcessing: boolean;
  wakeWordDetected: boolean;
  currentTranscription: string;
  error: string | null;
}

export interface VoiceActions {
  setConfig: (config: Partial<VoiceConfig>) => void;
  setListening: (listening: boolean) => void;
  setSpeaking: (speaking: boolean) => void;
  setProcessing: (processing: boolean) => void;
  setWakeWordDetected: (detected: boolean) => void;
  setTranscription: (text: string) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export type VoiceStore = VoiceState & VoiceActions;

const defaultVoiceConfig: VoiceConfig = {
  enabled: true,
  wakeWord: 'jarvis',
  language: 'en-US',
  voice: 'Brian',
  speakingRate: 1.0,
};

export const createVoiceStore = () =>
  createStore<VoiceStore>((set) => ({
    config: defaultVoiceConfig,
    isListening: false,
    isSpeaking: false,
    isProcessing: false,
    wakeWordDetected: false,
    currentTranscription: '',
    error: null,

    setConfig: (config) =>
      set((state) => ({ config: { ...state.config, ...config } })),

    setListening: (isListening) => set({ isListening }),

    setSpeaking: (isSpeaking) => set({ isSpeaking }),

    setProcessing: (isProcessing) => set({ isProcessing }),

    setWakeWordDetected: (wakeWordDetected) => set({ wakeWordDetected }),

    setTranscription: (currentTranscription) => set({ currentTranscription }),

    setError: (error) => set({ error }),

    reset: () =>
      set({
        isListening: false,
        isSpeaking: false,
        isProcessing: false,
        wakeWordDetected: false,
        currentTranscription: '',
        error: null,
      }),
  }));

// Briefing State
export interface BriefingState {
  currentBriefing: DailyBriefing | null;
  isLoading: boolean;
  lastFetchedAt: Date | null;
  error: string | null;
}

export interface BriefingActions {
  setBriefing: (briefing: DailyBriefing | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export type BriefingStore = BriefingState & BriefingActions;

export const createBriefingStore = () =>
  createStore<BriefingStore>((set) => ({
    currentBriefing: null,
    isLoading: false,
    lastFetchedAt: null,
    error: null,

    setBriefing: (currentBriefing) =>
      set({ currentBriefing, lastFetchedAt: new Date() }),

    setLoading: (isLoading) => set({ isLoading }),

    setError: (error) => set({ error }),
  }));

// Connection State
export interface ConnectionState {
  status: WebSocketStatus;
  lastConnectedAt: Date | null;
  reconnectAttempts: number;
  error: string | null;
}

export interface ConnectionActions {
  setStatus: (status: WebSocketStatus) => void;
  setError: (error: string | null) => void;
  incrementReconnectAttempts: () => void;
  resetReconnectAttempts: () => void;
}

export type ConnectionStore = ConnectionState & ConnectionActions;

export const createConnectionStore = () =>
  createStore<ConnectionStore>((set) => ({
    status: 'disconnected',
    lastConnectedAt: null,
    reconnectAttempts: 0,
    error: null,

    setStatus: (status) =>
      set((state) => ({
        status,
        lastConnectedAt: status === 'connected' ? new Date() : state.lastConnectedAt,
      })),

    setError: (error) => set({ error }),

    incrementReconnectAttempts: () =>
      set((state) => ({ reconnectAttempts: state.reconnectAttempts + 1 })),

    resetReconnectAttempts: () => set({ reconnectAttempts: 0 }),
  }));

// Combined App Store
export interface AppState {
  conversation: ReturnType<typeof createConversationStore>;
  auth: ReturnType<typeof createAuthStore>;
  voice: ReturnType<typeof createVoiceStore>;
  briefing: ReturnType<typeof createBriefingStore>;
  connection: ReturnType<typeof createConnectionStore>;
}

export const createAppStores = (): AppState => ({
  conversation: createConversationStore(),
  auth: createAuthStore(),
  voice: createVoiceStore(),
  briefing: createBriefingStore(),
  connection: createConnectionStore(),
});
