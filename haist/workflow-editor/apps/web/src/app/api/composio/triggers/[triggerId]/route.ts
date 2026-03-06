/**
 * Composio Trigger by ID API Route
 *
 * DELETE /api/composio/triggers/[triggerId] - Delete a trigger
 * PUT /api/composio/triggers/[triggerId] - Enable/disable a trigger
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { composioService } from '@/lib/composio/composio-service';

type RouteParams = {
  params: Promise<{ triggerId: string }>;
};

/**
 * Verifies that the trigger belongs to the authenticated user
 */
async function verifyTriggerOwnership(triggerId: string, userId: string): Promise<boolean> {
  try {
    // Get all user triggers and check if the triggerId exists for this user
    const userTriggers = await composioService.getUserTriggers();
    return userTriggers.some(trigger => 
      trigger.id === triggerId || trigger.uuid === triggerId
    );
  } catch (error) {
    console.error('Error verifying trigger ownership:', error);
    return false;
  }
}

/**
 * DELETE - Delete a trigger
 */
export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    if (!process.env.COMPOSIO_API_KEY) {
      return NextResponse.json(
        { error: 'COMPOSIO_API_KEY is not configured' },
        { status: 500 }
      );
    }

    const { triggerId } = await params;

    if (!triggerId) {
      return NextResponse.json(
        { error: 'triggerId is required' },
        { status: 400 }
      );
    }

    // Verify trigger ownership
    const isOwner = await verifyTriggerOwnership(triggerId, userId);
    if (!isOwner) {
      return NextResponse.json(
        { error: 'Trigger not found or access denied' },
        { status: 403 }
      );
    }

    const result = await composioService.deleteTrigger(triggerId);

    return NextResponse.json({
      success: true,
      triggerId: result.triggerId,
    });
  } catch (error) {
    console.error('Delete trigger error:', error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : 'Failed to delete trigger',
      },
      { status: 500 }
    );
  }
}

/**
 * PUT - Enable or disable a trigger
 */
export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    if (!process.env.COMPOSIO_API_KEY) {
      return NextResponse.json(
        { error: 'COMPOSIO_API_KEY is not configured' },
        { status: 500 }
      );
    }

    const { triggerId } = await params;

    if (!triggerId) {
      return NextResponse.json(
        { error: 'triggerId is required' },
        { status: 400 }
      );
    }

    // Verify trigger ownership
    const isOwner = await verifyTriggerOwnership(triggerId, userId);
    if (!isOwner) {
      return NextResponse.json(
        { error: 'Trigger not found or access denied' },
        { status: 403 }
      );
    }

    const body = await request.json();
    const { enabled } = body;

    if (typeof enabled !== 'boolean') {
      return NextResponse.json(
        { error: 'enabled field is required (boolean)' },
        { status: 400 }
      );
    }

    const result = enabled
      ? await composioService.enableTrigger(triggerId)
      : await composioService.disableTrigger(triggerId);

    return NextResponse.json({
      success: true,
      status: result.status,
    });
  } catch (error) {
    console.error('Update trigger error:', error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : 'Failed to update trigger',
      },
      { status: 500 }
    );
  }
}
