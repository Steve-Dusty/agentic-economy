import type { Notification, NotificationInput } from './types';

/** In-memory store (use globalThis to survive Next.js dev-mode HMR) */
const g = globalThis as unknown as { __notifications?: Notification[] };
if (!g.__notifications) g.__notifications = [];
const notifications = g.__notifications;

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substring(2, 10);
}

export const notificationsStorage = {
  async create(input: NotificationInput): Promise<Notification> {
    const notification: Notification = {
      id: generateId(),
      userId: input.userId,
      type: input.type,
      title: input.title,
      body: input.body,
      ruleId: input.ruleId,
      ruleName: input.ruleName,
      logId: input.logId,
      read: false,
      createdAt: new Date().toISOString(),
    };
    notifications.push(notification);
    return notification;
  },

  async getByUserId(
    userId: string,
    options?: { unreadOnly?: boolean; limit?: number; offset?: number }
  ): Promise<{ notifications: Notification[]; total: number; unreadCount: number }> {
    const { unreadOnly = false, limit = 20, offset = 0 } = options || {};

    let filtered = notifications.filter((n) => n.userId === userId);
    if (unreadOnly) {
      filtered = filtered.filter((n) => !n.read);
    }

    // Sort by createdAt descending
    filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    const total = filtered.length;
    const unreadCount = notifications.filter((n) => n.userId === userId && !n.read).length;
    const paginated = filtered.slice(offset, offset + limit);

    return { notifications: paginated, total, unreadCount };
  },

  async markAsRead(id: string, userId: string): Promise<void> {
    const notification = notifications.find((n) => n.id === id && n.userId === userId);
    if (notification) {
      notification.read = true;
    }
  },

  async markAllAsRead(userId: string): Promise<void> {
    for (const n of notifications) {
      if (n.userId === userId && !n.read) {
        n.read = true;
      }
    }
  },

  async delete(id: string, userId: string): Promise<void> {
    const index = notifications.findIndex((n) => n.id === id && n.userId === userId);
    if (index !== -1) {
      notifications.splice(index, 1);
    }
  },

  async getUnreadCount(userId: string): Promise<number> {
    return notifications.filter((n) => n.userId === userId && !n.read).length;
  },
};
