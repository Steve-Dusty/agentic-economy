'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
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
  Pencil,
  Bell,
  X,
  History,
  Activity,
  CheckCircle2,
  Clock,
  ArrowRight,
  MessageSquare,
} from 'lucide-react';
import { clsx } from 'clsx';
import { AuthenticatedLayout } from '../layout';
import { TriggersManager } from './TriggersManager';
import {
  TutorialProvider,
  TutorialTooltip,
  TutorialOverlay,
  CompletionModal,
  useTutorialContext,
} from '@/components/tutorial';
import { ExecutionLogPanel } from './ExecutionLogPanel';
import { TemplatePicker } from './TemplatePicker';
import type {
  ExecutionRule,
  ExecutionRuleInput,
  ExecutionStep,
  OutputConfig,
  ActivationMode,
  ScheduleInterval,
} from '@/lib/execution-rules/types';

export function AutomationsClient() {
  return (
    <TutorialProvider>
      <AutomationsContent />
    </TutorialProvider>
  );
}

function AutomationsContent() {
  const [showTriggersModal, setShowTriggersModal] = useState(false);
  const [rules, setRules] = useState<ExecutionRule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingRule, setEditingRule] = useState<ExecutionRule | null>(null);
  const [expandedRuleId, setExpandedRuleId] = useState<string | null>(null);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);
  const [templatePrefill, setTemplatePrefill] = useState<ExecutionRuleInput | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const [logsRuleId, setLogsRuleId] = useState<string | undefined>(undefined);
  const [logsRuleName, setLogsRuleName] = useState<string | undefined>(undefined);
  const [globalStats, setGlobalStats] = useState<{ totalRuns: number; successRate: number; avgDurationMs: number } | null>(null);

  // Tutorial refs
  const headerRef = useRef<HTMLDivElement>(null);
  const tutorial = useTutorialContext();

  // Fetch rules
  const fetchRules = useCallback(async () => {
    try {
      setIsLoading(true);
      const res = await fetch('/api/automations');
      if (!res.ok) throw new Error('Failed to fetch rules');
      const data = await res.json();
      setRules(data.rules || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch rules');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch global execution stats
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch('/api/automations/logs?limit=0');
      if (res.ok) {
        const data = await res.json();
        if (data.stats) setGlobalStats(data.stats);
      }
    } catch {
      // Stats are non-critical, silently fail
    }
  }, []);

  useEffect(() => {
    fetchRules();
    fetchStats();
  }, [fetchRules, fetchStats]);

  // Toggle rule active state
  const toggleRule = async (rule: ExecutionRule) => {
    try {
      const res = await fetch(`/api/automations/${rule.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isActive: !rule.isActive }),
      });
      if (!res.ok) throw new Error('Failed to update rule');
      fetchRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update rule');
    }
  };

  // Delete rule
  const deleteRule = async (id: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    try {
      const res = await fetch(`/api/automations/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete rule');
      fetchRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete rule');
    }
  };

  return (
    <AuthenticatedLayout title="Automations">
      <div className="p-6 max-w-5xl mx-auto">
        {/* Stats Dashboard */}
        {!isLoading && rules.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Zap className="w-3.5 h-3.5 text-primary" />
                <span className="text-xs font-medium">Active</span>
              </div>
              <p className="text-2xl font-semibold">{rules.filter(r => r.isActive).length}</p>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Activity className="w-3.5 h-3.5 text-blue-500" />
                <span className="text-xs font-medium">Executions</span>
              </div>
              <p className="text-2xl font-semibold">{globalStats?.totalRuns ?? rules.reduce((sum, r) => sum + (r.executionCount || 0), 0)}</p>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                <span className="text-xs font-medium">Success Rate</span>
              </div>
              <p className="text-2xl font-semibold">
                {globalStats
                  ? globalStats.totalRuns > 0 ? `${Math.round(globalStats.successRate)}%` : '—'
                  : '—'}
              </p>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 text-muted-foreground mb-1">
                <Clock className="w-3.5 h-3.5 text-amber-500" />
                <span className="text-xs font-medium">Time Saved</span>
              </div>
              <p className="text-2xl font-semibold">
                {(() => {
                  const totalExecs = globalStats?.totalRuns ?? rules.reduce((sum, r) => sum + (r.executionCount || 0), 0);
                  const minutes = totalExecs * 2;
                  if (minutes < 60) return `${minutes}m`;
                  return `${(minutes / 60).toFixed(1)}h`;
                })()}
              </p>
            </div>
          </div>
        )}

        {/* Header */}
        <div
          ref={headerRef}
          className={clsx(
            'flex items-center justify-between mb-6',
            tutorial.isActive && tutorial.currentStep === 5 && 'tutorial-pulse-highlight rounded-lg p-2 -m-2'
          )}
        >
          <div>
            <p className="text-muted-foreground">
              Mission control for your automations
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setLogsRuleId(undefined);
                setLogsRuleName(undefined);
                setShowLogs(true);
              }}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-md',
                'border border-border bg-background',
                'hover:bg-muted transition-colors'
              )}
            >
              <History className="w-4 h-4" />
              History
            </button>
            <button
              onClick={() => setShowTriggersModal(true)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-md',
                'border border-border bg-background',
                'hover:bg-muted transition-colors'
              )}
            >
              <Bell className="w-4 h-4" />
              Manage Triggers
            </button>
            <button
              onClick={() => setShowTemplatePicker(true)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-md',
                'border border-primary/50 text-primary bg-primary/5',
                'hover:bg-primary/10 transition-colors'
              )}
            >
              <Zap className="w-4 h-4" />
              From Template
            </button>
            <button
              onClick={() => setShowCreateForm(true)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-md',
                'bg-primary text-primary-foreground',
                'hover:bg-primary/90 transition-colors'
              )}
            >
              <Plus className="w-4 h-4" />
              New Rule
            </button>
          </div>
        </div>

        {/* Triggers Modal */}
        {showTriggersModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-card border rounded-lg shadow-lg w-full max-w-4xl max-h-[90vh] overflow-hidden">
              <div className="flex items-center justify-between p-4 border-b">
                <div className="flex items-center gap-2">
                  <Bell className="w-5 h-5" />
                  <h2 className="text-lg font-semibold">Manage Triggers</h2>
                </div>
                <button
                  onClick={() => setShowTriggersModal(false)}
                  className="p-2 hover:bg-muted rounded-md transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-4 overflow-y-auto max-h-[calc(90vh-80px)]">
                <TriggersManager />
              </div>
            </div>
          </div>
        )}

        {/* Template Picker */}
        {showTemplatePicker && (
          <TemplatePicker
            onSelect={(template) => {
              setTemplatePrefill(template);
              setShowTemplatePicker(false);
              setShowCreateForm(true);
            }}
            onClose={() => setShowTemplatePicker(false)}
          />
        )}

        {/* Execution Log Panel */}
        {showLogs && (
          <ExecutionLogPanel
            ruleId={logsRuleId}
            ruleName={logsRuleName}
            onClose={() => setShowLogs(false)}
          />
        )}

        {/* Error display */}
            {error && (
              <div className="mb-4 p-4 bg-destructive/10 border border-destructive/20 rounded-md flex items-center gap-2 text-destructive">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}

            {/* Create Form Modal */}
            {showCreateForm && (
              <RuleForm
                prefill={templatePrefill || undefined}
                onClose={() => {
                  setShowCreateForm(false);
                  setTemplatePrefill(null);
                }}
                onSaved={() => {
                  setShowCreateForm(false);
                  setTemplatePrefill(null);
                  fetchRules();
                }}
              />
            )}

            {/* Edit Form Modal */}
            {editingRule && (
              <RuleForm
                rule={editingRule}
                onClose={() => setEditingRule(null)}
                onSaved={() => {
                  setEditingRule(null);
                  fetchRules();
                }}
              />
            )}

            {/* Loading state */}
            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            )}

            {/* Empty state */}
            {!isLoading && rules.length === 0 && (
              <div className="text-center py-16 px-6">
                <Zap className="w-12 h-12 mx-auto text-primary mb-6" />
                <h3 className="text-2xl font-semibold mb-2">Tell blockd what to automate</h3>
                <p className="text-muted-foreground mb-8 max-w-md mx-auto">
                  Describe any workflow in plain English. blockd builds it, runs it, and monitors it.
                </p>
                <div className="flex items-center gap-3 justify-center">
                  <button
                    onClick={() => setShowTemplatePicker(true)}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
                  >
                    <Zap className="w-4 h-4" />
                    Browse Templates
                  </button>
                  <a
                    href="/chat"
                    className="inline-flex items-center gap-2 px-6 py-3 border border-border rounded-lg hover:bg-muted transition-colors font-medium"
                  >
                    Start from scratch
                    <ArrowRight className="w-4 h-4" />
                  </a>
                </div>
                <div className="mt-10 flex flex-wrap justify-center gap-2">
                  {[
                    'When I get an email from a client, summarize it on Slack',
                    'Monitor GitHub issues and notify my team',
                    'Enrich new leads and add to CRM',
                  ].map((suggestion) => (
                    <a
                      key={suggestion}
                      href={`/chat?q=${encodeURIComponent(suggestion)}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-muted/50 border border-border/50 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                    >
                      <MessageSquare className="w-3 h-3" />
                      {suggestion}
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Rules list */}
            {!isLoading && rules.length > 0 && (
              <div className="space-y-3">
                {rules.map((rule) => (
                  <RuleCard
                    key={rule.id}
                    rule={rule}
                    isExpanded={expandedRuleId === rule.id}
                    onToggleExpand={() =>
                      setExpandedRuleId(expandedRuleId === rule.id ? null : rule.id)
                    }
                    onToggleActive={() => toggleRule(rule)}
                    onEdit={() => setEditingRule(rule)}
                    onDelete={() => deleteRule(rule.id)}
                    onViewLogs={() => {
                      setLogsRuleId(rule.id);
                      setLogsRuleName(rule.name);
                      setShowLogs(true);
                    }}
                  />
                ))}
              </div>
            )}
      </div>

      {/* Tutorial Step 5: Automations intro */}
      <TutorialOverlay targetRef={headerRef} step={5} padding={12} />
      <TutorialTooltip
        step={5}
        targetRef={headerRef}
        title="Create Automation Rules"
        message="Set up rules to automatically process triggers from your connected services. Define conditions and actions for each rule."
        position="bottom"
      />

      {/* Tutorial Completion Modal (step 6) */}
      <CompletionModal />
    </AuthenticatedLayout>
  );
}

// Rule Card Component
function RuleCard({
  rule,
  isExpanded,
  onToggleExpand,
  onToggleActive,
  onEdit,
  onDelete,
  onViewLogs,
}: {
  rule: ExecutionRule;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onToggleActive: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onViewLogs: () => void;
}) {
  return (
    <div
      className={clsx(
        'border rounded-lg bg-card overflow-hidden transition-colors',
        rule.isActive ? 'border-border' : 'border-border/60'
      )}
    >
      {/* Header */}
      <div
        className="flex items-center gap-4 p-4 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={onToggleExpand}
      >
        <div
          className={clsx(
            'w-2 h-2 rounded-full flex-shrink-0',
            rule.isActive ? 'bg-green-500' : 'bg-muted-foreground/40'
          )}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-medium truncate">{rule.name}</h3>
            <span className="text-xs px-2 py-0.5 bg-muted rounded-full">
              Priority: {rule.priority}
            </span>
            <ActivationModeBadge mode={rule.activationMode} />
            {rule.scheduleEnabled && rule.scheduleInterval && (
              <span className="text-xs px-2 py-0.5 bg-blue-500/10 text-blue-600 rounded-full">
                {rule.scheduleInterval}
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground truncate">
            {rule.topicCondition}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {rule.executionCount} executions
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleActive();
            }}
            className={clsx(
              'p-2 rounded-md transition-colors',
              rule.isActive
                ? 'bg-green-500/10 text-green-500 hover:bg-green-500/20'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            )}
            title={rule.isActive ? 'Disable rule' : 'Enable rule'}
          >
            {rule.isActive ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="p-2 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            title="Edit rule"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-2 rounded-md text-destructive hover:bg-destructive/10 transition-colors"
            title="Delete rule"
          >
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
        <div className="border-t border-border bg-muted/30 p-4 space-y-4">
          {/* Description */}
          {rule.description && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-1">
                Description
              </h4>
              <p className="text-sm">{rule.description}</p>
            </div>
          )}

          {/* Accepted Triggers */}
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-1">
              Accepted Triggers
            </h4>
            <div className="flex flex-wrap gap-1">
              {rule.acceptedTriggers.length === 0 ? (
                <span className="text-xs px-2 py-1 bg-muted rounded">All triggers</span>
              ) : (
                rule.acceptedTriggers.map((t) => (
                  <span key={t} className="text-xs px-2 py-1 bg-muted rounded">
                    {t}
                  </span>
                ))
              )}
            </div>
          </div>

          {/* Execution Steps */}
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-1">
              Execution Steps
            </h4>
            <div className="space-y-2">
              {rule.executionSteps.map((step, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 p-2 bg-background rounded border"
                >
                  <span className="text-xs px-1.5 py-0.5 bg-primary/10 text-primary rounded">
                    {i + 1}
                  </span>
                  <div className="flex-1">
                    <span className="text-xs text-muted-foreground">
                      {step.type === 'instruction' ? 'Instruction' : 'Action'}
                    </span>
                    <p className="text-sm">
                      {step.type === 'instruction'
                        ? step.content
                        : `${step.toolName}: ${JSON.stringify(step.parameters)}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Output Config */}
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-1">
              Output Configuration
            </h4>
            <div className="text-sm p-2 bg-background rounded border">
              <p>
                <span className="text-muted-foreground">Platform:</span>{' '}
                {rule.outputConfig.platform}
              </p>
              {rule.outputConfig.destination && (
                <p>
                  <span className="text-muted-foreground">Destination:</span>{' '}
                  {rule.outputConfig.destination}
                </p>
              )}
              <p>
                <span className="text-muted-foreground">Format:</span>{' '}
                {rule.outputConfig.format}
              </p>
            </div>
          </div>

          {/* Activation Mode */}
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-1">
              Activation Mode
            </h4>
            <div className="text-sm p-2 bg-background rounded border">
              <p>
                <span className="text-muted-foreground">Mode:</span>{' '}
                {rule.activationMode}
              </p>
              {rule.scheduleEnabled && (
                <>
                  <p>
                    <span className="text-muted-foreground">Schedule:</span>{' '}
                    {rule.scheduleInterval}
                  </p>
                  {rule.scheduleNextRun && (
                    <p>
                      <span className="text-muted-foreground">Next run:</span>{' '}
                      {new Date(rule.scheduleNextRun).toLocaleString()}
                    </p>
                  )}
                  {rule.scheduleLastRun && (
                    <p>
                      <span className="text-muted-foreground">Last run:</span>{' '}
                      {new Date(rule.scheduleLastRun).toLocaleString()}
                    </p>
                  )}
                </>
              )}
            </div>
          </div>

          {/* View Logs */}
          <div>
            <button
              onClick={onViewLogs}
              className={clsx(
                'flex items-center gap-2 px-3 py-1.5 text-sm rounded-md',
                'border border-border bg-background',
                'hover:bg-muted transition-colors'
              )}
            >
              <History className="w-3.5 h-3.5" />
              View Execution Logs
            </button>
          </div>

          {/* Metadata */}
          <div className="flex gap-4 text-xs text-muted-foreground flex-wrap">
            <span>Created: {new Date(rule.createdAt).toLocaleDateString()}</span>
            <span>Updated: {new Date(rule.updatedAt).toLocaleDateString()}</span>
            {rule.lastExecutedAt && (
              <span>
                Last executed: {new Date(rule.lastExecutedAt).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Activation Mode Badge Component
function ActivationModeBadge({ mode }: { mode: ActivationMode }) {
  const colors: Record<ActivationMode, string> = {
    trigger: 'bg-yellow-500/10 text-yellow-600',
    manual: 'bg-purple-500/10 text-purple-600',
    scheduled: 'bg-blue-500/10 text-blue-600',
    all: 'bg-green-500/10 text-green-600',
  };

  const labels: Record<ActivationMode, string> = {
    trigger: 'Trigger',
    manual: 'Manual',
    scheduled: 'Scheduled',
    all: 'All',
  };

  return (
    <span className={clsx('text-xs px-2 py-0.5 rounded-full', colors[mode])}>
      {labels[mode]}
    </span>
  );
}

// User's active trigger for the dropdown
interface ActiveTrigger {
  id: string;
  triggerName: string; // This is the slug like GMAIL_NEW_EMAIL
  connectedAccountId: string;
  disabledAt: string | null;
}

// Rule Form Component (Create or Edit) — Simplified
function RuleForm({
  rule,
  prefill,
  onClose,
  onSaved,
}: {
  rule?: ExecutionRule;
  prefill?: ExecutionRuleInput;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEditing = !!rule;
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // User's active triggers for dropdown
  const [activeTriggers, setActiveTriggers] = useState<ActiveTrigger[]>([]);
  const [isLoadingTriggers, setIsLoadingTriggers] = useState(false);

  // Source: editing rule > template prefill > defaults
  const src = rule || prefill;

  // Form state
  const [name, setName] = useState(src?.name || '');
  const [description, setDescription] = useState(src?.description || '');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [priority, setPriority] = useState(rule?.priority ?? prefill?.priority ?? 0);
  const [topicCondition, setTopicCondition] = useState(src?.topicCondition || '');
  const [outputPlatform, setOutputPlatform] = useState<'slack' | 'gmail' | 'webhook' | 'none'>(
    src?.outputConfig?.platform || 'none'
  );
  const [outputDestination, setOutputDestination] = useState(src?.outputConfig?.destination || '');
  const [outputFormat, setOutputFormat] = useState<'summary' | 'detailed' | 'raw'>(
    src?.outputConfig?.format || 'summary'
  );
  const [acceptedTriggers, setAcceptedTriggers] = useState<string[]>(
    src?.acceptedTriggers || []
  );
  const [steps, setSteps] = useState<ExecutionStep[]>(
    src?.executionSteps?.length ? src.executionSteps : [{ type: 'instruction', content: '' }]
  );
  const [activationMode, setActivationMode] = useState<ActivationMode>(
    src?.activationMode || 'trigger'
  );
  const [scheduleEnabled, setScheduleEnabled] = useState(src?.scheduleEnabled || false);
  const [scheduleInterval, setScheduleInterval] = useState<ScheduleInterval | ''>(
    src?.scheduleInterval || ''
  );

  // Fetch user's active triggers when activation mode requires it
  useEffect(() => {
    if (activationMode === 'trigger' || activationMode === 'all') {
      setIsLoadingTriggers(true);
      fetch('/api/composio/triggers')
        .then((res) => res.json())
        .then((data) => {
          setActiveTriggers(data.triggers || []);
        })
        .catch((err) => {
          console.error('Failed to fetch active triggers:', err);
        })
        .finally(() => {
          setIsLoadingTriggers(false);
        });
    }
  }, [activationMode]);

  // Step helpers
  const addStep = () => {
    setSteps([...steps, { type: 'instruction', content: '' }]);
  };

  const updateStep = (index: number, content: string) => {
    const newSteps = [...steps];
    newSteps[index] = { type: 'instruction', content };
    setSteps(newSteps);
  };

  const removeStep = (index: number) => {
    setSteps(steps.filter((_, i) => i !== index));
  };

  // Submit
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const input: ExecutionRuleInput = {
        name,
        description: description || undefined,
        priority,
        topicCondition: topicCondition || name,
        acceptedTriggers,
        executionSteps: steps.filter((s) =>
          s.type === 'instruction' ? s.content : ('toolName' in s ? s.toolName : false)
        ),
        outputConfig: {
          platform: outputPlatform,
          destination: outputDestination || undefined,
          format: outputFormat,
        },
        activationMode,
        scheduleEnabled: activationMode === 'scheduled' || activationMode === 'all' ? scheduleEnabled : false,
        scheduleInterval: scheduleEnabled && scheduleInterval ? scheduleInterval : undefined,
      };

      const url = isEditing ? `/api/automations/${rule.id}` : '/api/automations';
      const method = isEditing ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || `Failed to ${isEditing ? 'update' : 'create'} rule`);
      }

      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${isEditing ? 'update' : 'create'} rule`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-base font-medium">
            {isEditing ? 'Edit Rule' : 'New Rule'}
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded-md transition-colors"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 overflow-y-auto max-h-[70vh] space-y-4">
          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-destructive text-sm">
              {error}
            </div>
          )}

          {/* Name */}
          <div>
            <label className="block text-sm font-medium mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="e.g., Summarize client emails"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="What does this automation do?"
            />
          </div>

          {/* Activation Mode */}
          <div>
            <label className="block text-sm font-medium mb-1">Activation</label>
            <select
              value={activationMode}
              onChange={(e) => {
                const mode = e.target.value as ActivationMode;
                setActivationMode(mode);
                if (mode === 'scheduled') {
                  setScheduleEnabled(true);
                } else if (mode === 'trigger' || mode === 'manual') {
                  setScheduleEnabled(false);
                  setScheduleInterval('');
                }
              }}
              className="w-full px-3 py-2 border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="trigger">Trigger (webhook events)</option>
              <option value="manual">Manual (@mention in chat)</option>
              <option value="scheduled">Scheduled (runs on interval)</option>
              <option value="all">All methods</option>
            </select>
          </div>

          {/* Schedule Config - only when scheduled or all */}
          {(activationMode === 'scheduled' || activationMode === 'all') && (
            <div className="p-3 bg-muted/30 rounded-md border space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="scheduleEnabled"
                  checked={scheduleEnabled}
                  onChange={(e) => setScheduleEnabled(e.target.checked)}
                  className="rounded"
                />
                <label htmlFor="scheduleEnabled" className="text-sm">
                  Enable schedule
                </label>
              </div>
              {scheduleEnabled && (
                <select
                  value={scheduleInterval}
                  onChange={(e) => setScheduleInterval(e.target.value as ScheduleInterval | '')}
                  className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                >
                  <option value="">Select interval...</option>
                  <option value="15min">Every 15 minutes</option>
                  <option value="hourly">Every hour</option>
                  <option value="daily">Every day</option>
                  <option value="weekly">Every week</option>
                </select>
              )}
            </div>
          )}

          {/* Accepted Triggers - only when trigger or all */}
          {(activationMode === 'trigger' || activationMode === 'all') && (
            <div>
              <label className="block text-sm font-medium mb-1">Triggers</label>
              <p className="text-xs text-muted-foreground mb-2">
                Which events activate this rule? Leave empty for all.
              </p>
              {isLoadingTriggers ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Loading triggers...
                </div>
              ) : activeTriggers.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2">
                  No active triggers. Set them up in Manage Triggers first.
                </p>
              ) : (
                <>
                  <div className="max-h-36 overflow-y-auto border rounded-md bg-background">
                    {(() => {
                      const uniqueNames = [...new Set(activeTriggers.map(t => t.triggerName))];
                      const grouped = uniqueNames.reduce((acc, name) => {
                        const prefix = name.split('_')[0] || 'Other';
                        if (!acc[prefix]) acc[prefix] = [];
                        acc[prefix].push(name);
                        return acc;
                      }, {} as Record<string, string[]>);

                      return Object.entries(grouped).map(([prefix, names]) => (
                        <div key={prefix}>
                          <div className="px-3 py-1 bg-muted/50 text-xs font-medium text-muted-foreground sticky top-0">
                            {prefix}
                          </div>
                          {names.map((triggerName) => (
                            <label
                              key={triggerName}
                              className="flex items-center gap-2 px-3 py-1.5 hover:bg-muted/30 cursor-pointer"
                            >
                              <input
                                type="checkbox"
                                checked={acceptedTriggers.includes(triggerName)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setAcceptedTriggers([...acceptedTriggers, triggerName]);
                                  } else {
                                    setAcceptedTriggers(acceptedTriggers.filter(t => t !== triggerName));
                                  }
                                }}
                                className="rounded"
                              />
                              <span className="text-xs">
                                {triggerName.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())}
                              </span>
                            </label>
                          ))}
                        </div>
                      ));
                    })()}
                  </div>
                  {acceptedTriggers.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {acceptedTriggers.map((t) => (
                        <span key={t} className="inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-primary/10 text-primary rounded">
                          {t}
                          <button type="button" onClick={() => setAcceptedTriggers(acceptedTriggers.filter(x => x !== t))} className="hover:text-destructive">
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Execution Steps */}
          <div>
            <label className="block text-sm font-medium mb-2">Steps *</label>
            <div className="space-y-2">
              {steps.map((step, i) => (
                <div key={i} className="flex gap-2 items-start">
                  <span className="text-xs px-1.5 py-0.5 bg-muted rounded mt-2 text-muted-foreground">
                    {i + 1}
                  </span>
                  <textarea
                    value={step.type === 'instruction' ? step.content : ('toolName' in step ? `[Action] ${step.toolName}` : '')}
                    onChange={(e) => updateStep(i, e.target.value)}
                    rows={2}
                    className="flex-1 px-3 py-2 border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                    placeholder={i === 0 ? 'e.g., Summarize the email and send a Slack message to #team' : 'Next step...'}
                  />
                  {steps.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeStep(i)}
                      className="p-1.5 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded transition-colors mt-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addStep}
              className="mt-2 text-xs px-3 py-1.5 border border-dashed rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            >
              + Add step
            </button>
          </div>

          {/* Advanced */}
          <div>
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              Advanced settings
            </button>
            {showAdvanced && (
              <div className="mt-3 p-3 bg-muted/20 rounded-md border border-border/50 space-y-3">
                {/* Priority */}
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Priority (higher = checked first)
                  </label>
                  <input
                    type="number"
                    value={priority}
                    onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
                    className="w-24 px-2 py-1.5 border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                {/* Topic Condition */}
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Topic Condition (for trigger matching)
                  </label>
                  <textarea
                    value={topicCondition}
                    onChange={(e) => setTopicCondition(e.target.value)}
                    rows={2}
                    className="w-full px-2 py-1.5 border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    placeholder="Defaults to rule name if empty"
                  />
                </div>

                {/* Output Config */}
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Output Configuration
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="text-[10px] text-muted-foreground">Platform</label>
                      <select
                        value={outputPlatform}
                        onChange={(e) => setOutputPlatform(e.target.value as typeof outputPlatform)}
                        className="w-full px-2 py-1.5 border rounded-md bg-background text-xs"
                      >
                        <option value="none">None</option>
                        <option value="slack">Slack</option>
                        <option value="gmail">Gmail</option>
                        <option value="webhook">Webhook</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-muted-foreground">Destination</label>
                      <input
                        type="text"
                        value={outputDestination}
                        onChange={(e) => setOutputDestination(e.target.value)}
                        className="w-full px-2 py-1.5 border rounded-md bg-background text-xs"
                        placeholder={
                          outputPlatform === 'slack' ? '#channel'
                            : outputPlatform === 'gmail' ? 'email@example.com'
                            : 'https://...'
                        }
                      />
                    </div>
                    <div>
                      <label className="text-[10px] text-muted-foreground">Format</label>
                      <select
                        value={outputFormat}
                        onChange={(e) => setOutputFormat(e.target.value as typeof outputFormat)}
                        className="w-full px-2 py-1.5 border rounded-md bg-background text-xs"
                      >
                        <option value="summary">Summary</option>
                        <option value="detailed">Detailed</option>
                        <option value="raw">Raw</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border rounded-md hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 text-sm rounded-md',
                'bg-primary text-primary-foreground',
                'hover:bg-primary/90 disabled:opacity-50 transition-colors'
              )}
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {isEditing ? 'Save' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
