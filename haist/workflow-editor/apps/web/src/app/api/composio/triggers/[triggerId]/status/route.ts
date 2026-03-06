/**
 * Composio Trigger Status API Route
 *
 * PATCH /api/composio/triggers/[triggerId]/status - Enable/disable a trigger
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { composioService } from '@/lib/composio/composio-service';

type RouteParams = {
  params: Promise<{ triggerId: string }>;
};

/**
 * PATCH - Enable or disable a trigger
 */
export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    if (!process.env.COMPOSIO_API_KEY) {
      return NextResponse.json(
        { error: 'COMPOSIO_API_KEY is not configured' },
        { status: 500 }
      );
    }

    const { triggerId } = await params;
    const body = await request.json();
    const { status } = body;

    if (!triggerId) {
      return NextResponse.json(
        { error: 'triggerId is required' },
        { status: 400 }
      );
    }

    if (!status || !['enable', 'disable'].includes(status)) {
      return NextResponse.json(
        { error: 'status must be "enable" or "disable"' },
        { status: 400 }
      );
    }

    let result;
    if (status === 'enable') {
      result = await composioService.enableTrigger(triggerId);
    } else {
      result = await composioService.disableTrigger(triggerId);
    }

    return NextResponse.json({
      success: true,
      status: result.status,
    });
  } catch (error) {
    console.error('Update trigger status error:', error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : 'Failed to update trigger status',
      },
      { status: 500 }
    );
  }
}
