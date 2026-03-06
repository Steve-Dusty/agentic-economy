'use client';

import { useState, useCallback, useRef } from 'react';

export interface MentionableRule {
  id: string;
  name: string;
  description?: string;
}

/**
 * Hook to manage rule mentions in a text input
 * Follows the same pattern as useArtifactMention but for execution rules
 */
export function useRuleMention(
  onRuleSelect?: (ruleId: string) => void
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
      rule: MentionableRule,
      mentionStart: number,
      mentionEnd: number,
      currentValue: string,
      setValue: (value: string) => void
    ) => {
      // Replace the @query with @[Rule: rule.name]
      const before = currentValue.slice(0, mentionStart);
      const after = currentValue.slice(mentionEnd);
      const mention = `@[Rule: ${rule.name}] `;

      setValue(before + mention + after);
      setShowMention(false);

      // Call the callback with the rule ID
      onRuleSelect?.(rule.id);

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
    [onRuleSelect]
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

/**
 * Utility to detect rule mentions in a message
 * Returns the rule name and any context after the mention
 */
export function parseRuleMention(message: string): {
  hasRuleMention: boolean;
  ruleName?: string;
  context?: string;
} {
  // Match @[Rule: RuleName] pattern
  const mentionRegex = /@\[Rule:\s*([^\]]+)\]\s*(.*)/;
  const match = message.match(mentionRegex);

  if (match) {
    return {
      hasRuleMention: true,
      ruleName: match[1].trim(),
      context: match[2].trim() || undefined,
    };
  }

  return {
    hasRuleMention: false,
  };
}
