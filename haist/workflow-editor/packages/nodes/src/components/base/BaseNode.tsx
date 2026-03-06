'use client';

/**
 * Base node component
 */

import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { clsx } from 'clsx';
import type { WorkflowNode, WorkflowNodeData } from '@workflow-editor/core';
import { useSelectionStore } from '@workflow-editor/state';

export interface BaseNodeProps extends NodeProps<WorkflowNode> {
  /** Node icon */
  icon?: React.ReactNode;
  /** Node color (hex or tailwind class) */
  color?: string;
  /** Whether to show input handle (top - flow control) */
  showInput?: boolean;
  /** Whether to show output handle (bottom - flow control) */
  showOutput?: boolean;
  /** Whether to show data input handle (left - for dynamic inputs) */
  showDataInput?: boolean;
  /** Whether to show data output handle (right - for data outputs) */
  showDataOutput?: boolean;
  /** Custom header content */
  headerContent?: React.ReactNode;
  /** Custom body content */
  children?: React.ReactNode;
}

/**
 * Base node component that provides common structure
 */
export const BaseNode = memo(function BaseNode({
  id,
  data,
  selected,
  icon,
  color = '#64748b',
  showInput = true,
  showOutput = true,
  showDataInput = false,
  showDataOutput = false,
  headerContent,
  children,
}: BaseNodeProps) {
  const isNodeSelected = useSelectionStore((state) => state.isNodeSelected(id));
  const isSelected = selected || isNodeSelected;

  const hasErrors = data.validationErrors.length > 0;

  return (
    <div
      className={clsx(
        'rounded-lg border-2 bg-card shadow-md min-w-[200px] max-w-[300px]',
        'transition-all duration-150',
        isSelected ? 'border-primary ring-2 ring-primary/20' : 'border-border',
        hasErrors && !isSelected && 'border-destructive/50'
      )}
    >
      {/* Flow Control Input Handle (top) */}
      {showInput && (
        <Handle
          type="target"
          position={Position.Top}
          id="flow"
          className={clsx(
            'w-3 h-3 !bg-muted-foreground border-2 border-background',
            'hover:!bg-primary hover:scale-110 transition-all'
          )}
        />
      )}

      {/* Data Input Handle (left) */}
      {showDataInput && (
        <Handle
          type="target"
          position={Position.Left}
          id="data"
          className={clsx(
            'w-3 h-3 !bg-blue-500 border-2 border-background',
            'hover:!bg-blue-600 hover:scale-110 transition-all'
          )}
          style={{ top: '50%' }}
        />
      )}

      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-t-md"
        style={{ backgroundColor: `${color}20` }}
      >
        {icon && (
          <div
            className="flex items-center justify-center w-6 h-6 rounded"
            style={{ backgroundColor: color, color: 'white' }}
          >
            {icon}
          </div>
        )}
        <div className="flex-1 min-w-0">
          {headerContent || (
            <div className="font-medium text-sm truncate">{data.label}</div>
          )}
        </div>
        {hasErrors && (
          <div className="w-2 h-2 rounded-full bg-destructive animate-pulse" />
        )}
      </div>

      {/* Body */}
      {children && (
        <div className="px-3 py-2 text-xs text-muted-foreground">
          {children}
        </div>
      )}

      {/* Data Output Handle (right) */}
      {showDataOutput && (
        <Handle
          type="source"
          position={Position.Right}
          id="data-out"
          className={clsx(
            'w-3 h-3 !bg-blue-500 border-2 border-background',
            'hover:!bg-blue-600 hover:scale-110 transition-all'
          )}
          style={{ top: '50%' }}
        />
      )}

      {/* Flow Control Output Handle (bottom) */}
      {showOutput && (
        <Handle
          type="source"
          position={Position.Bottom}
          id="flow"
          className={clsx(
            'w-3 h-3 !bg-muted-foreground border-2 border-background',
            'hover:!bg-primary hover:scale-110 transition-all'
          )}
        />
      )}
    </div>
  );
});
