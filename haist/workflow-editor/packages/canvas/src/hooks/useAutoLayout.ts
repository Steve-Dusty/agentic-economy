'use client';

/**
 * Auto-layout hook using dagre
 */

import { useCallback } from 'react';
import dagre from 'dagre';
import { useWorkflowStore } from '@workflow-editor/state';
import type { WorkflowNode, WorkflowEdge } from '@workflow-editor/core';

export interface LayoutOptions {
  /** Direction: TB (top-bottom), LR (left-right), BT, RL */
  direction?: 'TB' | 'LR' | 'BT' | 'RL';
  /** Node width for layout calculation */
  nodeWidth?: number;
  /** Node height for layout calculation */
  nodeHeight?: number;
  /** Horizontal spacing between nodes */
  horizontalSpacing?: number;
  /** Vertical spacing between nodes */
  verticalSpacing?: number;
}

const DEFAULT_OPTIONS: Required<LayoutOptions> = {
  direction: 'TB',
  nodeWidth: 250,
  nodeHeight: 100,
  horizontalSpacing: 50,
  verticalSpacing: 50,
};

/**
 * Calculate auto-layout positions for nodes
 */
export function calculateLayout(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  options: LayoutOptions = {}
): WorkflowNode[] {
  const opts = { ...DEFAULT_OPTIONS, ...options };

  // Create dagre graph
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: opts.direction,
    nodesep: opts.horizontalSpacing,
    ranksep: opts.verticalSpacing,
    marginx: 20,
    marginy: 20,
  });
  g.setDefaultEdgeLabel(() => ({}));

  // Add nodes
  for (const node of nodes) {
    g.setNode(node.id, {
      width: opts.nodeWidth,
      height: opts.nodeHeight,
    });
  }

  // Add edges
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  // Calculate layout
  dagre.layout(g);

  // Apply positions
  return nodes.map((node) => {
    const nodeWithPosition = g.node(node.id);
    if (nodeWithPosition) {
      return {
        ...node,
        position: {
          x: nodeWithPosition.x - opts.nodeWidth / 2,
          y: nodeWithPosition.y - opts.nodeHeight / 2,
        },
      };
    }
    return node;
  });
}

/**
 * Hook for auto-layout functionality
 */
export function useAutoLayout() {
  const nodes = useWorkflowStore((state) => state.nodes);
  const edges = useWorkflowStore((state) => state.edges);
  const setNodes = useWorkflowStore((state) => state.setNodes);

  /**
   * Apply auto-layout to all nodes
   */
  const applyLayout = useCallback(
    (options: LayoutOptions = {}) => {
      const layoutedNodes = calculateLayout(nodes, edges, options);
      setNodes(layoutedNodes);
    },
    [nodes, edges, setNodes]
  );

  /**
   * Apply horizontal layout (left to right)
   */
  const applyHorizontalLayout = useCallback(() => {
    applyLayout({ direction: 'LR' });
  }, [applyLayout]);

  /**
   * Apply vertical layout (top to bottom)
   */
  const applyVerticalLayout = useCallback(() => {
    applyLayout({ direction: 'TB' });
  }, [applyLayout]);

  return {
    applyLayout,
    applyHorizontalLayout,
    applyVerticalLayout,
  };
}
