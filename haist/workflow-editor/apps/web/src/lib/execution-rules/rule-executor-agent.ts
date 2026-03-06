/**
 * Rule Executor Agent
 *
 * Uses OpenAI Agents SDK with Composio tools to execute rule steps.
 * Follows the pattern from tool-router-service.ts
 */

import { Composio } from '@composio/core';
import { OpenAIAgentsProvider } from '@composio/openai-agents';
import { Agent, run } from '@openai/agents';
import type {
  ExecutionRule,
  TriggerPayload,
  RuleExecutionResult,
  StepResult,
  ExecutionStep,
} from './types';
import { RULE_EXECUTOR_SYSTEM_PROMPT, buildRuleExecutorPrompt } from './prompts';

// Types for internal use
type AgentTools = Awaited<
  ReturnType<Awaited<ReturnType<Composio<OpenAIAgentsProvider>['create']>>['tools']>
>;

interface ComposioSessionData {
  tools: AgentTools;
  userId: string;
  createdAt: Date;
}

/**
 * Rule Executor Agent class
 */
class RuleExecutorAgent {
  private composio: Composio<OpenAIAgentsProvider> | null = null;
  private sessions: Map<string, ComposioSessionData> = new Map();

  /**
   * Get Composio client
   */
  private getComposio(): Composio<OpenAIAgentsProvider> | null {
    if (this.composio) return this.composio;

    if (!process.env.COMPOSIO_API_KEY) {
      console.warn('[RuleExecutorAgent] COMPOSIO_API_KEY not configured');
      return null;
    }

    this.composio = new Composio({
      apiKey: process.env.COMPOSIO_API_KEY,
      provider: new OpenAIAgentsProvider(),
    });
    return this.composio;
  }

  /**
   * Build auth configs from environment variables
   */
  private buildAuthConfigs(): Record<string, string> {
    const authConfigs: Record<string, string> = {};

    const authConfigMapping: Record<string, string | undefined> = {
      // Google Services
      gmail: process.env.GMAIL_AUTH_CONFIG_ID,
      googlecalendar: process.env.GOOGLE_CALENDAR_AUTH_CONFIG_ID,
      googledrive: process.env.GOOGLE_DRIVE_AUTH_CONFIG_ID,
      googledocs: process.env.GOOGLE_DOCS_AUTH_CONFIG_ID,
      googlesheets: process.env.GOOGLE_SHEETS_AUTH_CONFIG_ID,
      googletasks: process.env.GOOGLE_TASKS_AUTH_CONFIG_ID,
      google_maps: process.env.GOOGLE_MAPS_AUTH_CONFIG_ID,
      googlemeet: process.env.GOOGLEMEET_AUTH_CONFIG_ID,
      youtube: process.env.YOUTUBE_AUTH_CONFIG_ID,
      // Microsoft Services
      outlook: process.env.OUTLOOK_AUTH_CONFIG_ID,
      one_drive: process.env.ONE_DRIVE_AUTH_CONFIG_ID,
      microsoft_teams: process.env.MICROSOFT_TEAMS_AUTH_CONFIG_ID,
      // Communication
      slack: process.env.SLACK_AUTH_CONFIG_ID,
      discord: process.env.DISCORD_AUTH_CONFIG_ID,
      // Productivity
      notion: process.env.NOTION_AUTH_CONFIG_ID,
      linear: process.env.LINEAR_AUTH_CONFIG_ID,
      jira: process.env.JIRA_AUTH_CONFIG_ID,
      asana: process.env.ASANA_AUTH_CONFIG_ID,
      calendly: process.env.CALENDLY_AUTH_CONFIG_ID,
      canvas: process.env.CANVAS_AUTH_CONFIG_ID,
      // Development
      github: process.env.GITHUB_AUTH_CONFIG_ID,
      figma: process.env.FIGMA_AUTH_CONFIG_ID,
      // Social
      twitter: process.env.TWITTER_AUTH_CONFIG_ID,
      linkedin: process.env.LINKEDIN_AUTH_CONFIG_ID,
      reddit: process.env.REDDIT_AUTH_CONFIG_ID,
      // Design & Creative
      canva: process.env.CANVA_AUTH_CONFIG_ID,
      // Sales & CRM
      salesforce: process.env.SALESFORCE_AUTH_CONFIG_ID,
      apollo: process.env.APOLLO_AUTH_CONFIG_ID,
      // Search & Tools
      exa: process.env.EXA_AUTH_CONFIG_ID,
      browserbase_tool: process.env.BROWSERBASE_TOOL_AUTH_CONFIG_ID,
      firecrawl: process.env.FIRECRAWL_AUTH_CONFIG_ID,
    };

    for (const [app, configId] of Object.entries(authConfigMapping)) {
      if (configId) {
        authConfigs[app] = configId;
      }
    }

    return authConfigs;
  }

  /**
   * Get or create a Composio session for a user
   */
  private async getOrCreateSession(userId: string): Promise<ComposioSessionData | null> {
    const composio = this.getComposio();
    if (!composio) return null;

    // Check for existing session (refresh if older than 1 hour)
    const existingSession = this.sessions.get(userId);
    if (existingSession) {
      const ageMs = Date.now() - existingSession.createdAt.getTime();
      if (ageMs < 60 * 60 * 1000) {
        return existingSession;
      }
    }

    try {
      const authConfigs = this.buildAuthConfigs();
      const session = await composio.create(userId, { authConfigs });
      const tools = await session.tools();

      const sessionData: ComposioSessionData = {
        tools,
        userId,
        createdAt: new Date(),
      };

      this.sessions.set(userId, sessionData);
      return sessionData;
    } catch (error) {
      console.error('[RuleExecutorAgent] Failed to create Composio session:', error);
      return null;
    }
  }

  /**
   * Execute a rule's steps
   */
  async execute(
    rule: ExecutionRule,
    payload: TriggerPayload,
    userId: string
  ): Promise<RuleExecutionResult> {
    console.log(`[RuleExecutorAgent] Starting execution of rule "${rule.name}" with ${rule.executionSteps.length} steps`);

    const startTime = new Date().toISOString();
    const stepResults: StepResult[] = [];
    const previousResults: string[] = [];

    // Get Composio session
    console.log(`[RuleExecutorAgent] Getting Composio session for user ${userId}`);
    const sessionData = await this.getOrCreateSession(userId);
    if (!sessionData) {
      console.error('[RuleExecutorAgent] Failed to get Composio session');
      return {
        success: false,
        ruleId: rule.id,
        ruleName: rule.name,
        triggerSlug: payload.triggerSlug,
        stepResults: [],
        error: 'Composio service not configured',
        executedAt: startTime,
      };
    }

    console.log(`[RuleExecutorAgent] Session ready, executing ${rule.executionSteps.length} steps`);

    // Execute each step
    for (let i = 0; i < rule.executionSteps.length; i++) {
      const step = rule.executionSteps[i];
      const stepResult = await this.executeStep(
        step,
        i,
        rule,
        payload,
        sessionData,
        previousResults
      );
      stepResults.push(stepResult);

      if (stepResult.success && stepResult.result) {
        previousResults.push(String(stepResult.result));
      }
    }

    // Determine overall success
    const success = stepResults.every((r) => r.success);
    const output = previousResults.join('\n\n');

    return {
      success,
      ruleId: rule.id,
      ruleName: rule.name,
      triggerSlug: payload.triggerSlug,
      stepResults,
      output,
      error: success ? undefined : stepResults.find((r) => !r.success)?.error,
      executedAt: startTime,
    };
  }

  /**
   * Execute a single step
   */
  private async executeStep(
    step: ExecutionStep,
    index: number,
    rule: ExecutionRule,
    payload: TriggerPayload,
    sessionData: ComposioSessionData,
    previousResults: string[]
  ): Promise<StepResult> {
    try {
      if (step.type === 'instruction') {
        // Use AI agent to interpret and execute the instruction
        return await this.executeInstructionStep(
          step.content,
          index,
          rule,
          payload,
          sessionData,
          previousResults
        );
      } else if (step.type === 'action') {
        // Direct Composio tool execution
        return await this.executeActionStep(step, index, sessionData);
      } else {
        return {
          stepIndex: index,
          type: 'instruction',
          success: false,
          error: 'Unknown step type',
        };
      }
    } catch (error) {
      return {
        stepIndex: index,
        type: step.type,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Execute an instruction step using AI agent
   */
  private async executeInstructionStep(
    instruction: string,
    index: number,
    rule: ExecutionRule,
    payload: TriggerPayload,
    sessionData: ComposioSessionData,
    previousResults: string[]
  ): Promise<StepResult> {
    try {
      // Build the prompt with context
      const prompt = buildRuleExecutorPrompt(
        rule.name,
        payload.triggerSlug,
        payload.toolkitSlug,
        payload.payload || payload.originalPayload || {},
        instruction,
        previousResults
      );

      // Create agent with Composio tools
      const agent = new Agent({
        name: 'Rule Executor',
        instructions: RULE_EXECUTOR_SYSTEM_PROMPT,
        model: 'gpt-5.2',
        tools: sessionData.tools,
      });

      // Run the agent
      const result = await run(agent, prompt);

      return {
        stepIndex: index,
        type: 'instruction',
        success: true,
        result: result.finalOutput || 'Step completed',
      };
    } catch (error) {
      console.error(`[RuleExecutorAgent] Instruction step ${index} failed:`, error);
      return {
        stepIndex: index,
        type: 'instruction',
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Execute an action step (direct tool call)
   */
  private async executeActionStep(
    step: { toolName: string; parameters: Record<string, unknown> },
    index: number,
    sessionData: ComposioSessionData
  ): Promise<StepResult> {
    try {
      // For direct action steps, we use the AI agent with a specific instruction
      // to call the exact tool with the provided parameters
      const instruction = `Call the tool "${step.toolName}" with these exact parameters: ${JSON.stringify(step.parameters)}. Execute this tool call immediately.`;

      const agent = new Agent({
        name: 'Rule Executor',
        instructions:
          'You are a tool executor. When given a tool name and parameters, call that exact tool immediately with the provided parameters. Do not modify the parameters.',
        model: 'gpt-5.2',
        tools: sessionData.tools,
      });

      const result = await run(agent, instruction);

      return {
        stepIndex: index,
        type: 'action',
        success: true,
        result: result.finalOutput || 'Action completed',
      };
    } catch (error) {
      console.error(`[RuleExecutorAgent] Action step ${index} failed:`, error);
      return {
        stepIndex: index,
        type: 'action',
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Clean up expired sessions
   */
  cleanupSessions(): void {
    const now = Date.now();
    const maxAge = 60 * 60 * 1000; // 1 hour

    for (const [userId, session] of this.sessions.entries()) {
      if (now - session.createdAt.getTime() > maxAge) {
        this.sessions.delete(userId);
      }
    }
  }
}

// Export singleton instance
export const ruleExecutorAgent = new RuleExecutorAgent();
