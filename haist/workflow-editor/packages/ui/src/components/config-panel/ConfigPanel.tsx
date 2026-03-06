'use client';

/**
 * Configuration panel for selected nodes
 */

import React, { useMemo, useCallback, useRef, useEffect } from 'react';
import { Settings, Code, FileJson, Copy, Check, Link2, Type, Play, X, GripVertical } from 'lucide-react';
import { clsx } from 'clsx';
import { useWorkflowStore, useSelectionStore, useUIStore, useComposioStore } from '@workflow-editor/state';
import type { BubbleNodeData, TriggerNodeData, ComposioNodeData, WorkflowNode, WorkflowEdge, ArtifactConfig } from '@workflow-editor/core';
import { getBubble, ParameterType, createVariableParam, DEFAULT_ARTIFACT_CONFIG } from '@workflow-editor/core';
import { ArtifactConfigSection } from './ArtifactConfigSection';
import { generateFromWorkflow } from '@workflow-editor/codegen';

/**
 * Resize handle component for dragging panel width
 */
function ResizeHandle({ onResize }: { onResize: (delta: number) => void }) {
  const isDragging = useRef(false);
  const startX = useRef(0);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    isDragging.current = true;
    startX.current = e.clientX;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = startX.current - e.clientX;
      startX.current = e.clientX;
      onResize(delta);
    };

    const handleMouseUp = () => {
      isDragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [onResize]);

  return (
    <div
      onMouseDown={handleMouseDown}
      className={clsx(
        'absolute left-0 top-0 bottom-0 w-1 cursor-col-resize z-10',
        'hover:bg-primary/50 active:bg-primary transition-colors',
        'group flex items-center justify-center'
      )}
    >
      <div className="absolute left-0 w-4 h-full" /> {/* Larger hit area */}
      <GripVertical className="w-3 h-3 text-muted-foreground/50 opacity-0 group-hover:opacity-100 transition-opacity absolute -left-1" />
    </div>
  );
}

/**
 * Tab button component
 */
function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors',
        active
          ? 'bg-primary text-primary-foreground'
          : 'text-muted-foreground hover:bg-accent'
      )}
    >
      {children}
    </button>
  );
}

/**
 * No selection placeholder
 */
function NoSelection() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-4">
      <Settings className="w-12 h-12 text-muted-foreground/50 mb-3" />
      <h3 className="font-medium text-sm">No Node Selected</h3>
      <p className="text-xs text-muted-foreground mt-1">
        Select a node on the canvas to configure it
      </p>
    </div>
  );
}

/**
 * Trigger configuration
 */
function TriggerConfig({ node }: { node: WorkflowNode }) {
  const data = node.data as TriggerNodeData;
  const updateNodeData = useWorkflowStore((state) => state.updateNodeData);

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs font-medium text-muted-foreground">
          Trigger Type
        </label>
        <select
          value={data.triggerType}
          onChange={(e) =>
            updateNodeData(node.id, {
              triggerType: e.target.value as TriggerNodeData['triggerType'],
            })
          }
          className={clsx(
            'w-full mt-1 px-3 py-2 text-sm rounded-md',
            'bg-background border border-input',
            'focus:outline-none focus:ring-2 focus:ring-ring'
          )}
        >
          <option value="webhook/http">Webhook (HTTP)</option>
          <option value="schedule/cron">Cron Schedule</option>
          <option value="slack/bot_mentioned">Slack Mention</option>
        </select>
      </div>

      {data.triggerType === 'schedule/cron' && (
        <div>
          <label className="text-xs font-medium text-muted-foreground">
            Cron Expression
          </label>
          <input
            type="text"
            value={data.cronSchedule || ''}
            onChange={(e) =>
              updateNodeData(node.id, { cronSchedule: e.target.value })
            }
            placeholder="0 9 * * 1-5"
            className={clsx(
              'w-full mt-1 px-3 py-2 text-sm rounded-md font-mono',
              'bg-background border border-input',
              'focus:outline-none focus:ring-2 focus:ring-ring'
            )}
          />
          <p className="text-xs text-muted-foreground mt-1">
            e.g., &quot;0 9 * * 1-5&quot; for weekdays at 9am
          </p>
        </div>
      )}

      {data.triggerType === 'webhook/http' && (
        <div>
          <label className="text-xs font-medium text-muted-foreground">
            Webhook Path (optional)
          </label>
          <input
            type="text"
            value={data.webhookPath || ''}
            onChange={(e) =>
              updateNodeData(node.id, { webhookPath: e.target.value })
            }
            placeholder="/my-webhook"
            className={clsx(
              'w-full mt-1 px-3 py-2 text-sm rounded-md font-mono',
              'bg-background border border-input',
              'focus:outline-none focus:ring-2 focus:ring-ring'
            )}
          />
        </div>
      )}
    </div>
  );
}

/**
 * AI model options by provider
 */
const AI_MODELS_BY_PROVIDER: Record<string, Array<{ value: string; label: string }>> = {
  openai: [
    { value: 'openai/gpt-5.2', label: 'GPT-5.2' },
    { value: 'openai/gpt-5-mini', label: 'GPT-5 Mini' },
    { value: 'openai/gpt-5-nano', label: 'GPT-5 Nano' },
    { value: 'openai/gpt-5', label: 'GPT-5' },
  ],
  google: [
    { value: 'google/gemini-3-pro-preview', label: 'Gemini 3 Pro Preview' },
    { value: 'google/gemini-3-flash-preview', label: 'Gemini 3 Flash Preview' },
    { value: 'google/gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  ],
};

/**
 * Get provider from model string
 */
function getProviderFromModel(model: string): string {
  if (model.startsWith('openai/')) return 'openai';
  if (model.startsWith('google/')) return 'google';
  return '';
}

/**
 * AI Agent Model Configuration Component
 */
function AIAgentModelConfig({
  node,
  data,
  updateNodeData,
}: {
  node: WorkflowNode;
  data: BubbleNodeData;
  updateNodeData: (id: string, data: Partial<BubbleNodeData>) => void;
}) {
  // Get current model config object - handle legacy string values
  const rawModelValue = data.parameters.model?.value;
  const modelConfig: Record<string, unknown> =
    typeof rawModelValue === 'object' && rawModelValue !== null && !Array.isArray(rawModelValue)
      ? (rawModelValue as Record<string, unknown>)
      : {};

  const currentModel = (modelConfig.model as string) || '';
  const currentProvider = getProviderFromModel(currentModel);
  const currentTemperature = (modelConfig.temperature as number) ?? 0.7;

  // Get available models for current provider
  const availableModels = currentProvider ? AI_MODELS_BY_PROVIDER[currentProvider] || [] : [];

  // Update model config - create fresh object to avoid spreading corrupted data
  const updateModelConfig = (updates: Record<string, unknown>) => {
    const newModelConfig = {
      model: currentModel,
      temperature: currentTemperature,
      ...updates,
    };
    // Clean up legacy parameters and set new model config
    const { provider, maxTokens, ...cleanParams } = data.parameters;
    const newParams = {
      ...cleanParams,
      model: { type: ParameterType.OBJECT, value: newModelConfig },
    };
    updateNodeData(node.id, { parameters: newParams });
  };

  // Handle provider change
  const handleProviderChange = (newProvider: string) => {
    const firstModel = AI_MODELS_BY_PROVIDER[newProvider]?.[0]?.value || '';
    updateModelConfig({ model: firstModel });
  };

  return (
    <div className="space-y-3 p-3 bg-muted/50 rounded-md">
      <h5 className="text-xs font-medium text-muted-foreground">Model Configuration</h5>

      {/* Provider dropdown */}
      <div>
        <label className="text-xs font-medium">Provider</label>
        <select
          value={currentProvider}
          onChange={(e) => handleProviderChange(e.target.value)}
          className={clsx(
            'w-full mt-1 px-3 py-2 text-sm rounded-md',
            'bg-background border border-input',
            'focus:outline-none focus:ring-2 focus:ring-ring',
            !currentProvider && 'text-muted-foreground'
          )}
        >
          <option value="">Select a provider...</option>
          <option value="openai">OpenAI</option>
          <option value="google">Google</option>
        </select>
      </div>

      {/* Model dropdown */}
      <div>
        <label className="text-xs font-medium">Model</label>
        <select
          value={currentModel}
          onChange={(e) => updateModelConfig({ model: e.target.value })}
          disabled={!currentProvider}
          className={clsx(
            'w-full mt-1 px-3 py-2 text-sm rounded-md',
            'bg-background border border-input',
            'focus:outline-none focus:ring-2 focus:ring-ring',
            !currentProvider && 'opacity-50 cursor-not-allowed',
            !currentModel && 'text-muted-foreground'
          )}
        >
          <option value="">
            {currentProvider ? 'Select a model...' : 'Select a provider first'}
          </option>
          {availableModels.map((model) => (
            <option key={model.value} value={model.value}>
              {model.label}
            </option>
          ))}
        </select>
      </div>

      {/* Temperature */}
      <div>
        <label className="text-xs font-medium">Temperature</label>
        <input
          type="number"
          min="0"
          max="2"
          step="0.1"
          value={currentTemperature}
          onChange={(e) => updateModelConfig({ temperature: Number(e.target.value) })}
          className={clsx(
            'w-full mt-1 px-3 py-2 text-sm rounded-md',
            'bg-background border border-input',
            'focus:outline-none focus:ring-2 focus:ring-ring'
          )}
        />
        <p className="text-xs text-muted-foreground mt-0.5">0-2, higher = more creative</p>
      </div>
    </div>
  );
}

/**
 * Get source nodes connected to a node via data input
 */
function getConnectedSourceNodes(
  nodeId: string,
  nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): WorkflowNode[] {
  // Find edges where this node is the target (incoming connections)
  const incomingEdges = edges.filter((e) => e.target === nodeId);

  // Get the source nodes
  const sourceNodes: WorkflowNode[] = [];
  for (const edge of incomingEdges) {
    const sourceNode = nodes.find((n) => n.id === edge.source);
    if (sourceNode) {
      sourceNodes.push(sourceNode);
    }
  }

  return sourceNodes;
}

/**
 * Parameter input mode toggle
 */
function ParameterModeToggle({
  isVariable,
  onToggle,
}: {
  isVariable: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className={clsx(
        'flex items-center gap-1 px-2 py-0.5 text-xs rounded transition-colors',
        isVariable
          ? 'bg-blue-500/20 text-blue-600 hover:bg-blue-500/30'
          : 'bg-muted text-muted-foreground hover:bg-accent'
      )}
      title={isVariable ? 'Using input from connection' : 'Using static value'}
    >
      {isVariable ? (
        <>
          <Link2 className="w-3 h-3" />
          Input
        </>
      ) : (
        <>
          <Type className="w-3 h-3" />
          Static
        </>
      )}
    </button>
  );
}

/**
 * Bubble configuration
 */
function BubbleConfig({ node }: { node: WorkflowNode }) {
  const data = node.data as BubbleNodeData;
  const updateNodeData = useWorkflowStore((state) => state.updateNodeData);
  const nodes = useWorkflowStore((state) => state.nodes);
  const edges = useWorkflowStore((state) => state.edges);
  const bubble = getBubble(data.bubbleName);

  // Get nodes connected to this node's data input
  const connectedSourceNodes = useMemo(
    () => getConnectedSourceNodes(node.id, nodes, edges),
    [node.id, nodes, edges]
  );

  if (!bubble) {
    return <div className="text-sm text-muted-foreground">Unknown bubble type</div>;
  }

  // Check if this is the AI agent bubble
  const isAIAgent = data.bubbleName === 'ai-agent';

  // Toggle parameter between static value and variable reference
  const toggleParameterMode = (paramName: string) => {
    const currentParam = data.parameters[paramName];
    const isCurrentlyVariable = currentParam?.type === ParameterType.VARIABLE;

    if (isCurrentlyVariable) {
      // Switch to static - clear the variable reference
      const newParams = {
        ...data.parameters,
        [paramName]: { type: ParameterType.STRING, value: '' },
      };
      updateNodeData(node.id, { parameters: newParams });
    } else {
      // Switch to variable - use first connected node if available
      const firstSource = connectedSourceNodes[0];
      if (firstSource) {
        const newParams = {
          ...data.parameters,
          [paramName]: createVariableParam(firstSource.id, 'data'),
        };
        updateNodeData(node.id, { parameters: newParams });
      }
    }
  };

  // Update the referenced node for a variable parameter
  const updateVariableReference = (paramName: string, sourceNodeId: string) => {
    const newParams = {
      ...data.parameters,
      [paramName]: createVariableParam(sourceNodeId, 'data'),
    };
    updateNodeData(node.id, { parameters: newParams });
  };

  // Render a parameter input based on its definition
  const renderParameterInput = (paramName: string, paramDef: typeof bubble.schema[string]) => {
    // Special handling for AI agent model config (nested object)
    if (isAIAgent && paramName === 'model') {
      return (
        <AIAgentModelConfig
          key={paramName}
          node={node}
          data={data}
          updateNodeData={updateNodeData}
        />
      );
    }

    // Handle enum types with select dropdown
    if (paramDef.type === 'enum' && paramDef.enumValues) {
      const currentValue = data.parameters[paramName]?.value as string || paramDef.default?.toString() || '';
      return (
        <div key={paramName}>
          <label className="text-xs font-medium flex items-center gap-1">
            {paramName}
            {paramDef.required && <span className="text-destructive">*</span>}
          </label>
          <select
            value={currentValue}
            onChange={(e) => {
              const newParams = {
                ...data.parameters,
                [paramName]: { type: ParameterType.STRING, value: e.target.value },
              };
              updateNodeData(node.id, { parameters: newParams });
            }}
            className={clsx(
              'w-full mt-1 px-3 py-2 text-sm rounded-md',
              'bg-background border border-input',
              'focus:outline-none focus:ring-2 focus:ring-ring'
            )}
          >
            <option value="">Select {paramName}...</option>
            {paramDef.enumValues.map((enumVal) => (
              <option key={enumVal} value={enumVal}>
                {enumVal}
              </option>
            ))}
          </select>
          {paramDef.description && (
            <p className="text-xs text-muted-foreground mt-0.5">
              {paramDef.description}
            </p>
          )}
        </div>
      );
    }

    // Check if this parameter is using a variable reference
    const currentParam = data.parameters[paramName];
    const isVariable = currentParam?.type === ParameterType.VARIABLE;
    const hasConnections = connectedSourceNodes.length > 0;

    // Default input for other types
    return (
      <div key={paramName}>
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium flex items-center gap-1">
            {paramName}
            {paramDef.required && <span className="text-destructive">*</span>}
          </label>
          {/* Show toggle only if there are connected nodes */}
          {hasConnections && (
            <ParameterModeToggle
              isVariable={isVariable}
              onToggle={() => toggleParameterMode(paramName)}
            />
          )}
        </div>

        {isVariable ? (
          // Variable reference input - show dropdown to select source node
          <div className="mt-1 space-y-1">
            <select
              value={currentParam.referencedNodeId || ''}
              onChange={(e) => updateVariableReference(paramName, e.target.value)}
              className={clsx(
                'w-full px-3 py-2 text-sm rounded-md',
                'bg-blue-50 border border-blue-200 text-blue-700',
                'focus:outline-none focus:ring-2 focus:ring-blue-500'
              )}
            >
              <option value="">Select input source...</option>
              {connectedSourceNodes.map((sourceNode) => (
                <option key={sourceNode.id} value={sourceNode.id}>
                  {sourceNode.data.label} ({sourceNode.id.slice(0, 8)})
                </option>
              ))}
            </select>
            <p className="text-xs text-blue-600">
              Using output from connected node
            </p>
          </div>
        ) : (
          // Static value input
          <>
            <input
              type={paramDef.type === 'number' ? 'number' : 'text'}
              value={(() => {
                const paramValue = data.parameters[paramName]?.value;
                if (paramValue === undefined || paramValue === null) {
                  return paramDef.default?.toString() || '';
                }
                if (typeof paramValue === 'object') {
                  return JSON.stringify(paramValue);
                }
                return paramValue.toString();
              })()}
              onChange={(e) => {
                let value: string | number | object = e.target.value;
                let type = paramDef.type;

                // Convert value based on parameter type
                if (paramDef.type === 'number') {
                  value = Number(e.target.value);
                } else if (paramDef.type === 'object' || paramDef.type === 'array') {
                  // Try to parse as JSON for object/array types
                  try {
                    value = JSON.parse(e.target.value);
                  } catch {
                    // Keep as string if not valid JSON (user is still typing)
                    value = e.target.value;
                    type = 'string'; // Mark as string until valid JSON
                  }
                }

                const newParams = {
                  ...data.parameters,
                  [paramName]: {
                    type,
                    value,
                  },
                };
                updateNodeData(node.id, { parameters: newParams });
              }}
              placeholder={paramDef.description}
              className={clsx(
                'w-full mt-1 px-3 py-2 text-sm rounded-md',
                'bg-background border border-input',
                'focus:outline-none focus:ring-2 focus:ring-ring'
              )}
            />
            {paramDef.description && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {paramDef.description}
              </p>
            )}
          </>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Variable name */}
      <div>
        <label className="text-xs font-medium text-muted-foreground">
          Variable Name
        </label>
        <input
          type="text"
          value={data.variableName}
          onChange={(e) =>
            updateNodeData(node.id, { variableName: e.target.value })
          }
          className={clsx(
            'w-full mt-1 px-3 py-2 text-sm rounded-md font-mono',
            'bg-background border border-input',
            'focus:outline-none focus:ring-2 focus:ring-ring'
          )}
        />
      </div>

      {/* Parameters */}
      <div className="space-y-3">
        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Parameters
        </h4>
        {Object.entries(bubble.schema).map(([paramName, paramDef]) =>
          renderParameterInput(paramName, paramDef)
        )}
      </div>

      {/* Artifact Config (AI Agent only) */}
      {isAIAgent && (
        <div className="space-y-3">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Context
          </h4>
          <ArtifactConfigSection
            config={data.artifactConfig}
            onChange={(artifactConfig: ArtifactConfig) =>
              updateNodeData(node.id, { artifactConfig })
            }
          />
        </div>
      )}
    </div>
  );
}

/**
 * Composio node configuration
 */
function ComposioConfig({ node }: { node: WorkflowNode }) {
  const data = node.data as ComposioNodeData;
  const updateNodeData = useWorkflowStore((state) => state.updateNodeData);
  const availableTools = useComposioStore((state) => state.availableTools);

  // Get tools for this toolkit
  const toolkitTools = useMemo(() => {
    return availableTools[data.toolkit?.toUpperCase()] || [];
  }, [availableTools, data.toolkit]);

  // Format tool name for display
  const formatToolName = (toolName: string): string => {
    return toolName
      .replace(`${data.toolkit}_`, '')
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  // Generate variable name from tool name
  const generateVariableName = (toolName: string): string => {
    return (
      toolName
        .toLowerCase()
        .split('_')
        .map((word, i) =>
          i === 0 ? word : word.charAt(0).toUpperCase() + word.slice(1)
        )
        .join('') + 'Result'
    );
  };

  // Handle tool selection
  const handleToolChange = (toolName: string) => {
    const selectedTool = toolkitTools.find((t) => t.name === toolName);
    const label = toolName ? formatToolName(toolName) : data.label;
    const variableName = toolName ? generateVariableName(toolName) : data.variableName;

    updateNodeData(node.id, {
      toolName,
      label,
      variableName,
      toolDescription: selectedTool?.description || '',
      toolInputs: selectedTool?.inputs || '',
      toolInputSchema: selectedTool?.inputSchema, // Store structured schema
      parameters: {}, // Reset parameters when tool changes
      isValid: Boolean(toolName),
      validationErrors: toolName ? [] : ['Select a tool from the dropdown'],
    });
  };

  // Get the selected tool's schema for display
  const selectedTool = toolkitTools.find((t) => t.name === data.toolName);
  const inputSchema = data.toolInputSchema || selectedTool?.inputSchema;

  // Debug: Log the state of tools and schemas
  useEffect(() => {
    console.log('[ConfigPanel] Composio node state:', {
      toolkit: data.toolkit,
      toolName: data.toolName,
      hasStoredSchema: !!data.toolInputSchema,
      toolkitToolsCount: toolkitTools.length,
      selectedToolFound: !!selectedTool,
      selectedToolHasSchema: !!selectedTool?.inputSchema,
      schemaPropertyCount: selectedTool?.inputSchema?.properties
        ? Object.keys(selectedTool.inputSchema.properties).length
        : 0,
    });
  }, [data.toolkit, data.toolName, data.toolInputSchema, toolkitTools.length, selectedTool]);

  // Auto-save schema if tool is selected but schema is missing from node data
  // This handles cases where workflow was created before schema saving was implemented
  useEffect(() => {
    if (data.toolName && !data.toolInputSchema && selectedTool?.inputSchema) {
      console.log('[ConfigPanel] Auto-saving missing schema for', data.toolName, {
        properties: Object.keys(selectedTool.inputSchema.properties || {}),
      });
      updateNodeData(node.id, {
        toolInputSchema: selectedTool.inputSchema,
      });
    }
  }, [data.toolName, data.toolInputSchema, selectedTool?.inputSchema, node.id, updateNodeData]);

  return (
    <div className="space-y-4">
      {/* Tool selection */}
      <div>
        <label className="text-xs font-medium text-muted-foreground">
          Tool
        </label>
        <select
          value={data.toolName || ''}
          onChange={(e) => handleToolChange(e.target.value)}
          className={clsx(
            'w-full mt-1 px-3 py-2 text-sm rounded-md',
            'bg-background border border-input',
            'focus:outline-none focus:ring-2 focus:ring-ring',
            !data.toolName && 'text-muted-foreground'
          )}
        >
          <option value="">Select a tool...</option>
          {toolkitTools.map((tool) => (
            <option key={tool.name} value={tool.name}>
              {formatToolName(tool.name)}
            </option>
          ))}
        </select>
        {toolkitTools.length === 0 && (
          <p className="text-xs text-amber-600 mt-1">
            No tools loaded. Make sure the service is connected.
          </p>
        )}
      </div>

      {/* Tool description */}
      {data.toolDescription && (
        <div className="p-2 bg-muted rounded-md">
          <p className="text-xs text-muted-foreground">{data.toolDescription}</p>
        </div>
      )}

      {/* Variable name */}
      {data.toolName && (
        <div>
          <label className="text-xs font-medium text-muted-foreground">
            Variable Name
          </label>
          <input
            type="text"
            value={data.variableName}
            onChange={(e) =>
              updateNodeData(node.id, { variableName: e.target.value })
            }
            className={clsx(
              'w-full mt-1 px-3 py-2 text-sm rounded-md font-mono',
              'bg-background border border-input',
              'focus:outline-none focus:ring-2 focus:ring-ring'
            )}
          />
        </div>
      )}

      {/* Expected Input Schema - shows what parameters the AI should generate */}
      {data.toolName && inputSchema && (
        <div className="space-y-3">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Expected Input Schema
          </h4>
          <p className="text-xs text-muted-foreground mb-2">
            When connected to an AI agent, it will generate output matching this schema.
          </p>
          <div className="bg-muted/50 rounded-md p-3 space-y-2">
            {Object.entries(inputSchema.properties).map(([paramName, prop]) => {
              const isRequired = inputSchema.required?.includes(paramName);
              return (
                <div key={paramName} className="text-xs">
                  <div className="flex items-center gap-1">
                    <code className="font-mono text-primary">{paramName}</code>
                    <span className="text-muted-foreground">: {prop.type}</span>
                    {isRequired && (
                      <span className="text-destructive text-[10px]">*required</span>
                    )}
                    {prop.enum && (
                      <span className="text-muted-foreground text-[10px]">
                        [{prop.enum.slice(0, 3).join('|')}{prop.enum.length > 3 ? '...' : ''}]
                      </span>
                    )}
                  </div>
                  {prop.description && (
                    <p className="text-muted-foreground text-[10px] ml-2 mt-0.5">
                      {prop.description}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Parameters - simplified for now, can be expanded based on tool schema */}
      {data.toolName && (
        <div className="space-y-3">
          <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Parameters
          </h4>
          <p className="text-xs text-muted-foreground">
            Configure parameters in the execution payload or connect an AI agent.
          </p>
        </div>
      )}
    </div>
  );
}

/**
 * Node info display
 */
function NodeInfo({ node }: { node: WorkflowNode }) {
  const data = node.data;

  return (
    <div className="space-y-2 text-sm">
      <div className="flex justify-between">
        <span className="text-muted-foreground">ID</span>
        <code className="text-xs bg-muted px-1.5 py-0.5 rounded">{node.id}</code>
      </div>
      <div className="flex justify-between">
        <span className="text-muted-foreground">Type</span>
        <span>{node.type}</span>
      </div>
      {'bubbleName' in data && (
        <div className="flex justify-between">
          <span className="text-muted-foreground">Bubble</span>
          <span>{(data as BubbleNodeData).bubbleName}</span>
        </div>
      )}
      {'toolkit' in data && (
        <>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Toolkit</span>
            <span>{(data as ComposioNodeData).toolkit}</span>
          </div>
          {(data as ComposioNodeData).toolName && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Tool</span>
              <span>{(data as ComposioNodeData).toolName}</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/**
 * Results panel component - shows execution results
 */
function ResultsPanel() {
  const executionResult = useUIStore((state) => state.executionResult);
  const isExecuting = useUIStore((state) => state.isExecuting);
  const clearExecutionResult = useUIStore((state) => state.clearExecutionResult);

  if (isExecuting) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-4">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
        <h3 className="font-medium text-sm">Executing Workflow</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Please wait while the workflow runs...
        </p>
      </div>
    );
  }

  if (!executionResult) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-4">
        <Play className="w-12 h-12 text-muted-foreground/50 mb-3" />
        <h3 className="font-medium text-sm">No Results Yet</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Run the workflow to see execution results here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <span
            className={clsx(
              'w-2 h-2 rounded-full',
              executionResult.success ? 'bg-green-500' : 'bg-red-500'
            )}
          />
          {executionResult.success ? 'Execution Successful' : 'Execution Failed'}
        </h3>
        <button
          onClick={clearExecutionResult}
          className="p-1 hover:bg-accent rounded transition-colors"
          title="Clear results"
        >
          <X className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>

      {/* Error */}
      {executionResult.error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-md">
          <p className="text-sm text-red-500">{executionResult.error}</p>
        </div>
      )}

      {/* Node Outputs */}
      {executionResult.data?.bubbleResult?.nodeOutputs &&
        Object.keys(executionResult.data.bubbleResult.nodeOutputs).length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2">Node Outputs</h4>
            <div className="space-y-2">
              {Object.entries(executionResult.data.bubbleResult.nodeOutputs).map(
                ([nodeId, output]) => (
                  <div
                    key={nodeId}
                    className={clsx(
                      'p-3 rounded-md border',
                      output.success
                        ? 'bg-green-500/5 border-green-500/20'
                        : 'bg-red-500/5 border-red-500/20'
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium">{output.label}</span>
                      <span
                        className={clsx(
                          'px-1.5 py-0.5 text-[10px] rounded',
                          output.success
                            ? 'bg-green-500/20 text-green-600'
                            : 'bg-red-500/20 text-red-500'
                        )}
                      >
                        {output.success ? 'OK' : 'Failed'}
                      </span>
                    </div>
                    <pre className="text-xs overflow-auto max-h-32 bg-muted/50 p-2 rounded">
                      {typeof output.data === 'string'
                        ? output.data
                        : JSON.stringify(output.data, null, 2)}
                    </pre>
                  </div>
                )
              )}
            </div>
          </div>
        )}

      {/* Composio Results */}
      {executionResult.data?.composioResults &&
        Object.keys(executionResult.data.composioResults).length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted-foreground mb-2">
              Composio Results
            </h4>
            <pre className="p-3 bg-muted rounded-md text-xs overflow-auto max-h-40">
              {JSON.stringify(executionResult.data.composioResults, null, 2)}
            </pre>
          </div>
        )}

      {/* Logs */}
      {executionResult.logs && executionResult.logs.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-muted-foreground mb-2">Logs</h4>
          <div className="space-y-1 max-h-48 overflow-auto">
            {executionResult.logs.map((log, i) => (
              <div
                key={i}
                className={clsx(
                  'p-2 rounded text-xs',
                  log.level === 'error' ? 'bg-red-500/10' : 'bg-muted'
                )}
              >
                <span className="text-muted-foreground">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>{' '}
                <span
                  className={clsx(
                    log.level === 'error' ? 'text-red-500' : 'text-foreground'
                  )}
                >
                  {log.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Code preview component - shows generated TypeScript code
 */
function CodePreview() {
  const [copied, setCopied] = React.useState(false);
  const workflowName = useWorkflowStore((state) => state.metadata.name);
  const nodes = useWorkflowStore((state) => state.nodes);
  const edges = useWorkflowStore((state) => state.edges);
  const trigger = useWorkflowStore((state) => state.trigger);

  // Generate code from workflow
  const generatedCode = useMemo(() => {
    return generateFromWorkflow(workflowName, trigger, nodes, edges);
  }, [workflowName, trigger, nodes, edges]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(generatedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-sm">Generated TypeScript</h3>
        <button
          onClick={handleCopy}
          className={clsx(
            'flex items-center gap-1 px-2 py-1 text-xs rounded-md transition-colors',
            copied
              ? 'bg-green-500/20 text-green-600'
              : 'bg-muted hover:bg-accent'
          )}
        >
          {copied ? (
            <>
              <Check className="w-3 h-3" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              Copy
            </>
          )}
        </button>
      </div>
      <div className="flex-1 relative">
        <pre className="absolute inset-0 text-xs bg-muted p-3 rounded-md overflow-auto font-mono">
          <code className="text-foreground whitespace-pre">{generatedCode}</code>
        </pre>
      </div>
    </div>
  );
}

/**
 * Config panel component
 */
export function ConfigPanel() {
  const nodes = useWorkflowStore((state) => state.nodes);
  const selectedNodeIds = useSelectionStore((state) => state.selectedNodeIds);
  const rightPanelTab = useUIStore((state) => state.rightPanelTab);
  const setRightPanelTab = useUIStore((state) => state.setRightPanelTab);
  const rightPanelWidth = useUIStore((state) => state.rightPanelWidth);
  const setRightPanelWidth = useUIStore((state) => state.setRightPanelWidth);

  // Handle resize
  const handleResize = useCallback((delta: number) => {
    setRightPanelWidth(rightPanelWidth + delta);
  }, [rightPanelWidth, setRightPanelWidth]);

  // Get selected node
  const selectedNode = selectedNodeIds.length === 1
    ? nodes.find((n) => n.id === selectedNodeIds[0])
    : null;

  return (
    <div className="relative flex flex-col h-full bg-card border-l border-border">
      {/* Resize handle */}
      <ResizeHandle onResize={handleResize} />
      {/* Tabs */}
      <div className="flex gap-1 p-2 border-b border-border">
        <TabButton
          active={rightPanelTab === 'config'}
          onClick={() => setRightPanelTab('config')}
        >
          <Settings className="w-4 h-4" />
          Config
        </TabButton>
        <TabButton
          active={rightPanelTab === 'schema'}
          onClick={() => setRightPanelTab('schema')}
        >
          <FileJson className="w-4 h-4" />
          Schema
        </TabButton>
        <TabButton
          active={rightPanelTab === 'code'}
          onClick={() => setRightPanelTab('code')}
        >
          <Code className="w-4 h-4" />
          Code
        </TabButton>
        <TabButton
          active={rightPanelTab === 'results'}
          onClick={() => setRightPanelTab('results')}
        >
          <Play className="w-4 h-4" />
          Results
        </TabButton>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {rightPanelTab === 'code' ? (
          <CodePreview />
        ) : rightPanelTab === 'results' ? (
          <ResultsPanel />
        ) : !selectedNode ? (
          <NoSelection />
        ) : rightPanelTab === 'config' ? (
          <div className="space-y-4">
            <h3 className="font-semibold">{selectedNode.data.label}</h3>
            {'nodeType' in selectedNode.data &&
            selectedNode.data.nodeType === 'trigger' ? (
              <TriggerConfig node={selectedNode} />
            ) : 'nodeType' in selectedNode.data &&
              selectedNode.data.nodeType === 'bubble' ? (
              <BubbleConfig node={selectedNode} />
            ) : 'nodeType' in selectedNode.data &&
              selectedNode.data.nodeType === 'composio' ? (
              <ComposioConfig node={selectedNode} />
            ) : null}
          </div>
        ) : rightPanelTab === 'schema' ? (
          <div className="space-y-4">
            <h3 className="font-semibold">Node Info</h3>
            <NodeInfo node={selectedNode} />
          </div>
        ) : null}
      </div>

      {/* Validation errors */}
      {selectedNode && selectedNode.data.validationErrors.length > 0 && (
        <div className="p-3 border-t border-border bg-destructive/10">
          <h4 className="text-xs font-medium text-destructive mb-1">
            Validation Errors
          </h4>
          <ul className="text-xs text-destructive space-y-0.5">
            {selectedNode.data.validationErrors.map((error, i) => (
              <li key={i}>• {error}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
