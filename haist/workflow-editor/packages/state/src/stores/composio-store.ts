/**
 * Composio state store
 *
 * Manages connected accounts, available tools, and connection status
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

/**
 * Connected account from Composio
 */
export interface ConnectedAccount {
  id: string;
  appName: string;
  status: 'ACTIVE' | 'INITIATED' | 'EXPIRED';
  connectedAt?: string;
  lastAccessedAt?: string;
}

/**
 * Tool input schema property (structured)
 */
export interface ToolInputSchemaProperty {
  type: string;
  description?: string;
  required?: boolean;
  enum?: string[];
  default?: unknown;
  properties?: Record<string, ToolInputSchemaProperty>;
  items?: ToolInputSchemaProperty;
}

/**
 * Structured tool input schema
 */
export interface ToolInputSchema {
  properties: Record<string, ToolInputSchemaProperty>;
  required?: string[];
}

/**
 * Composio tool definition
 */
export interface ComposioToolInfo {
  name: string;
  description: string;
  toolkit: string;
  /** Input parameters schema string (legacy, for AI agent to know what params to generate) */
  inputs?: string;
  /** Structured input schema (for dynamic AI instructions) */
  inputSchema?: ToolInputSchema;
}

/**
 * Toolkit with its tools
 */
export interface ToolkitInfo {
  id: string;
  name: string;
  icon: string;
  isConnected: boolean;
  tools: ComposioToolInfo[];
}

/**
 * Trigger type from Composio
 */
export interface TriggerType {
  slug: string;
  name: string;
  description: string;
  instructions?: string;
  toolkit: {
    slug: string;
    name: string;
    logo?: string;
  };
  config: Record<string, unknown>;
  payload: Record<string, unknown>;
  version?: string;
}

/**
 * Active trigger instance
 */
export interface TriggerInstance {
  id: string;
  triggerName: string;
  triggerConfig: Record<string, unknown>;
  connectedAccountId: string;
  state: Record<string, unknown>;
  disabledAt: string | null;
  updatedAt: string;
  triggerData?: string;
  uuid?: string;
}

/**
 * Composio store state
 */
export interface ComposioState {
  // Connection state
  connectedAccounts: ConnectedAccount[];
  isLoadingAccounts: boolean;
  accountsError: string | null;

  // Tools state
  availableTools: Record<string, ComposioToolInfo[]>;
  isLoadingTools: boolean;
  toolsError: string | null;

  // Auth state
  pendingAuth: string | null; // toolkit name being authenticated

  // Triggers state
  triggerTypes: Record<string, TriggerType[]>; // keyed by toolkit slug
  activeTriggers: TriggerInstance[];
  isLoadingTriggerTypes: boolean;
  isLoadingTriggers: boolean;
  triggersError: string | null;
}

/**
 * Composio store actions
 */
export interface ComposioActions {
  // Account management
  fetchConnectedAccounts: () => Promise<void>;
  setConnectedAccounts: (accounts: ConnectedAccount[]) => void;

  // Authentication
  initiateAuth: (toolkit: string) => Promise<string | null>;
  setPendingAuth: (toolkit: string | null) => void;
  onAuthComplete: (toolkit: string, success: boolean) => void;

  // Tools
  fetchTools: (toolkits?: string[]) => Promise<void>;
  setAvailableTools: (
    toolkit: string,
    tools: ComposioToolInfo[]
  ) => void;

  // Status helpers
  isToolkitConnected: (toolkit: string) => boolean;
  getToolsForToolkit: (toolkit: string) => ComposioToolInfo[];
  getConnectedToolkits: () => string[];

  // Triggers
  fetchTriggerTypes: (toolkits?: string[]) => Promise<void>;
  fetchActiveTriggers: () => Promise<void>;
  createTrigger: (
    triggerSlug: string,
    connectedAccountId?: string,
    triggerConfig?: Record<string, unknown>
  ) => Promise<string | null>;
  deleteTrigger: (triggerId: string) => Promise<boolean>;
  toggleTriggerStatus: (triggerId: string, enable: boolean) => Promise<boolean>;
  getTriggerTypesForToolkit: (toolkit: string) => TriggerType[];
  getTriggersForAccount: (accountId: string) => TriggerInstance[];

  // Reset
  reset: () => void;
}

const initialState: ComposioState = {
  connectedAccounts: [],
  isLoadingAccounts: false,
  accountsError: null,
  availableTools: {},
  isLoadingTools: false,
  toolsError: null,
  pendingAuth: null,
  triggerTypes: {},
  activeTriggers: [],
  isLoadingTriggerTypes: false,
  isLoadingTriggers: false,
  triggersError: null,
};

/**
 * Composio store
 */
export const useComposioStore = create<ComposioState & ComposioActions>()(
  devtools(
    persist(
      immer((set, get) => ({
        ...initialState,

        /**
         * Fetch connected accounts from API
         */
        fetchConnectedAccounts: async () => {
          set((state) => {
            state.isLoadingAccounts = true;
            state.accountsError = null;
          });

          try {
            const response = await fetch(`/api/composio/connected-accounts`);
            const data = await response.json();

            if (response.ok) {
              set((state) => {
                state.connectedAccounts = data.accounts || [];
                state.isLoadingAccounts = false;
              });
            } else {
              set((state) => {
                state.accountsError = data.error || 'Failed to fetch accounts';
                state.isLoadingAccounts = false;
              });
            }
          } catch (error) {
            set((state) => {
              state.accountsError =
                error instanceof Error ? error.message : 'Network error';
              state.isLoadingAccounts = false;
            });
          }
        },

        /**
         * Set connected accounts directly
         */
        setConnectedAccounts: (accounts) => {
          set((state) => {
            state.connectedAccounts = accounts;
          });
        },

        /**
         * Initiate OAuth for a toolkit
         */
        initiateAuth: async (toolkit) => {
          set((state) => {
            state.pendingAuth = toolkit;
          });

          try {
            const response = await fetch(`/api/composio/auth/${toolkit}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                redirectUrl: `${window.location.origin}/api/composio/callback`,
              }),
            });

            const data = await response.json();

            if (response.ok && data.authRequest?.redirectUrl) {
              return data.authRequest.redirectUrl;
            } else if (data.authRequest?.connectionStatus === 'ACTIVE') {
              // Already connected
              get().fetchConnectedAccounts();
              set((state) => {
                state.pendingAuth = null;
              });
              return null;
            } else {
              set((state) => {
                state.pendingAuth = null;
              });
              throw new Error(data.error || 'Failed to initiate auth');
            }
          } catch (error) {
            set((state) => {
              state.pendingAuth = null;
            });
            throw error;
          }
        },

        /**
         * Set pending auth toolkit
         */
        setPendingAuth: (toolkit) => {
          set((state) => {
            state.pendingAuth = toolkit;
          });
        },

        /**
         * Handle auth completion
         */
        onAuthComplete: (toolkit, success) => {
          set((state) => {
            state.pendingAuth = null;
          });

          if (success) {
            // Refresh connected accounts
            get().fetchConnectedAccounts();
            // Fetch tools for the new toolkit
            get().fetchTools([toolkit]);
          }
        },

        /**
         * Fetch tools for toolkits
         */
        fetchTools: async (toolkits) => {
          set((state) => {
            state.isLoadingTools = true;
            state.toolsError = null;
          });

          try {
            const queryToolkits = toolkits?.join(',') || '';
            const url = queryToolkits
              ? `/api/composio/tools?toolkits=${queryToolkits}`
              : `/api/composio/tools`;

            const response = await fetch(url);
            const data = await response.json();

            if (response.ok) {
              // Group tools by toolkit
              const toolsByToolkit: Record<string, ComposioToolInfo[]> = {};

              for (const tool of data.tools || []) {
                const toolkit =
                  tool.toolkit ||
                  tool.name.split('_')[0]?.toUpperCase() ||
                  'OTHER';
                if (!toolsByToolkit[toolkit]) {
                  toolsByToolkit[toolkit] = [];
                }
                toolsByToolkit[toolkit].push({
                  name: tool.name,
                  description: tool.description,
                  toolkit,
                  inputs: tool.inputs,
                  inputSchema: tool.inputSchema,
                });
              }

              set((state) => {
                // Merge with existing tools
                for (const [toolkit, tools] of Object.entries(toolsByToolkit)) {
                  state.availableTools[toolkit] = tools;
                }
                state.isLoadingTools = false;
              });
            } else {
              set((state) => {
                state.toolsError = data.error || 'Failed to fetch tools';
                state.isLoadingTools = false;
              });
            }
          } catch (error) {
            set((state) => {
              state.toolsError =
                error instanceof Error ? error.message : 'Network error';
              state.isLoadingTools = false;
            });
          }
        },

        /**
         * Set tools for a toolkit
         */
        setAvailableTools: (toolkit, tools) => {
          set((state) => {
            state.availableTools[toolkit] = tools;
          });
        },

        /**
         * Check if a toolkit is connected
         */
        isToolkitConnected: (toolkit) => {
          const accounts = get().connectedAccounts;
          return accounts.some(
            (account) =>
              account.appName?.toUpperCase() === toolkit.toUpperCase() &&
              account.status === 'ACTIVE'
          );
        },

        /**
         * Get tools for a toolkit
         */
        getToolsForToolkit: (toolkit) => {
          return get().availableTools[toolkit.toUpperCase()] || [];
        },

        /**
         * Get list of connected toolkit names
         */
        getConnectedToolkits: () => {
          const accounts = get().connectedAccounts;
          return accounts
            .filter((account) => account.status === 'ACTIVE')
            .map((account) => account.appName?.toUpperCase() || '')
            .filter(Boolean);
        },

        // ============================================================
        // TRIGGER ACTIONS
        // ============================================================

        /**
         * Fetch available trigger types for toolkits
         */
        fetchTriggerTypes: async (toolkits) => {
          set((state) => {
            state.isLoadingTriggerTypes = true;
            state.triggersError = null;
          });

          try {
            const queryToolkits = toolkits?.join(',') || '';
            const url = queryToolkits
              ? `/api/composio/triggers/types?toolkits=${queryToolkits}`
              : `/api/composio/triggers/types`;

            const response = await fetch(url);
            const data = await response.json();

            if (response.ok) {
              // Group trigger types by toolkit
              const typesByToolkit: Record<string, TriggerType[]> = {};

              for (const triggerType of data.triggerTypes || []) {
                const toolkit = triggerType.toolkit?.slug?.toUpperCase() || 'OTHER';
                if (!typesByToolkit[toolkit]) {
                  typesByToolkit[toolkit] = [];
                }
                typesByToolkit[toolkit].push(triggerType);
              }

              set((state) => {
                // Merge with existing trigger types
                for (const [toolkit, types] of Object.entries(typesByToolkit)) {
                  state.triggerTypes[toolkit] = types;
                }
                state.isLoadingTriggerTypes = false;
              });
            } else {
              set((state) => {
                state.triggersError = data.error || 'Failed to fetch trigger types';
                state.isLoadingTriggerTypes = false;
              });
            }
          } catch (error) {
            set((state) => {
              state.triggersError =
                error instanceof Error ? error.message : 'Network error';
              state.isLoadingTriggerTypes = false;
            });
          }
        },

        /**
         * Fetch user's active triggers
         */
        fetchActiveTriggers: async () => {
          set((state) => {
            state.isLoadingTriggers = true;
            state.triggersError = null;
          });

          try {
            const response = await fetch('/api/composio/triggers?showDisabled=true');
            const data = await response.json();

            if (response.ok) {
              set((state) => {
                state.activeTriggers = data.triggers || [];
                state.isLoadingTriggers = false;
              });
            } else {
              set((state) => {
                state.triggersError = data.error || 'Failed to fetch triggers';
                state.isLoadingTriggers = false;
              });
            }
          } catch (error) {
            set((state) => {
              state.triggersError =
                error instanceof Error ? error.message : 'Network error';
              state.isLoadingTriggers = false;
            });
          }
        },

        /**
         * Create a new trigger
         */
        createTrigger: async (triggerSlug, connectedAccountId, triggerConfig) => {
          try {
            const response = await fetch('/api/composio/triggers', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                triggerSlug,
                connectedAccountId,
                triggerConfig,
              }),
            });

            const data = await response.json();

            if (response.ok && data.triggerId) {
              // Refresh active triggers
              get().fetchActiveTriggers();
              return data.triggerId;
            } else {
              throw new Error(data.error || 'Failed to create trigger');
            }
          } catch (error) {
            set((state) => {
              state.triggersError =
                error instanceof Error ? error.message : 'Failed to create trigger';
            });
            return null;
          }
        },

        /**
         * Delete a trigger
         */
        deleteTrigger: async (triggerId) => {
          try {
            const response = await fetch(`/api/composio/triggers/${triggerId}`, {
              method: 'DELETE',
            });

            const data = await response.json();

            if (response.ok && data.success) {
              // Remove from local state
              set((state) => {
                state.activeTriggers = state.activeTriggers.filter(
                  (t) => t.id !== triggerId
                );
              });
              return true;
            } else {
              throw new Error(data.error || 'Failed to delete trigger');
            }
          } catch (error) {
            set((state) => {
              state.triggersError =
                error instanceof Error ? error.message : 'Failed to delete trigger';
            });
            return false;
          }
        },

        /**
         * Toggle trigger status (enable/disable)
         */
        toggleTriggerStatus: async (triggerId, enable) => {
          try {
            const response = await fetch(`/api/composio/triggers/${triggerId}/status`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                status: enable ? 'enable' : 'disable',
              }),
            });

            const data = await response.json();

            if (response.ok && data.success) {
              // Update local state
              set((state) => {
                const trigger = state.activeTriggers.find((t) => t.id === triggerId);
                if (trigger) {
                  trigger.disabledAt = enable ? null : new Date().toISOString();
                }
              });
              return true;
            } else {
              throw new Error(data.error || 'Failed to update trigger status');
            }
          } catch (error) {
            set((state) => {
              state.triggersError =
                error instanceof Error
                  ? error.message
                  : 'Failed to update trigger status';
            });
            return false;
          }
        },

        /**
         * Get trigger types for a specific toolkit
         */
        getTriggerTypesForToolkit: (toolkit) => {
          return get().triggerTypes[toolkit.toUpperCase()] || [];
        },

        /**
         * Get triggers for a specific connected account
         */
        getTriggersForAccount: (accountId) => {
          return get().activeTriggers.filter(
            (trigger) => trigger.connectedAccountId === accountId
          );
        },

        /**
         * Reset store to initial state
         */
        reset: () => {
          set(initialState);
        },
      })),
      {
        name: 'workflow-editor-composio',
        partialize: (state) => ({
          // Only persist connected accounts
          connectedAccounts: state.connectedAccounts,
        }),
      }
    ),
    { name: 'ComposioStore' }
  )
);
