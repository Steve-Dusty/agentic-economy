/**
 * POST /api/execute
 *
 * Simple execution endpoint. Send a task, get a result.
 * Example: { "task": "send an email to bob@example.com saying hello" }
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { toolRouterService } from '@/lib/ai-assistant/tool-router-service';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const task = body.task;

    if (!task || typeof task !== 'string' || task.trim().length === 0) {
      return NextResponse.json(
        { error: 'Missing "task" field. Example: { "task": "search the web for AI news" }' },
        { status: 400 }
      );
    }

    if (task.length > 10000) {
      return NextResponse.json(
        { error: 'Task too long (max 10,000 characters)' },
        { status: 400 }
      );
    }

    const result = await toolRouterService.chat(
      DEV_USER.id,
      task.trim(),
      [] // no conversation history — single-shot execution
    );

    return NextResponse.json({
      result: result.message,
      toolCalls: result.toolCalls || [],
    });
  } catch (error) {
    console.error('Execute endpoint error:', error);
    return NextResponse.json(
      { error: 'Execution failed' },
      { status: 500 }
    );
  }
}
