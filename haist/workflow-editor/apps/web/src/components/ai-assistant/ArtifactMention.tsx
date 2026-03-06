'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Layers } from 'lucide-react';
import { clsx } from 'clsx';

interface Artifact {
  id: string;
  title: string;
  summary: string | null;
}

interface ArtifactMentionProps {
  inputValue: string;
  cursorPosition: number;
  onSelect: (artifact: Artifact, mentionStart: number, mentionEnd: number) => void;
  onClose: () => void;
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
}

export function ArtifactMention({
  inputValue,
  cursorPosition,
  onSelect,
  onClose,
  textareaRef,
}: ArtifactMentionProps) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [filteredArtifacts, setFilteredArtifacts] = useState<Artifact[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [mentionInfo, setMentionInfo] = useState<{
    start: number;
    query: string;
  } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch artifacts on mount
  useEffect(() => {
    fetchArtifacts();
  }, []);

  const fetchArtifacts = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/artifacts');
      if (response.ok) {
        const data = await response.json();
        setArtifacts(data.artifacts || []);
      }
    } catch (error) {
      console.error('Failed to fetch artifacts:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Detect @ mention and filter artifacts
  useEffect(() => {
    // Find the @ symbol before cursor
    const textBeforeCursor = inputValue.slice(0, cursorPosition);
    const lastAtIndex = textBeforeCursor.lastIndexOf('@');

    if (lastAtIndex === -1) {
      setMentionInfo(null);
      setFilteredArtifacts([]);
      return;
    }

    // Check if there's a space between @ and cursor (which would cancel the mention)
    const textAfterAt = textBeforeCursor.slice(lastAtIndex + 1);

    // Allow spaces within the mention for multi-word artifact names
    // But if there's a newline, cancel the mention
    if (textAfterAt.includes('\n')) {
      setMentionInfo(null);
      setFilteredArtifacts([]);
      return;
    }

    const query = textAfterAt.toLowerCase();
    setMentionInfo({ start: lastAtIndex, query });

    // Filter artifacts by query
    const filtered = artifacts.filter(
      (a) =>
        a.title.toLowerCase().includes(query) ||
        (a.summary?.toLowerCase().includes(query))
    );
    setFilteredArtifacts(filtered.slice(0, 5)); // Max 5 suggestions
    setSelectedIndex(0);
  }, [inputValue, cursorPosition, artifacts]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!mentionInfo || filteredArtifacts.length === 0) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < filteredArtifacts.length - 1 ? prev + 1 : 0
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev > 0 ? prev - 1 : filteredArtifacts.length - 1
        );
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        e.stopPropagation();
        const selected = filteredArtifacts[selectedIndex];
        if (selected) {
          const mentionEnd = cursorPosition;
          onSelect(selected, mentionInfo.start, mentionEnd);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'Tab') {
        e.preventDefault();
        const selected = filteredArtifacts[selectedIndex];
        if (selected) {
          const mentionEnd = cursorPosition;
          onSelect(selected, mentionInfo.start, mentionEnd);
        }
      }
    },
    [mentionInfo, filteredArtifacts, selectedIndex, cursorPosition, onSelect, onClose]
  );

  // Attach keyboard listener
  useEffect(() => {
    if (mentionInfo && filteredArtifacts.length > 0) {
      const textarea = textareaRef.current;
      if (textarea) {
        textarea.addEventListener('keydown', handleKeyDown, true);
        return () => {
          textarea.removeEventListener('keydown', handleKeyDown, true);
        };
      }
    }
  }, [mentionInfo, filteredArtifacts, handleKeyDown, textareaRef]);

  // Don't render if no mention is active or no results
  if (!mentionInfo || filteredArtifacts.length === 0) {
    return null;
  }

  return (
    <div
      ref={dropdownRef}
      className="absolute bottom-full left-0 mb-2 w-72 bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden"
    >
      <div className="p-1.5 border-b border-border bg-muted/30">
        <div className="flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground">
          <Layers className="w-3 h-3" />
          <span>Select an artifact</span>
          <span className="ml-auto text-[10px] opacity-60">↑↓ to navigate, Enter to select</span>
        </div>
      </div>
      <div className="max-h-48 overflow-y-auto p-1">
        {isLoading ? (
          <div className="text-center py-4 text-muted-foreground text-sm">
            Loading...
          </div>
        ) : (
          filteredArtifacts.map((artifact, index) => (
            <button
              key={artifact.id}
              onClick={() => {
                if (mentionInfo) {
                  onSelect(artifact, mentionInfo.start, cursorPosition);
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
                  <Layers className="w-3 h-3 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">{artifact.title}</div>
                  {artifact.summary && (
                    <div className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                      {artifact.summary}
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

/**
 * Hook to manage artifact mentions in a text input
 */
export function useArtifactMention(
  onArtifactSelect?: (artifactId: string) => void
) {
  const [showMention, setShowMention] = useState(false);
  const [cursorPosition, setCursorPosition] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleInputChange = useCallback(
    (value: string, selectionStart: number) => {
      setCursorPosition(selectionStart);

      // Check if @ was just typed
      const textBeforeCursor = value.slice(0, selectionStart);
      const hasActiveMention = textBeforeCursor.lastIndexOf('@') !== -1;

      // Check if the @ is followed by text without a closing space/newline
      if (hasActiveMention) {
        const lastAtIndex = textBeforeCursor.lastIndexOf('@');
        const textAfterAt = textBeforeCursor.slice(lastAtIndex + 1);
        // Show mention dropdown if no newline after @
        setShowMention(!textAfterAt.includes('\n'));
      } else {
        setShowMention(false);
      }
    },
    []
  );

  const handleSelect = useCallback(
    (
      artifact: Artifact,
      mentionStart: number,
      mentionEnd: number,
      currentValue: string,
      setValue: (value: string) => void
    ) => {
      // Replace the @query with @[artifact.title]
      const before = currentValue.slice(0, mentionStart);
      const after = currentValue.slice(mentionEnd);
      const mention = `@[${artifact.title}] `;

      setValue(before + mention + after);
      setShowMention(false);

      // Call the callback with the artifact ID
      onArtifactSelect?.(artifact.id);

      // Move cursor after the mention
      setTimeout(() => {
        if (textareaRef.current) {
          const newPosition = mentionStart + mention.length;
          textareaRef.current.selectionStart = newPosition;
          textareaRef.current.selectionEnd = newPosition;
          textareaRef.current.focus();
        }
      }, 0);
    },
    [onArtifactSelect]
  );

  return {
    showMention,
    setShowMention,
    cursorPosition,
    textareaRef,
    handleInputChange,
    handleSelect,
  };
}
