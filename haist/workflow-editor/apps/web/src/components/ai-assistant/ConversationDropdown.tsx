'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  ChevronDown,
  Plus,
  MessageSquare,
  Trash2,
  Pencil,
  Check,
  X,
  Wrench,
  Workflow,
} from 'lucide-react';
import { clsx } from 'clsx';
import type { Conversation, AssistantMode } from '@/lib/ai-assistant/types';

interface ConversationDropdownProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
}

export function ConversationDropdown({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRenameConversation,
}: ConversationDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId
  );

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setEditingId(null);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Focus input when editing starts
  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  const handleStartRename = (conv: Conversation, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditValue(conv.title);
  };

  const handleSaveRename = (id: string) => {
    if (editValue.trim()) {
      onRenameConversation(id, editValue.trim());
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

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return 'Today';
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const getModeIcon = (mode: AssistantMode) => {
    return mode === 'tool-router' ? (
      <Wrench className="w-3 h-3" />
    ) : (
      <Workflow className="w-3 h-3" />
    );
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Dropdown trigger */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors',
          'text-sm font-medium text-muted-foreground hover:text-foreground',
          'hover:bg-muted/50',
          isOpen && 'bg-muted/50 text-foreground'
        )}
      >
        <MessageSquare className="w-4 h-4" />
        <span className="max-w-[150px] truncate">
          {activeConversation?.title || 'Conversations'}
        </span>
        <ChevronDown
          className={clsx(
            'w-4 h-4 transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div
          className={clsx(
            'absolute top-full left-0 mt-1 z-50',
            'w-72 max-h-96 overflow-y-auto',
            'bg-card border border-border rounded-xl shadow-lg',
            'animate-in fade-in slide-in-from-top-2 duration-150'
          )}
        >
          {/* New conversation button */}
          <div className="p-2 border-b border-border">
            <button
              onClick={() => {
                onNewConversation();
                setIsOpen(false);
              }}
              className={clsx(
                'w-full flex items-center gap-2 px-3 py-2 rounded-lg',
                'text-sm font-medium text-primary',
                'hover:bg-primary/10 transition-colors'
              )}
            >
              <Plus className="w-4 h-4" />
              New conversation
            </button>
          </div>

          {/* Conversation list */}
          <div className="p-2">
            {conversations.length === 0 ? (
              <div className="px-3 py-4 text-center text-sm text-muted-foreground">
                No conversations yet
              </div>
            ) : (
              <div className="space-y-1">
                {conversations.map((conv) => (
                  <div
                    key={conv.id}
                    className={clsx(
                      'group relative flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer',
                      'transition-colors',
                      conv.id === activeConversationId
                        ? 'bg-primary/10 text-foreground'
                        : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'
                    )}
                    onClick={() => {
                      if (editingId !== conv.id) {
                        onSelectConversation(conv.id);
                        setIsOpen(false);
                      }
                    }}
                  >
                    {/* Mode icon */}
                    <div
                      className={clsx(
                        'flex-shrink-0 p-1 rounded',
                        conv.mode === 'tool-router'
                          ? 'text-orange-500'
                          : 'text-blue-500'
                      )}
                    >
                      {getModeIcon(conv.mode)}
                    </div>

                    {/* Title or edit input */}
                    <div className="flex-1 min-w-0">
                      {editingId === conv.id ? (
                        <div className="flex items-center gap-1">
                          <input
                            ref={inputRef}
                            type="text"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => handleKeyDown(e, conv.id)}
                            className={clsx(
                              'flex-1 bg-background border border-border rounded px-2 py-0.5',
                              'text-sm focus:outline-none focus:ring-1 focus:ring-primary'
                            )}
                            onClick={(e) => e.stopPropagation()}
                          />
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSaveRename(conv.id);
                            }}
                            className="p-1 text-green-500 hover:bg-green-500/10 rounded"
                          >
                            <Check className="w-3 h-3" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCancelRename();
                            }}
                            className="p-1 text-muted-foreground hover:bg-muted rounded"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ) : (
                        <>
                          <div className="text-sm font-medium truncate">
                            {conv.title}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {formatDate(conv.updatedAt)}
                          </div>
                        </>
                      )}
                    </div>

                    {/* Action buttons (visible on hover) */}
                    {editingId !== conv.id && (
                      <div
                        className={clsx(
                          'flex-shrink-0 flex items-center gap-1',
                          'opacity-0 group-hover:opacity-100 transition-opacity'
                        )}
                      >
                        <button
                          onClick={(e) => handleStartRename(conv, e)}
                          className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded"
                        >
                          <Pencil className="w-3 h-3" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteConversation(conv.id);
                          }}
                          className="p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
