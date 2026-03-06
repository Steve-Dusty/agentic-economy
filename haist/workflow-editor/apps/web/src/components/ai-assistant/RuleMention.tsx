'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Zap } from 'lucide-react';
import { clsx } from 'clsx';
import type { MentionableRule } from '@/lib/ai-assistant/hooks/useRuleMention';

interface RuleMentionProps {
  inputValue: string;
  cursorPosition: number;
  onSelect: (rule: MentionableRule, mentionStart: number, mentionEnd: number) => void;
  onClose: () => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
}

export function RuleMention({
  inputValue,
  cursorPosition,
  onSelect,
  onClose,
  textareaRef,
}: RuleMentionProps) {
  const [rules, setRules] = useState<MentionableRule[]>([]);
  const [filteredRules, setFilteredRules] = useState<MentionableRule[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [mentionInfo, setMentionInfo] = useState<{
    start: number;
    query: string;
  } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch rules that support manual invocation on mount
  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/automations/manual');
      if (response.ok) {
        const data = await response.json();
        setRules(
          (data.rules || []).map((r: { id: string; name: string; description?: string }) => ({
            id: r.id,
            name: r.name,
            description: r.description,
          }))
        );
      }
    } catch (error) {
      console.error('Failed to fetch rules:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Detect @ mention and filter rules
  useEffect(() => {
    // Find the @ symbol before cursor
    const textBeforeCursor = inputValue.slice(0, cursorPosition);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');

    if (lastAtIndex === -1) {
      setMentionInfo(null);
      setFilteredRules([]);
      return;
    }

    // Check if there's a newline between @ and cursor (which would cancel the mention)
    const textAfterAt = textBeforeCursor.slice(lastAtIndex + 1);

    if (textAfterAt.includes('\n')) {
      setMentionInfo(null);
      setFilteredRules([]);
      return;
    }

    const query = textAfterAt.toLowerCase();
    setMentionInfo({ start: lastAtIndex, query });

    // Filter rules by query
    const filtered = rules.filter(
      (r) =>
        r.name.toLowerCase().includes(query) ||
        (r.description?.toLowerCase().includes(query))
    );
    setFilteredRules(filtered.slice(0, 5)); // Max 5 suggestions
    setSelectedIndex(0);
  }, [inputValue, cursorPosition, rules]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!mentionInfo || filteredRules.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredRules.length - 1 ? prev + 1 : 0
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : filteredRules.length - 1
        );
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        e.stopPropagation();
        const selected = filteredRules[selectedIndex];
        if (selected) {
          const mentionEnd = cursorPosition;
          onSelect(selected, mentionInfo.start, mentionEnd);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'Tab') {
        e.preventDefault();
        const selected = filteredRules[selectedIndex];
        if (selected) {
          const mentionEnd = cursorPosition;
          onSelect(selected, mentionInfo.start, mentionEnd);
        }
      }
    },
    [mentionInfo, filteredRules, selectedIndex, cursorPosition, onSelect, onClose]
  );

  // Attach keyboard listener
  useEffect(() => {
    if (mentionInfo && filteredRules.length > 0) {
      const textarea = textareaRef.current;
      if (textarea) {
        textarea.addEventListener('keydown', handleKeyDown, true);
        return () => {
          textarea.removeEventListener('keydown', handleKeyDown, true);
        };
      }
    }
  }, [mentionInfo, filteredRules, handleKeyDown, textareaRef]);

  // Don't render if no mention is active or no results
  if (!mentionInfo || filteredRules.length === 0) {
    return null;
  }

  return (
    <div
      ref={dropdownRef}
      className="absolute bottom-full left-0 mb-2 w-72 bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden"
    >
      <div className="p-1.5 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground">
          <Zap className="w-3 h-3" />
          <span>Select a rule to invoke</span>
          <span className="ml-auto text-[10px] opacity-60">
            ↑↓ to navigate, Enter to select
          </span>
        </div>
      </div>
      <div className="max-h-48 overflow-y-auto p-1">
        {isLoading ? (
          <div className="text-center py-4 text-muted-foreground text-sm">
            Loading...
          </div>
        ) : (
          filteredRules.map((rule, index) => (
            <button
              key={rule.id}
              onClick={() => {
                if (mentionInfo) {
                  onSelect(rule, mentionInfo.start, cursorPosition);
                }
              }}
              className={clsx(
                'w-full text-left p-2 rounded-lg transition-colors',
                index === selectedIndex
                  ? 'bg-primary/10 border border-primary/30'
                  : 'hover:bg-muted/70 border border-transparent'
              )}
            >
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded bg-primary/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Zap className="w-3 h-3 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">{rule.name}</div>
                  {rule.description && (
                    <div className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                      {rule.description}
                    </div>
                  )}
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
