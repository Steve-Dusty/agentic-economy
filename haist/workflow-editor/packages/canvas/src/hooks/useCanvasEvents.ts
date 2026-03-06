'use client';

/**
 * Canvas event handling hook
 */

import { useCallback } from 'react';
import { useReactFlow } from '@xyflow/react';
import { useWorkflowStore, useCanvasStore, useSelectionStore } from '@workflow-editor/state';
import type { WorkflowNode, NodeType, BubbleNodeData, TriggerNodeData } from '@workflow-editor/core';
import { generateNodeId, generateVariableName, getBubble, createBubbleNodeData, createTriggerNodeData } from '@workflow-editor/core';

/**
 * Hook for handling canvas events
 */
export function useCanvasEvents() {
  const { screenToFlowPosition, fitView } = useReactFlow();

  const nodes = useWorkflowStore((state) => state.nodes);
  const addNode = useWorkflowStore((state) => state.addNode);
  const removeNode = useWorkflowStore((state) => state.removeNode);
  const duplicateNode = useWorkflowStore((state) => state.duplicateNode);

  const selectedNodeIds = useSelectionStore((state) => state.selectedNodeIds);
  const clearSelection = useSelectionStore((state) => state.clearSelection);

  const setDropTarget = useCanvasStore((state) => state.setDropTarget);
  const setIsDraggingOver = useCanvasStore((state) => state.setIsDraggingOver);

  /**
   * Handle dropping a node from the palette
   */
  const handleDrop = useCallback(
    (event: React.DragEvent, position: { x: number; y: number }) => {
      event.preventDefault();
      setIsDraggingOver(false);
      setDropTarget(null);

      const nodeType = event.dataTransfer.getData('application/reactflow-type');
      const bubbleName = event.dataTransfer.getData('application/reactflow-bubble');

      if (!nodeType) return;

      // Get existing variable names for uniqueness
      const existingNames = nodes
        .filter((n): n is WorkflowNode => 'variableName' in n.data)
        .map((n) => (n.data as BubbleNodeData).variableName);

      let nodeData: WorkflowNode['data'];

      if (nodeType === 'trigger') {
        const triggerType = event.dataTransfer.getData('application/reactflow-trigger') as TriggerNodeData['triggerType'] || 'webhook/http';
        nodeData = createTriggerNodeData(triggerType);
      } else if (bubbleName) {
        const bubble = getBubble(bubbleName);
        if (bubble) {
          nodeData = {
            ...createBubbleNodeData(bubbleName, bubble.className, bubble.type),
            variableName: generateVariableName(bubbleName, existingNames),
          };
        } else {
          console.warn(`Unknown bubble: ${bubbleName}`);
          return;
        }
      } else {
        console.warn(`Unknown node type: ${nodeType}`);
        return;
      }

      const newNode: WorkflowNode = {
        id: generateNodeId(nodeType),
        type: nodeType,
        position,
        data: nodeData,
      };

      addNode(newNode);
    },
    [nodes, addNode, setDropTarget, setIsDraggingOver]
  );

  /**
   * Delete selected nodes
   */
  const deleteSelected = useCallback(() => {
    for (const nodeId of selectedNodeIds) {
      removeNode(nodeId);
    }
    clearSelection();
  }, [selectedNodeIds, removeNode, clearSelection]);

  /**
   * Duplicate selected nodes
   */
  const duplicateSelected = useCallback(() => {
    for (const nodeId of selectedNodeIds) {
      duplicateNode(nodeId);
    }
  }, [selectedNodeIds, duplicateNode]);

  /**
   * Fit view to show all nodes
   */
  const handleFitView = useCallback(() => {
    fitView({ padding: 0.2, duration: 200 });
  }, [fitView]);

  /**
   * Center view on a specific node
   */
  const centerOnNode = useCallback(
    (nodeId: string) => {
      const node = nodes.find((n) => n.id === nodeId);
      if (node) {
        fitView({
          nodes: [node],
          padding: 0.5,
          duration: 200,
        });
      }
    },
    [nodes, fitView]
  );

  return {
    handleDrop,
    deleteSelected,
    duplicateSelected,
    handleFitView,
    centerOnNode,
  };
}
