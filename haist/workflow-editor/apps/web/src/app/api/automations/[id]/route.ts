/**
 * Execution Rule by ID API Route
 *
 * GET /api/execution-rules/[id] - Get a specific rule
 * PUT /api/execution-rules/[id] - Update a rule
 * DELETE /api/execution-rules/[id] - Delete a rule
 */

import { NextRequest, NextResponse } from 'next/server';
import { DEV_USER } from '@/lib/dev-user';
import { executionRulesStorage } from '@/lib/execution-rules/storage';
import type { ExecutionRuleInput } from '@/lib/execution-rules/types';

interface RouteParams {
  params: Promise<{ id: string }>;
}

/**
 * GET /api/execution-rules/[id] - Get a specific rule
 */
export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    const { id } = await params;
    const rule = await executionRulesStorage.get(id);

    if (!rule) {
      return NextResponse.json({ error: 'Rule not found' }, { status: 404 });
    }

    // Check ownership
    if (rule.userId !== userId) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    return NextResponse.json({ rule });
  } catch (error) {
    console.error('Error getting execution rule:', error);
    return NextResponse.json(
      { error: 'Failed to get execution rule' },
      { status: 500 }
    );
  }
}

/**
 * PUT /api/execution-rules/[id] - Update a rule
 */
export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    const { id } = await params;
    const existingRule = await executionRulesStorage.get(id);

    if (!existingRule) {
      return NextResponse.json({ error: 'Rule not found' }, { status: 404 });
    }

    // Check ownership
    if (existingRule.userId !== userId) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    const body = (await request.json()) as Partial<ExecutionRuleInput>;

    // Validate execution steps if provided
    if (body.executionSteps) {
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
    }

    // Validate output config if provided
    if (body.outputConfig) {
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

    const updatedRule = await executionRulesStorage.update(id, {
      name: body.name?.trim(),
      description: body.description?.trim(),
      isActive: body.isActive,
      priority: body.priority,
      acceptedTriggers: body.acceptedTriggers,
      topicCondition: body.topicCondition?.trim(),
      executionSteps: body.executionSteps,
      outputConfig: body.outputConfig,
      activationMode: body.activationMode,
      scheduleEnabled: body.scheduleEnabled,
      scheduleInterval: body.scheduleInterval,
    });

    return NextResponse.json({ rule: updatedRule, success: true });
  } catch (error) {
    console.error('Error updating execution rule:', error);
    return NextResponse.json(
      { error: 'Failed to update execution rule' },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/execution-rules/[id] - Delete a rule
 */
export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const userId = DEV_USER.id;

    const { id } = await params;
    const existingRule = await executionRulesStorage.get(id);

    if (!existingRule) {
      return NextResponse.json({ error: 'Rule not found' }, { status: 404 });
    }

    // Check ownership
    if (existingRule.userId !== userId) {
      return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
    }

    await executionRulesStorage.delete(id);

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting execution rule:', error);
    return NextResponse.json(
      { error: 'Failed to delete execution rule' },
      { status: 500 }
    );
  }
}
