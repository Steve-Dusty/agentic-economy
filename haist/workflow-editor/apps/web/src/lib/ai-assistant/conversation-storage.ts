/**
 * Conversation Storage Service
 *
 * In-memory storage for AI Assistant chat conversations.
 * Data resets on server restart.
 */

import { v4 as uuidv4 } from 'uuid';
import type {
  Conversation,
  AssistantMode,
  ChatMessage,
  ToolRouterMessage,
} from './types';

/** In-memory stores (use globalThis to survive Next.js dev-mode HMR) */
const g = globalThis as unknown as {
  __conversations?: Map<string, Conversation & { userId: string; summarizedAt?: string }>;
  __conversationMessages?: Map<string, (ToolRouterMessage & { conversationId: string })[]>;
};
if (!g.__conversations) g.__conversations = new Map();
if (!g.__conversationMessages) g.__conversationMessages = new Map();
const conversations = g.__conversations;
const messages = g.__conversationMessages;

/**
 * Generate a title from message content
 */
function generateTitle(content: string): string {
  const cleaned = content.trim().replace(/\s+/g, ' ');
  if (cleaned.length <= 40) {
    return cleaned;
  }
  return cleaned.substring(0, 40).trim() + '...';
}

/**
 * Conversation storage operations
 */
export const conversationsStorage = {
  /**
   * Get all conversations for a user (with messages)
   */
  async getByUserId(userId: string): Promise<Conversation[]> {
    const userConvs = Array.from(conversations.values())
      .filter((c) => c.userId === userId)
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());

    return userConvs.map((conv) => {
      const convMessages = messages.get(conv.id) || [];
      const toolRouterMessages: ToolRouterMessage[] = convMessages
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
        .map(({ conversationId, ...msg }) => msg);

      return {
        id: conv.id,
        title: conv.title,
        mode: conv.mode,
        messages: [],
        toolRouterMessages,
        createdAt: conv.createdAt,
        updatedAt: conv.updatedAt,
      };
    });
  },

  /**
   * Get a specific conversation by ID
   */
  async get(id: string): Promise<Conversation | null> {
    const conv = conversations.get(id);
    if (!conv) return null;

    const convMessages = messages.get(id) || [];
    const toolRouterMessages: ToolRouterMessage[] = convMessages
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
      .map(({ conversationId, ...msg }) => msg);

    return {
      id: conv.id,
      title: conv.title,
      mode: conv.mode,
      messages: [],
      toolRouterMessages,
      createdAt: conv.createdAt,
      updatedAt: conv.updatedAt,
    };
  },

  /**
   * Create a new conversation
   */
  async create(userId: string, mode: AssistantMode): Promise<Conversation> {
    const id = uuidv4();
    const now = new Date().toISOString();

    const conv = {
      id,
      userId,
      title: 'New conversation',
      mode,
      messages: [] as ChatMessage[],
      toolRouterMessages: [] as ToolRouterMessage[],
      createdAt: now,
      updatedAt: now,
    };

    conversations.set(id, conv);
    messages.set(id, []);

    return {
      id,
      title: 'New conversation',
      mode,
      messages: [],
      toolRouterMessages: [],
      createdAt: now,
      updatedAt: now,
    };
  },

  /**
   * Add a message to a conversation
   */
  async addMessage(
    conversationId: string,
    message: ChatMessage | ToolRouterMessage,
    mode: AssistantMode
  ): Promise<void> {
    const id = message.id || uuidv4();

    const toolMsg = message as ToolRouterMessage;
    const storedMessage = {
      id,
      conversationId,
      role: toolMsg.role,
      content: toolMsg.content,
      timestamp: toolMsg.timestamp,
      toolCalls: toolMsg.toolCalls,
    };

    const convMessages = messages.get(conversationId);
    if (convMessages) {
      convMessages.push(storedMessage);
    } else {
      messages.set(conversationId, [storedMessage]);
    }

    // Update conversation title if it's the first user message
    const allMessages = messages.get(conversationId) || [];
    if (allMessages.length === 1 && message.role === 'user') {
      const conv = conversations.get(conversationId);
      if (conv) {
        conv.title = generateTitle(message.content);
      }
    }
  },

  /**
   * Update conversation mode
   */
  async updateMode(id: string, mode: AssistantMode): Promise<void> {
    const conv = conversations.get(id);
    if (conv) {
      conv.mode = mode;
      conv.updatedAt = new Date().toISOString();
    }
  },

  /**
   * Rename a conversation
   */
  async rename(id: string, title: string): Promise<void> {
    const conv = conversations.get(id);
    if (conv) {
      conv.title = title;
      conv.updatedAt = new Date().toISOString();
    }
  },

  /**
   * Delete a conversation
   */
  async delete(id: string): Promise<boolean> {
    messages.delete(id);
    return conversations.delete(id);
  },

  /**
   * Find conversations that have been inactive for a given threshold
   * and haven't been summarized yet
   */
  async findInactiveConversations(thresholdMs: number): Promise<Conversation[]> {
    const cutoffTime = Date.now() - thresholdMs;

    const inactive = Array.from(conversations.values())
      .filter(
        (c) =>
          new Date(c.updatedAt).getTime() < cutoffTime &&
          !c.summarizedAt
      )
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
      .slice(0, 50);

    return inactive.map((conv) => {
      const convMessages = messages.get(conv.id) || [];
      const toolRouterMessages: ToolRouterMessage[] = convMessages
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
        .map(({ conversationId, ...msg }) => msg);

      return {
        id: conv.id,
        title: conv.title,
        mode: conv.mode,
        messages: [],
        toolRouterMessages,
        createdAt: conv.createdAt,
        updatedAt: conv.updatedAt,
      };
    });
  },

  /**
   * Mark a conversation as summarized
   */
  async markAsSummarized(id: string): Promise<void> {
    const conv = conversations.get(id);
    if (conv) {
      conv.summarizedAt = new Date().toISOString();
    }
  },

  /**
   * Get the user ID for a conversation
   */
  async getUserId(id: string): Promise<string | null> {
    const conv = conversations.get(id);
    return conv ? conv.userId : null;
  },
};
