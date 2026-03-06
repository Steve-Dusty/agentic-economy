/**
 * Memory Distillation Service
 *
 * Reviews recent daily artifacts and distills key facts, preferences,
 * and patterns into the user's soul artifact (__user_profile__).
 * Runs as a scheduled system feature.
 */

import { artifactService } from '@/lib/artifacts';
import OpenAI from 'openai';

const PROFILE_TITLE = '__user_profile__';
const DAILY_PREFIX = 'Daily — ';

/**
 * Run distillation for a specific user.
 * Reads daily artifacts from the last N days, extracts key insights,
 * and adds them to the soul artifact.
 */
export async function distillMemory(userId: string, daysBack = 3): Promise<{
  success: boolean;
  dailiesReviewed: number;
  insightsAdded: number;
  error?: string;
}> {
  try {
    // Get all user artifacts
    const allArtifacts = await artifactService.getByUserId(userId);

    // Find the soul artifact
    const soulArtifact = allArtifacts.find((a) => a.title === PROFILE_TITLE);
    if (!soulArtifact) {
      return { success: true, dailiesReviewed: 0, insightsAdded: 0 };
    }

    // Find recent daily artifacts
    const now = new Date();
    const dailyArtifacts = [];
    for (let i = 0; i < daysBack; i++) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      const daily = allArtifacts.find((a) => a.title === `${DAILY_PREFIX}${dateStr}`);
      if (daily) {
        dailyArtifacts.push(daily);
      }
    }

    if (dailyArtifacts.length === 0) {
      return { success: true, dailiesReviewed: 0, insightsAdded: 0 };
    }

    // Load entries from all daily artifacts
    const dailyEntries: string[] = [];
    for (const daily of dailyArtifacts) {
      const withEntries = await artifactService.getWithEntries(daily.id);
      if (withEntries) {
        for (const entry of withEntries.entries) {
          dailyEntries.push(`[${daily.title}] ${entry.content}`);
        }
      }
    }

    if (dailyEntries.length === 0) {
      return { success: true, dailiesReviewed: dailyArtifacts.length, insightsAdded: 0 };
    }

    // Load current soul artifact content for context
    const soulWithEntries = await artifactService.getWithEntries(soulArtifact.id);
    const existingSoulContent = soulWithEntries
      ? soulWithEntries.entries
          .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
          .slice(0, 10)
          .map((e) => e.content)
          .join('\n')
      : '';

    // Use AI to distill insights
    const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

    const response = await openai.chat.completions.create({
      model: 'gpt-4.1-mini',
      messages: [
        {
          role: 'system',
          content: `You are a memory distillation agent. Your job is to review daily logs and extract key facts worth remembering long-term about the user.

Extract ONLY:
- Stable facts (name, school, job, location, important people)
- Preferences and patterns (communication style, tools, habits)
- Important decisions or plans (travel, projects, deadlines)
- Recurring needs or interests

Do NOT extract:
- Trivial tasks or one-off questions
- Things already in the existing profile
- Temporary context that won't matter in a week

Format: Return a JSON array of strings, each being a concise fact/insight. Return an empty array [] if nothing new is worth remembering.

Example output: ["User is traveling to SFO Feb 20-24 for a conference", "Prefers Slack notifications over email for urgent items"]`,
        },
        {
          role: 'user',
          content: `EXISTING PROFILE:\n${existingSoulContent || '(empty)'}\n\nRECENT DAILY LOGS:\n${dailyEntries.join('\n')}`,
        },
      ],
      temperature: 0.3,
      response_format: { type: 'json_object' },
    });

    const content = response.choices[0]?.message?.content;
    if (!content) {
      return { success: true, dailiesReviewed: dailyArtifacts.length, insightsAdded: 0 };
    }

    let insights: string[] = [];
    try {
      const parsed = JSON.parse(content);
      insights = Array.isArray(parsed) ? parsed : (parsed.insights || parsed.facts || []);
    } catch {
      return { success: true, dailiesReviewed: dailyArtifacts.length, insightsAdded: 0 };
    }

    // Add each insight to the soul artifact
    let added = 0;
    for (const insight of insights) {
      if (typeof insight === 'string' && insight.trim()) {
        await artifactService.addEntry(soulArtifact.id, {
          content: insight.trim(),
          source: 'manual',
        });
        added++;
      }
    }

    return { success: true, dailiesReviewed: dailyArtifacts.length, insightsAdded: added };
  } catch (error) {
    console.error('[DistillationService] Error:', error);
    return {
      success: false,
      dailiesReviewed: 0,
      insightsAdded: 0,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Run distillation for all users who have daily artifacts.
 */
export async function distillAllUsers(): Promise<{
  usersProcessed: number;
  totalInsights: number;
  errors: string[];
}> {
  // In dev mode, just process the dev user
  const { DEV_USER } = await import('@/lib/dev-user');
  const userIds: string[] = [DEV_USER.id];
  let totalInsights = 0;
  const errors: string[] = [];

  for (const userId of userIds) {
    const outcome = await distillMemory(userId);
    if (outcome.success) {
      totalInsights += outcome.insightsAdded;
    } else if (outcome.error) {
      errors.push(`User ${userId}: ${outcome.error}`);
    }
  }

  return { usersProcessed: userIds.length, totalInsights, errors };
}
