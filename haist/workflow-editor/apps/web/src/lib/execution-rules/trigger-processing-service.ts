/**
 * Trigger Processing Service
 *
 * Orchestrates the flow of:
 * 1. Getting user's active rules
 * 2. Matching trigger against rules
 * 3. Executing the matched rule
 * 4. Sending output to destination
 */

import { executionRulesStorage } from './storage';
import { executionLogStorage } from './execution-log-storage';
import { ruleMatcherAgent } from './rule-matcher-agent';
import { ruleExecutorAgent } from './rule-executor-agent';
import type {
  TriggerPayload,
  ExecutionRule,
  RuleExecutionResult,
  ProcessingResult,
  OutputFormat,
  ScheduleInterval,
} from './types';
import { notificationsStorage } from '@/lib/notifications/storage';

/**
 * Result of manual invocation
 */
interface ManualProcessingResult {
  success: boolean;
  output?: string;
  error?: string;
}

/**
 * Result of scheduled execution
 */
interface ScheduledProcessingResult {
  rulesProcessed: number;
  rulesSucceeded: number;
  rulesFailed: number;
  errors: Array<{ ruleId: string; ruleName: string; error: string }>;
}

/**
 * Trigger Processing Service class
 */
class TriggerProcessingService {
  /**
   * Process an incoming trigger for a user
   */
  async process(userId: string, payload: TriggerPayload): Promise<ProcessingResult> {
    console.log(`[TriggerProcessing] Processing trigger ${payload.triggerSlug} for user ${userId}`);

    try {
      // 1. Get user's active rules (sorted by priority DESC)
      const rules = await executionRulesStorage.getActiveByUserId(userId);

      if (rules.length === 0) {
        console.log(`[TriggerProcessing] User ${userId} has no active rules`);
        return { matched: false, executed: false };
      }

      console.log(`[TriggerProcessing] Found ${rules.length} active rules for user ${userId}`);

      // 2. Filter rules by activation mode - only 'trigger' or 'all' modes are eligible
      const triggerEligibleRules = rules.filter(
        (rule) => rule.activationMode === 'trigger' || rule.activationMode === 'all'
      );

      if (triggerEligibleRules.length === 0) {
        console.log(
          `[TriggerProcessing] No rules with trigger-eligible activation mode for user ${userId}`
        );
        return { matched: false, executed: false };
      }

      console.log(
        `[TriggerProcessing] ${triggerEligibleRules.length} rules have trigger-eligible activation mode`
      );

      // 3. Filter rules by accepted triggers
      const applicableRules = this.filterByAcceptedTriggers(triggerEligibleRules, payload.triggerSlug);

      if (applicableRules.length === 0) {
        console.log(
          `[TriggerProcessing] No rules accept trigger ${payload.triggerSlug}`
        );
        return { matched: false, executed: false };
      }

      console.log(
        `[TriggerProcessing] ${applicableRules.length} rules accept trigger ${payload.triggerSlug}`
      );

      // 4. Match trigger content against rules using AI
      const matchResult = await ruleMatcherAgent.match(payload, applicableRules);

      if (!matchResult.matched || !matchResult.rule) {
        console.log(
          `[TriggerProcessing] No rule matched. Reasoning: ${matchResult.reasoning}`
        );
        return { matched: false, executed: false };
      }

      console.log(
        `[TriggerProcessing] Matched rule "${matchResult.rule.name}" (confidence: ${matchResult.confidence})`
      );

      // 5. Execute the matched rule
      const startTime = Date.now();
      const executionResult = await ruleExecutorAgent.execute(
        matchResult.rule,
        payload,
        userId
      );
      const durationMs = Date.now() - startTime;

      console.log(
        `[TriggerProcessing] Rule execution ${executionResult.success ? 'succeeded' : 'failed'}`
      );

      // 5.5. Save execution log
      const hasPartial = executionResult.stepResults.some(s => s.success) && executionResult.stepResults.some(s => !s.success);
      try {
        await executionLogStorage.create({
          ruleId: matchResult.rule.id,
          ruleName: matchResult.rule.name,
          userId,
          triggerSlug: payload.triggerSlug,
          status: executionResult.success ? 'success' : hasPartial ? 'partial' : 'failure',
          stepsJson: executionResult.stepResults,
          outputText: executionResult.output,
          errorText: executionResult.error,
          durationMs,
        });
      } catch (logError) {
        console.error('[TriggerProcessing] Failed to save execution log:', logError);
      }

      // 5.6. Create notification
      try {
        await notificationsStorage.create({
          userId,
          type: executionResult.success ? 'execution_success' : 'execution_failure',
          title: executionResult.success
            ? `✅ ${matchResult.rule.name} completed`
            : `❌ ${matchResult.rule.name} failed`,
          body: executionResult.success
            ? (executionResult.output?.slice(0, 200) || 'Rule executed successfully.')
            : (executionResult.error?.slice(0, 200) || 'An unknown error occurred.'),
          ruleId: matchResult.rule.id,
          ruleName: matchResult.rule.name,
        });
      } catch (notifError) {
        console.error('[TriggerProcessing] Failed to create notification:', notifError);
      }

      // 6. Update execution stats
      await executionRulesStorage.incrementExecutionCount(matchResult.rule.id);

      // 7. Send output if configured
      if (matchResult.rule.outputConfig.platform !== 'none') {
        await this.sendOutput(matchResult.rule, executionResult, userId);
      }

      return {
        matched: true,
        executed: executionResult.success,
        ruleName: matchResult.rule.name,
        ruleId: matchResult.rule.id,
        error: executionResult.error,
      };
    } catch (error) {
      console.error('[TriggerProcessing] Error processing trigger:', error);
      return {
        matched: false,
        executed: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Process a manual invocation of a rule
   */
  async processManual(
    userId: string,
    rule: ExecutionRule,
    context: string,
    conversationHistory?: Array<{ role: string; content: string }>
  ): Promise<ManualProcessingResult> {
    console.log(`[TriggerProcessing] Processing manual invocation of rule "${rule.name}" for user ${userId}`);

    try {
      // Create a synthetic trigger payload for manual invocation
      // Format conversation history if provided
      const chatHistoryText = conversationHistory?.length
        ? conversationHistory
            .map((m) => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`)
            .join('\n\n')
        : undefined;

      const syntheticPayload: TriggerPayload = {
        id: `manual_${Date.now()}`,
        uuid: `manual_${Date.now()}`,
        triggerSlug: 'MANUAL_INVOCATION',
        toolkitSlug: 'manual',
        userId,
        payload: {
          userContext: context,
          invokedAt: new Date().toISOString(),
          ...(chatHistoryText ? { conversationHistory: chatHistoryText } : {}),
        },
        originalPayload: {
          userContext: context,
          ...(chatHistoryText ? { conversationHistory: chatHistoryText } : {}),
        },
        metadata: {
          id: `manual_${Date.now()}`,
          uuid: `manual_${Date.now()}`,
          toolkitSlug: 'manual',
          triggerSlug: 'MANUAL_INVOCATION',
          triggerConfig: {},
          connectedAccount: {
            id: userId,
            uuid: userId,
            authConfigId: '',
            authConfigUUID: '',
            userId,
            status: 'ACTIVE',
          },
        },
      };

      // Execute the rule directly (skip matching since user explicitly selected it)
      const startTime = Date.now();
      const executionResult = await ruleExecutorAgent.execute(
        rule,
        syntheticPayload,
        userId
      );
      const durationMs = Date.now() - startTime;

      console.log(
        `[TriggerProcessing] Manual execution ${executionResult.success ? 'succeeded' : 'failed'}`
      );

      // Save execution log
      const hasPartial = executionResult.stepResults.some(s => s.success) && executionResult.stepResults.some(s => !s.success);
      try {
        await executionLogStorage.create({
          ruleId: rule.id,
          ruleName: rule.name,
          userId,
          triggerSlug: 'MANUAL_INVOCATION',
          status: executionResult.success ? 'success' : hasPartial ? 'partial' : 'failure',
          stepsJson: executionResult.stepResults,
          outputText: executionResult.output,
          errorText: executionResult.error,
          durationMs,
        });
      } catch (logError) {
        console.error('[TriggerProcessing] Failed to save execution log:', logError);
      }

      // Create notification
      try {
        await notificationsStorage.create({
          userId,
          type: executionResult.success ? 'execution_success' : 'execution_failure',
          title: executionResult.success
            ? `✅ ${rule.name} completed`
            : `❌ ${rule.name} failed`,
          body: executionResult.success
            ? (executionResult.output?.slice(0, 200) || 'Rule executed successfully.')
            : (executionResult.error?.slice(0, 200) || 'An unknown error occurred.'),
          ruleId: rule.id,
          ruleName: rule.name,
        });
      } catch (notifError) {
        console.error('[TriggerProcessing] Failed to create notification:', notifError);
      }

      // Update execution stats
      await executionRulesStorage.incrementExecutionCount(rule.id);

      // Send output if configured
      if (rule.outputConfig.platform !== 'none') {
        await this.sendOutput(rule, executionResult, userId);
      }

      return {
        success: executionResult.success,
        output: executionResult.output,
        error: executionResult.error,
      };
    } catch (error) {
      console.error('[TriggerProcessing] Error processing manual invocation:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Process all scheduled rules that are due to run
   */
  async processScheduled(): Promise<ScheduledProcessingResult> {
    console.log('[TriggerProcessing] Processing scheduled rules');

    const result: ScheduledProcessingResult = {
      rulesProcessed: 0,
      rulesSucceeded: 0,
      rulesFailed: 0,
      errors: [],
    };

    try {
      // Get all rules that are due to run
      const dueRules = await executionRulesStorage.getScheduledRulesDue();

      console.log(`[TriggerProcessing] Found ${dueRules.length} scheduled rules due to run`);

      for (const rule of dueRules) {
        result.rulesProcessed++;

        try {
          // Create a synthetic trigger payload for scheduled execution
          const syntheticPayload: TriggerPayload = {
            id: `scheduled_${Date.now()}`,
            uuid: `scheduled_${Date.now()}`,
            triggerSlug: 'SCHEDULED_EXECUTION',
            toolkitSlug: 'scheduled',
            userId: rule.userId,
            payload: {
              scheduledAt: new Date().toISOString(),
              interval: rule.scheduleInterval,
            },
            originalPayload: {
              scheduledAt: new Date().toISOString(),
            },
            metadata: {
              id: `scheduled_${Date.now()}`,
              uuid: `scheduled_${Date.now()}`,
              toolkitSlug: 'scheduled',
              triggerSlug: 'SCHEDULED_EXECUTION',
              triggerConfig: {},
              connectedAccount: {
                id: rule.userId,
                uuid: rule.userId,
                authConfigId: '',
                authConfigUUID: '',
                userId: rule.userId,
                status: 'ACTIVE',
              },
            },
          };

          // Execute the rule
          const startTime = Date.now();
          const executionResult = await ruleExecutorAgent.execute(
            rule,
            syntheticPayload,
            rule.userId
          );
          const durationMs = Date.now() - startTime;

          // Save execution log
          const hasPartial = executionResult.stepResults.some(s => s.success) && executionResult.stepResults.some(s => !s.success);
          try {
            await executionLogStorage.create({
              ruleId: rule.id,
              ruleName: rule.name,
              userId: rule.userId,
              triggerSlug: 'SCHEDULED_EXECUTION',
              status: executionResult.success ? 'success' : hasPartial ? 'partial' : 'failure',
              stepsJson: executionResult.stepResults,
              outputText: executionResult.output,
              errorText: executionResult.error,
              durationMs,
            });
          } catch (logError) {
            console.error('[TriggerProcessing] Failed to save execution log:', logError);
          }

          // Create notification
          try {
            await notificationsStorage.create({
              userId: rule.userId,
              type: executionResult.success ? 'execution_success' : 'execution_failure',
              title: executionResult.success
                ? `✅ ${rule.name} completed`
                : `❌ ${rule.name} failed`,
              body: executionResult.success
                ? (executionResult.output?.slice(0, 200) || 'Scheduled rule executed successfully.')
                : (executionResult.error?.slice(0, 200) || 'An unknown error occurred.'),
              ruleId: rule.id,
              ruleName: rule.name,
            });
          } catch (notifError) {
            console.error('[TriggerProcessing] Failed to create notification:', notifError);
          }

          // Update schedule timestamps
          if (rule.scheduleInterval) {
            await executionRulesStorage.updateScheduleRun(
              rule.id,
              rule.scheduleInterval as ScheduleInterval
            );
          }

          // Send output if configured
          if (rule.outputConfig.platform !== 'none') {
            await this.sendOutput(rule, executionResult, rule.userId);
          }

          if (executionResult.success) {
            result.rulesSucceeded++;
            console.log(`[TriggerProcessing] Scheduled rule "${rule.name}" executed successfully`);
          } else {
            result.rulesFailed++;
            result.errors.push({
              ruleId: rule.id,
              ruleName: rule.name,
              error: executionResult.error || 'Unknown error',
            });
            console.log(`[TriggerProcessing] Scheduled rule "${rule.name}" failed: ${executionResult.error}`);
          }
        } catch (error) {
          result.rulesFailed++;
          result.errors.push({
            ruleId: rule.id,
            ruleName: rule.name,
            error: error instanceof Error ? error.message : 'Unknown error',
          });
          console.error(`[TriggerProcessing] Error executing scheduled rule "${rule.name}":`, error);
        }
      }

      console.log(
        `[TriggerProcessing] Scheduled processing complete: ${result.rulesSucceeded}/${result.rulesProcessed} succeeded`
      );

      return result;
    } catch (error) {
      console.error('[TriggerProcessing] Error processing scheduled rules:', error);
      return result;
    }
  }

  /**
   * Filter rules by accepted triggers
   */
  private filterByAcceptedTriggers(
    rules: ExecutionRule[],
    triggerSlug: string
  ): ExecutionRule[] {
    return rules.filter((rule) => {
      // Empty array means accept all triggers
      if (!rule.acceptedTriggers || rule.acceptedTriggers.length === 0) {
        return true;
      }
      return rule.acceptedTriggers.includes(triggerSlug);
    });
  }

  /**
   * Send output to configured destination
   */
  private async sendOutput(
    rule: ExecutionRule,
    result: RuleExecutionResult,
    userId: string
  ): Promise<void> {
    const { platform, destination, format, template } = rule.outputConfig;

    // Format the output message
    const message = this.formatOutput(result, format, template);

    console.log(
      `[TriggerProcessing] Sending output to ${platform}${destination ? `:${destination}` : ''}`
    );

    try {
      switch (platform) {
        case 'slack':
          await this.sendToSlack(destination!, message, userId);
          break;
        case 'gmail':
          await this.sendToGmail(destination!, rule.name, message, userId);
          break;
        case 'webhook':
          await this.sendToWebhook(destination!, rule.name, result);
          break;
        default:
          console.log(`[TriggerProcessing] Unknown platform: ${platform}`);
      }
    } catch (error) {
      console.error(`[TriggerProcessing] Failed to send output to ${platform}:`, error);
    }
  }

  /**
   * Format output message based on format and template
   */
  private formatOutput(
    result: RuleExecutionResult,
    format: OutputFormat,
    template?: string
  ): string {
    if (template) {
      return template.replace(/\{\{result\}\}/g, result.output || '');
    }

    switch (format) {
      case 'summary':
        return `Rule "${result.ruleName}" executed ${result.success ? 'successfully' : 'with errors'}.\n\n${result.output || ''}`;
      case 'detailed':
        return JSON.stringify(result, null, 2);
      case 'raw':
        return result.output || '';
      default:
        return result.output || '';
    }
  }

  /**
   * Send message to Slack
   */
  private async sendToSlack(
    channel: string,
    message: string,
    userId: string
  ): Promise<void> {
    // Use the existing Composio service to send Slack message
    const { Composio } = await import('@composio/core');
    const { OpenAIAgentsProvider } = await import('@composio/openai-agents');

    const composio = new Composio({
      apiKey: process.env.COMPOSIO_API_KEY!,
      provider: new OpenAIAgentsProvider(),
    });

    const authConfigs: Record<string, string> = {};
    if (process.env.SLACK_AUTH_CONFIG_ID) {
      authConfigs.slack = process.env.SLACK_AUTH_CONFIG_ID;
    }

    const session = await composio.create(userId, { authConfigs });
    const tools = await session.tools();

    // Use the agent to send the message
    const { Agent, run } = await import('@openai/agents');
    const agent = new Agent({
      name: 'Slack Sender',
      instructions: 'Send the provided message to the specified Slack channel.',
      model: 'gpt-5.2',
      tools,
    });

    await run(agent, `Send this message to channel ${channel}: ${message}`);
  }

  /**
   * Send email via Gmail
   */
  private async sendToGmail(
    to: string,
    subject: string,
    body: string,
    userId: string
  ): Promise<void> {
    const { Composio } = await import('@composio/core');
    const { OpenAIAgentsProvider } = await import('@composio/openai-agents');

    const composio = new Composio({
      apiKey: process.env.COMPOSIO_API_KEY!,
      provider: new OpenAIAgentsProvider(),
    });

    const authConfigs: Record<string, string> = {};
    if (process.env.GMAIL_AUTH_CONFIG_ID) {
      authConfigs.gmail = process.env.GMAIL_AUTH_CONFIG_ID;
    }

    const session = await composio.create(userId, { authConfigs });
    const tools = await session.tools();

    const { Agent, run } = await import('@openai/agents');
    const agent = new Agent({
      name: 'Gmail Sender',
      instructions: 'Send the provided email to the specified recipient.',
      model: 'gpt-5.2',
      tools,
    });

    await run(
      agent,
      `Send an email to ${to} with subject "Automation Result: ${subject}" and body: ${body}`
    );
  }

  /**
   * Send to webhook
   */
  private async sendToWebhook(
    url: string,
    ruleName: string,
    result: RuleExecutionResult
  ): Promise<void> {
    await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rule: ruleName,
        result,
        timestamp: new Date().toISOString(),
      }),
    });
  }
}

// Export singleton instance
export const triggerProcessingService = new TriggerProcessingService();
