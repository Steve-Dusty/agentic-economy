/**
 * History store for undo/redo functionality
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import type { WorkflowNode, WorkflowEdge } from '@workflow-editor/core';

/**
 * History entry
 */
export interface HistoryEntry {
  /** Snapshot of nodes */
  nodes: WorkflowNode[];
  /** Snapshot of edges */
  edges: WorkflowEdge[];
  /** Timestamp */
  timestamp: number;
  /** Description of the change */
  description: string;
}

/**
 * History store state
 */
export interface HistoryState {
  /** Past states (for undo) */
  past: HistoryEntry[];
  /** Future states (for redo) */
  future: HistoryEntry[];
  /** Maximum history entries */
  maxHistory: number;
  /** Whether currently in a batch operation */
  isBatching: boolean;
}

/**
 * History store actions
 */
export interface HistoryActions {
  /** Push current state to history */
  pushState: (
    nodes: WorkflowNode[],
    edges: WorkflowEdge[],
    description: string
  ) => void;

  /** Undo last change */
  undo: () => HistoryEntry | null;

  /** Redo last undone change */
  redo: () => HistoryEntry | null;

  /** Check if can undo */
  canUndo: () => boolean;

  /** Check if can redo */
  canRedo: () => boolean;

  /** Clear all history */
  clearHistory: () => void;

  /** Set max history entries */
  setMaxHistory: (max: number) => void;

  /** Start batching (multiple changes = one undo) */
  startBatch: () => void;

  /** End batching */
  endBatch: (
    nodes: WorkflowNode[],
    edges: WorkflowEdge[],
    description: string
  ) => void;

  /** Get history length */
  getHistoryLength: () => { past: number; future: number };

  /** Reset */
  reset: () => void;
}

export type HistoryStore = HistoryState & HistoryActions;

const DEFAULT_MAX_HISTORY = 50;

const initialState: HistoryState = {
  past: [],
  future: [],
  maxHistory: DEFAULT_MAX_HISTORY,
  isBatching: false,
};

/**
 * History store for undo/redo
 */
export const useHistoryStore = create<HistoryStore>()(
  devtools(
    immer((set, get) => ({
      ...initialState,

      pushState: (nodes, edges, description) =>
        set((state) => {
          // Don't push if batching
          if (state.isBatching) return;

          // Create new entry
          const entry: HistoryEntry = {
            nodes: JSON.parse(JSON.stringify(nodes)),
            edges: JSON.parse(JSON.stringify(edges)),
            timestamp: Date.now(),
            description,
          };

          // Add to past
          state.past.push(entry);

          // Trim if exceeds max
          if (state.past.length > state.maxHistory) {
            state.past.shift();
          }

          // Clear future on new action
          state.future = [];
        }),

      undo: () => {
        const state = get();
        if (state.past.length === 0) return null;

        let entry: HistoryEntry | null = null;

        set((s) => {
          entry = s.past.pop()!;
          // Current state becomes future
          // Note: The actual current state should be passed from the workflow store
          // This is handled by the integration layer
        });

        return entry;
      },

      redo: () => {
        const state = get();
        if (state.future.length === 0) return null;

        let entry: HistoryEntry | null = null;

        set((s) => {
          entry = s.future.pop()!;
        });

        return entry;
      },

      canUndo: () => get().past.length > 0,

      canRedo: () => get().future.length > 0,

      clearHistory: () =>
        set((state) => {
          state.past = [];
          state.future = [];
        }),

      setMaxHistory: (max) =>
        set((state) => {
          state.maxHistory = max;
          // Trim if current history exceeds new max
          if (state.past.length > max) {
            state.past = state.past.slice(-max);
          }
        }),

      startBatch: () =>
        set((state) => {
          state.isBatching = true;
        }),

      endBatch: (nodes, edges, description) =>
        set((state) => {
          state.isBatching = false;

          // Push the batched state
          const entry: HistoryEntry = {
            nodes: JSON.parse(JSON.stringify(nodes)),
            edges: JSON.parse(JSON.stringify(edges)),
            timestamp: Date.now(),
            description,
          };

          state.past.push(entry);

          if (state.past.length > state.maxHistory) {
            state.past.shift();
          }

          state.future = [];
        }),

      getHistoryLength: () => ({
        past: get().past.length,
        future: get().future.length,
      }),

      reset: () => set(initialState),
    })),
    { name: 'HistoryStore' }
  )
);
