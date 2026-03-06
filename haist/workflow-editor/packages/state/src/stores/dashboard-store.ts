/**
 * Dashboard state store
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

/**
 * Workflow summary for list display
 */
export interface WorkflowSummary {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  nodeCount: number;
  triggerType?: string;
  isActive?: boolean;
  totalRuns?: number;
  successRuns?: number;
  failedRuns?: number;
  lastRunAt?: string;
}

/**
 * Execution record
 */
export interface ExecutionRecord {
  id: string;
  workflowId: string;
  status: 'running' | 'completed' | 'failed';
  startedAt: string;
  completedAt?: string;
  durationMs?: number;
  error?: string;
  triggerSource?: string;
}

/**
 * View mode for the dashboard
 */
export type ViewMode = 'grid' | 'table';

/**
 * Sort options
 */
export type SortBy = 'name' | 'updatedAt' | 'createdAt' | 'lastRunAt';
export type SortOrder = 'asc' | 'desc';

/**
 * Dashboard state
 */
export interface DashboardState {
  // Workflows list
  workflows: WorkflowSummary[];
  isLoading: boolean;
  error: string | null;

  // View settings
  viewMode: ViewMode;
  searchQuery: string;
  sortBy: SortBy;
  sortOrder: SortOrder;

  // Selected workflow for operations
  selectedWorkflowId: string | null;

  // Modal states
  isCreateModalOpen: boolean;
  isDeleteModalOpen: boolean;
  isExecutionHistoryOpen: boolean;

  // Execution state
  executingWorkflowId: string | null;
  executionHistory: ExecutionRecord[];
  isLoadingHistory: boolean;
}

/**
 * Dashboard actions
 */
export interface DashboardActions {
  // Fetch workflows
  fetchWorkflows: () => Promise<void>;

  // CRUD operations
  createWorkflow: (name: string, description?: string) => Promise<string | null>;
  deleteWorkflow: (id: string) => Promise<boolean>;
  duplicateWorkflow: (id: string) => Promise<string | null>;

  // Execute
  executeWorkflow: (id: string) => Promise<boolean>;

  // Execution history
  fetchExecutionHistory: (workflowId: string) => Promise<void>;

  // View settings
  setViewMode: (mode: ViewMode) => void;
  setSearchQuery: (query: string) => void;
  setSorting: (sortBy: SortBy, sortOrder: SortOrder) => void;

  // Selection
  setSelectedWorkflow: (id: string | null) => void;

  // Modals
  openCreateModal: () => void;
  closeCreateModal: () => void;
  openDeleteModal: (id: string) => void;
  closeDeleteModal: () => void;
  openExecutionHistory: (id: string) => void;
  closeExecutionHistory: () => void;

  // Reset
  reset: () => void;
}

export type DashboardStore = DashboardState & DashboardActions;

const initialState: DashboardState = {
  workflows: [],
  isLoading: false,
  error: null,
  viewMode: 'grid',
  searchQuery: '',
  sortBy: 'updatedAt',
  sortOrder: 'desc',
  selectedWorkflowId: null,
  isCreateModalOpen: false,
  isDeleteModalOpen: false,
  isExecutionHistoryOpen: false,
  executingWorkflowId: null,
  executionHistory: [],
  isLoadingHistory: false,
};

/**
 * Dashboard state store
 */
export const useDashboardStore = create<DashboardStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        // Fetch workflows
        fetchWorkflows: async () => {
          set((state) => {
            state.isLoading = true;
            state.error = null;
          });

          try {
            const response = await fetch('/api/workflows');
            const data = await response.json();

            if (response.ok) {
              set((state) => {
                state.workflows = data.workflows || [];
                state.isLoading = false;
              });
            } else {
              set((state) => {
                state.error = data.error || 'Failed to fetch workflows';
                state.isLoading = false;
              });
            }
          } catch (error) {
            set((state) => {
              state.error = error instanceof Error ? error.message : 'Network error';
              state.isLoading = false;
            });
          }
        },

        // Create workflow
        createWorkflow: async (name, description) => {
          try {
            const response = await fetch('/api/workflows', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name, description }),
            });

            const data = await response.json();

            if (response.ok && data.id) {
              get().fetchWorkflows();
              return data.id;
            }
            return null;
          } catch {
            return null;
          }
        },

        // Delete workflow
        deleteWorkflow: async (id) => {
          try {
            const response = await fetch(`/api/workflows/${id}`, {
              method: 'DELETE',
            });

            if (response.ok) {
              set((state) => {
                state.workflows = state.workflows.filter((w) => w.id !== id);
                state.isDeleteModalOpen = false;
                state.selectedWorkflowId = null;
              });
              return true;
            }
            return false;
          } catch {
            return false;
          }
        },

        // Duplicate workflow
        duplicateWorkflow: async (id) => {
          try {
            const response = await fetch(`/api/workflows/${id}/duplicate`, {
              method: 'POST',
            });

            const data = await response.json();

            if (response.ok && data.id) {
              get().fetchWorkflows();
              return data.id;
            }
            return null;
          } catch {
            return null;
          }
        },

        // Execute workflow
        executeWorkflow: async (id) => {
          set((state) => {
            state.executingWorkflowId = id;
          });

          try {
            const response = await fetch(`/api/workflows/${id}/execute`, {
              method: 'POST',
            });

            set((state) => {
              state.executingWorkflowId = null;
            });

            if (response.ok) {
              // Refresh workflows to get updated stats
              get().fetchWorkflows();
              return true;
            }
            return false;
          } catch {
            set((state) => {
              state.executingWorkflowId = null;
            });
            return false;
          }
        },

        // Fetch execution history
        fetchExecutionHistory: async (workflowId) => {
          set((state) => {
            state.isLoadingHistory = true;
          });

          try {
            const response = await fetch(`/api/workflows/${workflowId}/executions`);
            const data = await response.json();

            if (response.ok) {
              set((state) => {
                state.executionHistory = data.executions || [];
                state.isLoadingHistory = false;
              });
            } else {
              set((state) => {
                state.executionHistory = [];
                state.isLoadingHistory = false;
              });
            }
          } catch {
            set((state) => {
              state.executionHistory = [];
              state.isLoadingHistory = false;
            });
          }
        },

        // View settings
        setViewMode: (mode) =>
          set((state) => {
            state.viewMode = mode;
          }),

        setSearchQuery: (query) =>
          set((state) => {
            state.searchQuery = query;
          }),

        setSorting: (sortBy, sortOrder) =>
          set((state) => {
            state.sortBy = sortBy;
            state.sortOrder = sortOrder;
          }),

        // Selection
        setSelectedWorkflow: (id) =>
          set((state) => {
            state.selectedWorkflowId = id;
          }),

        // Modals
        openCreateModal: () =>
          set((state) => {
            state.isCreateModalOpen = true;
          }),

        closeCreateModal: () =>
          set((state) => {
            state.isCreateModalOpen = false;
          }),

        openDeleteModal: (id) =>
          set((state) => {
            state.selectedWorkflowId = id;
            state.isDeleteModalOpen = true;
          }),

        closeDeleteModal: () =>
          set((state) => {
            state.isDeleteModalOpen = false;
            state.selectedWorkflowId = null;
          }),

        openExecutionHistory: (id) =>
          set((state) => {
            state.selectedWorkflowId = id;
            state.isExecutionHistoryOpen = true;
          }),

        closeExecutionHistory: () =>
          set((state) => {
            state.isExecutionHistoryOpen = false;
            state.selectedWorkflowId = null;
            state.executionHistory = [];
          }),

        // Reset
        reset: () => set(initialState),
      })),
      {
        name: 'workflow-dashboard',
        partialize: (state) => ({
          viewMode: state.viewMode,
          sortBy: state.sortBy,
          sortOrder: state.sortOrder,
        }),
      }
    ),
    { name: 'DashboardStore' }
  )
);
