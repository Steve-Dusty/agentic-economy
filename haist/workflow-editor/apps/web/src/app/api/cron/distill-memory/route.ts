/**
 * Cron Endpoint for Memory Distillation
 *
 * GET /api/cron/distill-memory - Review daily artifacts and distill insights into soul artifact
 *
 * Should be called once daily (e.g., 2 AM) by an external cron service.
 * Protected by CRON_SECRET.
 */

import { NextRequest, NextResponse } from 'next/server';
import { distillAllUsers } from '@/lib/memory/distillation-service';

export async function GET(request: NextRequest) {
  try {
    // Verify cron secret
    const cronSecret = process.env.CRON_SECRET;
    if (!cronSecret) {
      console.error('[Cron/Distill] CRON_SECRET is not configured');
      return NextResponse.json(
        { error: 'Cron not configured' },
        { status: 503 }
      );
    }

    const authHeader = request.headers.get('authorization');
    if (authHeader !== `Bearer ${cronSecret}`) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    console.log('[Cron/Distill] Starting memory distillation...');
    const result = await distillAllUsers();
    console.log(
      `[Cron/Distill] Done. Users: ${result.usersProcessed}, Insights: ${result.totalInsights}, Errors: ${result.errors.length}`
    );

    return NextResponse.json({
      success: true,
      ...result,
    });
  } catch (error) {
    console.error('[Cron/Distill] Error:', error);
    return NextResponse.json(
      { error: 'Internal error' },
      { status: 500 }
    );
  }
}
