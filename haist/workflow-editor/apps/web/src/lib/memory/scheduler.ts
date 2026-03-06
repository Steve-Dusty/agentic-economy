/**
 * In-Process Scheduler
 *
 * Handles two types of scheduled work:
 * 1. Memory distillation — daily at 5 AM EST
 * 2. Scheduled execution rules — every 5 minutes (checks which rules are due)
 *
 * Self-initializing: import this module once and it starts automatically.
 * Safe to import multiple times — only starts one scheduler.
 */

import { distillAllUsers } from './distillation-service';

// ── Config ──────────────────────────────────────────────────────────────
const DISTILL_HOUR_EST = 5; // 5 AM EST
const RULES_CHECK_INTERVAL_MS = 5 * 60 * 1000; // Every 5 minutes
const DISTILL_CHECK_INTERVAL_MS = 30 * 60 * 1000; // Check every 30 minutes

let schedulerStarted = false;
let lastDistillDate = '';

// ── Helpers ─────────────────────────────────────────────────────────────

function getESTDate(): { dateStr: string; hour: number } {
  const now = new Date();
  // Convert to EST (UTC-5)
  const estOffset = -5 * 60;
  const utcMinutes = now.getUTCHours() * 60 + now.getUTCMinutes();
  const estMinutes = utcMinutes + estOffset;

  const estDate = new Date(now);
  estDate.setUTCMinutes(estDate.getUTCMinutes() + estOffset);

  return {
    dateStr: estDate.toISOString().split('T')[0]!,
    hour: Math.floor(((estMinutes % 1440) + 1440) % 1440 / 60),
  };
}

// ── Memory Distillation ─────────────────────────────────────────────────

async function checkDistillation() {
  const { dateStr, hour } = getESTDate();

  if (hour >= DISTILL_HOUR_EST && lastDistillDate !== dateStr) {
    lastDistillDate = dateStr;
    console.log(`[Scheduler] Running daily memory distillation for ${dateStr}...`);
    try {
      const result = await distillAllUsers();
      console.log(
        `[Scheduler] Distillation done. Users: ${result.usersProcessed}, Insights: ${result.totalInsights}${
          result.errors.length > 0 ? `, Errors: ${result.errors.length}` : ''
        }`
      );
    } catch (error) {
      console.error('[Scheduler] Distillation failed:', error);
    }
  }
}

// ── Scheduled Execution Rules ───────────────────────────────────────────

async function checkScheduledRules() {
  try {
    const { triggerProcessingService } = await import(
      '@/lib/execution-rules/trigger-processing-service'
    );
    const result = await triggerProcessingService.processScheduled();
    if (result.rulesProcessed > 0) {
      console.log(
        `[Scheduler] Scheduled rules: ${result.rulesSucceeded}/${result.rulesProcessed} succeeded`
      );
    }
  } catch (error) {
    console.error('[Scheduler] Scheduled rules check failed:', error);
  }
}

// ── Start ───────────────────────────────────────────────────────────────

export function startMemoryScheduler() {
  if (schedulerStarted) return;
  schedulerStarted = true;

  if (process.env.NODE_ENV === 'development' && !process.env.ENABLE_SCHEDULER) {
    console.log('[Scheduler] Skipped in development (set ENABLE_SCHEDULER=1 to enable)');
    return;
  }

  console.log(
    `[Scheduler] Started. Memory distillation daily at ${DISTILL_HOUR_EST}:00 EST. ` +
    `Scheduled rules every ${RULES_CHECK_INTERVAL_MS / 60000} min.`
  );

  // Run checks immediately on startup
  checkDistillation();
  checkScheduledRules();

  // Memory distillation — check every 30 min
  setInterval(checkDistillation, DISTILL_CHECK_INTERVAL_MS);

  // Scheduled execution rules — check every 5 min
  setInterval(checkScheduledRules, RULES_CHECK_INTERVAL_MS);
}
