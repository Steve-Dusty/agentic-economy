"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Bell } from "lucide-react";
import { clsx } from "clsx";

interface NotificationBellProps {
  isOpen?: boolean;
  onToggle?: () => void;
}

export function NotificationBell({ isOpen, onToggle }: NotificationBellProps) {
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchCount = useCallback(async () => {
    try {
      const res = await fetch("/api/notifications?unreadOnly=true&limit=0");
      if (res.ok) {
        const data = await res.json();
        setUnreadCount(data.unreadCount ?? 0);
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchCount();
    const interval = setInterval(fetchCount, 30000);
    return () => clearInterval(interval);
  }, [fetchCount]);

  // Refresh count when panel closes
  useEffect(() => {
    if (!isOpen) fetchCount();
  }, [isOpen, fetchCount]);

  return (
    <button
      onClick={onToggle}
      className={clsx(
        "relative inline-flex items-center justify-center",
        "h-8 w-8 rounded-md",
        "hover:bg-muted transition-colors group",
        "active:scale-95",
        isOpen && "bg-muted"
      )}
      type="button"
      aria-label="Notifications"
    >
      <Bell className={clsx(
        "w-5 h-5 transition-colors",
        isOpen ? "text-foreground" : "text-muted-foreground group-hover:text-foreground"
      )} />
      {unreadCount > 0 && (
        <span className="absolute -top-1 -right-1 flex items-center justify-center min-w-[16px] h-4 px-1 rounded-full bg-destructive text-destructive-foreground text-[10px] font-semibold leading-none ring-2 ring-card">
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      )}
    </button>
  );
}
