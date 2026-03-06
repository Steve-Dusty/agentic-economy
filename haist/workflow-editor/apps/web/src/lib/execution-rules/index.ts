/**
 * Execution Rules Module
 *
 * Automated trigger processing system that:
 * 1. Receives Composio trigger events
 * 2. Matches against user-defined rules using AI
 * 3. Executes matched rule's steps via Composio tools
 * 4. Sends output to configured destinations
 */

// Types
export type {
  ExecutionRule,
  ExecutionRuleInput,
  ExecutionStep,
  InstructionStep,
  ActionStep,
  OutputConfig,
  OutputPlatform,
  OutputFormat,
  TriggerPayload,
  RuleMatchResult,
  RuleExecutionResult,
  StepResult,
  ProcessingResult,
  // Activation mode types
  ActivationMode,
  ScheduleInterval,
  ManualInvocationContext,
  ManualInvocationResult,
} from './types';

// Storage
export { executionRulesStorage } from './storage';

// Agents
export { ruleMatcherAgent } from './rule-matcher-agent';
export { ruleExecutorAgent } from './rule-executor-agent';

// Services
export { triggerProcessingService } from './trigger-processing-service';

// Prompts
export {
  RULE_MATCHER_SYSTEM_PROMPT,
  RULE_EXECUTOR_SYSTEM_PROMPT,
  buildRuleMatcherPrompt,
  buildRuleExecutorPrompt,
} from './prompts';
