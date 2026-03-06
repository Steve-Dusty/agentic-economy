'use client';

/**
 * Generic bubble node component
 */

import React, { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import {
  Brain,
  Globe,
  MessageSquare,
  Database,
  Mail,
  Table,
  Search,
  Wrench,
  Workflow,
  type LucideIcon,
} from 'lucide-react';
import type { BubbleNodeData, BubbleWorkflowNode } from '@workflow-editor/core';
import { getBubble } from '@workflow-editor/core';
import { BaseNode } from '../base/BaseNode';

/**
 * Icon mapping for bubbles
 */
const ICON_MAP: Record<string, LucideIcon> = {
  brain: Brain,
  globe: Globe,
  slack: MessageSquare,
  database: Database,
  mail: Mail,
  table: Table,
  search: Search,
  send: MessageSquare,
  // Add more mappings as needed
};

/**
 * Get icon component for a bubble
 */
function getIcon(iconName: string): React.ReactNode {
  const IconComponent = ICON_MAP[iconName] || Wrench;
  return <IconComponent className="w-4 h-4" />;
}

/**
 * Get node icon based on bubble type
 */
function getTypeIcon(type: BubbleNodeData['bubbleType']): React.ReactNode {
  switch (type) {
    case 'service':
      return <Globe className="w-4 h-4" />;
    case 'tool':
      return <Wrench className="w-4 h-4" />;
    case 'workflow':
      return <Workflow className="w-4 h-4" />;
    default:
      return <Wrench className="w-4 h-4" />;
  }
}

export interface BubbleNodeProps extends NodeProps<BubbleWorkflowNode> {}

/**
 * Generic bubble node component
 */
export const BubbleNode = memo(function BubbleNode(props: BubbleNodeProps) {
  const { data } = props;
  const bubble = getBubble(data.bubbleName);

  const icon = bubble ? getIcon(bubble.icon) : getTypeIcon(data.bubbleType);
  const color = bubble?.color || '#64748b';

  // Get configured parameters count
  const configuredParams = Object.keys(data.parameters).length;
  const requiredParams = bubble
    ? Object.values(bubble.schema).filter((p) => p.required).length
    : 0;

  return (
    <BaseNode {...props} icon={icon} color={color} showDataInput={true} showDataOutput={true}>
      <div className="space-y-1">
        {/* Variable name */}
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground">var:</span>
          <code className="text-primary font-mono">{data.variableName}</code>
        </div>

        {/* Parameters summary */}
        {requiredParams > 0 && (
          <div className="flex items-center gap-1">
            <span className="text-muted-foreground">params:</span>
            <span
              className={
                configuredParams >= requiredParams
                  ? 'text-green-600'
                  : 'text-amber-600'
              }
            >
              {configuredParams}/{requiredParams} configured
            </span>
          </div>
        )}

        {/* Description */}
        {data.description && (
          <div className="text-muted-foreground truncate">{data.description}</div>
        )}
      </div>
    </BaseNode>
  );
});

/**
 * Service bubble node
 */
export const ServiceBubbleNode = memo(function ServiceBubbleNode(
  props: NodeProps<BubbleWorkflowNode>
) {
  return <BubbleNode {...props} />;
});

/**
 * Tool bubble node
 */
export const ToolBubbleNode = memo(function ToolBubbleNode(
  props: NodeProps<BubbleWorkflowNode>
) {
  return <BubbleNode {...props} />;
});

/**
 * Workflow bubble node
 */
export const WorkflowBubbleNode = memo(function WorkflowBubbleNode(
  props: NodeProps<BubbleWorkflowNode>
) {
  return <BubbleNode {...props} />;
});
