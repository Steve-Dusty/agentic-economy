'use client';

/**
 * Composio Connection Manager
 *
 * Modal component for managing OAuth connections to external services
 * like Gmail, Slack, Notion, etc. via Composio SDK.
 * Also manages Composio triggers for connected services.
 */

import React, { useEffect, useCallback, useState } from 'react';
import { X, RefreshCw, ExternalLink, Check, AlertCircle, Loader2, Zap, Trash2, Power, PowerOff, Plus, ChevronDown } from 'lucide-react';
import { clsx } from 'clsx';
import { useComposioStore, useUIStore, type TriggerType, type TriggerInstance } from '@workflow-editor/state';

type TabType = 'services' | 'triggers';

/**
 * Available toolkits with their metadata
 */
const TOOLKITS = [
  { id: 'GMAIL', name: 'Gmail', icon: '📧', description: 'Send and read emails' },
  { id: 'GOOGLECALENDAR', name: 'Google Calendar', icon: '📅', description: 'Manage calendar events' },
  { id: 'GOOGLEDRIVE', name: 'Google Drive', icon: '📁', description: 'Access files and folders' },
  { id: 'GOOGLEDOCS', name: 'Google Docs', icon: '📄', description: 'Create and edit documents' },
  { id: 'GOOGLESHEETS', name: 'Google Sheets', icon: '📊', description: 'Work with spreadsheets' },
  { id: 'SLACK', name: 'Slack', icon: '💬', description: 'Send messages and manage channels' },
  { id: 'NOTION', name: 'Notion', icon: '📝', description: 'Create pages and databases' },
  { id: 'GITHUB', name: 'GitHub', icon: '🐙', description: 'Manage repositories and issues' },
  { id: 'OUTLOOK', name: 'Outlook', icon: '📬', description: 'Microsoft email and calendar' },
];

/**
 * Connection status badge
 */
function StatusBadge({ status }: { status: 'ACTIVE' | 'INITIATED' | 'EXPIRED' | 'none' }) {
  if (status === 'ACTIVE') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
        <Check className="w-3 h-3" />
        Connected
      </span>
    );
  }

  if (status === 'EXPIRED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">
        <AlertCircle className="w-3 h-3" />
        Expired
      </span>
    );
  }

  if (status === 'INITIATED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
        <Loader2 className="w-3 h-3 animate-spin" />
        Pending
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-muted text-muted-foreground">
      Not connected
    </span>
  );
}

/**
 * Trigger card component
 */
function TriggerCard({
  trigger,
  toolkitInfo,
  onToggle,
  onDelete,
  isDeleting,
}: {
  trigger: TriggerInstance;
  toolkitInfo?: typeof TOOLKITS[number];
  onToggle: (enable: boolean) => void;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const isDisabled = trigger.disabledAt !== null;

  return (
    <div
      className={clsx(
        'flex flex-col p-4 rounded-lg border transition-colors',
        isDisabled
          ? 'border-border bg-muted/30'
          : 'border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-900/10'
      )}
    >
      <div className="flex items-start gap-3">
        <div className="text-2xl">{toolkitInfo?.icon || '⚡'}</div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm">{trigger.triggerName}</div>
          <div className="text-xs text-muted-foreground truncate">
            {toolkitInfo?.name || 'Unknown service'}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
        <span
          className={clsx(
            'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full',
            isDisabled
              ? 'bg-muted text-muted-foreground'
              : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
          )}
        >
          {isDisabled ? (
            <>
              <PowerOff className="w-3 h-3" />
              Disabled
            </>
          ) : (
            <>
              <Power className="w-3 h-3" />
              Active
            </>
          )}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onToggle(!isDisabled)}
            className={clsx(
              'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md transition-colors',
              'bg-secondary text-secondary-foreground hover:bg-secondary/80'
            )}
            title={isDisabled ? 'Enable trigger' : 'Disable trigger'}
          >
            {isDisabled ? <Power className="w-3 h-3" /> : <PowerOff className="w-3 h-3" />}
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className={clsx(
              'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-md transition-colors',
              'bg-destructive/10 text-destructive hover:bg-destructive/20',
              isDeleting && 'opacity-50 cursor-not-allowed'
            )}
            title="Delete trigger"
          >
            {isDeleting ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Trash2 className="w-3 h-3" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Trigger type selector component
 */
function TriggerTypeSelector({
  triggerTypes,
  toolkits,
  onCreate,
  isCreating,
}: {
  triggerTypes: Record<string, TriggerType[]>;
  toolkits: typeof TOOLKITS;
  onCreate: (triggerSlug: string) => void;
  isCreating: boolean;
}) {
  const [selectedToolkit, setSelectedToolkit] = useState<string | null>(null);
  const [selectedTrigger, setSelectedTrigger] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const availableToolkits = toolkits.filter(
    (tk) => (triggerTypes[tk.id] || []).length > 0
  );

  const handleCreate = () => {
    if (selectedTrigger) {
      onCreate(selectedTrigger);
      setSelectedToolkit(null);
      setSelectedTrigger(null);
      setIsOpen(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
      >
        <Plus className="w-4 h-4" />
        Add Trigger
      </button>
    );
  }

  return (
    <div className="p-4 rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-sm">Create New Trigger</h4>
        <button
          onClick={() => {
            setIsOpen(false);
            setSelectedToolkit(null);
            setSelectedTrigger(null);
          }}
          className="p-1 rounded hover:bg-accent"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Service selector */}
      <div className="mb-3">
        <label className="block text-xs text-muted-foreground mb-1">
          Select Service
        </label>
        <div className="relative">
          <select
            value={selectedToolkit || ''}
            onChange={(e) => {
              setSelectedToolkit(e.target.value || null);
              setSelectedTrigger(null);
            }}
            className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background appearance-none pr-8"
          >
            <option value="">Choose a service...</option>
            {availableToolkits.map((tk) => (
              <option key={tk.id} value={tk.id}>
                {tk.icon} {tk.name} ({(triggerTypes[tk.id] || []).length} triggers)
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
        </div>
      </div>

      {/* Trigger type selector */}
      {selectedToolkit && (
        <div className="mb-3">
          <label className="block text-xs text-muted-foreground mb-1">
            Select Trigger Type
          </label>
          <div className="relative">
            <select
              value={selectedTrigger || ''}
              onChange={(e) => setSelectedTrigger(e.target.value || null)}
              className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background appearance-none pr-8"
            >
              <option value="">Choose a trigger...</option>
              {(triggerTypes[selectedToolkit] || []).map((tt) => (
                <option key={tt.slug} value={tt.slug}>
                  {tt.name}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          </div>
          {selectedTrigger && (
            <p className="mt-2 text-xs text-muted-foreground">
              {triggerTypes[selectedToolkit]?.find((t) => t.slug === selectedTrigger)?.description}
            </p>
          )}
        </div>
      )}

      {/* Create button */}
      <button
        onClick={handleCreate}
        disabled={!selectedTrigger || isCreating}
        className={clsx(
          'w-full inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors',
          'bg-primary text-primary-foreground hover:bg-primary/90',
          (!selectedTrigger || isCreating) && 'opacity-50 cursor-not-allowed'
        )}
      >
        {isCreating ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Creating...
          </>
        ) : (
          <>
            <Zap className="w-4 h-4" />
            Create Trigger
          </>
        )}
      </button>
    </div>
  );
}

/**
 * Toolkit card component
 */
function ToolkitCard({
  toolkit,
  status,
  isConnecting,
  onConnect,
}: {
  toolkit: typeof TOOLKITS[number];
  status: 'ACTIVE' | 'INITIATED' | 'EXPIRED' | 'none';
  isConnecting: boolean;
  onConnect: () => void;
}) {
  return (
    <div
      className={clsx(
        'flex flex-col p-4 rounded-lg border transition-colors',
        status === 'ACTIVE'
          ? 'border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-900/10'
          : 'border-border bg-card hover:bg-accent/50'
      )}
    >
      <div className="flex items-start gap-3">
        <div className="text-2xl">{toolkit.icon}</div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm">{toolkit.name}</div>
          <div className="text-xs text-muted-foreground truncate">
            {toolkit.description}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
        <StatusBadge status={status} />
        <button
          onClick={onConnect}
          disabled={isConnecting || status === 'INITIATED'}
          className={clsx(
            'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
            status === 'ACTIVE'
              ? 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              : 'bg-primary text-primary-foreground hover:bg-primary/90',
            (isConnecting || status === 'INITIATED') && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isConnecting ? (
            <>
              <Loader2 className="w-3 h-3 animate-spin" />
              Connecting...
            </>
          ) : status === 'ACTIVE' ? (
            <>
              <RefreshCw className="w-3 h-3" />
              Reconnect
            </>
          ) : (
            <>
              <ExternalLink className="w-3 h-3" />
              Connect
            </>
          )}
        </button>
      </div>
    </div>
  );
}

/**
 * Composio Connection Manager component
 */
export function ComposioConnectionManager() {
  const activeDialog = useUIStore((state) => state.activeDialog);
  const closeDialog = useUIStore((state) => state.closeDialog);
  const addNotification = useUIStore((state) => state.addNotification);

  const connectedAccounts = useComposioStore((state) => state.connectedAccounts);
  const isLoadingAccounts = useComposioStore((state) => state.isLoadingAccounts);
  const pendingAuth = useComposioStore((state) => state.pendingAuth);
  const fetchConnectedAccounts = useComposioStore((state) => state.fetchConnectedAccounts);
  const initiateAuth = useComposioStore((state) => state.initiateAuth);
  const isToolkitConnected = useComposioStore((state) => state.isToolkitConnected);

  // Trigger state
  const triggerTypes = useComposioStore((state) => state.triggerTypes);
  const activeTriggers = useComposioStore((state) => state.activeTriggers);
  const isLoadingTriggerTypes = useComposioStore((state) => state.isLoadingTriggerTypes);
  const isLoadingTriggers = useComposioStore((state) => state.isLoadingTriggers);
  const fetchTriggerTypes = useComposioStore((state) => state.fetchTriggerTypes);
  const fetchActiveTriggers = useComposioStore((state) => state.fetchActiveTriggers);
  const createTrigger = useComposioStore((state) => state.createTrigger);
  const deleteTrigger = useComposioStore((state) => state.deleteTrigger);
  const toggleTriggerStatus = useComposioStore((state) => state.toggleTriggerStatus);

  const [activeTab, setActiveTab] = useState<TabType>('services');
  const [isCreatingTrigger, setIsCreatingTrigger] = useState(false);
  const [deletingTriggerId, setDeletingTriggerId] = useState<string | null>(null);

  const isOpen = activeDialog === 'connections';

  // Fetch connected accounts and triggers when dialog opens
  useEffect(() => {
    if (isOpen) {
      fetchConnectedAccounts();
      fetchActiveTriggers();
      // Fetch trigger types for all toolkits
      const toolkitSlugs = TOOLKITS.map((tk) => tk.id.toLowerCase());
      fetchTriggerTypes(toolkitSlugs);
    }
  }, [isOpen, fetchConnectedAccounts, fetchActiveTriggers, fetchTriggerTypes]);

  // Get status for a toolkit
  const getStatus = useCallback(
    (toolkitId: string): 'ACTIVE' | 'INITIATED' | 'EXPIRED' | 'none' => {
      const account = connectedAccounts.find(
        (acc) => acc.appName?.toUpperCase() === toolkitId.toUpperCase()
      );
      return account?.status || 'none';
    },
    [connectedAccounts]
  );

  // Handle connect click
  const handleConnect = useCallback(
    async (toolkitId: string) => {
      try {
        const redirectUrl = await initiateAuth(toolkitId);

        if (redirectUrl) {
          // Open OAuth popup
          const popup = window.open(
            redirectUrl,
            'composio-auth',
            'width=600,height=700,scrollbars=yes'
          );

          // Poll for popup close and refresh
          const pollTimer = setInterval(() => {
            if (popup?.closed) {
              clearInterval(pollTimer);
              fetchConnectedAccounts();
            }
          }, 1000);

          // Cleanup after 5 minutes
          setTimeout(() => {
            clearInterval(pollTimer);
          }, 5 * 60 * 1000);
        }
      } catch (error) {
        addNotification({
          type: 'error',
          title: 'Connection Failed',
          message: error instanceof Error ? error.message : 'Failed to initiate authentication',
        });
      }
    },
    [initiateAuth, fetchConnectedAccounts, addNotification]
  );

  // Handle create trigger
  const handleCreateTrigger = useCallback(
    async (triggerSlug: string) => {
      setIsCreatingTrigger(true);
      try {
        const triggerId = await createTrigger(triggerSlug);
        if (triggerId) {
          addNotification({
            type: 'success',
            title: 'Trigger Created',
            message: `Trigger ${triggerSlug} has been created successfully`,
          });
        }
      } catch (error) {
        addNotification({
          type: 'error',
          title: 'Failed to Create Trigger',
          message: error instanceof Error ? error.message : 'Unknown error',
        });
      } finally {
        setIsCreatingTrigger(false);
      }
    },
    [createTrigger, addNotification]
  );

  // Handle delete trigger
  const handleDeleteTrigger = useCallback(
    async (triggerId: string) => {
      setDeletingTriggerId(triggerId);
      try {
        const success = await deleteTrigger(triggerId);
        if (success) {
          addNotification({
            type: 'success',
            title: 'Trigger Deleted',
            message: 'Trigger has been deleted successfully',
          });
        }
      } catch (error) {
        addNotification({
          type: 'error',
          title: 'Failed to Delete Trigger',
          message: error instanceof Error ? error.message : 'Unknown error',
        });
      } finally {
        setDeletingTriggerId(null);
      }
    },
    [deleteTrigger, addNotification]
  );

  // Handle toggle trigger status
  const handleToggleTrigger = useCallback(
    async (triggerId: string, enable: boolean) => {
      try {
        const success = await toggleTriggerStatus(triggerId, enable);
        if (success) {
          addNotification({
            type: 'success',
            title: enable ? 'Trigger Enabled' : 'Trigger Disabled',
            message: `Trigger has been ${enable ? 'enabled' : 'disabled'} successfully`,
          });
        }
      } catch (error) {
        addNotification({
          type: 'error',
          title: 'Failed to Update Trigger',
          message: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    },
    [toggleTriggerStatus, addNotification]
  );

  // Get toolkit info by trigger's connected account
  const getToolkitForTrigger = useCallback(
    (trigger: TriggerInstance) => {
      const account = connectedAccounts.find(
        (acc) => acc.id === trigger.connectedAccountId
      );
      if (!account) return undefined;
      return TOOLKITS.find(
        (tk) => tk.id.toUpperCase() === account.appName?.toUpperCase()
      );
    },
    [connectedAccounts]
  );

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        closeDialog();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, closeDialog]);

  if (!isOpen) return null;

  const connectedCount = connectedAccounts.filter((acc) => acc.status === 'ACTIVE').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={closeDialog}
      />

      {/* Modal */}
      <div className="relative bg-card rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h2 className="text-lg font-semibold">Service Connections</h2>
            <p className="text-sm text-muted-foreground">
              Connect your accounts to use them in workflows
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => fetchConnectedAccounts()}
              disabled={isLoadingAccounts}
              className={clsx(
                'p-2 rounded-md hover:bg-accent transition-colors',
                isLoadingAccounts && 'animate-spin'
              )}
              title="Refresh connections"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={closeDialog}
              className="p-2 rounded-md hover:bg-accent transition-colors"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="px-6 py-2 bg-muted/50 border-b border-border flex items-center gap-4">
          <button
            onClick={() => setActiveTab('services')}
            className={clsx(
              'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
              activeTab === 'services'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            Services
            <span className="ml-1.5 text-xs text-muted-foreground">
              {connectedCount}/{TOOLKITS.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('triggers')}
            className={clsx(
              'px-3 py-1.5 text-sm font-medium rounded-md transition-colors inline-flex items-center gap-1.5',
              activeTab === 'triggers'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Zap className="w-3.5 h-3.5" />
            Triggers
            <span className="ml-1 text-xs text-muted-foreground">
              {activeTriggers.filter((t) => !t.disabledAt).length}
            </span>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'services' ? (
            // Services Tab
            isLoadingAccounts && connectedAccounts.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {TOOLKITS.map((toolkit) => (
                  <ToolkitCard
                    key={toolkit.id}
                    toolkit={toolkit}
                    status={getStatus(toolkit.id)}
                    isConnecting={pendingAuth === toolkit.id}
                    onConnect={() => handleConnect(toolkit.id)}
                  />
                ))}
              </div>
            )
          ) : (
            // Triggers Tab
            <div className="space-y-6">
              {/* Create trigger section */}
              {connectedCount > 0 && (
                <TriggerTypeSelector
                  triggerTypes={triggerTypes}
                  toolkits={TOOLKITS.filter((tk) => isToolkitConnected(tk.id))}
                  onCreate={handleCreateTrigger}
                  isCreating={isCreatingTrigger}
                />
              )}

              {/* Active triggers list */}
              {isLoadingTriggers && activeTriggers.length === 0 ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              ) : activeTriggers.length === 0 ? (
                <div className="text-center py-12">
                  <Zap className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
                  <h3 className="font-medium text-muted-foreground mb-2">
                    No triggers configured
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {connectedCount > 0
                      ? 'Create a trigger to receive events from your connected services.'
                      : 'Connect a service first to create triggers.'}
                  </p>
                </div>
              ) : (
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">
                    Active Triggers ({activeTriggers.length})
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {activeTriggers.map((trigger) => (
                      <TriggerCard
                        key={trigger.id}
                        trigger={trigger}
                        toolkitInfo={getToolkitForTrigger(trigger)}
                        onToggle={(enable) => handleToggleTrigger(trigger.id, enable)}
                        onDelete={() => handleDeleteTrigger(trigger.id)}
                        isDeleting={deletingTriggerId === trigger.id}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-border text-xs text-muted-foreground">
          {activeTab === 'services' ? (
            'Connections are stored securely via Composio. Each service requires separate authorization.'
          ) : (
            'Triggers listen for events from your connected services. Configure your webhook URL in Composio to receive events.'
          )}
        </div>
      </div>
    </div>
  );
}
