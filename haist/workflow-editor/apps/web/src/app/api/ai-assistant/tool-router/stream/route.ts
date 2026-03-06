/**
 * POST /api/ai-assistant/tool-router/stream
 *
 * SSE streaming endpoint for the Tool Router feature.
 * Receives user messages and returns AI responses with tool execution capabilities via Server-Sent Events.
 */

import { NextRequest } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { toolRouterService } from '@/lib/ai-assistant/tool-router-service';
import { findArtifactsWithConfidence, formatArtifactsForContext } from '@/lib/artifacts/smart-artifact-matcher';
import type { ToolRouterChatRequest, InjectedArtifactInfo, ToolCallResult } from '@/lib/ai-assistant/types';

/**
 * POST handler - streaming chat with tool router
 */
export async function POST(request: NextRequest) {
  try {
    const userId = DEV_USER.id;
    const body = (await request.json()) as ToolRouterChatRequest;

    if (!body.message || typeof body.message !== 'string') {
      return new Response(
        `event: error\ndata: ${JSON.stringify({ message: 'Message is required' })}\n\n`,
        {
          status: 400,
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
          },
        }
      );
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
        console.log(`[tool-router-stream] Injected ${matchedArtifacts.length} artifact(s) into context`);
      }
    } catch (error) {
      console.error('Error fetching artifacts for tool-router stream:', error);
    }

    // Get the streaming result from the service
    const streamResult = await toolRouterService.chatStream(
      userId,
      body.message,
      body.conversationHistory || [],
      artifactsContext || undefined
    );

    // Create ReadableStream for SSE
    const stream = new ReadableStream({
      async start(controller) {
        const encoder = new TextEncoder();
        
        // Track tool calls for final summary
        const toolCalls: ToolCallResult[] = [];
        const toolCallsMap = new Map<string, ToolCallResult>();
        
        try {
          for await (const event of streamResult) {
            // Handle different types of stream events
            if (event.type === 'raw_model_stream_event') {
              // Text streaming from the model
              const modelEvent = event as any;
              if (modelEvent.data?.type === 'output_text_delta') {
                const delta = modelEvent.data.delta;
                if (delta && typeof delta === 'string') {
                  const sseEvent = `event: text\ndata: ${JSON.stringify({ chunk: delta })}\n\n`;
                  controller.enqueue(encoder.encode(sseEvent));
                }
              }
            } else if (event.type === 'run_item_stream_event') {
              // Tool call events
              const itemEvent = event as any;
              
              if (itemEvent.name === 'tool_called') {
                // Tool call started
                const toolItem = itemEvent.item;
                const rawItem = toolItem?.rawItem || toolItem;
                const toolName = rawItem?.name || rawItem?.call?.function?.name || 'unknown';
                const toolkit = toolName.split('_')[0]?.toLowerCase() || 'unknown';
                const callId = rawItem?.call_id || rawItem?.id || `tool_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
                
                const toolCall: ToolCallResult = {
                  id: callId,
                  toolName,
                  toolkit,
                  success: false,
                  timestamp: new Date().toISOString(),
                };
                
                toolCallsMap.set(callId, toolCall);
                
                const sseEvent = `event: tool_call\ndata: ${JSON.stringify({ 
                  toolName, 
                  toolkit, 
                  id: callId 
                })}\n\n`;
                controller.enqueue(encoder.encode(sseEvent));
              } else if (itemEvent.name === 'tool_output') {
                // Tool call completed
                const toolItem = itemEvent.item;
                const rawItem = toolItem?.rawItem || toolItem;
                const callId = rawItem?.call_id;
                const output = rawItem?.output;
                
                if (callId && toolCallsMap.has(callId)) {
                  const toolCall = toolCallsMap.get(callId)!;
                  toolCall.success = true;
                  toolCall.result = output;
                  toolCalls.push(toolCall);
                  
                  const sseEvent = `event: tool_result\ndata: ${JSON.stringify({
                    toolName: toolCall.toolName,
                    toolkit: toolCall.toolkit,
                    id: callId,
                    success: true,
                    result: output
                  })}\n\n`;
                  controller.enqueue(encoder.encode(sseEvent));
                }
              }
            }
          }
          
          // Send final done event with summary
          const doneEvent = `event: done\ndata: ${JSON.stringify({
            toolCalls: toolCalls.length > 0 ? toolCalls : undefined,
            sessionId: userId,
            injectedArtifacts: injectedArtifacts.length > 0 ? injectedArtifacts : undefined,
          })}\n\n`;
          controller.enqueue(encoder.encode(doneEvent));
          
        } catch (error) {
          console.error('Streaming error:', error);
          const errorEvent = `event: error\ndata: ${JSON.stringify({ 
            message: error instanceof Error ? error.message : 'An error occurred during streaming' 
          })}\n\n`;
          controller.enqueue(encoder.encode(errorEvent));
        } finally {
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      },
    });

  } catch (error) {
    console.error('Error in tool router streaming endpoint:', error);
    return new Response(
      `event: error\ndata: ${JSON.stringify({ message: 'Failed to process message' })}\n\n`,
      {
        status: 500,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
        },
      }
    );
  }
}