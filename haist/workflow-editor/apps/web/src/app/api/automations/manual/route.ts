/**
 * Manual Rules API Route
 *
 * GET /api/execution-rules/manual - Get rules available for manual invocation
 */

import { NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { executionRulesStorage } from '@/lib/execution-rules/storage';

/**
 * GET /api/execution-rules/manual - Get rules available for manual invocation
 * Returns rules where activation_mode is 'manual' or 'all'
 */
export async function GET() {
  try {
    const userId = DEV_USER.id;

    const rules = await executionRulesStorage.getManualRules(userId);

    // Return simplified rule data for the mention dropdown
    return NextResponse.json({
      rules: rules.map((rule) => ({
        id: rule.id,
        name: rule.name,
        description: rule.description,
      })),
    });
  } catch (error) {
    console.error('Error fetching manual rules:', error);
    return NextResponse.json(
      { error: 'Failed to fetch manual rules' },
      { status: 500 }
    );
  }
}
