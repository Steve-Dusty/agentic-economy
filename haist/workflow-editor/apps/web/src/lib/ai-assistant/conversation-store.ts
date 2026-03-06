/**
 * Conversation Store
 *
 * Zustand store for managing AI Assistant conversation state.
 * Shared between Sidebar and AIAssistantClient.
 */

import { create } from 'zustand';
import type {
  Conversation,
  AssistantMode,
  ChatMessage,
  ToolRouterMessage,
} from './types';

interface ConversationState {
  conversations: Conversation[];
  activeConversationId: string | null;
  isLoading: boolean;

  // Actions
  setConversations: (conversations: Conversation[]) => void;
  setActiveConversationId: (id: string | null) => void;
  setLoading: (loading: boolean) => void;
  clearActiveConversation: () => void;

  // API actions
  fetchConversations: () => Promise<void>;
  createConversation: (mode: AssistantMode) => Promise<Conversation | null>;
  selectConversation: (id: string) => Promise<Conversation | null>;
  deleteConversation: (id: string) => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
  updateConversationMode: (id: string, mode: AssistantMode) => Promise<void>;
  addMessage: (
    conversationId: string,
    message: ChatMessage | ToolRouterMessage,
    mode: AssistantMode
  ) => Promise<void>;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  isLoading: false,

  setConversations: (conversations) => set({ conversations }),
  setActiveConversationId: (id) => set({ activeConversationId: id }),
  setLoading: (loading) => set({ isLoading: loading }),
  clearActiveConversation: () => set({ activeConversationId: null }),

  fetchConversations: async () => {
    try {
      const response = await fetch('/api/ai-assistant/conversations');
      if (response.ok) {
        const data = await response.json();
        set({ conversations: data.conversations || [] });
      }
    } catch (err) {
      console.error('Failed to fetch conversations:', err);
    }
  },

  createConversation: async (mode) => {
    try {
      const response = await fetch('/api/ai-assistant/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });

      if (response.ok) {
        const data = await response.json();
        const newConv = data.conversation;
        set((state) => ({
          conversations: [newConv, ...state.conversations],
          activeConversationId: newConv.id,
        }));
        return newConv;
      }
    } catch (err) {
      console.error('Failed to create conversation:', err);
    }
    return null;
  },

  selectConversation: async (id) => {
    try {
      const response = await fetch(`/api/ai-assistant/conversations/${id}`);
      if (response.ok) {
        const data = await response.json();
        set({ activeConversationId: id });
        return data.conversation;
      }
    } catch (err) {
      console.error('Failed to select conversation:', err);
    }
    return null;
  },

  deleteConversation: async (id) => {
    try {
      const response = await fetch(`/api/ai-assistant/conversations/${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        const { conversations, activeConversationId } = get();
        const remaining = conversations.filter((c) => c.id !== id);
        set({
          conversations: remaining,
          activeConversationId:
            id === activeConversationId
              ? remaining.length > 0
                ? remaining[0].id
                : null
              : activeConversationId,
        });
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  },

  renameConversation: async (id, title) => {
    try {
      const response = await fetch(`/api/ai-assistant/conversations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });

      if (response.ok) {
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === id ? { ...c, title } : c
          ),
        }));
      }
    } catch (err) {
      console.error('Failed to rename conversation:', err);
    }
  },

  updateConversationMode: async (id, mode) => {
    try {
      await fetch(`/api/ai-assistant/conversations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });

      set((state) => ({
        conversations: state.conversations.map((c) =>
          c.id === id ? { ...c, mode } : c
        ),
      }));
    } catch (err) {
      console.error('Failed to update conversation mode:', err);
    }
  },

  addMessage: async (conversationId, message, mode) => {
    try {
      await fetch(`/api/ai-assistant/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, mode }),
      });

      // Refresh conversations to get updated title
      await get().fetchConversations();
    } catch (err) {
      console.error('Failed to add message:', err);
    }
  },
}));
