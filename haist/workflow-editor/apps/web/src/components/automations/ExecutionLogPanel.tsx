'use client';

import React, { useEffect, useState, useCallback } from 'react';
import {
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Clock,
  Activity,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { clsx } from 'clsx';
import type { ExecutionLogEntry, ExecutionLogStats, StepResult } from '@/lib/execution-rules/types';

interface ExecutionLogPanelProps {
  ruleId?: string;
  ruleName?: string;
  onClose: () => void;
}

export function ExecutionLogPanel({ ruleId, ruleName, onClose }: ExecutionLogPanelProps) {
  const [logs, setLogs] = useState<ExecutionLogEntry[]>([]);
  const [stats, setStats] = useState<ExecutionLogStats | null>(null);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const fetchLogs = useCallback(async () => {
    try {
      setIsLoading(true);
      const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
      if (ruleId) params.set('ruleId', ruleId);

      const url = ruleId
        ? `/api/automations/${ruleId}/logs?${params}`
        : `/api/automations/logs?${params}`;

      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch logs');
      const data = await res.json();
      setLogs(data.logs || []);
      setTotal(data.total || 0);
      setStats(data.stats || null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch logs');
    } finally {
      setIsLoading(false);
    }
  }, [ruleId, offset]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const statusConfig = {
    success: { icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-500/10', label: 'Success' },
    failure: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10', label: 'Failed' },
    partial: { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-500/10', label: 'Partial' },
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '—';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card border rounded-lg shadow-lg w-full max-w-3xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            <h2 className="text-lg font-semibold">
              {ruleName ? `Logs: ${ruleName}` : 'Execution History'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-muted rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Stats */}
        {stats && stats.totalRuns > 0 && (
          <div className="grid grid-cols-3 gap-4 p-4 border-b bg-muted/20">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Total Runs</p>
                <p className="text-lg font-semibold">{stats.totalRuns}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Success Rate</p>
                <p className={clsx('text-lg font-semibold', stats.successRate >= 80 ? 'text-green-500' : stats.successRate >= 50 ? 'text-yellow-500' : 'text-red-500')}>
                  {stats.successRate.toFixed(1)}%
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Avg Duration</p>
                <p className="text-lg font-semibold">{formatDuration(stats.avgDurationMs)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[calc(90vh-200px)]">
          {/* Error */}
          {error && (
            <div className="mb-4 p-4 bg-destructive/10 border border-destructive/20 rounded-md flex items-center gap-2 text-destructive">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          {/* Loading */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Empty */}
          {!isLoading && logs.length === 0 && (
            <div className="text-center py-12 bg-muted/30 rounded-lg border border-dashed">
              <Activity className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No execution logs yet</h3>
              <p className="text-muted-foreground">
                Logs will appear here after rules are executed
              </p>
            </div>
          )}

          {/* Log entries */}
          {!isLoading && logs.length > 0 && (
            <div className="space-y-2">
              {logs.map((log) => {
                const sc = statusConfig[log.status];
                const StatusIcon = sc.icon;
                const isExpanded = expandedLogId === log.id;

                return (
                  <div key={log.id} className="border rounded-lg bg-card overflow-hidden">
                    <div
                      className="flex items-center gap-3 p-3 cursor-pointer hover:bg-muted/50"
                      onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                    >
                      <StatusIcon className={clsx('w-4 h-4 flex-shrink-0', sc.color)} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          {!ruleId && (
                            <span className="font-medium text-sm truncate">{log.ruleName}</span>
                          )}
                          <span className={clsx('text-xs px-2 py-0.5 rounded-full', sc.bg, sc.color)}>
                            {sc.label}
                          </span>
                          <span className="text-xs px-2 py-0.5 bg-muted rounded-full">
                            {log.triggerSlug}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground flex-shrink-0">
                        {log.durationMs && <span>{formatDuration(log.durationMs)}</span>}
                        <span>{new Date(log.createdAt).toLocaleString()}</span>
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="border-t bg-muted/20 p-3 space-y-3">
                        {/* Output */}
                        {log.outputText && (
                          <div>
                            <h4 className="text-xs font-medium text-muted-foreground mb-1">Output</h4>
                            <pre className="text-sm p-2 bg-background rounded border whitespace-pre-wrap break-words max-h-40 overflow-y-auto">
                              {log.outputText}
                            </pre>
                          </div>
                        )}

                        {/* Error */}
                        {log.errorText && (
                          <div>
                            <h4 className="text-xs font-medium text-destructive mb-1">Error</h4>
                            <pre className="text-sm p-2 bg-destructive/5 border border-destructive/20 rounded whitespace-pre-wrap break-words">
                              {log.errorText}
                            </pre>
                          </div>
                        )}

                        {/* Steps */}
                        {log.stepsJson && log.stepsJson.length > 0 && (
                          <div>
                            <h4 className="text-xs font-medium text-muted-foreground mb-1">Steps</h4>
                            <div className="space-y-1">
                              {log.stepsJson.map((step: StepResult, i: number) => (
                                <div
                                  key={i}
                                  className="flex items-start gap-2 p-2 bg-background rounded border text-sm"
                                >
                                  <span className="text-xs px-1.5 py-0.5 bg-muted rounded">{step.stepIndex + 1}</span>
                                  {step.success ? (
                                    <CheckCircle2 className="w-3.5 h-3.5 text-green-500 mt-0.5 flex-shrink-0" />
                                  ) : (
                                    <XCircle className="w-3.5 h-3.5 text-red-500 mt-0.5 flex-shrink-0" />
                                  )}
                                  <div className="flex-1 min-w-0">
                                    <span className="text-xs text-muted-foreground">{step.type}</span>
                                    {step.error && (
                                      <p className="text-xs text-destructive mt-0.5">{String(step.error)}</p>
                                    )}
                                    {step.result != null && (
                                      <p className="text-xs text-muted-foreground mt-0.5 truncate">
                                        {typeof step.result === 'string' ? step.result : JSON.stringify(step.result)}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="px-3 py-1.5 text-sm border rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-muted-foreground">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={currentPage >= totalPages}
                className="px-3 py-1.5 text-sm border rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
