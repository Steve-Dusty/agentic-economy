/**
 * Selection state store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

/**
 * Selection store state
 */
export interface SelectionState {
  // Selected items
  selectedNodeIds: string[];
  selectedEdgeIds: string[];

  // Hover state
  hoveredNodeId: string | null;
  hoveredEdgeId: string | null;

  // Context menu
  contextMenuPosition: { x: number; y: number } | null;
  contextMenuTargetId: string | null;
  contextMenuType: 'node' | 'edge' | 'canvas' | null;
}

/**
 * Selection store actions
 */
export interface SelectionActions {
  // Node selection
  selectNode: (id: string, multiSelect?: boolean) => void;
  deselectNode: (id: string) => void;
  toggleNodeSelection: (id: string) => void;

  // Edge selection
  selectEdge: (id: string, multiSelect?: boolean) => void;
  deselectEdge: (id: string) => void;
  toggleEdgeSelection: (id: string) => void;

  // Bulk operations
  selectMultiple: (nodeIds: string[], edgeIds: string[]) => void;
  selectAll: (nodeIds: string[], edgeIds: string[]) => void;
  clearSelection: () => void;

  // Hover
  setHoveredNode: (id: string | null) => void;
  setHoveredEdge: (id: string | null) => void;

  // Context menu
  openContextMenu: (
    position: { x: number; y: number },
    targetId: string | null,
    type: 'node' | 'edge' | 'canvas'
  ) => void;
  closeContextMenu: () => void;

  // Computed helpers
  isNodeSelected: (id: string) => boolean;
  isEdgeSelected: (id: string) => boolean;
  hasSelection: () => boolean;
  getSelectionCount: () => number;

  // Reset
  reset: () => void;
}

export type SelectionStore = SelectionState & SelectionActions;

const initialState: SelectionState = {
  selectedNodeIds: [],
  selectedEdgeIds: [],
  hoveredNodeId: null,
  hoveredEdgeId: null,
  contextMenuPosition: null,
  contextMenuTargetId: null,
  contextMenuType: null,
};

/**
 * Selection state store
 */
export const useSelectionStore = create<SelectionStore>()(
  devtools(
    immer((set, get) => ({
      ...initialState,

      // Node selection
      selectNode: (id, multiSelect = false) =>
        set((state) => {
          if (multiSelect) {
            if (!state.selectedNodeIds.includes(id)) {
              state.selectedNodeIds.push(id);
            }
          } else {
            state.selectedNodeIds = [id];
            state.selectedEdgeIds = [];
          }
        }),

      deselectNode: (id) =>
        set((state) => {
          state.selectedNodeIds = state.selectedNodeIds.filter((nid) => nid !== id);
        }),

      toggleNodeSelection: (id) =>
        set((state) => {
          const index = state.selectedNodeIds.indexOf(id);
          if (index === -1) {
            state.selectedNodeIds.push(id);
          } else {
            state.selectedNodeIds.splice(index, 1);
          }
        }),

      // Edge selection
      selectEdge: (id, multiSelect = false) =>
        set((state) => {
          if (multiSelect) {
            if (!state.selectedEdgeIds.includes(id)) {
              state.selectedEdgeIds.push(id);
            }
          } else {
            state.selectedEdgeIds = [id];
            state.selectedNodeIds = [];
          }
        }),

      deselectEdge: (id) =>
        set((state) => {
          state.selectedEdgeIds = state.selectedEdgeIds.filter((eid) => eid !== id);
        }),

      toggleEdgeSelection: (id) =>
        set((state) => {
          const index = state.selectedEdgeIds.indexOf(id);
          if (index === -1) {
            state.selectedEdgeIds.push(id);
          } else {
            state.selectedEdgeIds.splice(index, 1);
          }
        }),

      // Bulk operations
      selectMultiple: (nodeIds, edgeIds) =>
        set((state) => {
          state.selectedNodeIds = [...new Set([...state.selectedNodeIds, ...nodeIds])];
          state.selectedEdgeIds = [...new Set([...state.selectedEdgeIds, ...edgeIds])];
        }),

      selectAll: (nodeIds, edgeIds) =>
        set((state) => {
          state.selectedNodeIds = nodeIds;
          state.selectedEdgeIds = edgeIds;
        }),

      clearSelection: () =>
        set((state) => {
          state.selectedNodeIds = [];
          state.selectedEdgeIds = [];
        }),

      // Hover
      setHoveredNode: (id) =>
        set((state) => {
          state.hoveredNodeId = id;
        }),

      setHoveredEdge: (id) =>
        set((state) => {
          state.hoveredEdgeId = id;
        }),

      // Context menu
      openContextMenu: (position, targetId, type) =>
        set((state) => {
          state.contextMenuPosition = position;
          state.contextMenuTargetId = targetId;
          state.contextMenuType = type;
        }),

      closeContextMenu: () =>
        set((state) => {
          state.contextMenuPosition = null;
          state.contextMenuTargetId = null;
          state.contextMenuType = null;
        }),

      // Computed helpers
      isNodeSelected: (id) => get().selectedNodeIds.includes(id),
      isEdgeSelected: (id) => get().selectedEdgeIds.includes(id),
      hasSelection: () =>
        get().selectedNodeIds.length > 0 || get().selectedEdgeIds.length > 0,
      getSelectionCount: () =>
        get().selectedNodeIds.length + get().selectedEdgeIds.length,

      // Reset
      reset: () => set(initialState),
    })),
    { name: 'SelectionStore' }
  )
);
