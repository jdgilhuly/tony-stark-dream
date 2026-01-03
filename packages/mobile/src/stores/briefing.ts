import { create } from 'zustand';
import { apiClient } from '../services/api';
import { useVoiceStore } from './voice';

interface Weather {
  temperature: number;
  condition: string;
  humidity: number;
  wind: number;
  icon?: string;
}

interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  location?: string;
}

interface NewsArticle {
  title: string;
  source: string;
  url: string;
  publishedAt: Date;
}

interface Task {
  id: string;
  title: string;
  completed: boolean;
  priority: string;
}

interface Briefing {
  weather?: Weather;
  calendar?: CalendarEvent[];
  news?: NewsArticle[];
  tasks?: Task[];
  summary?: string;
  audioUrl?: string;
  generatedAt: Date;
}

interface BriefingState {
  briefing: Briefing | null;
  isLoading: boolean;
  isPlaying: boolean;
  error: string | null;

  fetchBriefing: () => Promise<void>;
  playBriefing: () => Promise<void>;
  stopBriefing: () => void;
}

export const useBriefingStore = create<BriefingState>((set, get) => ({
  briefing: null,
  isLoading: false,
  isPlaying: false,
  error: null,

  fetchBriefing: async () => {
    set({ isLoading: true, error: null });

    try {
      const response = await apiClient.get('/briefing/daily');
      const data = response.data;

      const briefing: Briefing = {
        weather: data.weather,
        calendar: data.calendar?.map((e: any) => ({
          ...e,
          start: new Date(e.start),
          end: new Date(e.end),
        })),
        news: data.news?.map((a: any) => ({
          ...a,
          publishedAt: new Date(a.publishedAt),
        })),
        tasks: data.tasks,
        summary: data.summary,
        audioUrl: data.audioUrl,
        generatedAt: new Date(data.generatedAt || Date.now()),
      };

      set({ briefing, isLoading: false });
    } catch (error: any) {
      set({
        isLoading: false,
        error: error.response?.data?.message || 'Failed to fetch briefing',
      });
    }
  },

  playBriefing: async () => {
    const { briefing } = get();
    if (!briefing?.summary) return;

    set({ isPlaying: true });

    try {
      const { speak } = useVoiceStore.getState();
      await speak(briefing.summary);
      set({ isPlaying: false });
    } catch (error) {
      set({ isPlaying: false });
    }
  },

  stopBriefing: () => {
    const { stopSpeaking } = useVoiceStore.getState();
    stopSpeaking();
    set({ isPlaying: false });
  },
}));
