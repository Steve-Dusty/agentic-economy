/**
 * GET /api/ai-assistant/context
 *
 * Returns the full context for the AI assistant including:
 * - All bubbles from the registry
 * - User's connected Composio accounts and their tools
 * - Available toolkits
 *
 * Includes caching to prevent repeated Composio API calls
 */

import { NextResponse } from 'next/server';
import { getBubbleRegistryForAI } from '@workflow-editor/core';
import { DEV_USER } from '@/lib/dev-user';
import { composioService } from '@/lib/composio/composio-service';
import type { AIAssistantContext, ConnectedAccountInfo, ComposioToolSummary, ParameterSummary } from '@/lib/ai-assistant/types';

// Simple in-memory cache for context data
const contextCache = new Map<string, { data: AIAssistantContext; timestamp: number }>();
const CACHE_TTL_MS = 60 * 1000; // 1 minute cache TTL

function getCachedContext(userId: string): AIAssistantContext | null {
  const cached = contextCache.get(userId);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return cached.data;
  }
  // Clean up expired entry
  if (cached) {
    contextCache.delete(userId);
  }
  return null;
}

function setCachedContext(userId: string, data: AIAssistantContext): void {
  // Limit cache size to prevent memory issues
  if (contextCache.size > 100) {
    // Remove oldest entries
    const entries = Array.from(contextCache.entries());
    entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
    for (let i = 0; i < 20; i++) {
      contextCache.delete(entries[i][0]);
    }
  }
  contextCache.set(userId, { data, timestamp: Date.now() });
}

/**
 * GET handler - fetch AI assistant context
 * Use ?refresh=true to bypass cache
 */
export async function GET(request: Request) {
  try {
    const userId = DEV_USER.id;

    // Check for cache bypass
    const url = new URL(request.url);
    const refresh = url.searchParams.get('refresh') === 'true';

    // Check cache first (unless refresh requested)
    if (!refresh) {
      const cachedContext = getCachedContext(userId);
      if (cachedContext) {
        return NextResponse.json(cachedContext);
      }
    } else {
      // Clear cache for this user
      contextCache.delete(userId);
    }

    // Get bubble registry (static data)
    const bubbleRegistry = getBubbleRegistryForAI();

    // Get user's connected accounts from Composio
    const connectedAccounts = await composioService.getUserConnectedAccounts(userId);

    // Debug logging
    console.log('[Context API] Connected accounts:', connectedAccounts.map(acc => ({
      app: acc.appName || acc.appUniqueId,
      status: acc.status,
    })));

    // Build connected account info with tools - fetch all in parallel
    const activeAccounts = connectedAccounts.filter(acc => acc.status === 'ACTIVE');
    const inactiveAccounts = connectedAccounts.filter(acc => acc.status !== 'ACTIVE');

    console.log(`[Context API] Active: ${activeAccounts.length}, Inactive: ${inactiveAccounts.length}`);

    // Prepare inactive accounts (no API calls needed)
    const inactiveAccountsInfo: ConnectedAccountInfo[] = inactiveAccounts.map(account => ({
      toolkit: (account.appName || account.appUniqueId || 'unknown').toUpperCase(),
      status: account.status,
      tools: [],
    }));

    // Fetch tools for all active accounts in parallel
    const activeAccountsPromises = activeAccounts.map(async (account) => {
      const toolkitName = (account.appName || account.appUniqueId || 'unknown').toUpperCase();

      try {
        // Get tools for this toolkit
        const tools = await composioService.getUserTools(userId, [toolkitName]);

        const toolSummaries: ComposioToolSummary[] = tools.map((tool) => {
          // Parse input schema if available
          const parameters: ParameterSummary[] = [];

          if (tool.inputSchema && typeof tool.inputSchema === 'object') {
            const schema = tool.inputSchema as {
              properties?: Record<string, { type?: string; description?: string; enum?: string[] }>;
              required?: string[];
            };

            if (schema.properties) {
              const required = new Set(schema.required || []);
              for (const [name, prop] of Object.entries(schema.properties)) {
                parameters.push({
                  name,
                  type: prop.type || 'string',
                  required: required.has(name),
                  description: prop.description,
                  enumValues: prop.enum,
                });
              }
            }
          }

          return {
            name: tool.name,
            description: tool.description || '',
            parameters,
          };
        });

        return {
          toolkit: toolkitName,
          status: account.status,
          tools: toolSummaries,
        } as ConnectedAccountInfo;
      } catch (error) {
        console.error(`Failed to get tools for ${toolkitName}:`, error);
        return {
          toolkit: toolkitName,
          status: account.status,
          tools: [],
        } as ConnectedAccountInfo;
      }
    });

    // Wait for all parallel requests to complete
    const activeAccountsInfo = await Promise.all(activeAccountsPromises);
    const connectedAccountsWithTools = [...inactiveAccountsInfo, ...activeAccountsInfo];

    // Get list of available toolkits
    const availableApps = composioService.getAvailableApps();
    const availableToolkits = availableApps.map((app) => app.appId);

    // Build the context response
    const context: AIAssistantContext = {
      bubbles: {
        services: bubbleRegistry.services.map((b) => ({
          name: b.name,
          className: b.className,
          type: b.type,
          description: b.description,
          icon: b.icon,
          color: b.color,
          parameters: b.parameters,
          authType: b.authType,
        })),
        tools: bubbleRegistry.tools.map((b) => ({
          name: b.name,
          className: b.className,
          type: b.type,
          description: b.description,
          icon: b.icon,
          color: b.color,
          parameters: b.parameters,
          authType: b.authType,
        })),
        workflows: bubbleRegistry.workflows.map((b) => ({
          name: b.name,
          className: b.className,
          type: b.type,
          description: b.description,
          icon: b.icon,
          color: b.color,
          parameters: b.parameters,
          authType: b.authType,
        })),
      },
      composio: {
        connectedAccounts: connectedAccountsWithTools,
        availableToolkits,
      },
    };

    // Cache the context
    setCachedContext(userId, context);

    return NextResponse.json(context);
  } catch (error) {
    console.error('Error fetching AI assistant context:', error);
    return NextResponse.json(
      { error: 'Failed to fetch context' },
      { status: 500 }
    );
  }
}
