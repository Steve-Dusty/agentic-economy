'use client';

import React, { useState, useEffect, useRef } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  MoreHorizontal,
  Trash2,
  Pencil,
  Check,
  X,
  Wrench,
  Workflow,
  CircleDashed,
} from 'lucide-react';
import { clsx } from 'clsx';
import { createPortal } from 'react-dom';
import { useConversationStore } from '@/lib/ai-assistant/conversation-store';
import type { Conversation, AssistantMode } from '@/lib/ai-assistant/types';

export function SidebarConversations() {
  const pathname = usePathname();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const [mounted, setMounted] = useState(false);
  const menuButtonRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

  const {
    conversations,
    activeConversationId,
    fetchConversations,
    selectConversation,
    deleteConversation,
    renameConversation,
  } = useConversationStore();

  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch conversations on mount
  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuOpenId) {
        const target = event.target as Node;
        const menuButton = menuButtonRefs.current.get(menuOpenId);
        if (menuButton && !menuButton.contains(target)) {
          setMenuOpenId(null);
        }
      }
    }

    if (menuOpenId) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [menuOpenId]);

  // Only show on Chat page
  const isChatPage = pathname === '/chat';
  if (!isChatPage) return null;

  const handleSelectConversation = async (id: string) => {
    await selectConversation(id);
    if (pathname !== '/chat') {
      router.push('/chat');
    }
  };

  const handleStartRename = (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuOpenId(null);
    setEditingId(conv.id);
    setEditValue(conv.title);
  };

  const handleSaveRename = async (id: string) => {
    if (editValue.trim()) {
      await renameConversation(id, editValue.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = () => {
    setEditingId(null);
    setEditValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent, id: string) => {
    if (e.key === 'Enter') {
      handleSaveRename(id);
    } else if (e.key === 'Escape') {
      handleCancelRename();
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setMenuOpenId(null);
    await deleteConversation(id);
  };

  const handleOpenMenu = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const button = menuButtonRefs.current.get(id);
    if (button) {
      const rect = button.getBoundingClientRect();
      setMenuPosition({
        top: rect.bottom + 4,
        left: rect.left - 100,
      });
    }
    setMenuOpenId(menuOpenId === id ? null : id);
  };

  const getModeIcon = (mode: AssistantMode) => {
    return mode === 'tool-router' ? (
      <Wrench className="w-4 h-4" />
    ) : (
      <Workflow className="w-4 h-4" />
    );
  };

  if (conversations.length === 0) {
    return null;
  }

  const menuContent = menuOpenId && (
    <div
      className="fixed w-40 bg-popover border border-border rounded-lg shadow-lg py-1 z-[9999] animate-scale-in"
      style={{
        top: menuPosition.top,
        left: menuPosition.left,
      }}
    >
      <button
        onClick={(e) => {
          const conv = conversations.find((c) => c.id === menuOpenId);
          if (conv) handleStartRename(conv, e);
        }}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-foreground hover:bg-muted transition-colors"
      >
        <Pencil className="w-4 h-4" />
        Rename
      </button>
      <button
        onClick={(e) => handleDelete(menuOpenId, e)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 transition-colors"
      >
        <Trash2 className="w-4 h-4" />
        Delete
      </button>
    </div>
  );

  return (
    <div className="flex-1 relative px-2 mt-4">
      <div className="flex flex-col flex-grow">
        {/* Recents Header */}
        <div className="flex items-center justify-between mb-2">
          <h3
            role="button"
            tabIndex={0}
            aria-expanded={isOpen}
            onClick={() => setIsOpen(!isOpen)}
            className="text-muted-foreground pb-2 mt-1 text-xs select-none pl-2 pr-2 group/header cursor-pointer flex items-center justify-between gap-2 w-full"
          >
            <span>Recents</span>
            <span className="text-muted-foreground/60 opacity-0 group-hover/header:opacity-75 transition-opacity">
              {isOpen ? 'Hide' : 'Show'}
            </span>
          </h3>
        </div>

        {/* Conversation List */}
        {isOpen && (
          <ul className="flex flex-col gap-px">
            {conversations.slice(0, 20).map((conv) => (
              <li key={conv.id} style={{ opacity: 1 }}>
                <div className="relative group">
                  {editingId === conv.id ? (
                    <div className="flex items-center gap-1 px-2 py-1.5">
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={(e) => handleKeyDown(e, conv.id)}
                        className={clsx(
                          'flex-1 bg-background border border-border rounded px-2 py-1',
                          'text-sm focus:outline-none focus:ring-1 focus:ring-primary'
                        )}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSaveRename(conv.id);
                        }}
                        className="p-1 text-green-500 hover:bg-green-500/10 rounded"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCancelRename();
                        }}
                        className="p-1 text-muted-foreground hover:bg-muted rounded"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleSelectConversation(conv.id)}
                      className={clsx(
                        'sidebar-nav-item',
                        'h-8 w-full rounded-lg px-4 py-1.5',
                        'active:bg-muted active:scale-100',
                        conv.id === activeConversationId && '!bg-foreground/[0.06]'
                      )}
                    >
                      <div className="-translate-x-2 w-full flex flex-row items-center justify-start gap-3">
                        <span
                          className={clsx(
                            'truncate text-sm whitespace-nowrap flex-1 text-left',
                            'group-hover:[mask-image:linear-gradient(to_right,hsl(var(--foreground))_78%,transparent_95%)]',
                            'group-focus-within:[mask-image:linear-gradient(to_right,hsl(var(--foreground))_78%,transparent_95%)]',
                            '[mask-size:100%_100%]',
                            conv.id === activeConversationId
                              ? '[mask-image:linear-gradient(to_right,hsl(var(--foreground))_78%,transparent_95%)] text-foreground'
                              : 'text-muted-foreground group-hover:text-foreground'
                          )}
                        >
                          {conv.title}
                        </span>
                      </div>
                    </button>
                  )}

                  {/* More Options Button */}
                  {editingId !== conv.id && (
                    <div
                      className={clsx(
                        'absolute right-0 top-1/2 -translate-y-1/2 transition-opacity duration-150',
                        conv.id === activeConversationId
                          ? 'block opacity-100'
                          : 'hidden group-hover:block group-focus-within:block opacity-0 group-hover:opacity-100 group-focus-within:opacity-100'
                      )}
                    >
                      <button
                        ref={(el) => {
                          if (el) menuButtonRefs.current.set(conv.id, el);
                        }}
                        onClick={(e) => handleOpenMenu(conv.id, e)}
                        className={clsx(
                          'inline-flex items-center justify-center',
                          'h-8 w-8 rounded-md',
                          'active:scale-95 transition-colors',
                          'hover:bg-muted',
                          menuOpenId === conv.id && '!bg-muted'
                        )}
                        type="button"
                        aria-label={`More options for ${conv.title}`}
                      >
                        <MoreHorizontal className="w-5 h-5 text-muted-foreground" />
                      </button>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* All Chats Link */}
        {isOpen && conversations.length > 20 && (
          <div className="relative group mt-1">
            <button
              onClick={() => {
                // Could navigate to a full chats list page
              }}
              className={clsx(
                'sidebar-nav-item',
                'h-8 w-full rounded-lg px-4 py-1.5',
                'active:bg-muted active:scale-100'
              )}
            >
              <div className="-translate-x-2 w-full flex flex-row items-center justify-start gap-3">
                <CircleDashed className="w-5 h-5 text-muted-foreground shrink-0" />
                <span className="truncate text-sm whitespace-nowrap flex-1 text-muted-foreground group-hover:text-foreground">
                  All chats
                </span>
              </div>
            </button>
          </div>
        )}
      </div>

      {/* Dropdown Menu Portal */}
      {menuOpenId && mounted && createPortal(menuContent, document.body)}
    </div>
  );
}
