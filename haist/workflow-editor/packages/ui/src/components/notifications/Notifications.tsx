'use client';

/**
 * Notifications component - displays toast notifications
 */

import React, { useEffect } from 'react';
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { clsx } from 'clsx';
import { useUIStore, type Notification } from '@workflow-editor/state';

/**
 * Get icon for notification type
 */
function getIcon(type: Notification['type']) {
  switch (type) {
    case 'success':
      return <CheckCircle className="w-5 h-5 text-green-500" />;
    case 'error':
      return <AlertCircle className="w-5 h-5 text-red-500" />;
    case 'warning':
      return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
    case 'info':
      return <Info className="w-5 h-5 text-blue-500" />;
  }
}

/**
 * Single notification item
 */
function NotificationItem({ notification }: { notification: Notification }) {
  const removeNotification = useUIStore((state) => state.removeNotification);

  useEffect(() => {
    const duration = notification.duration ?? 4000;
    const timer = setTimeout(() => {
      removeNotification(notification.id);
    }, duration);

    return () => clearTimeout(timer);
  }, [notification.id, notification.duration, removeNotification]);

  return (
    <div
      className={clsx(
        'flex items-start gap-3 p-4 rounded-lg shadow-lg border',
        'bg-card text-card-foreground',
        'animate-in slide-in-from-right-full fade-in duration-300'
      )}
    >
      {getIcon(notification.type)}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm">{notification.title}</p>
        {notification.message && (
          <p className="text-xs text-muted-foreground mt-0.5">
            {notification.message}
          </p>
        )}
      </div>
      <button
        onClick={() => removeNotification(notification.id)}
        className="p-1 hover:bg-accent rounded transition-colors"
      >
        <X className="w-4 h-4 text-muted-foreground" />
      </button>
    </div>
  );
}

/**
 * Notifications container
 */
export function Notifications() {
  const notifications = useUIStore((state) => state.notifications);

  if (notifications.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {notifications.map((notification) => (
        <NotificationItem key={notification.id} notification={notification} />
      ))}
    </div>
  );
}
