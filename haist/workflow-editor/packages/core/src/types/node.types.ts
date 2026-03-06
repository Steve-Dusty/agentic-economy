/**
 * Node type definitions for the workflow editor
 */

import type { Node } from '@xyflow/react';
import type { ParameterValue, SchemaDefinition } from './parameter.types';

/**
 * All available node types in the editor
 */
export enum NodeType {
  // Triggers
  TRIGGER = 'trigger',

  // Bubbles
  SERVICE_BUBBLE = 'serviceBubble',
  TOOL_BUBBLE = 'toolBubble',
  WORKFLOW_BUBBLE = 'workflowBubble',

  // Composio (external services via Composio SDK)
  COMPOSIO = 'composio',

  // Control Flow
  IF_ELSE = 'ifElse',
  FOR_LOOP = 'forLoop',
  WHILE_LOOP = 'whileLoop',
  TRY_CATCH = 'tryCatch',
  PARALLEL = 'parallel',

  // Special
  CODE_BLOCK = 'codeBlock',
  COMMENT = 'comment',
  START = 'start',
  END = 'end',
}

/**
 * Bubble type categories
 */
export type BubbleType = 'service' | 'tool' | 'workflow';

/**
 * Trigger event types
 */
export type TriggerType = 'webhook/http' | 'schedule/cron' | 'slack/bot_mentioned';

/**
 * Base data interface for all nodes
 * Includes index signature for compatibility with @xyflow/react Node type
 */
export interface BaseNodeData {
  /** Index signature for @xyflow/react compatibility */
  [key: string]: unknown;
  /** Display label for the node */
  label: string;
  /** Optional description */
  description?: string;
  /** Whether the node configuration is valid */
  isValid: boolean;
  /** List of validation error messages */
  validationErrors: string[];
}

/**
 * Trigger node data (entry point)
 */
export interface TriggerNodeData extends BaseNodeData {
  nodeType: 'trigger';
  /** The type of trigger */
  triggerType: TriggerType;
  /** Cron schedule (for schedule/cron) */
  cronSchedule?: string;
  /** Webhook path (for webhook/http) */
  webhookPath?: string;
  /** Payload schema definition */
  payloadSchema?: SchemaDefinition;
}

/**
 * Configuration for artifact retrieval on AI agent nodes
 */
export interface ArtifactConfig {
  /** Enable automatic artifact injection (default: true) */
  autoInject: boolean;
  /** Maximum number of artifacts to inject (default: 3) */
  maxArtifacts: number;
  /** Explicit artifact IDs to always include */
  includeArtifacts?: string[];
  /** Artifact IDs to exclude from injection */
  excludeArtifacts?: string[];
}

/**
 * Default artifact configuration
 */
export const DEFAULT_ARTIFACT_CONFIG: ArtifactConfig = {
  autoInject: true,
  maxArtifacts: 3,
};

/**
 * Bubble node data (service, tool, or workflow)
 */
export interface BubbleNodeData extends BaseNodeData {
  nodeType: 'bubble';
  /** The bubble name (e.g., 'ai-agent', 'reddit-scrape-tool') */
  bubbleName: string;
  /** The bubble type category */
  bubbleType: BubbleType;
  /** The bubble class name (e.g., 'AIAgentBubble') */
  className: string;
  /** Variable name for code generation */
  variableName: string;
  /** Parameter values */
  parameters: Record<string, ParameterValue>;
  /** Input schema (from previous nodes) */
  inputSchema?: SchemaDefinition;
  /** Output schema (result) */
  outputSchema?: SchemaDefinition;
  /** Required credential types */
  requiredCredentials?: string[];
  /** Artifact configuration for AI agents (context retrieval) */
  artifactConfig?: ArtifactConfig;
}

/**
 * Tool input schema property (for structured schema storage)
 */
export interface ToolInputSchemaProperty {
  /** Parameter type (string, number, boolean, object, array) */
  type: string;
  /** Parameter description */
  description?: string;
  /** Whether this parameter is required */
  required?: boolean;
  /** Enum values if this is an enum type */
  enum?: string[];
  /** Default value */
  default?: unknown;
  /** Nested properties for object types */
  properties?: Record<string, ToolInputSchemaProperty>;
  /** Item schema for array types */
  items?: ToolInputSchemaProperty;
}

/**
 * Structured tool input schema
 */
export interface ToolInputSchema {
  /** Schema properties */
  properties: Record<string, ToolInputSchemaProperty>;
  /** List of required property names */
  required?: string[];
}

/**
 * Composio node data (external services via Composio SDK)
 */
export interface ComposioNodeData extends BaseNodeData {
  nodeType: 'composio';
  /** The toolkit name (e.g., 'GMAIL', 'SLACK') */
  toolkit: string;
  /** The tool name (e.g., 'GMAIL_SEND_EMAIL') */
  toolName: string;
  /** Variable name for code generation */
  variableName: string;
  /** Parameter values */
  parameters: Record<string, ParameterValue>;
  /** Tool description */
  toolDescription?: string;
  /** Tool input schema (legacy string format - deprecated) */
  toolInputs?: string;
  /** Structured tool input schema (for AI agent to know what parameters to generate) */
  toolInputSchema?: ToolInputSchema;
}

/**
 * Control flow node data
 */
export interface ControlFlowNodeData extends BaseNodeData {
  nodeType: 'controlFlow';
  /** The control flow type */
  controlType: 'if' | 'for' | 'while' | 'try_catch' | 'parallel';
  /** Condition expression (for if/while) */
  condition?: string;
  /** Iterator variable name (for for loops) */
  iteratorVariable?: string;
  /** Iterable expression (for for loops) */
  iterableExpression?: string;
  /** Maximum iterations (safety limit) */
  maxIterations?: number;
}

/**
 * Code block node data (custom TypeScript)
 */
export interface CodeBlockNodeData extends BaseNodeData {
  nodeType: 'codeBlock';
  /** The TypeScript code */
  code: string;
  /** Language (always typescript for now) */
  language: 'typescript';
  /** Variable name for the result */
  variableName: string;
}

/**
 * Comment node data (annotation)
 */
export interface CommentNodeData extends BaseNodeData {
  nodeType: 'comment';
  /** The comment text */
  text: string;
  /** Background color */
  color?: string;
}

/**
 * Union of all node data types
 */
export type WorkflowNodeData =
  | TriggerNodeData
  | BubbleNodeData
  | ComposioNodeData
  | ControlFlowNodeData
  | CodeBlockNodeData
  | CommentNodeData;

/**
 * Typed workflow node (ReactFlow node with our data)
 */
export type WorkflowNode = Node<WorkflowNodeData>;

/**
 * Specific node types for proper NodeProps typing
 */
export type TriggerWorkflowNode = Node<TriggerNodeData>;
export type BubbleWorkflowNode = Node<BubbleNodeData>;
export type ComposioWorkflowNode = Node<ComposioNodeData>;
export type ControlFlowWorkflowNode = Node<ControlFlowNodeData>;
export type CodeBlockWorkflowNode = Node<CodeBlockNodeData>;
export type CommentWorkflowNode = Node<CommentNodeData>;

/**
 * Handle position type
 */
export type HandlePosition = 'top' | 'right' | 'bottom' | 'left';

/**
 * Handle definition for node inputs/outputs
 */
export interface HandleDefinition {
  /** Unique handle ID */
  id: string;
  /** Display name */
  name: string;
  /** Handle type (data or control) */
  type: 'data' | 'control';
  /** Position on the node */
  position: HandlePosition;
  /** Schema for type checking */
  schema?: SchemaDefinition;
  /** Whether this handle is required */
  required?: boolean;
}

/**
 * Node metadata for the palette and registry
 */
export interface NodeMetadata {
  /** Display name */
  name: string;
  /** Short description */
  description: string;
  /** Category for grouping */
  category: NodeCategory;
  /** Icon name or component */
  icon: string;
  /** Theme color (hex) */
  color: string;
  /** Input handles */
  inputs: HandleDefinition[];
  /** Output handles */
  outputs: HandleDefinition[];
  /** Default data for new nodes */
  defaultData: Partial<WorkflowNodeData>;
}

/**
 * Node categories for the palette
 */
export type NodeCategory =
  | 'triggers'
  | 'service-bubbles'
  | 'tool-bubbles'
  | 'workflow-bubbles'
  | 'composio-services'
  | 'control-flow'
  | 'utilities';

/**
 * Create default trigger node data
 */
export function createTriggerNodeData(
  triggerType: TriggerType = 'webhook/http'
): TriggerNodeData {
  return {
    nodeType: 'trigger',
    label: triggerType === 'webhook/http' ? 'Webhook Trigger' :
           triggerType === 'schedule/cron' ? 'Cron Trigger' : 'Slack Trigger',
    triggerType,
    isValid: true,
    validationErrors: [],
  };
}

/**
 * Create default bubble node data
 */
export function createBubbleNodeData(
  bubbleName: string,
  className: string,
  bubbleType: BubbleType
): BubbleNodeData {
  return {
    nodeType: 'bubble',
    label: className.replace('Bubble', '').replace('Tool', ''),
    bubbleName,
    bubbleType,
    className,
    variableName: `${bubbleName.replace(/-/g, '')}Result`,
    parameters: {},
    isValid: true,
    validationErrors: [],
  };
}

/**
 * Create default control flow node data
 */
export function createControlFlowNodeData(
  controlType: ControlFlowNodeData['controlType']
): ControlFlowNodeData {
  const labels: Record<ControlFlowNodeData['controlType'], string> = {
    if: 'If / Else',
    for: 'For Loop',
    while: 'While Loop',
    try_catch: 'Try / Catch',
    parallel: 'Parallel',
  };

  return {
    nodeType: 'controlFlow',
    label: labels[controlType],
    controlType,
    isValid: true,
    validationErrors: [],
  };
}

/**
 * Create default Composio node data
 * toolName is optional - when not provided, user must select from dropdown
 */
export function createComposioNodeData(
  toolkit: string,
  toolName?: string,
  toolDescription?: string,
  toolInputs?: string
): ComposioNodeData {
  const upperToolkit = toolkit.toUpperCase();

  // If no tool name, show toolkit name as label
  if (!toolName) {
    // Toolkit display names
    const toolkitNames: Record<string, string> = {
      GMAIL: 'Gmail',
      GOOGLECALENDAR: 'Google Calendar',
      GOOGLEDRIVE: 'Google Drive',
      GOOGLEDOCS: 'Google Docs',
      GOOGLESHEETS: 'Google Sheets',
      SLACK: 'Slack',
      NOTION: 'Notion',
      GITHUB: 'GitHub',
      OUTLOOK: 'Outlook',
    };

    return {
      nodeType: 'composio',
      label: toolkitNames[upperToolkit] || toolkit,
      toolkit: upperToolkit,
      toolName: '',
      variableName: `${toolkit.toLowerCase()}Result`,
      parameters: {},
      toolDescription,
      toolInputs,
      isValid: false,
      validationErrors: ['Select a tool from the dropdown'],
    };
  }

  // Generate a readable label from tool name
  // e.g., "GMAIL_SEND_EMAIL" -> "Send Email"
  const label = toolName
    .replace(`${upperToolkit}_`, '')
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');

  // Generate variable name from tool name
  // e.g., "GMAIL_SEND_EMAIL" -> "gmailSendEmailResult"
  const variableName =
    toolName
      .toLowerCase()
      .split('_')
      .map((word, i) =>
        i === 0 ? word : word.charAt(0).toUpperCase() + word.slice(1)
      )
      .join('') + 'Result';

  return {
    nodeType: 'composio',
    label,
    toolkit: upperToolkit,
    toolName,
    variableName,
    parameters: {},
    toolDescription,
    toolInputs,
    isValid: true,
    validationErrors: [],
  };
}
