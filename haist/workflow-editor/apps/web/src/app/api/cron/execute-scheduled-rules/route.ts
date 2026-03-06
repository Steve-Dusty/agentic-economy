/**
 * Cron Endpoint for Scheduled Rule Execution
 *
 * GET /api/cron/execute-scheduled-rules - Execute all scheduled rules that are due
 *
 * This endpoint should be called by an external cron service (e.g., Vercel Cron, GitHub Actions)
 * every 5 minutes to process scheduled rules.
 *
 * Security: This endpoint can optionally be protected with a CRON_SECRET environment variable.
 * If CRON_SECRET is set, the request must include an Authorization header with the value
 * "Bearer <CRON_SECRET>".
 */

import { NextRequest, NextResponse } from 'next/server';
import { triggerProcessingService } from '@/lib/execution-rules/trigger-processing-service';

/**
 * GET /api/cron/execute-scheduled-rules - Execute scheduled rules
 */
export async function GET(request: NextRequest) {
  try {
    // Verify cron secret (required)
    const cronSecret = process.env.CRON_SECRET;
    if (!cronSecret) {
      console.error('[Cron] CRON_SECRET is not configured');
      return NextResponse.json(
        { error: 'Cron not configured' },
        { status: 503 }
      );
    }

    const authHeader = request.headers.get('authorization');
    const providedSecret = authHeader?.replace('Bearer ', '');
    if (providedSecret !== cronSecret) {
      console.warn('[Cron] Unauthorized cron request - invalid or missing secret');
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    console.log('[Cron] Starting scheduled rules execution');
    const startTime = Date.now();

    // Process all due scheduled rules
    const result = await triggerProcessingService.processScheduled();

    const duration = Date.now() - startTime;
    console.log(
      `[Cron] Scheduled rules execution complete in ${duration}ms: ` +
      `${result.rulesSucceeded}/${result.rulesProcessed} succeeded`
    );

    return NextResponse.json({
      success: true,
      result: {
        rulesProcessed: result.rulesProcessed,
        rulesSucceeded: result.rulesSucceeded,
        rulesFailed: result.rulesFailed,
        errors: result.errors,
        durationMs: duration,
      },
    });
  } catch (error) {
    console.error('[Cron] Error executing scheduled rules:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to execute scheduled rules',
      },
      { status: 500 }
    );
  }
}

// Vercel Cron configuration
export const maxDuration = 60; // Allow up to 60 seconds for this route
