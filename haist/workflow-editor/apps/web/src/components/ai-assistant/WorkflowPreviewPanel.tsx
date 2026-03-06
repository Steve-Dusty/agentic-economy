'use client';

import React from 'react';
import { Save, ExternalLink, Workflow, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import type { WorkflowDocument } from '@workflow-editor/core';

interface WorkflowPreviewPanelProps {
  workflow: WorkflowDocument | null;
  onSave: () => void;
  isSaving: boolean;
}

export function WorkflowPreviewPanel({
  workflow,
  onSave,
  isSaving,
}: WorkflowPreviewPanelProps) {
  if (!workflow) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-4">
        <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
          <Workflow className="w-6 h-6 text-muted-foreground" />
        </div>
        <h3 className="font-medium mb-1">No Workflow Yet</h3>
        <p className="text-sm text-muted-foreground">
          Describe your workflow in the chat and I&apos;ll generate a preview here.
        </p>
      </div>
    );
  }

  // Count node types
  const nodeCounts = workflow.nodes.reduce(
    (acc, node) => {
      const data = node.data as { nodeType?: string };
      const nodeType = data.nodeType || 'unknown';
      acc[nodeType] = (acc[nodeType] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  // Get unique services/tools used
  const usedComponents = workflow.nodes.map((node) => {
    const data = node.data as {
      nodeType?: string;
      bubbleName?: string;
      toolkit?: string;
      toolName?: string;
    };
    if (data.nodeType === 'bubble') {
      return data.bubbleName || 'Unknown Bubble';
    }
    if (data.nodeType === 'composio') {
      return data.toolkit || 'Composio';
    }
    return 'Unknown';
  });

  const uniqueComponents = [...new Set(usedComponents)];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h3 className="font-semibold flex items-center gap-2">
          <Workflow className="w-4 h-4 text-primary" />
          Workflow Preview
        </h3>
      </div>

      {/* Workflow Info */}
      <div className="p-4 space-y-4 flex-1 overflow-y-auto">
        {/* Name & Description */}
        <div>
          <h4 className="font-medium text-lg">{workflow.metadata.name}</h4>
          {workflow.metadata.description && (
            <p className="text-sm text-muted-foreground mt-1">
              {workflow.metadata.description}
            </p>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-muted/50">
            <div className="text-2xl font-bold">{workflow.nodes.length}</div>
            <div className="text-sm text-muted-foreground">Nodes</div>
          </div>
          <div className="p-3 rounded-lg bg-muted/50">
            <div className="text-2xl font-bold">{workflow.edges.length}</div>
            <div className="text-sm text-muted-foreground">Connections</div>
          </div>
        </div>

        {/* Trigger */}
        <div>
          <h5 className="text-sm font-medium text-muted-foreground mb-2">
            Trigger
          </h5>
          <div className="p-3 rounded-lg bg-muted/50">
            <span className="font-mono text-sm">{workflow.trigger.type}</span>
            {workflow.trigger.cronSchedule && (
              <div className="text-xs text-muted-foreground mt-1">
                Schedule: {workflow.trigger.cronSchedule}
              </div>
            )}
          </div>
        </div>

        {/* Node Types */}
        {Object.keys(nodeCounts).length > 0 && (
          <div>
            <h5 className="text-sm font-medium text-muted-foreground mb-2">
              Node Types
            </h5>
            <div className="flex flex-wrap gap-2">
              {Object.entries(nodeCounts).map(([type, count]) => (
                <span
                  key={type}
                  className="px-2 py-1 rounded-md bg-muted text-sm"
                >
                  {type}: {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Components Used */}
        {uniqueComponents.length > 0 && (
          <div>
            <h5 className="text-sm font-medium text-muted-foreground mb-2">
              Components Used
            </h5>
            <div className="flex flex-wrap gap-2">
              {uniqueComponents.map((component) => (
                <span
                  key={component}
                  className="px-2 py-1 rounded-md bg-primary/10 text-primary text-sm"
                >
                  {component}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Node List */}
        <div>
          <h5 className="text-sm font-medium text-muted-foreground mb-2">
            Nodes
          </h5>
          <div className="space-y-2">
            {workflow.nodes.map((node, index) => {
              const data = node.data as {
                label?: string;
                nodeType?: string;
                bubbleName?: string;
                toolkit?: string;
                toolName?: string;
              };
              return (
                <div
                  key={node.id}
                  className="p-2 rounded-md bg-muted/50 text-sm"
                >
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-primary/20 text-primary text-xs flex items-center justify-center">
                      {index + 1}
                    </span>
                    <span className="font-medium">
                      {data.label ||
                        data.bubbleName ||
                        data.toolName ||
                        'Node'}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 pl-7">
                    {data.nodeType === 'bubble' && data.bubbleName}
                    {data.nodeType === 'composio' &&
                      `${data.toolkit}: ${data.toolName}`}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-border space-y-2">
        <button
          onClick={onSave}
          disabled={isSaving}
          className={clsx(
            'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg',
            'bg-primary text-primary-foreground',
            'hover:bg-primary/90 transition-colors',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          {isSaving ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Save & Edit in Editor
            </>
          )}
        </button>
        <p className="text-xs text-center text-muted-foreground">
          Saves the workflow and opens it in the visual editor
        </p>
      </div>
    </div>
  );
}
