/**
 * Workflow document types
 */

import type { WorkflowNode, TriggerType } from './node.types';
import type { WorkflowEdge } from './edge.types';

/**
 * Trigger configuration
 */
export interface TriggerConfig {
  /** The type of trigger */
  type: TriggerType;
  /** Cron schedule (for schedule/cron) */
  cronSchedule?: string;
  /** Webhook path (for webhook/http) */
  webhookPath?: string;
  /** Whether the trigger is active */
  isActive?: boolean;
}

/**
 * Workflow metadata
 */
export interface WorkflowMetadata {
  /** Workflow ID (for persistence) */
  id?: string;
  /** Workflow name */
  name: string;
  /** Optional description */
  description?: string;
  /** Version number */
  version?: number;
  /** Created timestamp */
  createdAt?: string;
  /** Updated timestamp */
  updatedAt?: string;
  /** Author information */
  author?: string;
  /** Tags for categorization */
  tags?: string[];
}

/**
 * Validation error for workflows
 */
export interface ValidationError {
  /** Node ID (null for workflow-level errors) */
  nodeId: string | null;
  /** Error message */
  message: string;
  /** Error severity */
  severity: 'error' | 'warning';
  /** Field path if applicable */
  field?: string;
}

/**
 * Complete workflow document
 */
export interface WorkflowDocument {
  /** Workflow metadata */
  metadata: WorkflowMetadata;
  /** Trigger configuration */
  trigger: TriggerConfig;
  /** Workflow nodes */
  nodes: WorkflowNode[];
  /** Workflow edges */
  edges: WorkflowEdge[];
}

/**
 * Serialized workflow for storage/export
 */
export interface SerializedWorkflow {
  /** Format version */
  formatVersion: string;
  /** Workflow metadata */
  metadata: WorkflowMetadata;
  /** Trigger configuration */
  trigger: TriggerConfig;
  /** Serialized nodes */
  nodes: SerializedNode[];
  /** Serialized edges */
  edges: SerializedEdge[];
}

/**
 * Serialized node (JSON-safe)
 */
export interface SerializedNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
}

/**
 * Serialized edge (JSON-safe)
 */
export interface SerializedEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  type?: string;
  data?: Record<string, unknown>;
}

/**
 * Execution result from a workflow run
 */
export interface WorkflowExecutionResult {
  /** Whether execution succeeded */
  success: boolean;
  /** Result data */
  data?: unknown;
  /** Error message if failed */
  error?: string;
  /** Execution duration in ms */
  duration?: number;
  /** Per-node execution results */
  nodeResults?: Record<string, NodeExecutionResult>;
}

/**
 * Per-node execution result
 */
export interface NodeExecutionResult {
  /** Node ID */
  nodeId: string;
  /** Whether node execution succeeded */
  success: boolean;
  /** Result data */
  data?: unknown;
  /** Error if failed */
  error?: string;
  /** Execution duration in ms */
  duration?: number;
}

/**
 * Create a new empty workflow document
 */
export function createEmptyWorkflow(name = 'Untitled Workflow'): WorkflowDocument {
  return {
    metadata: {
      name,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
    trigger: {
      type: 'webhook/http',
      isActive: false,
    },
    nodes: [],
    edges: [],
  };
}

/**
 * Serialize a workflow for storage
 */
export function serializeWorkflow(workflow: WorkflowDocument): SerializedWorkflow {
  return {
    formatVersion: '1.0.0',
    metadata: workflow.metadata,
    trigger: workflow.trigger,
    nodes: workflow.nodes.map((node) => ({
      id: node.id,
      type: node.type ?? 'default',
      position: node.position,
      data: node.data as Record<string, unknown>,
    })),
    edges: workflow.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle ?? undefined,
      targetHandle: edge.targetHandle ?? undefined,
      type: edge.type,
      data: edge.data as Record<string, unknown> | undefined,
    })),
  };
}

/**
 * Deserialize a workflow from storage
 */
export function deserializeWorkflow(serialized: SerializedWorkflow): WorkflowDocument {
  return {
    metadata: serialized.metadata,
    trigger: serialized.trigger,
    nodes: serialized.nodes.map((node) => ({
      id: node.id,
      type: node.type,
      position: node.position,
      data: node.data,
    })) as WorkflowNode[],
    edges: serialized.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle,
      targetHandle: edge.targetHandle,
      type: edge.type,
      data: edge.data,
    })) as WorkflowEdge[],
  };
}
