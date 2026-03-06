/**
 * Execution Rules Types
 *
 * Type definitions for the automated trigger processing system.
 */

/**
 * Activation mode for rule execution
 * - 'trigger': Only fires on Composio webhook events (default)
 * - 'manual': User invokes via @RuleName in AI Assistant chat
 * - 'scheduled': Runs automatically on preset intervals
 * - 'all': Can be triggered by any method
 */
export type ActivationMode = 'trigger' | 'manual' | 'scheduled' | 'all';

/**
 * Schedule interval options for scheduled rules
 */
export type ScheduleInterval = '15min' | 'hourly' | 'daily' | 'weekly';

/**
 * Output platforms for rule execution results
 */
export type OutputPlatform = 'slack' | 'gmail' | 'webhook' | 'none';

/**
 * Output format options
 */
export type OutputFormat = 'summary' | 'detailed' | 'raw';

/**
 * Output configuration for where to send results
 */
export interface OutputConfig {
  platform: OutputPlatform;
  destination?: string; // channel ID, email, webhook URL
  format: OutputFormat;
  template?: string; // Message template with {{result}} placeholders
}

/**
 * Instruction-based execution step (AI interprets)
 */
export interface InstructionStep {
  type: 'instruction';
  content: string; // Human language instruction for AI
}

/**
 * Structured action execution step (direct tool call)
 */
export interface ActionStep {
  type: 'action';
  toolName: string; // Composio tool name, e.g., "GMAIL_SEND_EMAIL"
  parameters: Record<string, unknown>; // Tool parameters
}

/**
 * Union type for execution steps
 */
export type ExecutionStep = InstructionStep | ActionStep;

/**
 * Stored execution rule
 */
export interface ExecutionRule {
  id: string;
  userId: string;
  name: string;
  description?: string;
  isActive: boolean;
  priority: number;
  acceptedTriggers: string[]; // Trigger slugs
  topicCondition: string; // Human language condition
  executionSteps: ExecutionStep[];
  outputConfig: OutputConfig;
  executionCount: number;
  lastExecutedAt?: string;
  createdAt: string;
  updatedAt: string;
  // Activation mode fields
  activationMode: ActivationMode;
  scheduleEnabled: boolean;
  scheduleInterval?: ScheduleInterval;
  scheduleLastRun?: string;
  scheduleNextRun?: string;
}

/**
 * Create/update execution rule request
 */
export interface ExecutionRuleInput {
  name: string;
  description?: string;
  isActive?: boolean;
  priority?: number;
  acceptedTriggers?: string[];
  topicCondition: string;
  executionSteps: ExecutionStep[];
  outputConfig: OutputConfig;
  // Activation mode fields
  activationMode?: ActivationMode;
  scheduleEnabled?: boolean;
  scheduleInterval?: ScheduleInterval;
}

/**
 * Incoming Composio trigger payload (from webhook)
 */
export interface TriggerPayload {
  id: string;
  uuid: string;
  triggerSlug: string;
  toolkitSlug: string;
  userId: string; // Composio user ID (maps to our user ID)
  payload?: Record<string, unknown>;
  originalPayload?: Record<string, unknown>;
  metadata: {
    id: string;
    uuid: string;
    toolkitSlug: string;
    triggerSlug: string;
    triggerData?: string;
    triggerConfig: Record<string, unknown>;
    connectedAccount: {
      id: string;
      uuid: string;
      authConfigId: string;
      authConfigUUID: string;
      userId: string;
      status: 'ACTIVE' | 'INACTIVE';
    };
  };
}

/**
 * Result of rule matching
 */
export interface RuleMatchResult {
  matched: boolean;
  rule?: ExecutionRule;
  confidence?: number;
  reasoning?: string;
}

/**
 * Result of a single step execution
 */
export interface StepResult {
  stepIndex: number;
  type: 'instruction' | 'action';
  success: boolean;
  result?: unknown;
  error?: string;
}

/**
 * Result of rule execution
 */
export interface RuleExecutionResult {
  success: boolean;
  ruleId: string;
  ruleName: string;
  triggerSlug: string;
  stepResults: StepResult[];
  output?: string;
  error?: string;
  executedAt: string;
}

/**
 * Result of trigger processing
 */
export interface ProcessingResult {
  matched: boolean;
  executed: boolean;
  ruleId?: string;
  ruleName?: string;
  error?: string;
}

/**
 * Execution log entry stored in the database
 */
export interface ExecutionLogEntry {
  id: string;
  ruleId: string;
  ruleName: string;
  userId: string;
  triggerSlug: string;
  status: 'success' | 'failure' | 'partial';
  stepsJson: StepResult[];
  outputText?: string;
  errorText?: string;
  durationMs?: number;
  createdAt: string;
}

/**
 * Aggregated execution log statistics
 */
export interface ExecutionLogStats {
  totalRuns: number;
  successRate: number;
  avgDurationMs: number;
}

/**
 * Context for manual rule invocation via @mention
 */
export interface ManualInvocationContext {
  userMessage: string; // The message the user typed after @RuleName
  conversationId?: string; // Optional conversation ID for context
}

/**
 * Result of manual rule invocation
 */
export interface ManualInvocationResult {
  success: boolean;
  ruleId: string;
  ruleName: string;
  output?: string;
  error?: string;
  executedAt: string;
}
