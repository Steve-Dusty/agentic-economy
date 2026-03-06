/**
 * UI state store
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

/**
 * Right panel tabs
 */
export type RightPanelTab = 'config' | 'code' | 'schema' | 'results';

/**
 * Node output from execution
 */
export interface NodeOutput {
  data: unknown;
  success: boolean;
  label: string;
}

/**
 * Execution result type
 */
export interface ExecutionResult {
  success: boolean;
  data?: {
    bubbleResult?: {
      result?: unknown;
      success?: boolean;
      nodeOutputs?: Record<string, NodeOutput>;
    };
    composioResults?: Record<string, unknown>;
  };
  error?: string;
  logs?: Array<{
    timestamp: string;
    level: string;
    message: string;
    data?: unknown;
  }>;
  summary?: string;
  code?: string;
}

/**
 * Dialog types
 */
export type DialogType = 'trigger' | 'export' | 'import' | 'validation' | 'settings' | 'help' | 'connections';

/**
 * UI store state
 */
export interface UIState {
  // Panels
  leftPanelOpen: boolean;
  rightPanelOpen: boolean;
  leftPanelWidth: number;
  rightPanelWidth: number;

  // Tabs
  rightPanelTab: RightPanelTab;

  // Dialogs
  activeDialog: DialogType | null;
  dialogData: Record<string, unknown>;

  // Palette
  paletteSearchQuery: string;
  paletteExpandedCategories: string[];

  // Code preview
  codePreviewAutoUpdate: boolean;

  // Theme
  theme: 'light' | 'dark' | 'system';

  // Notifications
  notifications: Notification[];

  // Execution
  executionResult: ExecutionResult | null;
  isExecuting: boolean;
}

/**
 * Notification type
 */
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  createdAt: number;
}

/**
 * UI store actions
 */
export interface UIActions {
  // Panels
  toggleLeftPanel: () => void;
  toggleRightPanel: () => void;
  setLeftPanelWidth: (width: number) => void;
  setRightPanelWidth: (width: number) => void;
  openLeftPanel: () => void;
  closeLeftPanel: () => void;
  openRightPanel: () => void;
  closeRightPanel: () => void;

  // Tabs
  setRightPanelTab: (tab: RightPanelTab) => void;

  // Dialogs
  openDialog: (dialog: DialogType, data?: Record<string, unknown>) => void;
  closeDialog: () => void;
  setDialogData: (data: Record<string, unknown>) => void;

  // Palette
  setPaletteSearch: (query: string) => void;
  togglePaletteCategory: (category: string) => void;
  expandAllCategories: () => void;
  collapseAllCategories: () => void;

  // Code preview
  toggleCodePreviewAutoUpdate: () => void;

  // Theme
  setTheme: (theme: UIState['theme']) => void;

  // Notifications
  addNotification: (notification: Omit<Notification, 'id' | 'createdAt'>) => string;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;

  // Execution
  setExecutionResult: (result: ExecutionResult | null) => void;
  setIsExecuting: (isExecuting: boolean) => void;
  clearExecutionResult: () => void;

  // Reset
  reset: () => void;
}

export type UIStore = UIState & UIActions;

const DEFAULT_LEFT_PANEL_WIDTH = 280;
const DEFAULT_RIGHT_PANEL_WIDTH = 420;

const DEFAULT_CATEGORIES = [
  'triggers',
  'service-bubbles',
  'tool-bubbles',
  'workflow-bubbles',
  'composio-services',
  'control-flow',
];

const initialState: UIState = {
  leftPanelOpen: true,
  rightPanelOpen: true,
  leftPanelWidth: DEFAULT_LEFT_PANEL_WIDTH,
  rightPanelWidth: DEFAULT_RIGHT_PANEL_WIDTH,
  rightPanelTab: 'config',
  activeDialog: null,
  dialogData: {},
  paletteSearchQuery: '',
  paletteExpandedCategories: DEFAULT_CATEGORIES,
  codePreviewAutoUpdate: true,
  theme: 'system',
  notifications: [],
  executionResult: null,
  isExecuting: false,
};

/**
 * UI state store
 */
export const useUIStore = create<UIStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        // Panels
        toggleLeftPanel: () =>
          set((state) => {
            state.leftPanelOpen = !state.leftPanelOpen;
          }),

        toggleRightPanel: () =>
          set((state) => {
            state.rightPanelOpen = !state.rightPanelOpen;
          }),

        setLeftPanelWidth: (width) =>
          set((state) => {
            state.leftPanelWidth = Math.max(200, Math.min(400, width));
          }),

        setRightPanelWidth: (width) =>
          set((state) => {
            state.rightPanelWidth = Math.max(300, Math.min(700, width));
          }),

        openLeftPanel: () =>
          set((state) => {
            state.leftPanelOpen = true;
          }),

        closeLeftPanel: () =>
          set((state) => {
            state.leftPanelOpen = false;
          }),

        openRightPanel: () =>
          set((state) => {
            state.rightPanelOpen = true;
          }),

        closeRightPanel: () =>
          set((state) => {
            state.rightPanelOpen = false;
          }),

        // Tabs
        setRightPanelTab: (tab) =>
          set((state) => {
            state.rightPanelTab = tab;
            // Open panel if closed
            if (!state.rightPanelOpen) {
              state.rightPanelOpen = true;
            }
          }),

        // Dialogs
        openDialog: (dialog, data = {}) =>
          set((state) => {
            state.activeDialog = dialog;
            state.dialogData = data;
          }),

        closeDialog: () =>
          set((state) => {
            state.activeDialog = null;
            state.dialogData = {};
          }),

        setDialogData: (data) =>
          set((state) => {
            state.dialogData = { ...state.dialogData, ...data };
          }),

        // Palette
        setPaletteSearch: (query) =>
          set((state) => {
            state.paletteSearchQuery = query;
          }),

        togglePaletteCategory: (category) =>
          set((state) => {
            const index = state.paletteExpandedCategories.indexOf(category);
            if (index === -1) {
              state.paletteExpandedCategories.push(category);
            } else {
              state.paletteExpandedCategories.splice(index, 1);
            }
          }),

        expandAllCategories: () =>
          set((state) => {
            state.paletteExpandedCategories = [...DEFAULT_CATEGORIES];
          }),

        collapseAllCategories: () =>
          set((state) => {
            state.paletteExpandedCategories = [];
          }),

        // Code preview
        toggleCodePreviewAutoUpdate: () =>
          set((state) => {
            state.codePreviewAutoUpdate = !state.codePreviewAutoUpdate;
          }),

        // Theme
        setTheme: (theme) =>
          set((state) => {
            state.theme = theme;
          }),

        // Notifications
        addNotification: (notification) => {
          const id = `notification_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

          set((state) => {
            state.notifications.push({
              ...notification,
              id,
              createdAt: Date.now(),
            });
          });

          // Auto-remove after duration
          const duration = notification.duration ?? 5000;
          if (duration > 0) {
            setTimeout(() => {
              get().removeNotification(id);
            }, duration);
          }

          return id;
        },

        removeNotification: (id) =>
          set((state) => {
            state.notifications = state.notifications.filter((n) => n.id !== id);
          }),

        clearNotifications: () =>
          set((state) => {
            state.notifications = [];
          }),

        // Execution
        setExecutionResult: (result) =>
          set((state) => {
            state.executionResult = result;
            if (result) {
              state.rightPanelTab = 'results';
              state.rightPanelOpen = true;
            }
          }),

        setIsExecuting: (isExecuting) =>
          set((state) => {
            state.isExecuting = isExecuting;
          }),

        clearExecutionResult: () =>
          set((state) => {
            state.executionResult = null;
          }),

        // Reset
        reset: () => set(initialState),
      })),
      {
        name: 'workflow-editor-ui',
        partialize: (state) => ({
          leftPanelOpen: state.leftPanelOpen,
          rightPanelOpen: state.rightPanelOpen,
          leftPanelWidth: state.leftPanelWidth,
          rightPanelWidth: state.rightPanelWidth,
          rightPanelTab: state.rightPanelTab,
          paletteExpandedCategories: state.paletteExpandedCategories,
          codePreviewAutoUpdate: state.codePreviewAutoUpdate,
          theme: state.theme,
        }),
      }
    ),
    { name: 'UIStore' }
  )
);
