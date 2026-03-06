/**
 * Plugin system types for extensibility
 */

import type { ComponentType } from 'react';
import type { NodeProps, EdgeProps } from '@xyflow/react';
import type { WorkflowNode } from './node.types';
import type { NodeMetadata, NodeCategory } from './node.types';
import type { WorkflowEdge, WorkflowEdgeData } from './edge.types';

/**
 * Main plugin interface
 */
export interface WorkflowEditorPlugin {
  /** Unique plugin identifier */
  id: string;
  /** Display name */
  name: string;
  /** Plugin version */
  version: string;
  /** Plugin description */
  description?: string;

  /** Lifecycle: called when plugin is registered */
  onRegister?: (registry: PluginRegistryAPI) => void;
  /** Lifecycle: called when plugin is unregistered */
  onUnregister?: () => void;

  /** Node contributions */
  nodes?: NodeContribution[];
  /** Edge contributions */
  edges?: EdgeContribution[];
  /** Palette category contributions */
  paletteCategories?: PaletteCategoryContribution[];
  /** Code generator contributions */
  codeGenerators?: CodeGeneratorContribution[];
}

/**
 * Node contribution from a plugin
 */
export interface NodeContribution {
  /** Unique node type key */
  type: string;
  /** React component for rendering the node */
  component: ComponentType<NodeProps>;
  /** Node metadata for palette and registry */
  metadata: NodeMetadata;
  /** Optional custom config panel component */
  configPanel?: ComponentType<ConfigPanelProps>;
  /** Code generator function */
  codeGenerator?: (node: WorkflowNode) => string;
  /** Import statements for code generation */
  imports?: (node: WorkflowNode) => string[];
}

/**
 * Edge contribution from a plugin
 */
export interface EdgeContribution {
  /** Unique edge type key */
  type: string;
  /** React component for rendering the edge */
  component: ComponentType<EdgeProps<WorkflowEdge>>;
  /** Default data for new edges of this type */
  defaultData?: Partial<WorkflowEdgeData>;
}

/**
 * Palette category contribution
 */
export interface PaletteCategoryContribution {
  /** Category key */
  key: NodeCategory | string;
  /** Display name */
  name: string;
  /** Optional icon */
  icon?: string;
  /** Sort order (lower = higher) */
  order?: number;
}

/**
 * Code generator contribution
 */
export interface CodeGeneratorContribution {
  /** Node type this generator handles */
  nodeType: string;
  /** Generate code for the node */
  generate: (node: WorkflowNode, context: GeneratorContext) => string;
  /** Get import statements */
  imports: (node: WorkflowNode) => string[];
  /** Priority (higher = processed first) */
  priority?: number;
}

/**
 * Context passed to code generators
 */
export interface GeneratorContext {
  /** All nodes in the workflow */
  nodes: WorkflowNode[];
  /** Get a node by ID */
  getNode: (id: string) => WorkflowNode | undefined;
  /** Get nodes connected to this node's inputs */
  getInputNodes: (nodeId: string) => WorkflowNode[];
  /** Get nodes connected to this node's outputs */
  getOutputNodes: (nodeId: string) => WorkflowNode[];
  /** Indent level for code formatting */
  indentLevel: number;
  /** Get indent string */
  indent: () => string;
}

/**
 * Props for custom config panel components
 */
export interface ConfigPanelProps {
  /** The selected node */
  node: WorkflowNode;
  /** Update node data */
  onUpdate: (data: Partial<WorkflowNode['data']>) => void;
}

/**
 * API exposed to plugins during registration
 */
export interface PluginRegistryAPI {
  /** Register a node type */
  registerNode: (contribution: NodeContribution) => void;
  /** Unregister a node type */
  unregisterNode: (type: string) => void;
  /** Register an edge type */
  registerEdge: (contribution: EdgeContribution) => void;
  /** Unregister an edge type */
  unregisterEdge: (type: string) => void;
  /** Register a code generator */
  registerCodeGenerator: (contribution: CodeGeneratorContribution) => void;
  /** Get all registered node types */
  getNodeTypes: () => string[];
  /** Get all registered edge types */
  getEdgeTypes: () => string[];
}

/**
 * Plugin validation result
 */
export interface PluginValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * Validate a plugin before registration
 */
export function validatePlugin(plugin: WorkflowEditorPlugin): PluginValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!plugin.id) {
    errors.push('Plugin must have an id');
  }

  if (!plugin.name) {
    errors.push('Plugin must have a name');
  }

  if (!plugin.version) {
    errors.push('Plugin must have a version');
  }

  if (plugin.nodes) {
    for (const node of plugin.nodes) {
      if (!node.type) {
        errors.push('Node contribution must have a type');
      }
      if (!node.component) {
        errors.push(`Node ${node.type} must have a component`);
      }
      if (!node.metadata) {
        errors.push(`Node ${node.type} must have metadata`);
      }
    }
  }

  if (plugin.codeGenerators) {
    for (const gen of plugin.codeGenerators) {
      if (!gen.nodeType) {
        errors.push('Code generator must specify a nodeType');
      }
      if (!gen.generate) {
        errors.push(`Code generator for ${gen.nodeType} must have a generate function`);
      }
      if (!gen.imports) {
        warnings.push(`Code generator for ${gen.nodeType} has no imports function`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}
