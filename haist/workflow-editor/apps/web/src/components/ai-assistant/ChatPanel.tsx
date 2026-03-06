'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowUp,
  Loader2,
  Workflow,
  User,
  Sparkles,
  Copy,
  Check,
  Bot,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
  Pencil,
  ChevronDown,
} from 'lucide-react';
import { clsx } from 'clsx';
import ReactMarkdown from 'react-markdown';
import type {
  ChatMessage,
  AIAssistantContext,
  AssistantMode,
  ToolRouterMessage,
} from '@/lib/ai-assistant/types';
import type { WorkflowDocument } from '@workflow-editor/core';
import { EXAMPLE_PROMPTS } from '@/lib/ai-assistant/prompts';
import { ToolCallCard } from './ToolCallCard';
import { ArtifactPicker } from './ArtifactPicker';
import { ArtifactMention, useArtifactMention } from './ArtifactMention';
import { RuleMention } from './RuleMention';
import { useRuleMention, parseRuleMention, type MentionableRule } from '@/lib/ai-assistant/hooks/useRuleMention';

interface ChatPanelProps {
  messages: ChatMessage[];
  toolRouterMessages?: ToolRouterMessage[];
  mode: AssistantMode;
  onModeChange: (mode: AssistantMode) => void;
  onSendMessage: (message: string, artifactIds?: string[]) => void;
  onSelectWorkflow: (workflow: WorkflowDocument) => void;
  isLoading: boolean;
  context: AIAssistantContext | null;
  selectedArtifactIds?: string[];
  onArtifactSelectionChange?: (ids: string[]) => void;
  onRuleInvoke?: (ruleId: string, ruleName: string, context: string) => void;
}

export function ChatPanel({
  messages,
  toolRouterMessages = [],
  mode,
  onModeChange,
  onSendMessage,
  onSelectWorkflow,
  isLoading,
  context,
  selectedArtifactIds = [],
  onArtifactSelectionChange,
  onRuleInvoke,
}: ChatPanelProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [selectedRule, setSelectedRule] = useState<MentionableRule | null>(null);

  // Artifact mention state
  const {
    showMention: showArtifactMention,
    setShowMention: setShowArtifactMention,
    cursorPosition: artifactCursorPosition,
    handleInputChange: handleArtifactInputChange,
    handleSelect: handleArtifactMentionSelect,
  } = useArtifactMention((artifactId) => {
    if (onArtifactSelectionChange && !selectedArtifactIds.includes(artifactId)) {
      onArtifactSelectionChange([...selectedArtifactIds, artifactId]);
    }
  });

  // Rule mention state
  const {
    showMention: showRuleMention,
    setShowMention: setShowRuleMention,
    cursorPosition: ruleCursorPosition,
    handleInputChange: handleRuleInputChange,
    handleSelect: handleRuleMentionSelect,
  } = useRuleMention((ruleId) => {
    // Handle rule selection
  });

  // Combined input change handler
  const handleCombinedInputChange = (value: string, selectionStart: number) => {
    handleArtifactInputChange(value, selectionStart);
    handleRuleInputChange(value, selectionStart);
  };

  // Get messages based on mode
  const displayMessages = mode === 'tool-router' ? toolRouterMessages : messages;

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [displayMessages, isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 200);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (input.trim() && !isLoading) {
      const ruleMention = parseRuleMention(input.trim());

      if (ruleMention.hasRuleMention && ruleMention.ruleName && onRuleInvoke) {
        invokeRuleByName(ruleMention.ruleName, ruleMention.context || '');
      } else {
        onSendMessage(input.trim(), selectedArtifactIds);
      }

      setInput('');
      setSelectedRule(null);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const invokeRuleByName = async (ruleName: string, ruleContext: string) => {
    try {
      const response = await fetch('/api/automations/manual');
      if (!response.ok) return;

      const data = await response.json();
      const rule = data.rules?.find((r: MentionableRule) => r.name === ruleName);

      if (rule && onRuleInvoke) {
        onRuleInvoke(rule.id, rule.name, ruleContext);
      }
    } catch (error) {
      console.error('[ChatPanel] Error invoking rule:', error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleExampleClick = (prompt: string) => {
    if (!isLoading) {
      onSendMessage(prompt);
    }
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Messages Area - Scrollable */}
      <div className="flex-1 overflow-y-auto thin-scrollbar">
        <div className="max-w-3xl mx-auto px-4 py-8">
          {displayMessages.length === 0 ? (
            <EmptyState
              context={context}
              mode={mode}
              onExampleClick={handleExampleClick}
            />
          ) : (
            <div className="flex flex-col">
              {mode === 'tool-router'
                ? toolRouterMessages.map((message, index) => (
                    <div
                      key={message.id}
                      className="animate-fade-in"
                      style={{ animationDelay: `${Math.min(index * 50, 200)}ms` }}
                    >
                      <ToolRouterMessageRow message={message} />
                    </div>
                  ))
                : messages.map((message, index) => (
                    <div
                      key={message.id}
                      className="animate-fade-in"
                      style={{ animationDelay: `${Math.min(index * 50, 200)}ms` }}
                    >
                      <MessageRow
                        message={message}
                        onSelectWorkflow={onSelectWorkflow}
                      />
                    </div>
                  ))}

              {/* Loading indicator */}
              {isLoading && (
                <div className="chat-message-container assistant animate-fade-in">
                  <div className="chat-message-assistant-content">
                    <div className="flex gap-1 py-4">
                      <span className="claude-loading-dot" />
                      <span className="claude-loading-dot" />
                      <span className="claude-loading-dot" />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Floating Input Area */}
      <div className="relative z-10 bg-gradient-to-t from-background to-transparent pt-6 pb-6 px-4">
        <div className="max-w-3xl mx-auto">
          <div className="claude-input-container">
            <div className="flex flex-col m-3.5 gap-3">
              <div className="relative">
                {/* Artifact mention dropdown */}
                {showArtifactMention && onArtifactSelectionChange && !showRuleMention && (
                  <ArtifactMention
                    inputValue={input}
                    cursorPosition={artifactCursorPosition}
                    onSelect={(artifact, start, end) => {
                      handleArtifactMentionSelect(artifact, start, end, input, setInput);
                    }}
                    onClose={() => setShowArtifactMention(false)}
                    textareaRef={textareaRef}
                  />
                )}
                {/* Rule mention dropdown */}
                {showRuleMention && mode === 'tool-router' && (
                  <RuleMention
                    inputValue={input}
                    cursorPosition={ruleCursorPosition}
                    onSelect={(rule, start, end) => {
                      handleRuleMentionSelect(rule, start, end, input, setInput);
                      setSelectedRule(rule);
                    }}
                    onClose={() => setShowRuleMention(false)}
                    textareaRef={textareaRef}
                  />
                )}
                <div className="w-full overflow-y-auto break-words max-h-96 min-h-[3rem] pl-1.5 pt-1.5">
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => {
                      setInput(e.target.value);
                      handleCombinedInputChange(e.target.value, e.target.selectionStart || 0);
                    }}
                    onSelect={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      handleCombinedInputChange(input, target.selectionStart || 0);
                    }}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      mode === 'tool-router'
                        ? 'Ask me to do something...'
                        : 'How can I help you today?'
                    }
                    disabled={isLoading}
                    rows={1}
                    className={clsx(
                      'w-full bg-transparent resize-none text-base',
                      'placeholder:text-muted-foreground',
                      'focus:outline-none',
                      'disabled:opacity-50 disabled:cursor-not-allowed',
                      'min-h-[28px] max-h-[200px]'
                    )}
                  />
                </div>
              </div>
              <div className="flex gap-2 w-full items-center">
                <div className="relative flex-1 flex items-center shrink min-w-0 gap-1">
                  {onArtifactSelectionChange && (
                    <ArtifactPicker
                      selectedIds={selectedArtifactIds}
                      onSelectionChange={onArtifactSelectionChange}
                      maxSelections={3}
                      disabled={isLoading}
                    />
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => handleSubmit()}
                  disabled={!input.trim() || isLoading}
                  className="claude-send-btn"
                  aria-label="Send message"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Format timestamp
function formatTimestamp(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } else if (diffDays < 7) {
    return d.toLocaleDateString([], { weekday: 'short' });
  } else {
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }
}

// Empty state component
function EmptyState({
  context,
  mode,
  onExampleClick,
}: {
  context: AIAssistantContext | null;
  mode: AssistantMode;
  onExampleClick: (prompt: string) => void;
}) {
  const connectedServices =
    context?.composio.connectedAccounts
      .filter((acc) => acc.status === 'ACTIVE')
      .map((acc) => acc.toolkit) || [];

  const examples =
    mode === 'tool-router'
      ? [
          { label: 'Send an email', prompt: 'Send an email to test@example.com with subject "Hello"' },
          { label: 'Check my calendar', prompt: "What's on my calendar for today?" },
          { label: 'Create a GitHub issue', prompt: 'Create a GitHub issue to fix the login bug' },
        ]
      : EXAMPLE_PROMPTS;

  const getDayOfWeek = () => {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return days[new Date().getDay()];
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center animate-fade-in pt-[10vh]">
      <div className="mb-8">
        <div className="flex items-center justify-center gap-3 mb-2">
          <div className="claude-sparkle">
            <Sparkles className="w-8 h-8" />
          </div>
          <h1 className="claude-greeting">Happy {getDayOfWeek()}</h1>
        </div>
        <p className="text-muted-foreground text-lg">
          {mode === 'tool-router'
            ? 'What would you like me to do?'
            : 'What would you like to automate?'}
        </p>
      </div>

      {connectedServices.length > 0 && (
        <div className="mb-8 px-4 py-2 rounded-lg bg-muted/50 border border-border/50">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Connected:</span>{' '}
            {connectedServices.join(', ')}
          </p>
        </div>
      )}

      {mode === 'tool-router' && connectedServices.length === 0 && (
        <div className="mb-8 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg max-w-md">
          <p className="text-sm text-yellow-700 dark:text-yellow-300">
            No services connected yet. Connect services in settings to use Tool Router.
          </p>
        </div>
      )}

      <div className="flex flex-wrap justify-center gap-2 mb-8">
        {examples.slice(0, 4).map((example, index) => (
          <button
            key={index}
            onClick={() => onExampleClick(example.prompt)}
            className="claude-category-pill"
          >
            {example.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// Thinking block component
function ThinkingBlock({ content, summary }: { content: string; summary?: string }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="thinking-block">
      <button
        className="thinking-block-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex flex-row items-center gap-2 min-w-0">
          <div className="thinking-block-title">
            <span>{summary || 'Thinking...'}</span>
          </div>
        </div>
        <div className="flex flex-row items-center gap-1.5 min-w-0 shrink-0">
          <span
            className={clsx(
              'inline-flex transition-transform duration-300',
              isExpanded ? 'rotate-180' : 'rotate-0'
            )}
          >
            <ChevronDown className="w-4 h-4" />
          </span>
        </div>
      </button>
      <div
        className="thinking-block-content"
        style={{
          height: isExpanded ? 'auto' : '0px',
          opacity: isExpanded ? 1 : 0,
        }}
      >
        <div className="thinking-block-content-inner">
          <p className="leading-relaxed whitespace-pre-wrap">{content}</p>
        </div>
      </div>
    </div>
  );
}

// Tool Router message row - Claude.ai style
function ToolRouterMessageRow({ message }: { message: ToolRouterMessage }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [dismissedArtifacts, setDismissedArtifacts] = useState<Set<string>>(new Set());
  const timestamp = message.timestamp ? formatTimestamp(message.timestamp) : null;

  const visibleArtifacts = message.injectedArtifacts?.filter(
    (a) => !dismissedArtifacts.has(a.id)
  );

  const handleCopy = async () => {
    if (message.content) {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (isUser) {
    return (
      <div className="chat-message-container user group">
        <div className="chat-bubble-user">
          <div className="flex flex-row gap-2 relative">
            <div className="flex-1">
              <div className="py-0.5 whitespace-pre-wrap break-words">
                {message.content}
              </div>
            </div>
          </div>
        </div>
        <div className="chat-action-bar user" role="group" aria-label="Message actions">
          {timestamp && <span className="chat-timestamp">{timestamp}</span>}
          <button className="chat-action-btn" aria-label="Retry" title="Retry">
            <RotateCcw />
          </button>
          <button className="chat-action-btn" aria-label="Edit" title="Edit">
            <Pencil />
          </button>
          <button
            className="chat-action-btn"
            aria-label="Copy"
            title="Copy"
            onClick={handleCopy}
          >
            {copied ? <Check className="text-green-500" /> : <Copy />}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-message-container assistant group">
      {/* Injected artifacts indicator */}
      {visibleArtifacts && visibleArtifacts.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap mb-2 text-xs text-muted-foreground">
          <span>📎 Using context from:</span>
          {visibleArtifacts.map((a) => (
            <span
              key={a.id}
              className={clsx(
                'inline-flex items-center gap-1 px-2 py-0.5 rounded-full',
                a.confidence === 'high'
                  ? 'bg-primary/10 text-primary'
                  : 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-300'
              )}
            >
              {a.title}
              {a.confidence === 'possible' && (
                <button
                  onClick={() => setDismissedArtifacts((prev) => new Set([...prev, a.id]))}
                  className="ml-0.5 hover:text-foreground"
                  title="Dismiss"
                >
                  ×
                </button>
              )}
            </span>
          ))}
        </div>
      )}
      <div className="chat-message-assistant-content">
        {message.content && (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
                ul: ({ children }) => <ul className="list-disc pl-4 mb-3">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-4 mb-3">{children}</ol>,
                li: ({ children }) => <li className="mb-1">{children}</li>,
                code: ({ children, className }) => {
                  const isInline = !className;
                  return isInline ? (
                    <code className="px-1.5 py-0.5 bg-muted rounded text-sm font-mono">{children}</code>
                  ) : (
                    <code className="block p-3 bg-muted rounded-lg text-sm font-mono overflow-x-auto">{children}</code>
                  );
                },
                pre: ({ children }) => <pre className="mb-3">{children}</pre>,
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                    {children}
                  </a>
                ),
                strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                em: ({ children }) => <em className="italic">{children}</em>,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
      <div className="chat-action-bar" role="group" aria-label="Message actions">
        <button
          className="chat-action-btn"
          aria-label="Copy"
          title="Copy"
          onClick={handleCopy}
        >
          {copied ? <Check className="text-green-500" /> : <Copy />}
        </button>
        <button className="chat-action-btn" aria-label="Good response" title="Good response">
          <ThumbsUp />
        </button>
        <button className="chat-action-btn" aria-label="Bad response" title="Bad response">
          <ThumbsDown />
        </button>
        <button className="chat-action-btn" aria-label="Retry" title="Retry">
          <RotateCcw />
        </button>
      </div>
    </div>
  );
}

// Workflow Generator message row - Claude.ai style
function MessageRow({
  message,
  onSelectWorkflow,
}: {
  message: ChatMessage;
  onSelectWorkflow: (workflow: WorkflowDocument) => void;
}) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const timestamp = message.timestamp ? formatTimestamp(message.timestamp) : null;

  // Remove workflow JSON blocks from displayed content
  const displayContent = message.content
    .replace(/```workflow-json[\s\S]*?```/g, '')
    .replace(/```json[\s\S]*?```/g, '')
    .trim();

  const showContent = message.workflow ? displayContent : displayContent || message.content;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <div className="chat-message-container user group">
        <div className="chat-bubble-user">
          <div className="flex flex-row gap-2 relative">
            <div className="flex-1">
              <div className="py-0.5 whitespace-pre-wrap break-words">
                {message.content}
              </div>
            </div>
          </div>
        </div>
        <div className="chat-action-bar user" role="group" aria-label="Message actions">
          {timestamp && <span className="chat-timestamp">{timestamp}</span>}
          <button className="chat-action-btn" aria-label="Retry" title="Retry">
            <RotateCcw />
          </button>
          <button className="chat-action-btn" aria-label="Edit" title="Edit">
            <Pencil />
          </button>
          <button
            className="chat-action-btn"
            aria-label="Copy"
            title="Copy"
            onClick={handleCopy}
          >
            {copied ? <Check className="text-green-500" /> : <Copy />}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-message-container assistant group">
      <div className="chat-message-assistant-content">
        {showContent && (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <div className="whitespace-pre-wrap text-base leading-relaxed text-foreground">
              {showContent}
            </div>
          </div>
        )}

        {/* Workflow card if present */}
        {message.workflow && (
          <div
            className={clsx(
              'mt-5 p-5 rounded-2xl cursor-pointer',
              'bg-gradient-to-br from-primary/5 via-primary/10 to-primary/5',
              'border border-border',
              'hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5',
              'transition-all duration-300 group/workflow'
            )}
            onClick={() => onSelectWorkflow(message.workflow!)}
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-primary flex items-center justify-center shadow-md">
                <Workflow className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="font-semibold text-foreground group-hover/workflow:text-primary transition-colors">
                  {message.workflow.metadata.name}
                </span>
                <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                  <span>{message.workflow.nodes.length} nodes</span>
                  <span className="w-1 h-1 rounded-full bg-muted-foreground/50" />
                  <span>{message.workflow.edges.length} connections</span>
                </div>
              </div>
            </div>
            {message.workflow.metadata.description && (
              <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                {message.workflow.metadata.description}
              </p>
            )}
            <p className="text-xs text-primary font-medium flex items-center gap-1">
              Click to preview
              <span className="group-hover/workflow:translate-x-1 transition-transform">→</span>
            </p>
          </div>
        )}

        {/* Required connections warning */}
        {message.requiredConnections && message.requiredConnections.length > 0 && (
          <div className="mt-4 p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
            <p className="text-sm text-yellow-700 dark:text-yellow-300">
              <span className="font-semibold">Required connections: </span>
              {message.requiredConnections.join(', ')}
            </p>
          </div>
        )}
      </div>
      <div className="chat-action-bar" role="group" aria-label="Message actions">
        <button
          className="chat-action-btn"
          aria-label="Copy"
          title="Copy"
          onClick={handleCopy}
        >
          {copied ? <Check className="text-green-500" /> : <Copy />}
        </button>
        <button className="chat-action-btn" aria-label="Good response" title="Good response">
          <ThumbsUp />
        </button>
        <button className="chat-action-btn" aria-label="Bad response" title="Bad response">
          <ThumbsDown />
        </button>
        <button className="chat-action-btn" aria-label="Retry" title="Retry">
          <RotateCcw />
        </button>
      </div>
    </div>
  );
}
