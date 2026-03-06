'use client';

/**
 * Main workflow canvas component
 */

import React, { useCallback, useRef, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type Connection,
  type NodeTypes,
  type EdgeTypes,
  type ReactFlowInstance,
  type Node,
  type Edge,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useWorkflowStore, useCanvasStore, useSelectionStore } from '@workflow-editor/state';
import type { WorkflowNode, WorkflowEdge } from '@workflow-editor/core';
import { generateEdgeId } from '@workflow-editor/core';

export interface CanvasProps {
  /** Custom node types */
  nodeTypes?: NodeTypes;
  /** Custom edge types */
  edgeTypes?: EdgeTypes;
  /** Called when canvas is initialized */
  onInit?: (instance: ReactFlowInstance<WorkflowNode, WorkflowEdge>) => void;
  /** Called when a node is dropped from palette */
  onDrop?: (event: React.DragEvent, position: { x: number; y: number }) => void;
  /** Children (custom overlays) */
  children?: React.ReactNode;
}

/**
 * Main workflow canvas component
 */
export function Canvas({
  nodeTypes = {},
  edgeTypes = {},
  onInit,
  onDrop,
  children,
}: CanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  // Workflow store
  const nodes = useWorkflowStore((state) => state.nodes);
  const edges = useWorkflowStore((state) => state.edges);
  const setNodes = useWorkflowStore((state) => state.setNodes);
  const setEdges = useWorkflowStore((state) => state.setEdges);
  const addEdgeToStore = useWorkflowStore((state) => state.addEdge);

  // Canvas store
  const showGrid = useCanvasStore((state) => state.showGrid);
  const showMinimap = useCanvasStore((state) => state.showMinimap);
  const snapToGrid = useCanvasStore((state) => state.snapToGrid);
  const gridSize = useCanvasStore((state) => state.gridSize);
  const setViewport = useCanvasStore((state) => state.setViewport);
  const setIsDraggingOver = useCanvasStore((state) => state.setIsDraggingOver);
  const setDropTarget = useCanvasStore((state) => state.setDropTarget);

  // Selection store
  const selectNode = useSelectionStore((state) => state.selectNode);
  const selectEdge = useSelectionStore((state) => state.selectEdge);
  const clearSelection = useSelectionStore((state) => state.clearSelection);

  // Handle node changes (position, selection, etc.)
  // Clone nodes to avoid mutating frozen immer state
  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      const clonedNodes = nodes.map((n) => ({ ...n, data: { ...n.data } }));
      const updatedNodes = applyNodeChanges(changes, clonedNodes) as WorkflowNode[];
      setNodes(updatedNodes);
    },
    [nodes, setNodes]
  );

  // Handle edge changes
  // Clone edges to avoid mutating frozen immer state
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      const clonedEdges = edges.map((e) => ({ ...e, data: e.data ? { ...e.data } : undefined }));
      const updatedEdges = applyEdgeChanges(changes, clonedEdges) as WorkflowEdge[];
      setEdges(updatedEdges);
    },
    [edges, setEdges]
  );

  // Handle new connections
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (connection.source && connection.target) {
        const newEdge: WorkflowEdge = {
          id: generateEdgeId(connection.source, connection.target),
          source: connection.source,
          target: connection.target,
          sourceHandle: connection.sourceHandle ?? undefined,
          targetHandle: connection.targetHandle ?? undefined,
          data: {
            edgeType: 'data',
          },
        };
        addEdgeToStore(newEdge);
      }
    },
    [addEdgeToStore]
  );

  // Handle node selection
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      selectNode(node.id, _event.shiftKey || _event.metaKey);
    },
    [selectNode]
  );

  // Handle edge selection
  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      selectEdge(edge.id, _event.shiftKey || _event.metaKey);
    },
    [selectEdge]
  );

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  // Handle viewport change
  const onMoveEnd = useCallback(
    (_event: unknown, viewport: { x: number; y: number; zoom: number }) => {
      setViewport(viewport);
    },
    [setViewport]
  );

  // Handle drag over
  const onDragOver = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = 'move';
      setIsDraggingOver(true);

      if (reactFlowWrapper.current) {
        const bounds = reactFlowWrapper.current.getBoundingClientRect();
        const position = screenToFlowPosition({
          x: event.clientX - bounds.left,
          y: event.clientY - bounds.top,
        });
        setDropTarget(position);
      }
    },
    [screenToFlowPosition, setIsDraggingOver, setDropTarget]
  );

  // Handle drag leave
  const onDragLeave = useCallback(() => {
    setIsDraggingOver(false);
    setDropTarget(null);
  }, [setIsDraggingOver, setDropTarget]);

  // Handle drop
  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setIsDraggingOver(false);
      setDropTarget(null);

      if (reactFlowWrapper.current && onDrop) {
        const bounds = reactFlowWrapper.current.getBoundingClientRect();
        const position = screenToFlowPosition({
          x: event.clientX - bounds.left,
          y: event.clientY - bounds.top,
        });
        onDrop(event, position);
      }
    },
    [screenToFlowPosition, onDrop, setIsDraggingOver, setDropTarget]
  );

  // Memoize default edge options
  const defaultEdgeOptions = useMemo(
    () => ({
      animated: false,
      style: { strokeWidth: 2 },
    }),
    []
  );

  return (
    <div ref={reactFlowWrapper} className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        onMoveEnd={onMoveEnd}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={handleDrop}
        onInit={onInit}
        snapToGrid={snapToGrid}
        snapGrid={[gridSize, gridSize]}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        attributionPosition="bottom-left"
        className="bg-background"
      >
        {showGrid && (
          <Background
            variant={BackgroundVariant.Dots}
            gap={gridSize}
            size={1}
            color="hsl(var(--muted-foreground) / 0.3)"
          />
        )}
        <Controls showInteractive={false} />
        {showMinimap && (
          <MiniMap
            nodeStrokeWidth={3}
            zoomable
            pannable
            className="bg-background border rounded-lg"
          />
        )}
        {children}
      </ReactFlow>
    </div>
  );
}
