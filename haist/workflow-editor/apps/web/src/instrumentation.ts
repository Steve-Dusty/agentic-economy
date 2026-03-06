/**
 * Next.js Instrumentation
 *
 * This file is loaded once when the server starts.
 * Used to initialize background services like the memory scheduler.
 *
 * https://nextjs.org/docs/app/building-your-application/optimizing/instrumentation
 */

export async function register() {
  // Only run on the server (not edge runtime)
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    const { startMemoryScheduler } = await import('@/lib/memory/scheduler');
    startMemoryScheduler();
  }
}
