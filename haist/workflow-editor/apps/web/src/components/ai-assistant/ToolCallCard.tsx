'use client';

import React, { useState } from 'react';
import { CheckCircle2, XCircle, Wrench, ChevronDown, ChevronRight } from 'lucide-react';
import { clsx } from 'clsx';
import type { ToolCallResult } from '@/lib/ai-assistant/types';

interface ToolCallCardProps {
  toolCall: ToolCallResult;
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  const hasDetails = toolCall.result !== undefined || toolCall.error !== undefined;

  const formatResult = (result: unknown): string => {
    if (typeof result === 'string') {
      return result;
    }
    return JSON.stringify(result, null, 2);
  };

  return (
    <div
      className={clsx(
        'mt-2 p-3 rounded-lg border',
        toolCall.success
          ? 'bg-green-500/[0.06] border-green-500/20'
          : 'bg-red-500/[0.06] border-red-500/20'
      )}
    >
      <div
        className={clsx(
          'flex items-center gap-2',
          hasDetails && 'cursor-pointer'
        )}
        onClick={() => hasDetails && setExpanded(!expanded)}
      >
        {toolCall.success ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
        ) : (
          <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
        )}
        <Wrench className="w-3 h-3 text-muted-foreground flex-shrink-0" />
        <span className="text-sm font-medium truncate">{toolCall.toolName}</span>
        <span className="text-xs text-muted-foreground px-1.5 py-0.5 bg-muted rounded">
          {toolCall.toolkit}
        </span>
        {hasDetails && (
          <span className="ml-auto">
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
            )}
          </span>
        )}
      </div>

      {expanded && toolCall.result !== undefined && (
        <div className="mt-2">
          <pre className="p-2 bg-background/80 rounded-md text-xs overflow-auto max-h-40 whitespace-pre-wrap break-words border border-border/50">
            {formatResult(toolCall.result)}
          </pre>
        </div>
      )}

      {expanded && toolCall.error && (
        <p className="mt-2 text-xs text-red-400">{toolCall.error}</p>
      )}
    </div>
  );
}
