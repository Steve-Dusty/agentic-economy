/**
 * Edge type definitions for workflow connections
 */

import type { Edge } from '@xyflow/react';
import { MarkerType } from '@xyflow/react';

/**
 * Edge types in the workflow editor
 */
export enum EdgeType {
  DATA_FLOW = 'dataFlow',
  CONTROL_FLOW = 'controlFlow',
  ERROR_FLOW = 'errorFlow',
}

/**
 * Base edge data interface
 * Includes index signature for compatibility with @xyflow/react Edge type
 */
export interface BaseEdgeData {
  /** Index signature for @xyflow/react compatibility */
  [key: string]: unknown;
  /** Optional label */
  label?: string;
  /** Whether to animate the edge */
  animated?: boolean;
}

/**
 * Data flow edge - connects output to input
 */
export interface DataFlowEdgeData extends BaseEdgeData {
  edgeType: 'data';
  /** Source output field name */
  sourceOutput?: string;
  /** Target input field name */
  targetInput?: string;
}

/**
 * Control flow edge - execution order
 */
export interface ControlFlowEdgeData extends BaseEdgeData {
  edgeType: 'control';
  /** Branch type for control flow */
  branch?: 'then' | 'else' | 'catch' | 'finally' | 'loop' | 'parallel';
}

/**
 * Error flow edge - error handling path
 */
export interface ErrorFlowEdgeData extends BaseEdgeData {
  edgeType: 'error';
}

/**
 * Union of all edge data types
 */
export type WorkflowEdgeData =
  | DataFlowEdgeData
  | ControlFlowEdgeData
  | ErrorFlowEdgeData;

/**
 * Typed workflow edge
 */
export type WorkflowEdge = Edge<WorkflowEdgeData>;

/**
 * Edge style configuration
 */
export interface EdgeStyleConfig {
  strokeColor: string;
  strokeWidth: number;
  strokeDasharray?: string;
  animated?: boolean;
  markerEnd?: MarkerType;
}

/**
 * Default edge styles by type
 */
export const DEFAULT_EDGE_STYLES: Record<WorkflowEdgeData['edgeType'], EdgeStyleConfig> = {
  data: {
    strokeColor: '#64748b',
    strokeWidth: 2,
    animated: false,
    markerEnd: MarkerType.ArrowClosed,
  },
  control: {
    strokeColor: '#3b82f6',
    strokeWidth: 2,
    strokeDasharray: '5,5',
    animated: true,
    markerEnd: MarkerType.ArrowClosed,
  },
  error: {
    strokeColor: '#ef4444',
    strokeWidth: 2,
    animated: false,
    markerEnd: MarkerType.ArrowClosed,
  },
};

/**
 * Create a data flow edge
 */
export function createDataFlowEdge(
  id: string,
  source: string,
  target: string,
  sourceHandle?: string,
  targetHandle?: string
): WorkflowEdge {
  return {
    id,
    source,
    target,
    sourceHandle,
    targetHandle,
    type: EdgeType.DATA_FLOW,
    data: {
      edgeType: 'data',
      sourceOutput: sourceHandle,
      targetInput: targetHandle,
    },
  };
}

/**
 * Create a control flow edge
 */
export function createControlFlowEdge(
  id: string,
  source: string,
  target: string,
  branch?: ControlFlowEdgeData['branch']
): WorkflowEdge {
  return {
    id,
    source,
    target,
    type: EdgeType.CONTROL_FLOW,
    data: {
      edgeType: 'control',
      branch,
      label: branch,
      animated: true,
    },
  };
}

/**
 * Create an error flow edge
 */
export function createErrorFlowEdge(
  id: string,
  source: string,
  target: string
): WorkflowEdge {
  return {
    id,
    source,
    target,
    type: EdgeType.ERROR_FLOW,
    data: {
      edgeType: 'error',
      label: 'error',
    },
  };
}
