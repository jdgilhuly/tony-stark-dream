import { create } from 'zustand';
import { apiClient } from '../services/api';
import { offlineQueue } from '../services/offline';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

interface ConversationState {
  conversationId: string | null;
  messages: Message[];
  isLoading: boolean;
  error: string | null;

  loadConversation: () => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  clearConversation: () => Promise<void>;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversationId: null,
  messages: [],
  isLoading: false,
  error: null,

  loadConversation: async () => {
    try {
      const response = await apiClient.get('/conversation/current');
      const { conversationId, messages } = response.data;

      set({
        conversationId,
        messages: messages.map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp || m.created_at),
        })),
      });
    } catch (error) {
      // If no current conversation, start fresh
      set({ messages: [] });
    }
  },

  sendMessage: async (content: string) => {
    const { messages, conversationId } = get();

    // Optimistic update - add user message
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    };

    set({
      messages: [...messages, userMessage],
      isLoading: true,
      error: null,
    });

    try {
      const response = await apiClient.post('/conversation/message', {
        message: content,
        conversationId,
      });

      const { response: assistantContent, conversationId: newConvId } = response.data;

      // Add assistant response
      const assistantMessage: Message = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: assistantContent,
        timestamp: new Date(),
      };

      set((state) => ({
        conversationId: newConvId || state.conversationId,
        messages: [
          ...state.messages.filter((m) => m.id !== userMessage.id),
          { ...userMessage, id: `user-${Date.now()}` },
          assistantMessage,
        ],
        isLoading: false,
      }));
    } catch (error: any) {
      // If offline, queue the message
      if (!navigator.onLine) {
        offlineQueue.add({
          type: 'message',
          payload: { content, conversationId },
        });

        set({
          isLoading: false,
          error: 'Message queued for sending when online',
        });
        return;
      }

      // Remove optimistic message on error
      set((state) => ({
        messages: state.messages.filter((m) => m.id !== userMessage.id),
        isLoading: false,
        error: error.response?.data?.message || 'Failed to send message',
      }));
    }
  },

  clearConversation: async () => {
    try {
      await apiClient.post('/conversation/new');
      set({ conversationId: null, messages: [] });
    } catch (error) {
      console.error('Failed to clear conversation:', error);
    }
  },
}));
