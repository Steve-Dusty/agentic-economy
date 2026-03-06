/**
 * Automation Tools for the AI Assistant
 *
 * Custom tools that allow the AI to create, list, toggle, and delete
 * execution rules (automations) directly from natural language chat.
 * Uses JSON Schema parameters (not Zod) for compatibility with agents-core.
 */

import { tool } from '@openai/agents';
import { executionRulesStorage } from '@/lib/execution-rules/storage';
import { triggerProcessingService } from '@/lib/execution-rules/trigger-processing-service';
import type {
  ExecutionRuleInput,
  ExecutionStep,
  OutputConfig,
  ActivationMode,
  ScheduleInterval,
} from '@/lib/execution-rules/types';

/**
 * Creates all automation tools bound to a specific userId.
 */
export function createAutomationTools(userId: string) {
  const createAutomation = tool({
    name: 'create_automation',
    description: `Create a new automation rule that runs automatically based on triggers or schedules. Use this when the user wants something to happen automatically/repeatedly — NOT for one-time actions.

Examples: "Notify me on Slack when I get an email from my boss", "Every morning summarize my unread emails", "When a GitHub issue is assigned to me, create a task in Linear".

You must determine the trigger type (Composio trigger slug or scheduled mode), what steps to execute, and where to send output.`,
    parameters: {
      type: 'object' as const,
      properties: {
        name: { type: 'string', description: 'Short descriptive name, e.g. "Boss Email Notifier"' },
        description: { type: 'string', description: 'Longer description of what this automation does' },
        accepted_triggers: {
          type: 'array',
          items: { type: 'string' },
          description: 'Composio trigger slugs, e.g. ["GMAIL_NEW_GMAIL_MESSAGE"]. Empty for scheduled-only.',
        },
        topic_condition: {
          type: 'string',
          description: 'Human-readable condition the AI evaluates against trigger data, e.g. "Email is from john@company.com"',
        },
        execution_steps: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              type: { type: 'string', enum: ['instruction', 'action'] },
              content: { type: 'string', description: 'For instruction type: natural language description' },
              tool_name: { type: 'string', description: 'For action type: Composio tool name' },
              parameters: { type: 'object', description: 'For action type: tool parameters' },
            },
            required: ['type'],
          },
          description: 'Steps to execute when the automation fires',
        },
        output_platform: { type: 'string', enum: ['slack', 'gmail', 'webhook', 'none'], default: 'none' },
        output_destination: { type: 'string', description: 'Channel ID, email, or webhook URL' },
        output_format: { type: 'string', enum: ['summary', 'detailed', 'raw'], default: 'summary' },
        activation_mode: {
          type: 'string',
          enum: ['trigger', 'manual', 'scheduled', 'all'],
          default: 'trigger',
          description: '"trigger" for webhook-based, "scheduled" for time-based, "manual" for @mention, "all" for any',
        },
        schedule_interval: {
          type: 'string',
          enum: ['15min', 'hourly', 'daily', 'weekly'],
          description: 'Required if activation_mode is "scheduled" or "all"',
        },
        priority: { type: 'number', default: 0, description: 'Higher priority rules evaluated first' },
      },
      required: ['name', 'topic_condition', 'execution_steps'],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as Record<string, unknown>;
        const execStepsRaw = input.execution_steps as Array<{
          type: string; content?: string; tool_name?: string; parameters?: Record<string, unknown>;
        }>;

        const executionSteps: ExecutionStep[] = execStepsRaw.map((step) => {
          if (step.type === 'instruction') {
            return { type: 'instruction' as const, content: step.content || '' };
          }
          return {
            type: 'action' as const,
            toolName: step.tool_name || '',
            parameters: (step.parameters || {}) as Record<string, unknown>,
          };
        });

        const outputConfig: OutputConfig = {
          platform: (input.output_platform as OutputConfig['platform']) || 'none',
          destination: input.output_destination as string | undefined,
          format: (input.output_format as OutputConfig['format']) || 'summary',
        };

        const activationMode = (input.activation_mode as ActivationMode) || 'trigger';
        const scheduleInterval = input.schedule_interval as ScheduleInterval | undefined;
        const isScheduled = activationMode === 'scheduled' || activationMode === 'all';

        const ruleInput: ExecutionRuleInput = {
          name: input.name as string,
          description: input.description as string | undefined,
          isActive: true,
          priority: (input.priority as number) ?? 0,
          acceptedTriggers: (input.accepted_triggers as string[]) || [],
          topicCondition: input.topic_condition as string,
          executionSteps,
          outputConfig,
          activationMode,
          scheduleEnabled: isScheduled && !!scheduleInterval,
          scheduleInterval,
        };

        const rule = await executionRulesStorage.create(userId, ruleInput);

        return JSON.stringify({
          success: true,
          rule_id: rule.id,
          name: rule.name,
          activation_mode: rule.activationMode,
          is_active: rule.isActive,
          triggers: rule.acceptedTriggers,
          schedule: rule.scheduleEnabled ? rule.scheduleInterval : null,
          message: `Automation "${rule.name}" created and active.`,
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to create automation',
        });
      }
    },
  });

  const listAutomations = tool({
    name: 'list_automations',
    description: 'List all automations for the current user. Use when the user asks about their existing automations or rules.',
    parameters: {
      type: 'object' as const,
      properties: {
        active_only: { type: 'boolean', description: 'If true, only return active automations', default: false },
      },
      required: [] as string[],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as Record<string, unknown>;
        const activeOnly = input.active_only as boolean | undefined;
        const rules = activeOnly
          ? await executionRulesStorage.getActiveByUserId(userId)
          : await executionRulesStorage.getByUserId(userId);

        const summary = rules.map((r) => ({
          id: r.id,
          name: r.name,
          description: r.description,
          is_active: r.isActive,
          activation_mode: r.activationMode,
          triggers: r.acceptedTriggers,
          schedule: r.scheduleEnabled ? r.scheduleInterval : null,
          execution_count: r.executionCount,
          last_executed: r.lastExecutedAt,
        }));

        return JSON.stringify({ success: true, count: rules.length, automations: summary });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to list automations',
        });
      }
    },
  });

  const toggleAutomation = tool({
    name: 'toggle_automation',
    description: 'Enable or disable an existing automation. Use when the user wants to pause, resume, enable, or disable an automation.',
    parameters: {
      type: 'object' as const,
      properties: {
        rule_id: { type: 'string', description: 'The ID of the automation to toggle' },
        is_active: { type: 'boolean', description: 'true to enable, false to disable' },
      },
      required: ['rule_id', 'is_active'],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as { rule_id: string; is_active: boolean };
        const rule = await executionRulesStorage.getByIdAndUser(input.rule_id, userId);
        if (!rule) {
          return JSON.stringify({ success: false, error: 'Automation not found' });
        }

        const updated = await executionRulesStorage.update(input.rule_id, { isActive: input.is_active });
        return JSON.stringify({
          success: true,
          name: updated?.name,
          is_active: updated?.isActive,
          message: `Automation "${updated?.name}" ${input.is_active ? 'enabled' : 'disabled'}.`,
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to toggle automation',
        });
      }
    },
  });

  const deleteAutomation = tool({
    name: 'delete_automation',
    description: 'Permanently delete an automation. List automations first if you need the ID.',
    parameters: {
      type: 'object' as const,
      properties: {
        rule_id: { type: 'string', description: 'The ID of the automation to delete' },
      },
      required: ['rule_id'],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as { rule_id: string };
        const rule = await executionRulesStorage.getByIdAndUser(input.rule_id, userId);
        if (!rule) {
          return JSON.stringify({ success: false, error: 'Automation not found' });
        }

        const deleted = await executionRulesStorage.delete(input.rule_id);
        return JSON.stringify({
          success: true,
          deleted,
          name: rule.name,
          message: `Automation "${rule.name}" deleted.`,
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to delete automation',
        });
      }
    },
  });

  const invokeAutomation = tool({
    name: 'invoke_automation',
    description: `Manually invoke/run an existing automation rule right now. Use when the user @mentions a rule name or asks to run a specific automation.

IMPORTANT: ALWAYS include conversation_history with the full chat transcript when invoking. The automation executor runs in a separate context and has NO access to the current conversation unless you pass it explicitly.`,
    parameters: {
      type: 'object' as const,
      properties: {
        rule_id: { type: 'string', description: 'The ID of the automation to invoke. List automations first if needed.' },
        context: { type: 'string', description: 'Additional context or instructions for this invocation' },
        conversation_history: {
          type: 'string',
          description: 'REQUIRED: The full conversation history from this chat session, formatted as "User: ...\nAssistant: ..." for each message. The automation runs in isolation and needs this to access any chat content.',
        },
      },
      required: ['rule_id', 'conversation_history'],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as { rule_id: string; context?: string; conversation_history?: string };
        const rule = await executionRulesStorage.getByIdAndUser(input.rule_id, userId);
        if (!rule) {
          return JSON.stringify({ success: false, error: 'Automation not found' });
        }

        if (!rule.isActive) {
          return JSON.stringify({ success: false, error: 'Automation is not active. Enable it first.' });
        }

        if (rule.activationMode !== 'manual' && rule.activationMode !== 'all') {
          return JSON.stringify({ success: false, error: 'Automation does not support manual invocation.' });
        }

        // Build conversation history array if provided as text
        const historyArray = input.conversation_history
          ? [{ role: 'system', content: input.conversation_history }]
          : undefined;

        const result = await triggerProcessingService.processManual(
          userId,
          rule,
          input.context || '',
          historyArray
        );

        return JSON.stringify({
          success: result.success,
          rule_name: rule.name,
          output: result.output?.slice(0, 1000),
          error: result.error,
          message: result.success
            ? `Automation "${rule.name}" executed successfully.`
            : `Automation "${rule.name}" failed: ${result.error}`,
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to invoke automation',
        });
      }
    },
  });

  return [createAutomation, listAutomations, toggleAutomation, deleteAutomation, invokeAutomation];
}
