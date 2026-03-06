/**
 * Composio Trigger Types API Route
 *
 * GET /api/composio/triggers/types - List available trigger types
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { composioService } from '@/lib/composio/composio-service';

/**
 * GET - List available trigger types for toolkits
 */
export async function GET(request: NextRequest) {
  try {
    const userId = DEV_USER.id;

    if (!process.env.COMPOSIO_API_KEY) {
      return NextResponse.json({
        triggerTypes: [],
        total: 0,
        message: 'COMPOSIO_API_KEY is not configured',
      });
    }

    // Get query params
    const searchParams = request.nextUrl.searchParams;
    const toolkitsParam = searchParams.get('toolkits');
    const toolkitSlugs = toolkitsParam
      ? toolkitsParam.split(',').map((t) => t.trim().toLowerCase())
      : undefined;

    const triggerTypes =
      await composioService.getAvailableTriggerTypes(toolkitSlugs);

    return NextResponse.json({
      triggerTypes,
      total: triggerTypes.length,
    });
  } catch (error) {
    console.error('Get trigger types error:', error);
    return NextResponse.json(
      { error: 'Failed to get trigger types' },
      { status: 500 }
    );
  }
}
