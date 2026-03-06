/**
 * Manual Rule Invocation API Route
 *
 * POST /api/execution-rules/invoke - Manually invoke a rule with context
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { executionRulesStorage } from '@/lib/execution-rules/storage';
import { triggerProcessingService } from '@/lib/execution-rules/trigger-processing-service';
import type { ManualInvocationResult } from '@/lib/execution-rules/types';

interface InvokeRequest {
  ruleId: string;
  context?: string;
  conversationHistory?: Array<{ role: string; content: string }>;
}

/**
 * POST /api/execution-rules/invoke - Manually invoke a rule
 */
export async function POST(request: NextRequest) {
  try {
    const userId = DEV_USER.id;

    const body = (await request.json()) as InvokeRequest;

    // Validate required fields
    if (!body.ruleId || typeof body.ruleId !== 'string') {
      return NextResponse.json(
        { error: 'Rule ID is required' },
        { status: 400 }
      );
    }

    // Get the rule and verify ownership
    const rule = await executionRulesStorage.getByIdAndUser(body.ruleId, userId);

    if (!rule) {
      return NextResponse.json(
        { error: 'Rule not found' },
        { status: 404 }
      );
    }

    // Check if rule is active
    if (!rule.isActive) {
      return NextResponse.json(
        { error: 'Rule is not active' },
        { status: 400 }
      );
    }

    // Check if rule supports manual invocation
    if (rule.activationMode !== 'manual' && rule.activationMode !== 'all') {
      return NextResponse.json(
        { error: 'Rule does not support manual invocation' },
        { status: 400 }
      );
    }

    // Execute the rule with manual context + conversation history
    const result = await triggerProcessingService.processManual(
      userId,
      rule,
      body.context || '',
      body.conversationHistory
    );

    const response: ManualInvocationResult = {
      success: result.success,
      ruleId: rule.id,
      ruleName: rule.name,
      output: result.output,
      error: result.error,
      executedAt: new Date().toISOString(),
    };

    return NextResponse.json({ success: true, result: response });
  } catch (error) {
    console.error('Error invoking execution rule:', error);
    return NextResponse.json(
      { error: 'Failed to invoke execution rule' },
      { status: 500 }
    );
  }
}
