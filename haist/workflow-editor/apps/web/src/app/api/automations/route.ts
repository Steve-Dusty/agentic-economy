/**
 * Execution Rules API Route
 *
 * GET /api/execution-rules - List all rules for the authenticated user
 * POST /api/execution-rules - Create a new rule
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { executionRulesStorage } from '@/lib/execution-rules/storage';
import type { ExecutionRuleInput } from '@/lib/execution-rules/types';

/**
 * GET /api/execution-rules - List all rules for the authenticated user
 */
export async function GET() {
  try {
    const userId = DEV_USER.id;

    const rules = await executionRulesStorage.getByUserId(userId);

    return NextResponse.json({ rules });
  } catch (error) {
    console.error('Error listing execution rules:', error);
    return NextResponse.json(
      { error: 'Failed to list execution rules' },
      { status: 500 }
    );
  }
}

/**
 * POST /api/execution-rules - Create a new rule
 */
export async function POST(request: NextRequest) {
  try {
    const userId = DEV_USER.id;

    const body = (await request.json()) as ExecutionRuleInput;

    // Validate required fields
    if (!body.name || typeof body.name !== 'string') {
      return NextResponse.json({ error: 'Name is required' }, { status: 400 });
    }

    if (!body.topicCondition || typeof body.topicCondition !== 'string') {
      return NextResponse.json(
        { error: 'Topic condition is required' },
        { status: 400 }
      );
    }

    if (!body.executionSteps || !Array.isArray(body.executionSteps)) {
      return NextResponse.json(
        { error: 'Execution steps are required' },
        { status: 400 }
      );
    }

    if (!body.outputConfig || typeof body.outputConfig !== 'object') {
      return NextResponse.json(
        { error: 'Output config is required' },
        { status: 400 }
      );
    }

    // Validate execution steps
    for (const step of body.executionSteps) {
      if (step.type === 'instruction') {
        if (!step.content || typeof step.content !== 'string') {
          return NextResponse.json(
            { error: 'Instruction step requires content' },
            { status: 400 }
          );
        }
      } else if (step.type === 'action') {
        if (!step.toolName || typeof step.toolName !== 'string') {
          return NextResponse.json(
            { error: 'Action step requires toolName' },
            { status: 400 }
          );
        }
      } else {
        return NextResponse.json(
          { error: 'Invalid step type. Must be "instruction" or "action"' },
          { status: 400 }
        );
      }
    }

    // Validate output config
    const validPlatforms = ['slack', 'gmail', 'webhook', 'none'];
    if (!validPlatforms.includes(body.outputConfig.platform)) {
      return NextResponse.json(
        { error: 'Invalid output platform' },
        { status: 400 }
      );
    }

    const validFormats = ['summary', 'detailed', 'raw'];
    if (!validFormats.includes(body.outputConfig.format)) {
      return NextResponse.json(
        { error: 'Invalid output format' },
        { status: 400 }
      );
    }

    // Validate activation mode if provided
    if (body.activationMode !== undefined) {
      const validModes = ['trigger', 'manual', 'scheduled', 'all'];
      if (!validModes.includes(body.activationMode)) {
        return NextResponse.json(
          { error: 'Invalid activation mode' },
          { status: 400 }
        );
      }
    }

    // Validate schedule interval if provided
    if (body.scheduleInterval !== undefined) {
      const validIntervals = ['15min', 'hourly', 'daily', 'weekly'];
      if (!validIntervals.includes(body.scheduleInterval)) {
        return NextResponse.json(
          { error: 'Invalid schedule interval' },
          { status: 400 }
        );
      }
    }

    const rule = await executionRulesStorage.create(userId, {
      name: body.name.trim(),
      description: body.description?.trim(),
      isActive: body.isActive ?? true,
      priority: body.priority ?? 0,
      acceptedTriggers: body.acceptedTriggers || [],
      topicCondition: body.topicCondition.trim(),
      executionSteps: body.executionSteps,
      outputConfig: body.outputConfig,
      activationMode: body.activationMode ?? 'trigger',
      scheduleEnabled: body.scheduleEnabled ?? false,
      scheduleInterval: body.scheduleInterval,
    });

    return NextResponse.json({ rule, success: true });
  } catch (error) {
    console.error('Error creating execution rule:', error);
    return NextResponse.json(
      { error: 'Failed to create execution rule' },
      { status: 500 }
    );
  }
}
