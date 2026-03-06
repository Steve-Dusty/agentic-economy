'use client';

/**
 * Custom node handle component
 */

import React from 'react';
import { Handle, Position, type HandleProps } from '@xyflow/react';
import { clsx } from 'clsx';

export interface NodeHandleProps extends Omit<HandleProps, 'type' | 'position'> {
  /** Handle type */
  type: 'source' | 'target';
  /** Position on the node */
  position: 'top' | 'right' | 'bottom' | 'left';
  /** Label for the handle */
  label?: string;
  /** Whether the connection is required */
  required?: boolean;
  /** Custom color */
  color?: string;
}

const positionMap: Record<NodeHandleProps['position'], Position> = {
  top: Position.Top,
  right: Position.Right,
  bottom: Position.Bottom,
  left: Position.Left,
};

/**
 * Custom styled handle component
 */
export function NodeHandle({
  type,
  position,
  label,
  required,
  color,
  className,
  ...props
}: NodeHandleProps) {
  return (
    <div className="relative">
      <Handle
        type={type}
        position={positionMap[position]}
        className={clsx(
          'w-3 h-3 border-2 border-background transition-all',
          'hover:scale-110',
          color ? '' : 'bg-muted-foreground hover:bg-primary',
          required && 'ring-2 ring-primary/50',
          className
        )}
        style={color ? { backgroundColor: color } : undefined}
        {...props}
      />
      {label && (
        <span
          className={clsx(
            'absolute text-[10px] text-muted-foreground whitespace-nowrap',
            position === 'top' && '-top-4 left-1/2 -translate-x-1/2',
            position === 'bottom' && '-bottom-4 left-1/2 -translate-x-1/2',
            position === 'left' && 'top-1/2 -translate-y-1/2 -left-12',
            position === 'right' && 'top-1/2 -translate-y-1/2 -right-12'
          )}
        >
          {label}
        </span>
      )}
    </div>
  );
}
