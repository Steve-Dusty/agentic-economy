/**
 * Composio Triggers API Route
 *
 * GET /api/composio/triggers - List user's active triggers
 * POST /api/composio/triggers - Create a new trigger
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { composioService } from '@/lib/composio/composio-service';

/**
 * GET - List user's active triggers
 */
export async function GET(request: NextRequest) {
  try {
    const userId = DEV_USER.id;

    if (!process.env.COMPOSIO_API_KEY) {
      return NextResponse.json({
        triggers: [],
        total: 0,
        message: 'COMPOSIO_API_KEY is not configured',
      });
    }

    // Get user's connected accounts first
    const connectedAccounts =
      await composioService.getUserConnectedAccounts(userId);
    const connectedAccountIds = connectedAccounts
      .filter((acc) => acc.status === 'ACTIVE')
      .map((acc) => acc.id);

    if (connectedAccountIds.length === 0) {
      return NextResponse.json({
        triggers: [],
        total: 0,
      });
    }

    // Get query params
    const searchParams = request.nextUrl.searchParams;
    const showDisabled = searchParams.get('showDisabled') === 'true';

    const triggers = await composioService.getUserTriggers(connectedAccountIds, {
      showDisabled,
    });

    return NextResponse.json({
      triggers,
      total: triggers.length,
    });
  } catch (error) {
    console.error('Get triggers error:', error);
    return NextResponse.json(
      { error: 'Failed to get triggers' },
      { status: 500 }
    );
  }
}

/**
 * POST - Create a new trigger
 */
export async function POST(request: NextRequest) {
  try {
    const userId = DEV_USER.id;

    if (!process.env.COMPOSIO_API_KEY) {
      return NextResponse.json(
        { error: 'COMPOSIO_API_KEY is not configured' },
        { status: 500 }
      );
    }
    const body = await request.json();

    const { triggerSlug, connectedAccountId, triggerConfig } = body;

    if (!triggerSlug) {
      return NextResponse.json(
        { error: 'triggerSlug is required' },
        { status: 400 }
      );
    }

    const result = await composioService.createTrigger(
      userId,
      triggerSlug,
      connectedAccountId,
      triggerConfig
    );

    return NextResponse.json({
      success: true,
      triggerId: result.triggerId,
    });
  } catch (error) {
    console.error('Create trigger error:', error);
    return NextResponse.json(
      {
        error:
          error instanceof Error ? error.message : 'Failed to create trigger',
      },
      { status: 500 }
    );
  }
}
