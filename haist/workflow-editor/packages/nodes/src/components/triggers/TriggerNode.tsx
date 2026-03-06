'use client';

/**
 * Trigger node component
 */

import React, { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { Webhook, Clock, MessageSquare } from 'lucide-react';
import type { TriggerNodeData, TriggerWorkflowNode } from '@workflow-editor/core';
import { BaseNode } from '../base/BaseNode';

/**
 * Get trigger icon
 */
function getTriggerIcon(triggerType: TriggerNodeData['triggerType']): React.ReactNode {
  switch (triggerType) {
    case 'webhook/http':
      return <Webhook className="w-4 h-4" />;
    case 'schedule/cron':
      return <Clock className="w-4 h-4" />;
    case 'slack/bot_mentioned':
      return <MessageSquare className="w-4 h-4" />;
    default:
      return <Webhook className="w-4 h-4" />;
  }
}

/**
 * Get trigger color
 */
function getTriggerColor(triggerType: TriggerNodeData['triggerType']): string {
  switch (triggerType) {
    case 'webhook/http':
      return '#10b981'; // emerald
    case 'schedule/cron':
      return '#8b5cf6'; // violet
    case 'slack/bot_mentioned':
      return '#4a154b'; // slack purple
    default:
      return '#10b981';
  }
}

export interface TriggerNodeProps extends NodeProps<TriggerWorkflowNode> {}

/**
 * Trigger node component
 */
export const TriggerNode = memo(function TriggerNode(props: TriggerNodeProps) {
  const { data } = props;

  const icon = getTriggerIcon(data.triggerType);
  const color = getTriggerColor(data.triggerType);

  return (
    <BaseNode
      {...props}
      icon={icon}
      color={color}
      showInput={false}
      showOutput={true}
    >
      <div className="space-y-1">
        {/* Trigger type */}
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground">type:</span>
          <span className="font-medium">{data.triggerType}</span>
        </div>

        {/* Cron schedule */}
        {data.triggerType === 'schedule/cron' && data.cronSchedule && (
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">cron:</span>
            <code className="text-primary font-mono text-[10px]">
              {data.cronSchedule}
            </code>
          </div>
        )}

        {/* Webhook path */}
        {data.triggerType === 'webhook/http' && data.webhookPath && (
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">path:</span>
            <code className="text-primary font-mono text-[10px]">
              {data.webhookPath}
            </code>
          </div>
        )}
      </div>
    </BaseNode>
  );
});
