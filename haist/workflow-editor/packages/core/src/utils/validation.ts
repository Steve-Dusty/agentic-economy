/**
 * Validation utilities for workflows
 */

import type { WorkflowNode, BubbleNodeData, TriggerNodeData } from '../types/node.types';
import type { WorkflowEdge } from '../types/edge.types';
import type { ValidationError } from '../types/workflow.types';
import { ParameterType } from '../types/parameter.types';
import { getBubble } from '../constants/bubble-registry';

/**
 * Validate an entire workflow
 */
export function validateWorkflow(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): ValidationError[] {
  const errors: ValidationError[] = [];

  // Check for at least one trigger
  const triggers = nodes.filter((n) => (n.data as TriggerNodeData).nodeType === 'trigger');
  if (triggers.length === 0) {
    errors.push({
      nodeId: null,
      message: 'Workflow must have at least one trigger',
      severity: 'error',
    });
  }

  // Check for multiple triggers (warning)
  if (triggers.length > 1) {
    errors.push({
      nodeId: null,
      message: 'Workflow has multiple triggers - only the first will be used',
      severity: 'warning',
    });
  }

  // Validate each node
  for (const node of nodes) {
    const nodeErrors = validateNode(node, nodes, edges);
    errors.push(...nodeErrors);
  }

  // Check for disconnected nodes
  const connectedNodeIds = new Set<string>();
  for (const edge of edges) {
    connectedNodeIds.add(edge.source);
    connectedNodeIds.add(edge.target);
  }

  for (const node of nodes) {
    const isTrigger = (node.data as TriggerNodeData).nodeType === 'trigger';
    if (!isTrigger && !connectedNodeIds.has(node.id)) {
      errors.push({
        nodeId: node.id,
        message: 'Node is not connected to the workflow',
        severity: 'warning',
      });
    }
  }

  // Check for cycles (would cause infinite loops)
  const cycleError = detectCycles(nodes, edges);
  if (cycleError) {
    errors.push(cycleError);
  }

  return errors;
}

/**
 * Validate a single node
 */
export function validateNode(
  node: WorkflowNode,
  _allNodes: WorkflowNode[],
  _edges: WorkflowEdge[]
): ValidationError[] {
  const errors: ValidationError[] = [];
  const data = node.data;

  if ('nodeType' in data && data.nodeType === 'bubble') {
    const bubbleData = data as BubbleNodeData;
    const bubbleDef = getBubble(bubbleData.bubbleName);

    if (!bubbleDef) {
      errors.push({
        nodeId: node.id,
        message: `Unknown bubble type: ${bubbleData.bubbleName}`,
        severity: 'error',
      });
      return errors;
    }

    // Check required parameters
    for (const [paramName, paramDef] of Object.entries(bubbleDef.schema)) {
      const param = bubbleData.parameters[paramName];

      // Variable type parameters (dynamic inputs) are resolved at runtime
      // Consider them valid if they have a referenced node
      const isVariableRef = param?.type === ParameterType.VARIABLE && param.referencedNodeId;

      const hasValue = param && (
        isVariableRef ||
        (param.value !== undefined && param.value !== null && param.value !== '')
      );

      if (paramDef.required && !hasValue) {
        errors.push({
          nodeId: node.id,
          message: `Required parameter "${paramName}" is missing`,
          severity: 'error',
          field: paramName,
        });
      }
    }
  }

  if ('nodeType' in data && data.nodeType === 'controlFlow') {
    // Validate control flow nodes
    if (data.controlType === 'if' || data.controlType === 'while') {
      if (!data.condition) {
        errors.push({
          nodeId: node.id,
          message: 'Condition is required',
          severity: 'error',
          field: 'condition',
        });
      }
    }

    if (data.controlType === 'for') {
      if (!data.iteratorVariable) {
        errors.push({
          nodeId: node.id,
          message: 'Iterator variable is required',
          severity: 'error',
          field: 'iteratorVariable',
        });
      }
      if (!data.iterableExpression) {
        errors.push({
          nodeId: node.id,
          message: 'Iterable expression is required',
          severity: 'error',
          field: 'iterableExpression',
        });
      }
    }
  }

  return errors;
}

/**
 * Detect cycles in the workflow graph
 */
function detectCycles(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): ValidationError | null {
  const adjacencyList = new Map<string, string[]>();

  // Build adjacency list
  for (const node of nodes) {
    adjacencyList.set(node.id, []);
  }
  for (const edge of edges) {
    const neighbors = adjacencyList.get(edge.source);
    if (neighbors) {
      neighbors.push(edge.target);
    }
  }

  // DFS to detect cycles
  const visited = new Set<string>();
  const recursionStack = new Set<string>();

  function dfs(nodeId: string): boolean {
    visited.add(nodeId);
    recursionStack.add(nodeId);

    const neighbors = adjacencyList.get(nodeId) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor)) return true;
      } else if (recursionStack.has(neighbor)) {
        return true;
      }
    }

    recursionStack.delete(nodeId);
    return false;
  }

  for (const node of nodes) {
    if (!visited.has(node.id)) {
      if (dfs(node.id)) {
        return {
          nodeId: null,
          message: 'Workflow contains a cycle which would cause infinite loops',
          severity: 'error',
        };
      }
    }
  }

  return null;
}

/**
 * Get topologically sorted nodes (execution order)
 */
export function topologicalSort(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[]
): WorkflowNode[] {
  const adjacencyList = new Map<string, string[]>();
  const inDegree = new Map<string, number>();
  const nodeMap = new Map<string, WorkflowNode>();

  // Initialize
  for (const node of nodes) {
    adjacencyList.set(node.id, []);
    inDegree.set(node.id, 0);
    nodeMap.set(node.id, node);
  }

  // Build graph
  for (const edge of edges) {
    const neighbors = adjacencyList.get(edge.source);
    if (neighbors) {
      neighbors.push(edge.target);
    }
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
  }

  // Kahn's algorithm
  const queue: string[] = [];
  for (const [nodeId, degree] of inDegree) {
    if (degree === 0) {
      queue.push(nodeId);
    }
  }

  const sorted: WorkflowNode[] = [];
  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    const node = nodeMap.get(nodeId);
    if (node) {
      sorted.push(node);
    }

    for (const neighbor of adjacencyList.get(nodeId) || []) {
      const newDegree = (inDegree.get(neighbor) || 0) - 1;
      inDegree.set(neighbor, newDegree);
      if (newDegree === 0) {
        queue.push(neighbor);
      }
    }
  }

  return sorted;
}
