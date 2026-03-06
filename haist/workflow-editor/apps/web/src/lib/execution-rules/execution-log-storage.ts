/**
 * In-memory storage for execution logs
 */

import type { ExecutionLogEntry, ExecutionLogStats } from './types';

/** In-memory store (use globalThis to survive Next.js dev-mode HMR) */
const g = globalThis as unknown as { __executionLogs?: ExecutionLogEntry[] };
if (!g.__executionLogs) g.__executionLogs = [];
const logs = g.__executionLogs;

function generateId(): string {
  const timestamp = Date.now().toString(36);
  const randomPart = Math.random().toString(36).substring(2, 15);
  return `log_${timestamp}${randomPart}`;
}

export const executionLogStorage = {
  async create(log: Omit<ExecutionLogEntry, 'id' | 'createdAt'>): Promise<ExecutionLogEntry> {
    const entry: ExecutionLogEntry = {
      id: generateId(),
      ruleId: log.ruleId,
      ruleName: log.ruleName,
      userId: log.userId,
      triggerSlug: log.triggerSlug,
      status: log.status,
      stepsJson: log.stepsJson || [],
      outputText: log.outputText,
      errorText: log.errorText,
      durationMs: log.durationMs,
      createdAt: new Date().toISOString(),
    };
    logs.push(entry);
    return entry;
  },

  async getByRuleId(ruleId: string, limit = 50, offset = 0): Promise<{ logs: ExecutionLogEntry[]; total: number }> {
    const filtered = logs
      .filter((l) => l.ruleId === ruleId)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    const total = filtered.length;
    const paginated = filtered.slice(offset, offset + limit);

    return { logs: paginated, total };
  },

  async getByUserId(userId: string, limit = 50, offset = 0): Promise<{ logs: ExecutionLogEntry[]; total: number }> {
    const filtered = logs
      .filter((l) => l.userId === userId)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    const total = filtered.length;
    const paginated = filtered.slice(offset, offset + limit);

    return { logs: paginated, total };
  },

  async getRecent(userId: string, limit = 10): Promise<ExecutionLogEntry[]> {
    return logs
      .filter((l) => l.userId === userId)
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, limit);
  },

  async deleteOlderThan(days: number): Promise<number> {
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
    let deleted = 0;
    for (let i = logs.length - 1; i >= 0; i--) {
      if (new Date(logs[i].createdAt).getTime() < cutoff) {
        logs.splice(i, 1);
        deleted++;
      }
    }
    return deleted;
  },

  async getStats(userId: string): Promise<ExecutionLogStats> {
    const userLogs = logs.filter((l) => l.userId === userId);
    const totalRuns = userLogs.length;
    const successCount = userLogs.filter((l) => l.status === 'success').length;
    const durations = userLogs.filter((l) => l.durationMs != null).map((l) => l.durationMs!);
    const avgDurationMs = durations.length > 0
      ? Math.round(durations.reduce((sum, d) => sum + d, 0) / durations.length)
      : 0;

    return {
      totalRuns,
      successRate: totalRuns > 0 ? (successCount / totalRuns) * 100 : 0,
      avgDurationMs,
    };
  },

  async getStatsByRuleId(ruleId: string): Promise<ExecutionLogStats> {
    const ruleLogs = logs.filter((l) => l.ruleId === ruleId);
    const totalRuns = ruleLogs.length;
    const successCount = ruleLogs.filter((l) => l.status === 'success').length;
    const durations = ruleLogs.filter((l) => l.durationMs != null).map((l) => l.durationMs!);
    const avgDurationMs = durations.length > 0
      ? Math.round(durations.reduce((sum, d) => sum + d, 0) / durations.length)
      : 0;

    return {
      totalRuns,
      successRate: totalRuns > 0 ? (successCount / totalRuns) * 100 : 0,
      avgDurationMs,
    };
  },
};
