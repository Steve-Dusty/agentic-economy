/**
 * Rule-specific Execution Logs API Route
 *
 * GET /api/automations/[id]/logs - List execution logs for a specific rule
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { executionRulesStorage } from '@/lib/execution-rules/storage';
import { executionLogStorage } from '@/lib/execution-rules/execution-log-storage';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const userId = DEV_USER.id;

    const { id } = await params;

    // Verify rule belongs to user
    const rule = await executionRulesStorage.getByIdAndUser(id, userId);
    if (!rule) {
      return NextResponse.json({ error: 'Rule not found' }, { status: 404 });
    }

    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '50', 10);
    const offset = parseInt(searchParams.get('offset') || '0', 10);

    const { logs, total } = await executionLogStorage.getByRuleId(id, limit, offset);
    const stats = await executionLogStorage.getStatsByRuleId(id);

    return NextResponse.json({ logs, total, stats });
  } catch (error) {
    console.error('[API] Error fetching rule execution logs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch execution logs' },
      { status: 500 }
    );
  }
}
