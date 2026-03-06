/**
 * GET /api/cron/summarize-inactive
 *
 * API endpoint to summarize inactive conversations and store
 * summaries in the artifact system.
 *
 * Can be triggered:
 * - Manually during development
 * - By a free external cron service (cron-job.org, EasyCron, GitHub Actions)
 * - On user activity (e.g., when returning to the app)
 */

import { NextRequest, NextResponse } from 'next/server';
import { summarizeInactiveConversations } from '@/lib/artifacts/conversation-summarizer';

export const runtime = 'nodejs';
export const maxDuration = 300; // 5 minutes max

/**
 * GET handler - can be called by external cron service or manually
 */
export async function GET(request: NextRequest) {
  // Verify cron secret (required)
  const cronSecret = process.env.CRON_SECRET;
  if (!cronSecret) {
    console.error('[cron] CRON_SECRET is not configured');
    return NextResponse.json({ error: 'Cron not configured' }, { status: 503 });
  }

  const authHeader = request.headers.get('authorization');
  if (authHeader !== `Bearer ${cronSecret}`) {
    console.warn('[cron] Unauthorized request to summarize-inactive');
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  console.log('[cron] Starting conversation summarization job');

  try {
    const results = await summarizeInactiveConversations();

    const summary = {
      success: true,
      processed: results.length,
      addedToExisting: results.filter((r) => r.action === 'added_to_existing').length,
      createdNew: results.filter((r) => r.action === 'created_new').length,
      skipped: results.filter((r) => r.action === 'skipped').length,
      results: results.map((r) => ({
        conversationId: r.conversationId,
        action: r.action,
        artifactId: r.artifactId,
        reason: r.reason,
      })),
    };

    console.log('[cron] Summarization job completed:', {
      processed: summary.processed,
      addedToExisting: summary.addedToExisting,
      createdNew: summary.createdNew,
      skipped: summary.skipped,
    });

    return NextResponse.json(summary);
  } catch (error) {
    console.error('[cron] Summarization job failed:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
