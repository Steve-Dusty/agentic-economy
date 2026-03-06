/**
 * Trigger type definitions
 */

import type { TriggerType } from '../types/node.types';
import type { SchemaDefinition } from '../types/parameter.types';

/**
 * Trigger definition
 */
export interface TriggerDefinition {
  type: TriggerType;
  name: string;
  description: string;
  icon: string;
  color: string;
  payloadSchema: SchemaDefinition;
  configSchema: SchemaDefinition;
}

/**
 * All supported triggers
 */
export const TRIGGERS: Record<TriggerType, TriggerDefinition> = {
  'webhook/http': {
    type: 'webhook/http',
    name: 'Webhook',
    description: 'Trigger workflow via HTTP webhook',
    icon: 'webhook',
    color: '#10b981',
    payloadSchema: {
      type: 'object',
      properties: {
        body: { type: 'object', description: 'Request body' },
        headers: { type: 'object', description: 'Request headers' },
        query: { type: 'object', description: 'Query parameters' },
        method: { type: 'string', description: 'HTTP method' },
        path: { type: 'string', description: 'Request path' },
      },
    },
    configSchema: {
      type: 'object',
      properties: {
        webhookPath: { type: 'string', description: 'Custom webhook path' },
        methods: {
          type: 'array',
          description: 'Allowed HTTP methods',
        },
      },
    },
  },

  'schedule/cron': {
    type: 'schedule/cron',
    name: 'Cron Schedule',
    description: 'Trigger workflow on a schedule',
    icon: 'clock',
    color: '#8b5cf6',
    payloadSchema: {
      type: 'object',
      properties: {
        scheduledTime: { type: 'string', description: 'Scheduled execution time' },
        cron: { type: 'string', description: 'Cron expression' },
      },
    },
    configSchema: {
      type: 'object',
      properties: {
        cronSchedule: {
          type: 'string',
          description: 'Cron expression (e.g., "0 9 * * 1-5" for weekdays at 9am)',
          required: true,
        },
        timezone: { type: 'string', description: 'Timezone for schedule' },
      },
      required: ['cronSchedule'],
    },
  },

  'slack/bot_mentioned': {
    type: 'slack/bot_mentioned',
    name: 'Slack Mention',
    description: 'Trigger when bot is mentioned in Slack',
    icon: 'slack',
    color: '#4a154b',
    payloadSchema: {
      type: 'object',
      properties: {
        channel: { type: 'string', description: 'Slack channel ID' },
        user: { type: 'string', description: 'User who mentioned the bot' },
        text: { type: 'string', description: 'Message text' },
        thread_ts: { type: 'string', description: 'Thread timestamp' },
      },
    },
    configSchema: {
      type: 'object',
      properties: {
        channels: {
          type: 'array',
          description: 'Channels to listen in (empty = all)',
        },
      },
    },
  },
};

/**
 * Get trigger definition by type
 */
export function getTrigger(type: TriggerType): TriggerDefinition {
  return TRIGGERS[type];
}

/**
 * Get all trigger types
 */
export function getAllTriggerTypes(): TriggerType[] {
  return Object.keys(TRIGGERS) as TriggerType[];
}

/**
 * Common cron presets
 */
export const CRON_PRESETS = [
  { label: 'Every minute', value: '* * * * *' },
  { label: 'Every 5 minutes', value: '*/5 * * * *' },
  { label: 'Every 15 minutes', value: '*/15 * * * *' },
  { label: 'Every hour', value: '0 * * * *' },
  { label: 'Every day at midnight', value: '0 0 * * *' },
  { label: 'Every day at 9am', value: '0 9 * * *' },
  { label: 'Every Monday at 9am', value: '0 9 * * 1' },
  { label: 'Weekdays at 9am', value: '0 9 * * 1-5' },
  { label: 'First of month at midnight', value: '0 0 1 * *' },
] as const;
