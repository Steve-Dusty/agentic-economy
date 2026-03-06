'use client';

/**
 * Composio node component for external service integrations
 */

import React, { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { Mail, Calendar, FileText, MessageSquare, Database, Github, Cloud, ChevronDown, type LucideIcon } from 'lucide-react';
import type { ComposioWorkflowNode } from '@workflow-editor/core';
import { BaseNode } from '../base/BaseNode';

/**
 * Toolkit icon and color mapping
 */
const TOOLKIT_CONFIG: Record<string, { icon: LucideIcon; color: string; name: string }> = {
  GMAIL: { icon: Mail, color: '#EA4335', name: 'Gmail' },
  GOOGLECALENDAR: { icon: Calendar, color: '#4285F4', name: 'Google Calendar' },
  GOOGLEDRIVE: { icon: Cloud, color: '#0F9D58', name: 'Google Drive' },
  GOOGLEDOCS: { icon: FileText, color: '#4285F4', name: 'Google Docs' },
  GOOGLESHEETS: { icon: Database, color: '#0F9D58', name: 'Google Sheets' },
  SLACK: { icon: MessageSquare, color: '#4A154B', name: 'Slack' },
  NOTION: { icon: FileText, color: '#000000', name: 'Notion' },
  GITHUB: { icon: Github, color: '#24292F', name: 'GitHub' },
  OUTLOOK: { icon: Mail, color: '#0078D4', name: 'Outlook' },
};

export interface ComposioNodeProps extends NodeProps<ComposioWorkflowNode> {}

/**
 * Format tool name for display
 * e.g., "GMAIL_SEND_EMAIL" -> "Send Email"
 */
function formatToolName(toolName: string, toolkit: string): string {
  return toolName
    .replace(`${toolkit}_`, '')
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

/**
 * Composio node component
 */
export const ComposioNode = memo(function ComposioNode(props: ComposioNodeProps) {
  const { data } = props;

  const config = TOOLKIT_CONFIG[data.toolkit?.toUpperCase()] || {
    icon: Cloud,
    color: '#6B7280',
    name: data.toolkit || 'Unknown'
  };
  const IconComponent = config.icon;

  // Check if a tool is selected
  const hasToolSelected = Boolean(data.toolName);

  // Get configured parameters count
  const configuredParams = Object.keys(data.parameters || {}).length;

  return (
    <BaseNode
      {...props}
      icon={<IconComponent className="w-4 h-4" />}
      color={config.color}
    >
      <div className="space-y-1.5">
        {/* Toolkit badge */}
        <div className="flex items-center gap-1">
          <span
            className="text-xs px-1.5 py-0.5 rounded font-medium"
            style={{ backgroundColor: `${config.color}20`, color: config.color }}
          >
            {config.name}
          </span>
        </div>

        {/* Tool selection indicator */}
        {hasToolSelected ? (
          <>
            {/* Selected tool name */}
            <div className="flex items-center gap-1">
              <span className="text-muted-foreground text-xs">tool:</span>
              <span className="text-foreground text-xs font-medium">
                {formatToolName(data.toolName, data.toolkit)}
              </span>
            </div>

            {/* Variable name */}
            <div className="flex items-center gap-1">
              <span className="text-muted-foreground text-xs">var:</span>
              <code className="text-primary font-mono text-xs">{data.variableName}</code>
            </div>

            {/* Parameters summary */}
            {configuredParams > 0 && (
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground text-xs">params:</span>
                <span className="text-green-600 text-xs">{configuredParams} set</span>
              </div>
            )}
          </>
        ) : (
          /* No tool selected - prompt user */
          <div className="flex items-center gap-1 text-amber-600">
            <ChevronDown className="w-3 h-3" />
            <span className="text-xs">Select a tool</span>
          </div>
        )}

        {/* Tool description */}
        {data.toolDescription && (
          <div className="text-muted-foreground text-xs truncate max-w-[180px]">
            {data.toolDescription}
          </div>
        )}
      </div>
    </BaseNode>
  );
});
