/**
 * POST /api/ai-assistant/tool-router
 *
 * Chat endpoint for the Tool Router feature.
 * Receives user messages and returns AI responses with tool execution capabilities.
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { toolRouterService } from '@/lib/ai-assistant/tool-router-service';
import { findArtifactsWithConfidence, formatArtifactsForContext } from '@/lib/artifacts/smart-artifact-matcher';
import type { ToolRouterChatRequest, InjectedArtifactInfo } from '@/lib/ai-assistant/types';

/**
 * POST handler - chat with tool router
 */
export async function POST(request: NextRequest) {
  try {
    const userId = DEV_USER.id;
    const body = (await request.json()) as ToolRouterChatRequest;

    if (!body.message || typeof body.message !== 'string') {
      return NextResponse.json({ error: 'Message is required' }, { status: 400 });
    }

    // Fetch relevant artifacts for context
    let artifactsContext = '';
    let injectedArtifacts: InjectedArtifactInfo[] = [];
    try {
      const matchedArtifacts = await findArtifactsWithConfidence({
        userId,
        message: body.message,
        maxArtifacts: 3,
        minConfidence: 0.6,
      });

      if (matchedArtifacts.length > 0) {
        artifactsContext = formatArtifactsForContext(matchedArtifacts.map((m) => m.artifact));
        injectedArtifacts = matchedArtifacts.map((m) => ({
          id: m.artifact.id,
          title: m.artifact.title,
          confidence: m.confidence > 0.85 ? 'high' as const : 'possible' as const,
        }));
        console.log(`[tool-router] Injected ${matchedArtifacts.length} artifact(s) into context`);
      }
    } catch (error) {
      console.error('Error fetching artifacts for tool-router:', error);
    }

    const response = await toolRouterService.chat(
      userId,
      body.message,
      body.conversationHistory || [],
      artifactsContext || undefined
    );

    // Attach injected artifacts info to response
    if (injectedArtifacts.length > 0) {
      response.injectedArtifacts = injectedArtifacts;
    }

    return NextResponse.json({ response });
  } catch (error) {
    console.error('Error in tool router endpoint:', error);
    return NextResponse.json(
      { error: 'Failed to process message' },
      { status: 500 }
    );
  }
}
