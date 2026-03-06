/**
 * AI Assistant Types
 *
 * Type definitions for the AI workflow assistant feature.
 */

import type { WorkflowDocument, TriggerConfig } from '@workflow-editor/core';
import type { BubbleType } from '@workflow-editor/core';

/**
 * Chat message in the conversation
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  /** Generated workflow (if any) */
  workflow?: WorkflowDocument;
  /** Services that need to be connected */
  requiredConnections?: string[];
}

/**
 * AI response from chat endpoint
 */
export interface AIResponse {
  message: string;
  workflow?: WorkflowDocument;
  suggestions?: string[];
  requiredConnections?: string[];
}

/**
 * Bubble summary for AI context (compact representation)
 */
export interface BubbleSummary {
  name: string;
  className: string;
  type: BubbleType;
  description: string;
  icon: string;
  color: string;
  parameters: ParameterSummary[];
  authType?: 'oauth' | 'apikey' | 'none' | 'connection-string';
}

/**
 * Parameter summary for AI context
 */
export interface ParameterSummary {
  name: string;
  type: string;
  required: boolean;
  description?: string;
  enumValues?: string[];
  default?: unknown;
}

/**
 * Composio tool summary for AI context
 */
export interface ComposioToolSummary {
  name: string;
  description: string;
  parameters: ParameterSummary[];
}

/**
 * Connected account info
 */
export interface ConnectedAccountInfo {
  toolkit: string;
  status: 'ACTIVE' | 'INITIATED' | 'EXPIRED';
  tools: ComposioToolSummary[];
}

/**
 * Full context for AI assistant
 */
export interface AIAssistantContext {
  /** User ID for fetching user-specific tool details (e.g., Composio) */
  userId?: string;
  bubbles: {
    services: BubbleSummary[];
    tools: BubbleSummary[];
    workflows: BubbleSummary[];
  };
  composio: {
    connectedAccounts: ConnectedAccountInfo[];
    availableToolkits: string[];
  };
}

/**
 * AI-generated workflow output (before transformation)
 */
export interface AIWorkflowOutput {
  name: string;
  description: string;
  trigger: {
    type: 'webhook/http' | 'schedule/cron' | 'slack/bot_mentioned';
    config?: {
      cronSchedule?: string;
      webhookPath?: string;
    };
  };
  nodes: AINodeOutput[];
  edges: AIEdgeOutput[];
}

/**
 * AI-generated node (before transformation)
 */
export interface AINodeOutput {
  id: string;
  type: 'bubble' | 'composio' | 'controlFlow';
  /** For bubble nodes */
  bubbleName?: string;
  bubbleType?: BubbleType;
  /** For composio nodes */
  toolkit?: string;
  toolName?: string;
  /** For control flow nodes */
  controlType?: 'if' | 'for' | 'while' | 'try_catch' | 'parallel';
  condition?: string;
  /** Common */
  variableName?: string;
  parameters: Record<string, AIParameterValue>;
  /** Position (optional, will be auto-calculated if not provided) */
  position?: { x: number; y: number };
}

/**
 * AI-generated parameter value
 */
export interface AIParameterValue {
  type: 'static' | 'variable' | 'expression';
  value: string | number | boolean | object | unknown[];
  /** For variable type: which node's output to reference */
  referencedNodeId?: string;
  referencedField?: string;
}

/**
 * AI-generated edge (before transformation)
 */
export interface AIEdgeOutput {
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  type?: 'data' | 'control';
}

/**
 * Chat request to API
 */
export interface ChatRequest {
  message: string;
  conversationHistory?: ChatMessage[];
}

/**
 * Extended chat request with artifact options
 */
export interface ChatRequestWithArtifacts extends ChatRequest {
  /** Manually selected artifact IDs to include */
  manualArtifactIds?: string[];
  /** Whether to enable auto artifact injection (default: true) */
  enableAutoArtifacts?: boolean;
}

/**
 * Save workflow request to API
 */
export interface SaveWorkflowRequest {
  workflow: WorkflowDocument;
}

/**
 * Save workflow response from API
 */
export interface SaveWorkflowResponse {
  success: boolean;
  workflowId?: string;
  error?: string;
}

/**
 * Validation error for AI-generated workflows
 */
export interface WorkflowValidationError {
  nodeId?: string;
  field?: string;
  message: string;
  severity: 'error' | 'warning';
}

// ============================================
// Tool Router Types
// ============================================

/**
 * Mode for the AI assistant
 */
export type AssistantMode = 'tool-router';

/**
 * Result of a tool call execution
 */
export interface ToolCallResult {
  id: string;
  toolName: string;
  toolkit: string;
  success: boolean;
  result?: unknown;
  error?: string;
  timestamp: string;
}

/**
 * Message in tool router conversation
 */
export interface ToolRouterMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: string;
  toolCalls?: ToolCallResult[];
  injectedArtifacts?: InjectedArtifactInfo[];
}

/**
 * Request to tool router API
 */
export interface ToolRouterChatRequest {
  message: string;
  conversationHistory?: ToolRouterMessage[];
  sessionId?: string;
}

/**
 * Injected artifact metadata for UI display
 */
export interface InjectedArtifactInfo {
  id: string;
  title: string;
  confidence: 'high' | 'possible';
}

/**
 * Response from tool router API
 */
export interface ToolRouterChatResponse {
  message: string;
  toolCalls?: ToolCallResult[];
  sessionId: string;
  injectedArtifacts?: InjectedArtifactInfo[];
}

// ============================================
// SSE Streaming Types
// ============================================

/**
 * SSE event types for streaming chat
 */
export type SSEEventType = 'text' | 'tool_call' | 'tool_result' | 'done' | 'error';

/**
 * Text delta event data
 */
export interface TextEventData {
  chunk: string;
}

/**
 * Tool call event data
 */
export interface ToolCallEventData {
  toolName: string;
  toolkit: string;
  id: string;
}

/**
 * Tool result event data
 */
export interface ToolResultEventData {
  toolName: string;
  toolkit: string;
  id: string;
  success: boolean;
  result?: unknown;
  error?: string;
}

/**
 * Done event data (final summary)
 */
export interface DoneEventData {
  toolCalls: ToolCallResult[];
  sessionId: string;
  injectedArtifacts?: InjectedArtifactInfo[];
}

/**
 * Error event data
 */
export interface ErrorEventData {
  message: string;
}

/**
 * Union type for all SSE event data
 */
export type SSEEventData = TextEventData | ToolCallEventData | ToolResultEventData | DoneEventData | ErrorEventData;

// ============================================
// Conversation History Types
// ============================================

/**
 * A saved conversation
 */
export interface Conversation {
  id: string;
  title: string;
  mode: AssistantMode;
  messages: ChatMessage[];
  toolRouterMessages: ToolRouterMessage[];
  createdAt: string;
  updatedAt: string;
}

/**
 * Conversation storage data structure
 */
export interface ConversationStorage {
  conversations: Conversation[];
  activeConversationId: string | null;
}
