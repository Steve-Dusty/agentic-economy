"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  Plus,
  Trash2,
  Play,
  Pause,
  ChevronDown,
  ChevronUp,
  Zap,
  AlertCircle,
  Loader2,
  X,
} from "lucide-react";
import { clsx } from "clsx";

interface TriggerType {
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

interface TriggerInstance {
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

interface ConnectedAccount {
  id: string;
  appUniqueId?: string;
  appName?: string;
  status: "ACTIVE" | "INITIATED" | "EXPIRED";
}

// Map toolkit slugs to logo filenames in /public/integrations/
const TOOLKIT_LOGOS: Record<string, string> = {
  // Google Services
  gmail: "gmail.svg",
  googlecalendar: "google-calendar.svg",
  googledrive: "google-drive.svg",
  googledocs: "google-docs.svg",
  googlesheets: "google-sheets.svg",
  googletasks: "google-tasks.svg",
  google_maps: "google-maps.svg",
  googlemeet: "google-meet.svg",
  youtube: "youtube.svg",

  // Microsoft Services
  outlook: "outlook.svg",
  one_drive: "onedrive.svg",
  microsoft_teams: "microsoft-teams.svg",

  // Communication
  slack: "slack.svg",
  discord: "discord.svg",
  telegram: "telegram.svg",

  // Productivity
  notion: "notion.svg",
  linear: "linear.svg",
  jira: "jira.svg",
  asana: "asana.svg",
  calendly: "calendly.svg",
  canvas: "canvas.svg",
  airtable: "airtable.svg",

  // Development
  github: "github.svg",
  figma: "figma.svg",

  // Social
  twitter: "x.svg",
  linkedin: "linkedin.svg",
  reddit: "reddit.svg",

  // Design & Creative
  canva: "canva.svg",

  // Sales & CRM
  salesforce: "salesforce.svg",
  apollo: "apollo-io.svg",

  // Search & Tools
  exa: "exa-color.png",
  firecrawl: "firecrawl.svg",
};

// Helper component for toolkit logo
function ToolkitLogo({
  toolkit,
  size = "md",
}: {
  toolkit: string;
  size?: "sm" | "md" | "lg";
}) {
  const sizeClasses = {
    sm: "w-5 h-5",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  };

  const logo = TOOLKIT_LOGOS[toolkit.toLowerCase()];

  if (logo) {
    return (
      <img
        src={`/integrations/${logo}`}
        alt={toolkit}
        className={clsx(sizeClasses[size], "object-contain")}
      />
    );
  }

  // Fallback to first letter if no logo found
  return (
    <div
      className={clsx(
        sizeClasses[size],
        "rounded bg-muted flex items-center justify-center text-xs font-medium",
      )}>
      {toolkit.charAt(0).toUpperCase()}
    </div>
  );
}

export function TriggersManager() {
  const [triggerTypes, setTriggerTypes] = useState<TriggerType[]>([]);
  const [activeTriggers, setActiveTriggers] = useState<TriggerInstance[]>([]);
  const [connectedAccounts, setConnectedAccounts] = useState<
    ConnectedAccount[]
  >([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTriggerType, setSelectedTriggerType] =
    useState<TriggerType | null>(null);
  const [expandedTriggerId, setExpandedTriggerId] = useState<string | null>(
    null,
  );
  const [expandedToolkit, setExpandedToolkit] = useState<string | null>(null);

  // Fetch connected accounts
  const fetchConnectedAccounts = useCallback(async () => {
    try {
      const res = await fetch("/api/composio/connected-accounts");
      if (!res.ok) throw new Error("Failed to fetch connected accounts");
      const data = await res.json();
      setConnectedAccounts(data.accounts || []);
      return data.accounts || [];
    } catch (err) {
      console.error("Failed to fetch connected accounts:", err);
      return [];
    }
  }, []);

  // Fetch available trigger types
  const fetchTriggerTypes = useCallback(async (toolkitSlugs: string[]) => {
    if (toolkitSlugs.length === 0) {
      setTriggerTypes([]);
      return;
    }

    try {
      const res = await fetch(
        `/api/composio/triggers/types?toolkits=${toolkitSlugs.join(",")}`,
      );
      if (!res.ok) throw new Error("Failed to fetch trigger types");
      const data = await res.json();
      setTriggerTypes(data.triggerTypes || []);
    } catch (err) {
      console.error("Failed to fetch trigger types:", err);
      setTriggerTypes([]);
    }
  }, []);

  // Fetch active triggers
  const fetchActiveTriggers = useCallback(async () => {
    try {
      const res = await fetch("/api/composio/triggers?showDisabled=true");
      if (!res.ok) throw new Error("Failed to fetch triggers");
      const data = await res.json();
      setActiveTriggers(data.triggers || []);
    } catch (err) {
      console.error("Failed to fetch triggers:", err);
      setActiveTriggers([]);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const accounts = await fetchConnectedAccounts();
        const activeAccounts = accounts.filter(
          (acc: ConnectedAccount) => acc.status === "ACTIVE",
        );
        const toolkitSlugs = [
          ...new Set(
            activeAccounts.map((acc: ConnectedAccount) =>
              (acc.appName || "").toLowerCase(),
            ),
          ),
        ].filter(Boolean);

        await Promise.all([
          fetchTriggerTypes(toolkitSlugs as string[]),
          fetchActiveTriggers(),
        ]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [fetchConnectedAccounts, fetchTriggerTypes, fetchActiveTriggers]);

  // Toggle trigger enabled state
  const toggleTrigger = async (trigger: TriggerInstance) => {
    const isEnabled = !trigger.disabledAt;
    try {
      const res = await fetch(`/api/composio/triggers/${trigger.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !isEnabled }),
      });
      if (!res.ok) throw new Error("Failed to update trigger");
      await fetchActiveTriggers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update trigger");
    }
  };

  // Delete trigger
  const deleteTrigger = async (triggerId: string) => {
    if (!confirm("Are you sure you want to delete this trigger?")) return;
    try {
      const res = await fetch(`/api/composio/triggers/${triggerId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete trigger");
      await fetchActiveTriggers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete trigger");
    }
  };

  // Group trigger types by toolkit
  const triggersByToolkit = triggerTypes.reduce(
    (acc, trigger) => {
      const toolkit = trigger.toolkit.slug;
      if (!acc[toolkit]) {
        acc[toolkit] = {
          name: trigger.toolkit.name,
          slug: toolkit,
          triggers: [],
        };
      }
      acc[toolkit].triggers.push(trigger);
      return acc;
    },
    {} as Record<
      string,
      { name: string; slug: string; triggers: TriggerType[] }
    >,
  );

  // Get active connected accounts
  const activeAccounts = connectedAccounts.filter(
    (acc) => acc.status === "ACTIVE",
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error display */}
      {error && (
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-md flex items-center gap-2 text-destructive">
          <AlertCircle className="w-4 h-4" />
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-auto p-1 hover:bg-destructive/20 rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Active Triggers Section */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Active Triggers</h3>
        {activeTriggers.length === 0 ? (
          <div className="text-center py-8 bg-muted/30 rounded-lg border border-dashed">
            <Zap className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-muted-foreground mb-2">
              No triggers configured yet
            </p>
            <p className="text-sm text-muted-foreground">
              Create a trigger below to start receiving events from your
              connected services
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {activeTriggers.map((trigger) => (
              <TriggerCard
                key={trigger.id}
                trigger={trigger}
                isExpanded={expandedTriggerId === trigger.id}
                onToggleExpand={() =>
                  setExpandedTriggerId(
                    expandedTriggerId === trigger.id ? null : trigger.id,
                  )
                }
                onToggleEnabled={() => toggleTrigger(trigger)}
                onDelete={() => deleteTrigger(trigger.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Available Trigger Types Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">Available Triggers</h3>
          {activeAccounts.length === 0 && (
            <span className="text-sm text-muted-foreground">
              Connect services to see available triggers
            </span>
          )}
        </div>

        {activeAccounts.length > 0 && (
          <div className="space-y-2">
            {Object.keys(triggersByToolkit).length === 0 ? (
              <div className="text-center py-8 bg-muted/30 rounded-lg border border-dashed">
                <p className="text-muted-foreground">
                  No triggers available for your connected services
                </p>
              </div>
            ) : (
              Object.values(triggersByToolkit).map((toolkit) => (
                <div
                  key={toolkit.slug}
                  className="border rounded-lg bg-card overflow-hidden">
                  {/* Toolkit Header */}
                  <button
                    onClick={() =>
                      setExpandedToolkit(
                        expandedToolkit === toolkit.slug ? null : toolkit.slug,
                      )
                    }
                    className="w-full flex items-center gap-3 p-4 hover:bg-muted/50 transition-colors">
                    <ToolkitLogo toolkit={toolkit.slug} size="lg" />
                    <div className="flex-1 text-left">
                      <h4 className="font-medium">{toolkit.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        {toolkit.triggers.length} trigger
                        {toolkit.triggers.length !== 1 ? "s" : ""} available
                      </p>
                    </div>
                    {expandedToolkit === toolkit.slug ? (
                      <ChevronUp className="w-5 h-5 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-muted-foreground" />
                    )}
                  </button>

                  {/* Triggers List */}
                  {expandedToolkit === toolkit.slug && (
                    <div className="border-t bg-muted/20 p-3 space-y-2">
                      {toolkit.triggers.map((triggerType) => (
                        <div
                          key={triggerType.slug}
                          onClick={() => {
                            setSelectedTriggerType(triggerType);
                            setShowCreateModal(true);
                          }}
                          className="flex items-center gap-3 p-3 bg-background border rounded-md hover:border-primary/50 cursor-pointer transition-colors">
                          <div className="flex-1 min-w-0">
                            <h5 className="font-medium text-sm">
                              {triggerType.name}
                            </h5>
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {triggerType.description}
                            </p>
                          </div>
                          <Plus className="w-4 h-4 text-muted-foreground shrink-0" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Create Trigger Modal */}
      {showCreateModal && selectedTriggerType && (
        <CreateTriggerModal
          triggerType={selectedTriggerType}
          connectedAccounts={activeAccounts}
          onClose={() => {
            setShowCreateModal(false);
            setSelectedTriggerType(null);
          }}
          onCreated={() => {
            setShowCreateModal(false);
            setSelectedTriggerType(null);
            fetchActiveTriggers();
          }}
        />
      )}
    </div>
  );
}

// Trigger Card Component
function TriggerCard({
  trigger,
  isExpanded,
  onToggleExpand,
  onToggleEnabled,
  onDelete,
}: {
  trigger: TriggerInstance;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onToggleEnabled: () => void;
  onDelete: () => void;
}) {
  const isEnabled = !trigger.disabledAt;
  const toolkitSlug = trigger.triggerName.split("_")[0]?.toLowerCase() || "";

  return (
    <div
      className={clsx(
        "border rounded-lg bg-card overflow-hidden",
        isEnabled ? "border-primary/30" : "border-border",
      )}>
      {/* Header */}
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-muted/50"
        onClick={onToggleExpand}>
        <ToolkitLogo toolkit={toolkitSlug} size="md" />
        <div
          className={clsx(
            "w-2 h-2 rounded-full",
            isEnabled ? "bg-green-500" : "bg-muted-foreground",
          )}
        />
        <div className="flex-1 min-w-0">
          <h4 className="font-medium truncate">{trigger.triggerName}</h4>
          <p className="text-xs text-muted-foreground truncate">
            ID: {trigger.id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleEnabled();
            }}
            className={clsx(
              "p-2 rounded-md transition-colors",
              isEnabled
                ? "bg-green-500/10 text-green-500 hover:bg-green-500/20"
                : "bg-muted text-muted-foreground hover:bg-muted/80",
            )}
            title={isEnabled ? "Disable trigger" : "Enable trigger"}>
            {isEnabled ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-2 rounded-md text-destructive hover:bg-destructive/10 transition-colors"
            title="Delete trigger">
            <Trash2 className="w-4 h-4" />
          </button>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t bg-muted/20 p-3 space-y-3">
          <div>
            <h5 className="text-xs font-medium text-muted-foreground mb-1">
              Configuration
            </h5>
            <pre className="text-xs bg-background p-2 rounded border overflow-x-auto">
              {JSON.stringify(trigger.triggerConfig, null, 2)}
            </pre>
          </div>
          {trigger.state && Object.keys(trigger.state).length > 0 && (
            <div>
              <h5 className="text-xs font-medium text-muted-foreground mb-1">
                State
              </h5>
              <pre className="text-xs bg-background p-2 rounded border overflow-x-auto">
                {JSON.stringify(trigger.state, null, 2)}
              </pre>
            </div>
          )}
          <div className="flex gap-4 text-xs text-muted-foreground">
            <span>Updated: {new Date(trigger.updatedAt).toLocaleString()}</span>
            {trigger.disabledAt && (
              <span>
                Disabled: {new Date(trigger.disabledAt).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Create Trigger Modal
function CreateTriggerModal({
  triggerType,
  connectedAccounts,
  onClose,
  onCreated,
}: {
  triggerType: TriggerType;
  connectedAccounts: ConnectedAccount[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [configValues, setConfigValues] = useState<Record<string, string>>({});

  // Filter accounts that match the trigger's toolkit
  const matchingAccounts = connectedAccounts.filter(
    (acc) =>
      (acc.appName || "").toLowerCase() ===
      triggerType.toolkit.slug.toLowerCase(),
  );

  // Parse config schema to get required fields
  const configSchema = triggerType.config as {
    properties?: Record<
      string,
      { type?: string; description?: string; default?: unknown }
    >;
    required?: string[];
  };
  const configProperties = configSchema?.properties || {};
  const requiredFields = configSchema?.required || [];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      // Build trigger config from form values
      const triggerConfig: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(configValues)) {
        if (value) {
          triggerConfig[key] = value;
        }
      }

      const res = await fetch("/api/composio/triggers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          triggerSlug: triggerType.slug,
          connectedAccountId: selectedAccountId || undefined,
          triggerConfig:
            Object.keys(triggerConfig).length > 0 ? triggerConfig : undefined,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to create trigger");
      }

      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create trigger");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-card border rounded-lg shadow-lg w-full max-w-lg max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-3">
            <ToolkitLogo toolkit={triggerType.toolkit.slug} size="lg" />
            <div>
              <h2 className="text-lg font-semibold">Create Trigger</h2>
              <p className="text-sm text-muted-foreground">
                {triggerType.name}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground text-xl leading-none">
            &times;
          </button>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="p-4 overflow-y-auto max-h-[70vh]">
          {error && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded text-destructive text-sm">
              {error}
            </div>
          )}

          {/* Description */}
          <div className="mb-4 p-3 bg-muted/30 rounded-md">
            <p className="text-sm">{triggerType.description}</p>
            {triggerType.instructions && (
              <p className="text-xs text-muted-foreground mt-2">
                {triggerType.instructions}
              </p>
            )}
          </div>

          {/* Connected Account Selection */}
          {matchingAccounts.length > 1 && (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">
                Connected Account
              </label>
              <select
                value={selectedAccountId}
                onChange={(e) => setSelectedAccountId(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring">
                <option value="">Auto-select</option>
                {matchingAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.appName} ({acc.id.slice(0, 8)}...)
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Config Fields */}
          {Object.keys(configProperties).length > 0 && (
            <div className="space-y-4">
              <h4 className="text-sm font-medium">Configuration</h4>
              {Object.entries(configProperties).map(([key, prop]) => (
                <div key={key}>
                  <label className="block text-sm font-medium mb-1">
                    {key}
                    {requiredFields.includes(key) && (
                      <span className="text-destructive ml-1">*</span>
                    )}
                  </label>
                  {prop.description && (
                    <p className="text-xs text-muted-foreground mb-1">
                      {prop.description}
                    </p>
                  )}
                  <input
                    type="text"
                    value={configValues[key] || ""}
                    onChange={(e) =>
                      setConfigValues((prev) => ({
                        ...prev,
                        [key]: e.target.value,
                      }))
                    }
                    required={requiredFields.includes(key)}
                    placeholder={
                      prop.default ? String(prop.default) : undefined
                    }
                    className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
              ))}
            </div>
          )}

          {/* No matching accounts warning */}
          {matchingAccounts.length === 0 && (
            <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded text-yellow-600 text-sm">
              No connected {triggerType.toolkit.name} account found. Please
              connect your account first.
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded-md hover:bg-muted">
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || matchingAccounts.length === 0}
              className={clsx(
                "flex items-center gap-2 px-4 py-2 rounded-md",
                "bg-primary text-primary-foreground",
                "hover:bg-primary/90 disabled:opacity-50",
              )}>
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Create Trigger
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
