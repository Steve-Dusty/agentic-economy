/**
 * Canvas UI state store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

/**
 * Viewport state
 */
export interface Viewport {
  x: number;
  y: number;
  zoom: number;
}

/**
 * Interaction modes
 */
export type InteractionMode = 'select' | 'pan' | 'connect';

/**
 * Drop target position
 */
export interface DropTarget {
  x: number;
  y: number;
}

/**
 * Canvas store state
 */
export interface CanvasState {
  // Viewport
  viewport: Viewport;

  // Grid settings
  showGrid: boolean;
  snapToGrid: boolean;
  gridSize: number;

  // Minimap
  showMinimap: boolean;

  // Interaction
  interactionMode: InteractionMode;

  // Drag and drop
  dropTarget: DropTarget | null;
  isDraggingOver: boolean;
  draggingNodeType: string | null;

  // Canvas dimensions
  canvasWidth: number;
  canvasHeight: number;
}

/**
 * Canvas store actions
 */
export interface CanvasActions {
  // Viewport
  setViewport: (viewport: Viewport) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  zoomTo: (zoom: number) => void;
  panTo: (x: number, y: number) => void;
  fitView: () => void;

  // Grid
  toggleGrid: () => void;
  toggleSnapToGrid: () => void;
  setGridSize: (size: number) => void;

  // Minimap
  toggleMinimap: () => void;

  // Interaction
  setInteractionMode: (mode: InteractionMode) => void;

  // Drag and drop
  setDropTarget: (target: DropTarget | null) => void;
  setIsDraggingOver: (isDragging: boolean) => void;
  setDraggingNodeType: (nodeType: string | null) => void;

  // Canvas dimensions
  setCanvasDimensions: (width: number, height: number) => void;

  // Reset
  reset: () => void;
}

export type CanvasStore = CanvasState & CanvasActions;

const initialState: CanvasState = {
  viewport: { x: 0, y: 0, zoom: 1 },
  showGrid: true,
  snapToGrid: true,
  gridSize: 20,
  showMinimap: true,
  interactionMode: 'select',
  dropTarget: null,
  isDraggingOver: false,
  draggingNodeType: null,
  canvasWidth: 0,
  canvasHeight: 0,
};

const MIN_ZOOM = 0.1;
const MAX_ZOOM = 2;
const ZOOM_STEP = 0.1;

/**
 * Canvas state store
 */
export const useCanvasStore = create<CanvasStore>()(
  devtools(
    immer((set) => ({
      ...initialState,

      // Viewport
      setViewport: (viewport) =>
        set((state) => {
          state.viewport = viewport;
        }),

      zoomIn: () =>
        set((state) => {
          state.viewport.zoom = Math.min(MAX_ZOOM, state.viewport.zoom + ZOOM_STEP);
        }),

      zoomOut: () =>
        set((state) => {
          state.viewport.zoom = Math.max(MIN_ZOOM, state.viewport.zoom - ZOOM_STEP);
        }),

      zoomTo: (zoom) =>
        set((state) => {
          state.viewport.zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom));
        }),

      panTo: (x, y) =>
        set((state) => {
          state.viewport.x = x;
          state.viewport.y = y;
        }),

      fitView: () =>
        set((state) => {
          // Reset to center - actual fit logic should be in the canvas component
          state.viewport = { x: 0, y: 0, zoom: 1 };
        }),

      // Grid
      toggleGrid: () =>
        set((state) => {
          state.showGrid = !state.showGrid;
        }),

      toggleSnapToGrid: () =>
        set((state) => {
          state.snapToGrid = !state.snapToGrid;
        }),

      setGridSize: (size) =>
        set((state) => {
          state.gridSize = size;
        }),

      // Minimap
      toggleMinimap: () =>
        set((state) => {
          state.showMinimap = !state.showMinimap;
        }),

      // Interaction
      setInteractionMode: (mode) =>
        set((state) => {
          state.interactionMode = mode;
        }),

      // Drag and drop
      setDropTarget: (target) =>
        set((state) => {
          state.dropTarget = target;
        }),

      setIsDraggingOver: (isDragging) =>
        set((state) => {
          state.isDraggingOver = isDragging;
        }),

      setDraggingNodeType: (nodeType) =>
        set((state) => {
          state.draggingNodeType = nodeType;
        }),

      // Canvas dimensions
      setCanvasDimensions: (width, height) =>
        set((state) => {
          state.canvasWidth = width;
          state.canvasHeight = height;
        }),

      // Reset
      reset: () => set(initialState),
    })),
    { name: 'CanvasStore' }
  )
);
