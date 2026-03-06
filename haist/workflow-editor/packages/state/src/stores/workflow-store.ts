/**
 * Main workflow state store
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import type {
  WorkflowNode,
  WorkflowEdge,
  TriggerConfig,
  WorkflowMetadata,
  ValidationError,
  ParameterValue,
  SerializedWorkflow,
} from '@workflow-editor/core';
import {
  generateNodeId,
  generateEdgeId,
  validateWorkflow,
  createEmptyWorkflow,
  serializeWorkflow,
  deserializeWorkflow,
} from '@workflow-editor/core';

/**
 * Workflow store state
 */
export interface WorkflowState {
  // Metadata
  metadata: WorkflowMetadata;

  // Trigger configuration
  trigger: TriggerConfig;

  // ReactFlow data
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];

  // Validation
  validationErrors: ValidationError[];
  isValid: boolean;

  // Dirty state
  isDirty: boolean;
}

/**
 * Workflow store actions
 */
export interface WorkflowActions {
  // Metadata
  setMetadata: (metadata: Partial<WorkflowMetadata>) => void;
  setTrigger: (trigger: TriggerConfig) => void;

  // Node operations
  addNode: (node: WorkflowNode) => void;
  updateNode: (id: string, updates: Partial<WorkflowNode>) => void;
  updateNodeData: (id: string, data: Partial<WorkflowNode['data']>) => void;
  removeNode: (id: string) => void;
  duplicateNode: (id: string) => WorkflowNode | null;
  setNodes: (nodes: WorkflowNode[]) => void;

  // Edge operations
  addEdge: (edge: WorkflowEdge) => void;
  updateEdge: (id: string, updates: Partial<WorkflowEdge>) => void;
  removeEdge: (id: string) => void;
  setEdges: (edges: WorkflowEdge[]) => void;

  // Parameter operations
  updateNodeParameter: (nodeId: string, paramName: string, value: ParameterValue) => void;

  // Workflow operations
  newWorkflow: (name?: string) => void;
  importWorkflow: (serialized: SerializedWorkflow) => void;
  exportWorkflow: () => SerializedWorkflow;

  // Validation
  validate: () => ValidationError[];
  clearValidation: () => void;

  // State management
  markClean: () => void;
  reset: () => void;
}

export type WorkflowStore = WorkflowState & WorkflowActions;

const initialState: WorkflowState = {
  metadata: {
    name: 'Untitled Workflow',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  trigger: {
    type: 'webhook/http',
    isActive: false,
  },
  nodes: [],
  edges: [],
  validationErrors: [],
  isValid: true,
  isDirty: false,
};

/**
 * Normalize edge handles for backward compatibility
 * Old edges used 'output'/'input', new edges use 'flow'/'flow'
 */
function normalizeEdgeHandles(edge: WorkflowEdge): WorkflowEdge {
  return {
    ...edge,
    sourceHandle: edge.sourceHandle === 'output' ? 'flow' : edge.sourceHandle,
    targetHandle: edge.targetHandle === 'input' ? 'flow' : edge.targetHandle,
  };
}

/**
 * Helper to run validation and update state
 */
function runValidation(state: WorkflowState) {
  const errors = validateWorkflow(state.nodes, state.edges);
  state.validationErrors = errors;
  state.isValid = errors.filter((e) => e.severity === 'error').length === 0;

  // Update individual node validation errors
  // Use index-based access for proper immer draft handling
  for (let i = 0; i < state.nodes.length; i++) {
    const nodeId = state.nodes[i].id;
    const nodeErrors = errors
      .filter((e) => e.nodeId === nodeId && e.severity === 'error')
      .map((e) => e.message);
    state.nodes[i].data.validationErrors = nodeErrors;
    state.nodes[i].data.isValid = nodeErrors.length === 0;
  }
}

/**
 * Main workflow store
 */
export const useWorkflowStore = create<WorkflowStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        // Metadata
        setMetadata: (metadata) =>
          set((state) => {
            Object.assign(state.metadata, metadata);
            state.metadata.updatedAt = new Date().toISOString();
            state.isDirty = true;
          }),

        setTrigger: (trigger) =>
          set((state) => {
            state.trigger = trigger;
            state.isDirty = true;
            runValidation(state);
          }),

        // Node operations
        addNode: (node) =>
          set((state) => {
            state.nodes.push(node);
            state.isDirty = true;
            runValidation(state);
          }),

        updateNode: (id, updates) =>
          set((state) => {
            const index = state.nodes.findIndex((n) => n.id === id);
            if (index !== -1) {
              Object.assign(state.nodes[index], updates);
              state.isDirty = true;
              runValidation(state);
            }
          }),

        updateNodeData: (id, data) =>
          set((state) => {
            const node = state.nodes.find((n) => n.id === id);
            if (node) {
              Object.assign(node.data, data);
              state.isDirty = true;
              runValidation(state);
            }
          }),

        removeNode: (id) =>
          set((state) => {
            state.nodes = state.nodes.filter((n) => n.id !== id);
            // Also remove connected edges
            state.edges = state.edges.filter(
              (e) => e.source !== id && e.target !== id
            );
            state.isDirty = true;
            runValidation(state);
          }),

        duplicateNode: (id) => {
          const state = get();
          const node = state.nodes.find((n) => n.id === id);
          if (!node) return null;

          const newNode: WorkflowNode = {
            ...node,
            id: generateNodeId(),
            position: {
              x: node.position.x + 50,
              y: node.position.y + 50,
            },
            data: { ...node.data },
          };

          set((state) => {
            state.nodes.push(newNode);
            state.isDirty = true;
            runValidation(state);
          });

          return newNode;
        },

        setNodes: (nodes) =>
          set((state) => {
            state.nodes = nodes;
            state.isDirty = true;
            runValidation(state);
          }),

        // Edge operations
        addEdge: (edge) =>
          set((state) => {
            // Normalize handles for backward compatibility
            const normalizedEdge = normalizeEdgeHandles(edge);
            // Check for duplicate
            const exists = state.edges.some(
              (e) =>
                e.source === normalizedEdge.source &&
                e.target === normalizedEdge.target &&
                e.sourceHandle === normalizedEdge.sourceHandle &&
                e.targetHandle === normalizedEdge.targetHandle
            );
            if (!exists) {
              state.edges.push({
                ...normalizedEdge,
                id: normalizedEdge.id || generateEdgeId(normalizedEdge.source, normalizedEdge.target),
              });
              state.isDirty = true;
              runValidation(state);
            }
          }),

        updateEdge: (id, updates) =>
          set((state) => {
            const index = state.edges.findIndex((e) => e.id === id);
            if (index !== -1) {
              Object.assign(state.edges[index], updates);
              state.isDirty = true;
              runValidation(state);
            }
          }),

        removeEdge: (id) =>
          set((state) => {
            state.edges = state.edges.filter((e) => e.id !== id);
            state.isDirty = true;
            runValidation(state);
          }),

        setEdges: (edges) =>
          set((state) => {
            // Normalize handles for backward compatibility
            state.edges = edges.map(normalizeEdgeHandles);
            state.isDirty = true;
            runValidation(state);
          }),

        // Parameter operations
        updateNodeParameter: (nodeId, paramName, value) =>
          set((state) => {
            const node = state.nodes.find((n) => n.id === nodeId);
            if (node && 'parameters' in node.data) {
              (node.data as { parameters: Record<string, ParameterValue> }).parameters[paramName] = value;
              state.isDirty = true;
              runValidation(state);
            }
          }),

        // Workflow operations
        newWorkflow: (name = 'Untitled Workflow') =>
          set((state) => {
            const empty = createEmptyWorkflow(name);
            state.metadata = empty.metadata;
            state.trigger = empty.trigger;
            state.nodes = [];
            state.edges = [];
            state.validationErrors = [];
            state.isValid = true;
            state.isDirty = false;
          }),

        importWorkflow: (serialized) =>
          set((state) => {
            const workflow = deserializeWorkflow(serialized);
            state.metadata = workflow.metadata;
            state.trigger = workflow.trigger;
            state.nodes = workflow.nodes;
            // Normalize edge handles for backward compatibility
            state.edges = workflow.edges.map(normalizeEdgeHandles);
            state.isDirty = false;
            runValidation(state);
          }),

        exportWorkflow: () => {
          const state = get();
          return serializeWorkflow({
            metadata: state.metadata,
            trigger: state.trigger,
            nodes: state.nodes,
            edges: state.edges,
          });
        },

        // Validation
        validate: () => {
          let errors: ReturnType<typeof validateWorkflow> = [];
          set((s) => {
            runValidation(s);
            errors = s.validationErrors;
          });
          return errors;
        },

        clearValidation: () =>
          set((state) => {
            state.validationErrors = [];
            state.isValid = true;

            // Clear individual node validation errors using index-based access
            for (let i = 0; i < state.nodes.length; i++) {
              state.nodes[i].data.validationErrors = [];
              state.nodes[i].data.isValid = true;
            }
          }),

        // State management
        markClean: () =>
          set((state) => {
            state.isDirty = false;
          }),

        reset: () => set(initialState),
      })),
      {
        name: 'workflow-editor-storage',
        partialize: (state) => ({
          metadata: state.metadata,
          trigger: state.trigger,
          nodes: state.nodes,
          edges: state.edges,
        }),
      }
    ),
    { name: 'WorkflowStore' }
  )
);
