/**
 * API route for adding messages to a conversation
 *
 * POST /api/ai-assistant/conversations/[id]/messages - Add a message to a conversation
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { conversationsStorage } from '@/lib/ai-assistant/conversation-storage';
import type { ChatMessage, ToolRouterMessage, AssistantMode } from '@/lib/ai-assistant/types';

interface RouteParams {
  params: Promise<{ id: string }>;
}

/**
 * POST - Add a message to a conversation
 */
export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    const { id } = await params;
    const body = await request.json();

    // Check conversation exists
    const conversation = await conversationsStorage.get(id);
    if (!conversation) {
      return NextResponse.json(
        { error: 'Conversation not found' },
        { status: 404 }
      );
    }

    const ownerId = await conversationsStorage.getUserId(id);
    if (ownerId !== userId) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    // Validate message
    if (!body.message || typeof body.message !== 'object') {
      return NextResponse.json(
        { error: 'Message object is required' },
        { status: 400 }
      );
    }

    const mode: AssistantMode = body.mode || conversation.mode;
    const message = body.message as ChatMessage | ToolRouterMessage;

    // Add message to conversation
    await conversationsStorage.addMessage(id, message, mode);

    // Return updated conversation
    const updated = await conversationsStorage.get(id);
    return NextResponse.json({ conversation: updated });
  } catch (error) {
    console.error('Error adding message:', error);
    return NextResponse.json(
      { error: 'Failed to add message' },
      { status: 500 }
    );
  }
}
