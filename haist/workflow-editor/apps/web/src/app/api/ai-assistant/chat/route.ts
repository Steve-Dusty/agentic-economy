/**
 * POST /api/ai-assistant/chat
 *
 * Chat endpoint for the AI workflow assistant.
 * Receives user messages and returns AI responses with optional workflow generation.
 */

import { NextRequest, NextResponse } from 'next/server';
import { getBubbleRegistryForAI } from '@workflow-editor/core';
import { DEV_USER } from '@/lib/dev-user';
import { composioService } from '@/lib/composio/composio-service';
import { workflowAIService } from '@/lib/ai-assistant/workflow-ai-service';
import { findArtifactsForMessage, formatArtifactsForContext } from '@/lib/artifacts/smart-artifact-matcher';
import type { ChatRequestWithArtifacts, AIAssistantContext, ConnectedAccountInfo, ComposioToolSummary, ParameterSummary } from '@/lib/ai-assistant/types';

/**
 * POST handler - chat with AI assistant
 */
export async function POST(request: NextRequest) {
  try {
    const userId = DEV_USER.id;
    const body = (await request.json()) as ChatRequestWithArtifacts;

    // Validate and sanitize input
    if (!body.message || typeof body.message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Sanitize message content - remove potential script tags and limit length
    const sanitizedMessage = body.message
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '') // Remove script tags
      .replace(/<[^>]*>/g, '') // Remove other HTML tags
      .trim();
    
    if (sanitizedMessage.length === 0) {
      return NextResponse.json(
        { error: 'Message cannot be empty after sanitization' },
        { status: 400 }
      );
    }

    if (sanitizedMessage.length > 10000) {
      return NextResponse.json(
        { error: 'Message too long (max 10,000 characters)' },
        { status: 400 }
      );
    }

    // Validate conversation history if provided
    if (body.conversationHistory && Array.isArray(body.conversationHistory)) {
      for (const msg of body.conversationHistory) {
        if (msg && typeof msg.content === 'string' && msg.content.length > 50000) {
          return NextResponse.json(
            { error: 'Conversation history contains messages that are too long' },
            { status: 400 }
          );
        }
      }
    }

    // Update body with sanitized message
    body.message = sanitizedMessage;

    // Build the context
    const context = await buildContext(userId);

    // Smart artifact matching with high precision
    let artifactsContext = '';
    const enableAutoArtifacts = body.enableAutoArtifacts !== false; // Default to true
    const manualArtifactIds = body.manualArtifactIds || [];

    if (enableAutoArtifacts || manualArtifactIds.length > 0) {
      try {
        const artifacts = await findArtifactsForMessage({
          userId,
          message: body.message,
          conversationHistory: body.conversationHistory,
          manualArtifactIds,
          maxArtifacts: 2,
          minConfidence: 0.85, // Very high threshold - only inject if strong match
        });

        if (artifacts.length > 0) {
          artifactsContext = formatArtifactsForContext(artifacts);
          console.log(`[chat] Injected ${artifacts.length} artifact(s) into context`);
        }
      } catch (error) {
        console.error('Error fetching artifacts for context:', error);
        // Continue without artifacts on error
      }
    }

    // Call the AI service with artifact context
    const response = await workflowAIService.chat(
      body.message,
      body.conversationHistory || [],
      context,
      artifactsContext || undefined
    );

    return NextResponse.json({ response });
  } catch (error) {
    console.error('Error in AI chat endpoint:', error);
    return NextResponse.json(
      { error: 'Failed to process chat message' },
      { status: 500 }
    );
  }
}

/**
 * Build the context for the AI assistant
 */
async function buildContext(userId: string): Promise<AIAssistantContext> {
  // Get bubble registry
  const bubbleRegistry = getBubbleRegistryForAI();

  // Get user's connected accounts
  const connectedAccounts = await composioService.getUserConnectedAccounts(userId);

  // Build connected account info with tools
  const connectedAccountsWithTools: ConnectedAccountInfo[] = [];

  for (const account of connectedAccounts) {
    if (account.status !== 'ACTIVE') {
      connectedAccountsWithTools.push({
        toolkit: account.appName || 'unknown',
        status: account.status,
        tools: [],
      });
      continue;
    }

    try {
      const toolkit = (account.appName || account.appUniqueId || '').toUpperCase();
      const tools = await composioService.getUserTools(userId, [toolkit]);

      const toolSummaries: ComposioToolSummary[] = tools.map((tool) => {
        const parameters: ParameterSummary[] = [];

        if (tool.inputSchema && typeof tool.inputSchema === 'object') {
          const schema = tool.inputSchema as {
            properties?: Record<string, { type?: string; description?: string; enum?: string[]; default?: unknown }>;
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
                default: prop.default,
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

      connectedAccountsWithTools.push({
        toolkit: account.appName || toolkit,
        status: account.status,
        tools: toolSummaries,
      });
    } catch (error) {
      console.error(`Failed to get tools for ${account.appName}:`, error);
      connectedAccountsWithTools.push({
        toolkit: account.appName || 'unknown',
        status: account.status,
        tools: [],
      });
    }
  }

  // Get available toolkits
  const availableApps = composioService.getAvailableApps();
  const availableToolkits = availableApps.map((app) => app.appId);

  return {
    userId,
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
}
