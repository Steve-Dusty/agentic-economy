/**
 * Tool Router Service
 *
 * Handles Composio Tool Router with OpenAI Agents SDK in native format.
 */

import { Composio } from '@composio/core';
import { OpenAIAgentsProvider } from '@composio/openai-agents';
import { Agent, run } from '@openai/agents';
import type {
  ToolRouterMessage,
  ToolRouterChatResponse,
  ToolCallResult,
} from './types';
import { createAutomationTools } from './automation-tools';
import { createArtifactTools } from './artifact-tools';
import { createUserProfileTools, getUserProfileContext } from './user-profile-tools';
import { createOpenClawTools } from './openclaw-tools';
import { openClawService } from '@/lib/openclaw/openclaw-service';

// Types for internal use
type AgentTools = Awaited<ReturnType<Awaited<ReturnType<Composio<OpenAIAgentsProvider>['create']>>['tools']>>;

interface ComposioSessionData {
  tools: AgentTools;
  userId: string;
  createdAt: Date;
}

/**
 * Service for managing Composio Tool Router chat sessions
 */
class ToolRouterService {
  private composio: Composio<OpenAIAgentsProvider> | null = null;
  private sessions: Map<string, ComposioSessionData> = new Map();

  private getComposio(): Composio<OpenAIAgentsProvider> | null {
    if (this.composio) return this.composio;

    if (!process.env.COMPOSIO_API_KEY) {
      console.warn('COMPOSIO_API_KEY not configured');
      return null;
    }

    // Initialize Composio with OpenAI Agents provider (native format)
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
   * Build the system prompt for the AI agent
   */
  private buildSystemPrompt(currentDateTime: string, userId: string): string {
    return `Concise personal assistant. Do tasks, report results briefly. Now: ${currentDateTime}

CONTEXT:
You are the AI assistant inside the blockd app. The user is chatting with you directly in blockd's built-in chat interface. When the user says "this chat," "this conversation," or "the chat history," they mean THIS conversation with you in blockd — not Slack, Discord, or any external platform. The full conversation history is available to you as context in every message.

AUTOMATIONS:
Before creating automations, ask clarifying questions about trigger, conditions, action, and destination. Only call create_automation with specific details. Use "instruction" type for execution_steps with clear natural language. For recurring/automatic tasks, use automation tools. For one-time tasks, just do them directly.
For manual automations that reference "this chat" or "conversation history": when invoking an automation with invoke_automation, ALWAYS pass the full conversation history in the conversation_history parameter. The automation executor runs in a separate context with NO access to this chat — it only sees what you explicitly pass it.

MEMORY SYSTEM:
You have a 3-tier memory system using artifacts. Be PROACTIVE about remembering — don't wait to be asked.

1. SOUL (__user_profile__): Who the user is. Preferences, facts, patterns, recurring needs.
   → Use update_user_profile whenever you learn something about the user: their name, job, school, preferences, habits, tools they use, communication style, important people in their life, recurring tasks. Do this silently — don't announce it.

2. DAILY MEMORY: What happened today. Key decisions, tasks completed, important context.
   → After completing a task or learning something time-specific, use add_to_artifact to add it to today's daily artifact (title format: "Daily — YYYY-MM-DD"). If it doesn't exist, use save_to_artifacts to create it. Keep entries concise.

3. TOPIC ARTIFACTS: Large topics that span multiple conversations — trips, projects, research, ongoing work.
   → When a conversation involves a substantial topic (travel plans, project work, research), search for an existing topic artifact and add to it. If none exists and the topic is significant enough, create one.
   → Use add_to_artifact to append to existing artifacts. Use save_to_artifacts only for new topics.

ARTIFACT RULES:
- ALWAYS search before creating — don't create duplicates.
- Be proactive: after completing tasks, silently note key facts in the appropriate tier. Don't ask "should I save this?"
- Don't save trivial things (greetings, one-word answers, casual chat).
- DO save: travel plans, meeting outcomes, preferences, project decisions, important dates, research findings.
- If "Relevant information from previous conversations (artifacts)" is provided above, USE that context — don't start from scratch.
- Reference artifact information naturally in your responses when relevant.

EMAIL THREADING:
- Gmail: When replying to an existing email, ALWAYS use GMAIL_REPLY_TO_THREAD with the thread_id. Use GMAIL_SEND_EMAIL ONLY for brand new conversations with no prior thread.
- Outlook: When replying to an existing email, ALWAYS use OUTLOOK_REPLY_TO_EMAIL with the message_id. Use OUTLOOK_SEND_EMAIL ONLY for brand new conversations.
- Always extract thread_id/message_id from the conversation context or trigger data when replying.

LOCAL MACHINE (OpenClaw):
${openClawService.isConfigured(userId) ? `OpenClaw is connected. If the user asks about files on their computer, running shell commands, or anything OS-level, use openclaw_run. Only use it when the user explicitly asks about their local machine — don't use it proactively.` : 'OpenClaw is not connected. If the user asks about local files or running commands on their machine, let them know they can connect OpenClaw in the integrations panel.'}

RULES:
- Only use tools you have. If you can't do something, say so — don't suggest connecting other services.
- Never mention tool names, APIs, or technical details to the user.
- Never show raw URLs, event IDs, item IDs, or technical identifiers from tool results. Summarize the outcome in plain language instead (e.g., "Added to your Google Calendar" not the full event URL).
- Be proactive: if the user asks about email/calendar/GitHub, fetch it yourself instead of asking them.
- Use update_user_profile to remember stable facts about the user (school, projects, preferences).
- Look things up before asking. Only ask when you genuinely can't find the answer.
- For dates/deadlines, use the current date above to filter for future items only.`;
  }

  /**
   * Get or create a Composio session for a user
   */
  async getOrCreateSession(userId: string): Promise<ComposioSessionData | null> {
    const composio = this.getComposio();
    if (!composio) return null;

    // Check for existing session
    const existingSession = this.sessions.get(userId);
    if (existingSession) {
      // Refresh if older than 1 hour
      const ageMs = Date.now() - existingSession.createdAt.getTime();
      if (ageMs < 60 * 60 * 1000) {
        return existingSession;
      }
    }

    try {
      // Build auth configs from environment
      const authConfigs = this.buildAuthConfigs();

      // Create Tool Router session for the user
      const session = await composio.create(userId, { authConfigs });

      // Get tools in native OpenAI Agents format (no conversion needed)
      const composioTools = await session.tools();

      // Add custom tools: automations, artifacts, user profile, openclaw
      const automationTools = createAutomationTools(userId);
      const artifactTools = createArtifactTools(userId);
      const userProfileTools = createUserProfileTools(userId);
      const openclawTools = createOpenClawTools(userId);
      const tools = [...composioTools, ...automationTools, ...artifactTools, ...userProfileTools, ...openclawTools] as AgentTools;

      const sessionData: ComposioSessionData = {
        tools,
        userId,
        createdAt: new Date(),
      };

      this.sessions.set(userId, sessionData);
      return sessionData;
    } catch (error) {
      console.error('Failed to create Composio session:', error);
      return null;
    }
  }

  /**
   * Chat with tool calling capabilities
   */
  async chat(
    userId: string,
    message: string,
    conversationHistory: ToolRouterMessage[],
    artifactsContext?: string
  ): Promise<ToolRouterChatResponse> {
    const sessionData = await this.getOrCreateSession(userId);

    if (!sessionData) {
      return {
        message:
          'Composio service not configured. Please set COMPOSIO_API_KEY and OPENAI_API_KEY, and ensure your services are connected.',
        sessionId: userId,
      };
    }

    try {
      // Build conversation context from history, including tool results
      const contextMessages = conversationHistory
        .filter((m) => m.role !== 'tool')
        .map((m) => {
          const role = m.role === 'user' ? 'User' : 'Assistant';
          let messageContent = `${role}: ${m.content}`;

          // Include tool call results in the context so AI remembers what it did
          if (m.toolCalls && m.toolCalls.length > 0) {
            const toolResults = m.toolCalls
              .filter((tc) => tc.success && tc.result)
              .map((tc) => {
                // Format tool result - handle both string and object results
                const resultStr = typeof tc.result === 'string'
                  ? tc.result
                  : JSON.stringify(tc.result, null, 2);
                return `[Tool: ${tc.toolName}]\nResult: ${resultStr}`;
              })
              .join('\n\n');

            if (toolResults) {
              messageContent += `\n\nTool execution results:\n${toolResults}`;
            }
          }

          return messageContent;
        })
        .join('\n\n');

      // Load user profile context
      let profileContext = '';
      try {
        profileContext = await getUserProfileContext(userId);
      } catch (error) {
        console.error('Error loading user profile:', error);
      }

      // Build full input with all context
      let fullInput = '';

      if (profileContext) {
        fullInput += `${profileContext}\n\n`;
      }

      if (artifactsContext) {
        fullInput += `Relevant information from previous conversations (artifacts):\n${artifactsContext}\n\n`;
      }

      if (contextMessages) {
        fullInput += `Previous conversation:\n${contextMessages}\n\n`;
      }

      fullInput += `User: ${message}`;

      // Get current date/time for context
      const now = new Date();
      const currentDateTime = now.toLocaleString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      });

      // Create agent with Composio tools
      const agent = new Agent({
        name: 'Personal Assistant',
        instructions: this.buildSystemPrompt(currentDateTime, userId),
        model: 'gpt-5.2',
        tools: sessionData.tools,
      });

      // Run the agent with the user's message
      const result = await run(agent, fullInput, { maxTurns: 15 });

      // Extract tool calls from the run result if available
      const toolCalls: ToolCallResult[] = [];

      // The result.newItems contains all the items from this run
      if (result.newItems && Array.isArray(result.newItems)) {
        for (const item of result.newItems) {
          // Check for tool call output items
          if (item.type === 'tool_call_output_item') {
            const toolItem = item as {
              type: string;
              output?: string;
              rawItem?: { name?: string; call_id?: string };
            };
            toolCalls.push({
              id: toolItem.rawItem?.call_id || `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
              toolName: toolItem.rawItem?.name || 'unknown',
              toolkit: (toolItem.rawItem?.name || '').split('_')[0]?.toLowerCase() || 'unknown',
              success: true,
              result: toolItem.output,
              timestamp: new Date().toISOString(),
            });
          }
        }
      }

      return {
        message: result.finalOutput || '',
        toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
        sessionId: userId,
      };
    } catch (error) {
      console.error('Tool router chat error:', error);

      // Handle max turns exceeded error
      const errorMessage = error instanceof Error ? error.message : '';
      if (errorMessage.includes('Max turns') && errorMessage.includes('exceeded')) {
        return {
          message:
            'This task required too many steps to complete. Try breaking it into smaller requests, or be more specific about what you need.',
          sessionId: userId,
        };
      }

      return {
        message:
          'An error occurred while processing your request. Please try again.',
        sessionId: userId,
      };
    }
  }

  /**
   * Chat with tool calling capabilities (streaming)
   */
  async chatStream(
    userId: string,
    message: string,
    conversationHistory: ToolRouterMessage[],
    artifactsContext?: string
  ) {
    const sessionData = await this.getOrCreateSession(userId);

    if (!sessionData) {
      // Return an async generator that yields an error
      return async function* () {
        yield {
          type: 'error',
          data: {
            message: 'Composio service not configured. Please set COMPOSIO_API_KEY and OPENAI_API_KEY, and ensure your services are connected.'
          }
        };
      }();
    }

    try {
      // Build conversation context from history, including tool results
      const contextMessages = conversationHistory
        .filter((m) => m.role !== 'tool')
        .map((m) => {
          const role = m.role === 'user' ? 'User' : 'Assistant';
          let messageContent = `${role}: ${m.content}`;

          // Include tool call results in the context so AI remembers what it did
          if (m.toolCalls && m.toolCalls.length > 0) {
            const toolResults = m.toolCalls
              .filter((tc) => tc.success && tc.result)
              .map((tc) => {
                // Format tool result - handle both string and object results
                const resultStr = typeof tc.result === 'string'
                  ? tc.result
                  : JSON.stringify(tc.result, null, 2);
                return `[Tool: ${tc.toolName}]\nResult: ${resultStr}`;
              })
              .join('\n\n');

            if (toolResults) {
              messageContent += `\n\nTool execution results:\n${toolResults}`;
            }
          }

          return messageContent;
        })
        .join('\n\n');

      // Load user profile context
      let profileContext = '';
      try {
        profileContext = await getUserProfileContext(userId);
      } catch (error) {
        console.error('Error loading user profile:', error);
      }

      // Build full input with all context
      let fullInput = '';

      if (profileContext) {
        fullInput += `${profileContext}\n\n`;
      }

      if (artifactsContext) {
        fullInput += `Relevant information from previous conversations (artifacts):\n${artifactsContext}\n\n`;
      }

      if (contextMessages) {
        fullInput += `Previous conversation:\n${contextMessages}\n\n`;
      }

      fullInput += `User: ${message}`;

      // Get current date/time for context
      const now = new Date();
      const currentDateTime = now.toLocaleString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      });

      // Create agent with Composio tools
      const agent = new Agent({
        name: 'Personal Assistant',
        instructions: this.buildSystemPrompt(currentDateTime, userId),
        model: 'gpt-5.2',
        tools: sessionData.tools,
      });

      // Run the agent with streaming enabled
      const streamResult = await run(agent, fullInput, { stream: true, maxTurns: 15 });
      
      return streamResult;
    } catch (error) {
      console.error('Tool router chat stream error:', error);
      
      // Return an async generator that yields an error
      return async function* () {
        yield {
          type: 'error',
          data: {
            message: error instanceof Error ? error.message : 'An error occurred while processing your request. Please try again.'
          }
        };
      }();
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

  /**
   * Clear a specific user's session (useful for resetting conversation)
   */
  clearSession(userId: string): void {
    this.sessions.delete(userId);
  }
}

// Export singleton instance
export const toolRouterService = new ToolRouterService();
