/**
 * API routes for individual conversation operations
 *
 * GET /api/ai-assistant/conversations/[id] - Get a specific conversation
 * PATCH /api/ai-assistant/conversations/[id] - Update conversation (rename, mode change)
 * DELETE /api/ai-assistant/conversations/[id] - Delete a conversation
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { conversationsStorage } from '@/lib/ai-assistant/conversation-storage';
import type { AssistantMode } from '@/lib/ai-assistant/types';

interface RouteParams {
  params: Promise<{ id: string }>;
}

/**
 * GET - Get a specific conversation
 */
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    const { id } = await params;
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

    return NextResponse.json({ conversation });
  } catch (error) {
    console.error('Error fetching conversation:', error);
    return NextResponse.json(
      { error: 'Failed to fetch conversation' },
      { status: 500 }
    );
  }
}

/**
 * PATCH - Update conversation (rename or mode change)
 */
export async function PATCH(request: NextRequest, { params }: RouteParams) {
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

    // Update title if provided
    if (body.title && typeof body.title === 'string') {
      await conversationsStorage.rename(id, body.title);
    }

    // Update mode if provided (only tool-router is supported)
    if (body.mode) {
      const mode: AssistantMode = 'tool-router';
      await conversationsStorage.updateMode(id, mode);
    }

    // Return updated conversation
    const updated = await conversationsStorage.get(id);
    return NextResponse.json({ conversation: updated });
  } catch (error) {
    console.error('Error updating conversation:', error);
    return NextResponse.json(
      { error: 'Failed to update conversation' },
      { status: 500 }
    );
  }
}

/**
 * DELETE - Delete a conversation
 */
export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    const { id } = await params;

    const ownerId = await conversationsStorage.getUserId(id);
    if (!ownerId || ownerId !== userId) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const deleted = await conversationsStorage.delete(id);

    if (!deleted) {
      return NextResponse.json(
        { error: 'Conversation not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting conversation:', error);
    return NextResponse.json(
      { error: 'Failed to delete conversation' },
      { status: 500 }
    );
  }
}
