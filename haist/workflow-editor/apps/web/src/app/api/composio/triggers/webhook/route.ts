/**
 * Composio Trigger Webhook API Route (Global)
 *
 * POST /api/composio/triggers/webhook - Receive trigger events from Composio
 *
 * Supports both V3 and V2 webhook payload formats:
 * - V3: userId in metadata.user_id
 * - V2: userId in data.user_id
 */

import { NextRequest, NextResponse } from 'next/server';
import { executionRulesStorage } from '@/lib/execution-rules/storage';
import { triggerProcessingService } from '@/lib/execution-rules/trigger-processing-service';
import type { TriggerPayload } from '@/lib/execution-rules/types';

/**
 * Composio V3 webhook payload format
 */
interface ComposioV3Payload {
  id: string;
  timestamp: string;
  type: string;
  metadata: {
    user_id: string;
    trigger_slug: string;
    trigger_id: string;
    connected_account_id: string;
    auth_config_id: string;
    log_id?: string;
  };
  data: Record<string, unknown>;
}

/**
 * Composio V2 webhook payload format
 */
interface ComposioV2Payload {
  type: string;
  timestamp: string;
  data: {
    user_id: string;
    connection_id: string;
    trigger_id: string;
    [key: string]: unknown;
  };
}

/**
 * Legacy/raw payload format (headers + body wrapper)
 */
interface LegacyPayload {
  headers?: Record<string, string>;
  body?: Record<string, unknown>;
}

type ComposioWebhookPayload = ComposioV3Payload | ComposioV2Payload | LegacyPayload | Record<string, unknown>;

/**
 * Extract userId and trigger info from any Composio webhook format
 */
function parseComposioPayload(payload: ComposioWebhookPayload): {
  userId: string | null;
  triggerSlug: string | null;
  eventData: Record<string, unknown>;
} {
  // V3 format: metadata.user_id
  if ('metadata' in payload && payload.metadata && typeof payload.metadata === 'object') {
    const meta = payload.metadata as Record<string, unknown>;
    return {
      userId: (meta.user_id as string) || null,
      triggerSlug: (meta.trigger_slug as string) || null,
      eventData: ('data' in payload ? payload.data : payload) as Record<string, unknown>,
    };
  }

  // V2 format: data.user_id
  if ('data' in payload && payload.data && typeof payload.data === 'object') {
    const data = payload.data as Record<string, unknown>;
    if (data.user_id) {
      return {
        userId: data.user_id as string,
        triggerSlug: ('type' in payload ? payload.type : null) as string | null,
        eventData: data,
      };
    }
  }

  // Legacy format: headers + body wrapper
  if ('headers' in payload && 'body' in payload && payload.body) {
    const body = payload.body as Record<string, unknown>;
    // Try to find user_id in body
    const userId = (body.user_id as string) ||
                   ((body.metadata as Record<string, unknown>)?.user_id as string) ||
                   ((body.data as Record<string, unknown>)?.user_id as string) ||
                   null;
    return {
      userId,
      triggerSlug: inferTriggerSlug(body),
      eventData: body,
    };
  }

  // Fallback: try to find user_id anywhere in the payload
  const p = payload as Record<string, unknown>;
  return {
    userId: (p.user_id as string) || (p.userId as string) || null,
    triggerSlug: inferTriggerSlug(p),
    eventData: p,
  };
}

/**
 * Infer trigger type from payload content
 */
function inferTriggerSlug(data: Record<string, unknown>): string | null {
  if (data.message_id && (data.message_text || data.sender)) return 'GMAIL_NEW_GMAIL_MESSAGE';
  if (data.thread_id && data.label_ids) return 'GMAIL_NEW_GMAIL_MESSAGE';
  if (data.event_id || data.calendar_id) return 'GOOGLECALENDAR_EVENT_CREATED';
  if (data.channel && data.text && data.user) return 'SLACK_NEW_MESSAGE';
  return null;
}

/**
 * Infer toolkit from trigger slug
 */
function inferToolkitFromTrigger(triggerSlug?: string | null): string {
  if (!triggerSlug) return 'UNKNOWN';
  const slug = triggerSlug.toUpperCase();
  if (slug.includes('GMAIL')) return 'GMAIL';
  if (slug.includes('CALENDAR')) return 'GOOGLECALENDAR';
  if (slug.includes('SLACK')) return 'SLACK';
  if (slug.includes('NOTION')) return 'NOTION';
  if (slug.includes('GITHUB')) return 'GITHUB';
  if (slug.includes('DRIVE')) return 'GOOGLEDRIVE';
  return 'UNKNOWN';
}

/**
 * POST - Receive trigger events from Composio
 */
export async function POST(request: NextRequest) {
  try {
    // Verify webhook secret if configured
    const webhookSecret = process.env.COMPOSIO_WEBHOOK_SECRET;
    if (webhookSecret) {
      const providedSecret =
        request.headers.get('x-webhook-secret') ||
        request.headers.get('x-composio-signature');
      if (providedSecret !== webhookSecret) {
        console.warn('[Composio Webhook] Invalid or missing webhook secret');
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
      }
    } else {
      console.warn('[Composio Webhook] COMPOSIO_WEBHOOK_SECRET is not configured — webhook signature verification is disabled');
    }

    const rawPayload = (await request.json()) as ComposioWebhookPayload;

    // Parse the payload (handles V3, V2, and legacy formats)
    const { userId, triggerSlug, eventData } = parseComposioPayload(rawPayload);

    console.log('[Composio Webhook] Received trigger event:', {
      userId: userId ? '[PRESENT]' : '[MISSING]',
      triggerSlug,
      eventDataKeys: Object.keys(eventData),
      timestamp: new Date().toISOString(),
    });

    if (!userId) {
      console.log('[Composio Webhook] No user_id found in payload structure');
      return NextResponse.json({
        received: true,
        processed: false,
        reason: 'No user_id in webhook payload - check Composio webhook version',
      });
    }

    console.log(`[Composio Webhook] Identified user: ${userId}`);

    // Check if user has active rules
    const hasRules = await executionRulesStorage.hasActiveRules(userId);
    if (!hasRules) {
      console.log(`[Composio Webhook] User ${userId} has no active rules`);
      return NextResponse.json({ received: true, processed: false, reason: 'No active rules' });
    }

    // Build TriggerPayload
    const resolvedTriggerSlug = triggerSlug || inferTriggerSlug(eventData) || 'UNKNOWN_TRIGGER';
    const triggerPayload: TriggerPayload = {
      id: (eventData.id as string) || (eventData.message_id as string) || crypto.randomUUID(),
      uuid: crypto.randomUUID(),
      triggerSlug: resolvedTriggerSlug,
      toolkitSlug: inferToolkitFromTrigger(resolvedTriggerSlug),
      userId,
      payload: eventData,
      originalPayload: rawPayload as Record<string, unknown>,
      metadata: {
        id: '',
        uuid: '',
        toolkitSlug: inferToolkitFromTrigger(resolvedTriggerSlug),
        triggerSlug: resolvedTriggerSlug,
        triggerConfig: {},
        connectedAccount: {
          id: '',
          uuid: '',
          authConfigId: '',
          authConfigUUID: '',
          userId,
          status: 'ACTIVE',
        },
      },
    };

    // Process async
    processTriggerAsync(userId, triggerPayload).catch((err) => {
      console.error('[Composio Webhook] Async processing error:', err);
    });

    return NextResponse.json({
      received: true,
      processing: true,
      triggerId: triggerPayload.id,
      triggerSlug: resolvedTriggerSlug,
      userId,
    });
  } catch (error) {
    console.error('[Composio Webhook] Error:', error);
    return NextResponse.json({
      received: true,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
  }
}

/**
 * Process trigger asynchronously
 */
async function processTriggerAsync(userId: string, payload: TriggerPayload): Promise<void> {
  const result = await triggerProcessingService.process(userId, payload);

  if (result.matched && result.executed) {
    console.log(
      `[Composio Webhook] Successfully executed rule "${result.ruleName}" for trigger ${payload.triggerSlug}`
    );
  } else if (result.matched && !result.executed) {
    console.log(
      `[Composio Webhook] Rule "${result.ruleName}" matched but execution failed: ${result.error}`
    );
  } else {
    console.log(`[Composio Webhook] No rule matched for trigger ${payload.triggerSlug}`);
  }
}

/**
 * GET - Health check for the webhook endpoint
 */
export async function GET() {
  return NextResponse.json({
    status: 'ok',
    endpoint: '/api/composio/triggers/webhook',
    message: 'Webhook endpoint is active',
  });
}
