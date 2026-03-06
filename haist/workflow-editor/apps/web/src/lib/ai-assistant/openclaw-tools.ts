/**
 * OpenClaw Tools for the AI Assistant
 *
 * Custom tools that allow the AI to interact with the user's local machine
 * via the OpenClaw gateway.
 */

import { tool } from '@openai/agents';
import { openClawService } from '@/lib/openclaw/openclaw-service';

/**
 * Creates OpenClaw tools bound to a specific userId.
 */
export function createOpenClawTools(userId: string) {
  const openclawRun = tool({
    name: 'openclaw_run',
    description: `Execute a task on the user's local machine via OpenClaw. This gives you access to the user's filesystem, shell commands, web browsing, and more. Send a natural language instruction describing what you need done (e.g., "list all .ts files in ~/projects/myapp", "read the contents of ~/.zshrc", "count the number of lines in package.json"). The OpenClaw agent will figure out which internal tools to use (exec, read, write, browser, etc.) and return the result. Use this whenever the user asks about files, directories, running commands, or anything on their local machine.`,
    parameters: {
      type: 'object' as const,
      properties: {
        instruction: {
          type: 'string',
          description: 'Natural language instruction describing what to do on the local machine. Be specific and direct, e.g. "run `find /Users/kuant/blockd4 -name \'*.rs\' | wc -l`" or "read the file at /Users/kuant/blockd4/README.md"',
        },
      },
      required: ['instruction'],
      additionalProperties: true,
    },
    strict: false,
    execute: async (rawInput) => {
      try {
        const input = rawInput as { instruction: string };

        if (!openClawService.isConfigured(userId)) {
          return JSON.stringify({
            success: false,
            error: 'OpenClaw is not connected. Please connect OpenClaw in the integrations panel (enter your gateway URL and token).',
          });
        }

        const result = await openClawService.chatCompletion(userId, input.instruction);

        return JSON.stringify({
          success: true,
          result,
        });
      } catch (error) {
        return JSON.stringify({
          success: false,
          error: error instanceof Error ? error.message : 'Failed to execute OpenClaw instruction',
        });
      }
    },
  });

  const openclawStatus = tool({
    name: 'openclaw_status',
    description: `Check if the OpenClaw local machine gateway is connected and responsive. Use this to verify the connection before attempting local machine operations.`,
    parameters: {
      type: 'object' as const,
      properties: {},
      required: [],
      additionalProperties: true,
    },
    strict: false,
    execute: async () => {
      try {
        const config = openClawService.getConfig(userId);
        if (!config) {
          return JSON.stringify({
            connected: false,
            message: 'OpenClaw is not configured. The user needs to connect OpenClaw in the integrations panel.',
          });
        }

        const isAlive = await openClawService.testConnection(config.url, config.token);

        return JSON.stringify({
          connected: isAlive,
          url: config.url,
          message: isAlive
            ? 'OpenClaw gateway is connected and responsive.'
            : 'OpenClaw gateway is configured but not responding. The gateway may not be running.',
        });
      } catch (error) {
        return JSON.stringify({
          connected: false,
          error: error instanceof Error ? error.message : 'Failed to check OpenClaw status',
        });
      }
    },
  });

  return [openclawRun, openclawStatus];
}
