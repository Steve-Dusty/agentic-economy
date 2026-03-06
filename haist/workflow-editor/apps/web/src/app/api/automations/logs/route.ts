/**
 * Execution Logs API Route
 *
 * GET /api/automations/logs - List execution logs for the authenticated user
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { executionLogStorage } from '@/lib/execution-rules/execution-log-storage';

export async function GET(request: NextRequest) {
  try {
    const userId = DEV_USER.id;

    const { searchParams } = new URL(request.url);
    const ruleId = searchParams.get('ruleId');
    const limit = parseInt(searchParams.get('limit') || '50', 10);
    const offset = parseInt(searchParams.get('offset') || '0', 10);

    const { logs, total } = ruleId
      ? await executionLogStorage.getByRuleId(ruleId, limit, offset)
      : await executionLogStorage.getByUserId(userId, limit, offset);

    const stats = ruleId
      ? await executionLogStorage.getStatsByRuleId(ruleId)
      : await executionLogStorage.getStats(userId);

    return NextResponse.json({ logs, total, stats });
  } catch (error) {
    console.error('[API] Error fetching execution logs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch execution logs' },
      { status: 500 }
    );
  }
}
