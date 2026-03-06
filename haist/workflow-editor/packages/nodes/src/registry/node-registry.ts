/**
 * Node registry - maps node types to components
 */

import type { ComponentType } from 'react';
import type { NodeProps, NodeTypes } from '@xyflow/react';
import type { WorkflowNode, NodeType, NodeMetadata, NodeCategory } from '@workflow-editor/core';

import { TriggerNode } from '../components/triggers/TriggerNode';
import {
  ServiceBubbleNode,
  ToolBubbleNode,
  WorkflowBubbleNode,
} from '../components/bubbles/BubbleNode';
import { ComposioNode } from '../components/composio/ComposioNode';

/**
 * Node registry entry
 */
export interface NodeRegistryEntry {
  type: string;
  component: ComponentType<NodeProps<WorkflowNode>>;
  metadata: NodeMetadata;
}

/**
 * Default node types for ReactFlow
 * Cast through unknown to satisfy NodeTypes while maintaining type safety in components
 */
export const defaultNodeTypes: NodeTypes = {
  trigger: TriggerNode as unknown as ComponentType<NodeProps>,
  serviceBubble: ServiceBubbleNode as unknown as ComponentType<NodeProps>,
  toolBubble: ToolBubbleNode as unknown as ComponentType<NodeProps>,
  workflowBubble: WorkflowBubbleNode as unknown as ComponentType<NodeProps>,
  composio: ComposioNode as unknown as ComponentType<NodeProps>,
};

/**
 * Node registry class
 */
class NodeRegistryClass {
  private nodes: Map<string, NodeRegistryEntry> = new Map();
  private nodeTypes: NodeTypes = { ...defaultNodeTypes };

  constructor() {
    // Register default nodes
    this.registerDefaults();
  }

  /**
   * Register default node types
   */
  private registerDefaults() {
    // Trigger
    this.register({
      type: 'trigger',
      component: TriggerNode as ComponentType<NodeProps<WorkflowNode>>,
      metadata: {
        name: 'Trigger',
        description: 'Workflow entry point',
        category: 'triggers',
        icon: 'webhook',
        color: '#10b981',
        inputs: [],
        outputs: [
          {
            id: 'output',
            name: 'Output',
            type: 'data',
            position: 'bottom',
          },
        ],
        defaultData: {
          label: 'Trigger',
          nodeType: 'trigger',
          triggerType: 'webhook/http',
          isValid: true,
          validationErrors: [],
        },
      },
    });

    // Service Bubble
    this.register({
      type: 'serviceBubble',
      component: ServiceBubbleNode as ComponentType<NodeProps<WorkflowNode>>,
      metadata: {
        name: 'Service',
        description: 'External service integration',
        category: 'service-bubbles',
        icon: 'globe',
        color: '#3b82f6',
        inputs: [
          {
            id: 'input',
            name: 'Input',
            type: 'data',
            position: 'top',
          },
        ],
        outputs: [
          {
            id: 'output',
            name: 'Output',
            type: 'data',
            position: 'bottom',
          },
        ],
        defaultData: {
          label: 'Service',
          nodeType: 'bubble',
          bubbleType: 'service',
          isValid: false,
          validationErrors: [],
        },
      },
    });

    // Tool Bubble
    this.register({
      type: 'toolBubble',
      component: ToolBubbleNode as ComponentType<NodeProps<WorkflowNode>>,
      metadata: {
        name: 'Tool',
        description: 'Utility tool',
        category: 'tool-bubbles',
        icon: 'wrench',
        color: '#f59e0b',
        inputs: [
          {
            id: 'input',
            name: 'Input',
            type: 'data',
            position: 'top',
          },
        ],
        outputs: [
          {
            id: 'output',
            name: 'Output',
            type: 'data',
            position: 'bottom',
          },
        ],
        defaultData: {
          label: 'Tool',
          nodeType: 'bubble',
          bubbleType: 'tool',
          isValid: false,
          validationErrors: [],
        },
      },
    });

    // Workflow Bubble
    this.register({
      type: 'workflowBubble',
      component: WorkflowBubbleNode as ComponentType<NodeProps<WorkflowNode>>,
      metadata: {
        name: 'Workflow',
        description: 'Composite workflow',
        category: 'workflow-bubbles',
        icon: 'workflow',
        color: '#8b5cf6',
        inputs: [
          {
            id: 'input',
            name: 'Input',
            type: 'data',
            position: 'top',
          },
        ],
        outputs: [
          {
            id: 'output',
            name: 'Output',
            type: 'data',
            position: 'bottom',
          },
        ],
        defaultData: {
          label: 'Workflow',
          nodeType: 'bubble',
          bubbleType: 'workflow',
          isValid: false,
          validationErrors: [],
        },
      },
    });

    // Composio - External service integrations via Composio SDK
    this.register({
      type: 'composio',
      component: ComposioNode as ComponentType<NodeProps<WorkflowNode>>,
      metadata: {
        name: 'Composio',
        description: 'External service integration via Composio',
        category: 'composio-services',
        icon: 'cloud',
        color: '#6366f1',
        inputs: [
          {
            id: 'input',
            name: 'Input',
            type: 'data',
            position: 'top',
          },
        ],
        outputs: [
          {
            id: 'output',
            name: 'Output',
            type: 'data',
            position: 'bottom',
          },
        ],
        defaultData: {
          label: 'Composio Tool',
          nodeType: 'composio',
          toolkit: '',
          toolName: '',
          isValid: false,
          validationErrors: [],
        },
      },
    });
  }

  /**
   * Register a node type
   */
  register(entry: NodeRegistryEntry): void {
    this.nodes.set(entry.type, entry);
    this.nodeTypes[entry.type] = entry.component as ComponentType<NodeProps>;
  }

  /**
   * Unregister a node type
   */
  unregister(type: string): void {
    this.nodes.delete(type);
    delete this.nodeTypes[type];
  }

  /**
   * Get a node entry by type
   */
  get(type: string): NodeRegistryEntry | undefined {
    return this.nodes.get(type);
  }

  /**
   * Get all node entries
   */
  getAll(): NodeRegistryEntry[] {
    return Array.from(this.nodes.values());
  }

  /**
   * Get nodes by category
   */
  getByCategory(category: NodeCategory): NodeRegistryEntry[] {
    return this.getAll().filter((entry) => entry.metadata.category === category);
  }

  /**
   * Get ReactFlow node types object
   */
  getNodeTypes(): NodeTypes {
    return this.nodeTypes;
  }

  /**
   * Check if a node type is registered
   */
  has(type: string): boolean {
    return this.nodes.has(type);
  }
}

/**
 * Global node registry instance
 */
export const NodeRegistry = new NodeRegistryClass();
