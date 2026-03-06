/**
 * In-memory storage for execution rules
 */

import type {
  ExecutionRule,
  ExecutionRuleInput,
  ExecutionStep,
  OutputConfig,
  ActivationMode,
  ScheduleInterval,
} from './types';

/** In-memory store (use globalThis to survive Next.js dev-mode HMR) */
const g = globalThis as unknown as { __executionRules?: Map<string, ExecutionRule> };
if (!g.__executionRules) g.__executionRules = new Map();
const rules = g.__executionRules;

/**
 * Execution rules storage operations
 */
export const executionRulesStorage = {
  /**
   * Get all rules for a user
   */
  async getByUserId(userId: string): Promise<ExecutionRule[]> {
    return Array.from(rules.values())
      .filter((r) => r.userId === userId)
      .sort((a, b) => {
        if (b.priority !== a.priority) return b.priority - a.priority;
        return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
      });
  },

  /**
   * Get active rules for a user (sorted by priority DESC)
   */
  async getActiveByUserId(userId: string): Promise<ExecutionRule[]> {
    return Array.from(rules.values())
      .filter((r) => r.userId === userId && r.isActive)
      .sort((a, b) => b.priority - a.priority);
  },

  /**
   * Get a specific rule by ID
   */
  async get(id: string): Promise<ExecutionRule | undefined> {
    return rules.get(id);
  },

  /**
   * Create a new rule
   */
  async create(userId: string, input: ExecutionRuleInput): Promise<ExecutionRule> {
    const id = generateId('rule');
    const now = new Date().toISOString();
    const scheduleNextRun = input.scheduleEnabled && input.scheduleInterval
      ? calculateNextRunTime(input.scheduleInterval).toISOString()
      : undefined;

    const rule: ExecutionRule = {
      id,
      userId,
      name: input.name,
      description: input.description,
      isActive: input.isActive ?? true,
      priority: input.priority ?? 0,
      acceptedTriggers: input.acceptedTriggers || [],
      topicCondition: input.topicCondition,
      executionSteps: input.executionSteps,
      outputConfig: input.outputConfig,
      executionCount: 0,
      lastExecutedAt: undefined,
      createdAt: now,
      updatedAt: now,
      activationMode: input.activationMode ?? 'trigger',
      scheduleEnabled: input.scheduleEnabled ?? false,
      scheduleInterval: input.scheduleInterval,
      scheduleLastRun: undefined,
      scheduleNextRun,
    };

    rules.set(id, rule);
    return rule;
  },

  /**
   * Update an existing rule
   */
  async update(id: string, input: Partial<ExecutionRuleInput>): Promise<ExecutionRule | undefined> {
    const rule = rules.get(id);
    if (!rule) return undefined;

    if (input.name !== undefined) rule.name = input.name;
    if (input.description !== undefined) rule.description = input.description;
    if (input.isActive !== undefined) rule.isActive = input.isActive;
    if (input.priority !== undefined) rule.priority = input.priority;
    if (input.acceptedTriggers !== undefined) rule.acceptedTriggers = input.acceptedTriggers;
    if (input.topicCondition !== undefined) rule.topicCondition = input.topicCondition;
    if (input.executionSteps !== undefined) rule.executionSteps = input.executionSteps;
    if (input.outputConfig !== undefined) rule.outputConfig = input.outputConfig;
    if (input.activationMode !== undefined) rule.activationMode = input.activationMode;
    if (input.scheduleEnabled !== undefined) rule.scheduleEnabled = input.scheduleEnabled;
    if (input.scheduleInterval !== undefined) {
      rule.scheduleInterval = input.scheduleInterval;
      // Recalculate next run time when interval changes
      if (input.scheduleEnabled !== false && input.scheduleInterval) {
        rule.scheduleNextRun = calculateNextRunTime(input.scheduleInterval).toISOString();
      }
    }

    rule.updatedAt = new Date().toISOString();
    return rule;
  },

  /**
   * Delete a rule
   */
  async delete(id: string): Promise<boolean> {
    return rules.delete(id);
  },

  /**
   * Check if a user has any active rules
   */
  async hasActiveRules(userId: string): Promise<boolean> {
    for (const rule of rules.values()) {
      if (rule.userId === userId && rule.isActive) return true;
    }
    return false;
  },

  /**
   * Increment execution count and update last executed timestamp
   */
  async incrementExecutionCount(id: string): Promise<void> {
    const rule = rules.get(id);
    if (rule) {
      rule.executionCount += 1;
      rule.lastExecutedAt = new Date().toISOString();
    }
  },

  /**
   * Get rules available for manual invocation by a user
   * Returns rules with activation_mode = 'manual' or 'all'
   */
  async getManualRules(userId: string): Promise<ExecutionRule[]> {
    return Array.from(rules.values())
      .filter(
        (r) =>
          r.userId === userId &&
          r.isActive &&
          (r.activationMode === 'manual' || r.activationMode === 'all')
      )
      .sort((a, b) => {
        if (b.priority !== a.priority) return b.priority - a.priority;
        return a.name.localeCompare(b.name);
      });
  },

  /**
   * Get scheduled rules that are due to run
   * Returns rules where schedule_enabled = true AND schedule_next_run <= NOW()
   */
  async getScheduledRulesDue(): Promise<ExecutionRule[]> {
    const now = new Date();
    return Array.from(rules.values())
      .filter(
        (r) =>
          r.scheduleEnabled &&
          r.isActive &&
          (r.activationMode === 'scheduled' || r.activationMode === 'all') &&
          r.scheduleNextRun &&
          new Date(r.scheduleNextRun) <= now
      )
      .sort((a, b) => {
        const aTime = a.scheduleNextRun ? new Date(a.scheduleNextRun).getTime() : 0;
        const bTime = b.scheduleNextRun ? new Date(b.scheduleNextRun).getTime() : 0;
        return aTime - bTime;
      });
  },

  /**
   * Update schedule timestamps after a scheduled run
   */
  async updateScheduleRun(id: string, interval: ScheduleInterval): Promise<void> {
    const rule = rules.get(id);
    if (rule) {
      const now = new Date().toISOString();
      rule.scheduleLastRun = now;
      rule.scheduleNextRun = calculateNextRunTime(interval).toISOString();
      rule.executionCount += 1;
      rule.lastExecutedAt = now;
    }
  },

  /**
   * Get a rule by ID and user (for manual invocation validation)
   */
  async getByIdAndUser(id: string, userId: string): Promise<ExecutionRule | undefined> {
    const rule = rules.get(id);
    if (rule && rule.userId === userId) return rule;
    return undefined;
  },
};

/**
 * Generate unique ID (CUID-like format)
 */
function generateId(prefix: string = ''): string {
  const timestamp = Date.now().toString(36);
  const randomPart = Math.random().toString(36).substring(2, 15);
  return prefix ? `${prefix}_${timestamp}${randomPart}` : `c${timestamp}${randomPart}`;
}

/**
 * Calculate next run time based on schedule interval
 */
function calculateNextRunTime(interval: ScheduleInterval, fromDate?: Date): Date {
  const now = fromDate || new Date();
  const next = new Date(now);

  switch (interval) {
    case '15min':
      next.setMinutes(next.getMinutes() + 15);
      break;
    case 'hourly':
      next.setHours(next.getHours() + 1);
      break;
    case 'daily':
      next.setDate(next.getDate() + 1);
      break;
    case 'weekly':
      next.setDate(next.getDate() + 7);
      break;
  }

  return next;
}
