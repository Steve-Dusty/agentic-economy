"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  X,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Lightbulb,
  Info,
  CheckCheck,
  Loader2,
} from "lucide-react";
import { clsx } from "clsx";
import type { Notification, NotificationType } from "@/lib/notifications/types";

const typeConfig: Record<
  NotificationType,
  { icon: React.ComponentType<{ className?: string }>; color: string }
> = {
  execution_success: { icon: CheckCircle2, color: "text-green-500" },
  execution_failure: { icon: XCircle, color: "text-destructive" },
  needs_approval: { icon: AlertTriangle, color: "text-yellow-500" },
  suggestion: { icon: Lightbulb, color: "text-blue-500" },
  info: { icon: Info, color: "text-muted-foreground" },
};

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface NotificationPanelProps {
  onClose: () => void;
}

export function NotificationPanel({ onClose }: NotificationPanelProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const LIMIT = 20;

  const fetchNotifications = useCallback(async (offset = 0, append = false) => {
    try {
      const res = await fetch(`/api/notifications?limit=${LIMIT}&offset=${offset}`);
      if (res.ok) {
        const data = await res.json();
        setNotifications((prev) =>
          append ? [...prev, ...data.notifications] : data.notifications
        );
        setTotal(data.total);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const markAsRead = async (id: string) => {
    await fetch(`/api/notifications/${id}/read`, { method: "PUT" });
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const markAllRead = async () => {
    await fetch("/api/notifications/read-all", { method: "PUT" });
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const deleteNotification = async (id: string) => {
    await fetch(`/api/notifications/${id}`, { method: "DELETE" });
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    setTotal((t) => t - 1);
  };

  const loadMore = () => {
    setLoadingMore(true);
    fetchNotifications(notifications.length, true);
  };

  const hasMore = notifications.length < total;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-[60]"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-screen w-96 max-w-[calc(100vw-3rem)] bg-card border-l border-border shadow-xl z-[61] flex flex-col animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">Notifications</h2>
          <div className="flex items-center gap-1">
            <button
              onClick={markAllRead}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
              type="button"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark all read
            </button>
            <button
              onClick={onClose}
              className="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-muted transition-colors"
              type="button"
              aria-label="Close"
            >
              <X className="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
            </div>
          ) : notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Info className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-sm">No notifications yet</p>
            </div>
          ) : (
            <>
              {notifications.map((n) => {
                const config = typeConfig[n.type] || typeConfig.info;
                const Icon = config.icon;
                return (
                  <div
                    key={n.id}
                    className={clsx(
                      "flex gap-3 px-4 py-3 border-b border-border/50 hover:bg-muted/50 transition-colors cursor-pointer",
                      !n.read && "bg-primary/5"
                    )}
                    onClick={() => !n.read && markAsRead(n.id)}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      <Icon className={clsx("w-4 h-4", config.color)} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p
                          className={clsx(
                            "text-sm truncate",
                            !n.read ? "font-medium text-foreground" : "text-muted-foreground"
                          )}
                        >
                          {n.title}
                        </p>
                        {!n.read && (
                          <span className="flex-shrink-0 w-2 h-2 rounded-full bg-primary mt-1.5" />
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">
                        {n.body}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] text-muted-foreground/70">
                          {timeAgo(n.createdAt)}
                        </span>
                        {n.ruleId && (
                          <Link
                            href={`/automations?rule=${n.ruleId}`}
                            className="text-[10px] text-primary hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            View rule
                          </Link>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteNotification(n.id);
                          }}
                          className="text-[10px] text-muted-foreground/50 hover:text-destructive ml-auto"
                          type="button"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
              {hasMore && (
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="w-full py-3 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                  type="button"
                >
                  {loadingMore ? (
                    <Loader2 className="w-4 h-4 mx-auto animate-spin" />
                  ) : (
                    "Load more"
                  )}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
