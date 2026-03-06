'use client';

/**
 * Node palette component - draggable node list
 */

import React, { useMemo, useEffect } from 'react';
import { Search, ChevronDown, ChevronRight, Link2 } from 'lucide-react';
import { clsx } from 'clsx';
import {
  getBubblesByType,
  TRIGGERS,
  type BubbleDefinition,
  type NodeCategory,
} from '@workflow-editor/core';
import { useUIStore, useComposioStore } from '@workflow-editor/state';

/**
 * Palette category data
 */
interface PaletteCategory {
  key: NodeCategory;
  name: string;
  items: PaletteItem[];
}

/**
 * Palette item data
 */
interface PaletteItem {
  id: string;
  name: string;
  description: string;
  nodeType: string;
  bubbleName?: string;
  triggerType?: string;
  // Composio-specific fields
  toolkit?: string;
  toolName?: string;
  color: string;
  icon: string;
}

/**
 * Composio toolkit metadata
 */
const COMPOSIO_TOOLKIT_META: Record<string, { icon: string; color: string }> = {
  GMAIL: { icon: '📧', color: '#EA4335' },
  GOOGLECALENDAR: { icon: '📅', color: '#4285F4' },
  GOOGLEDRIVE: { icon: '📁', color: '#0F9D58' },
  GOOGLEDOCS: { icon: '📄', color: '#4285F4' },
  GOOGLESHEETS: { icon: '📊', color: '#0F9D58' },
  SLACK: { icon: '💬', color: '#4A154B' },
  NOTION: { icon: '📝', color: '#000000' },
  GITHUB: { icon: '🐙', color: '#24292F' },
  OUTLOOK: { icon: '📬', color: '#0078D4' },
};

/**
 * Build palette categories from registry
 */
function buildCategories(
  composioTools: Record<string, Array<{ name: string; description: string; toolkit: string }>>,
  connectedToolkits: string[]
): PaletteCategory[] {
  const categories: PaletteCategory[] = [];

  // Triggers
  const triggerItems: PaletteItem[] = Object.values(TRIGGERS).map((trigger) => ({
    id: `trigger-${trigger.type}`,
    name: trigger.name,
    description: trigger.description,
    nodeType: 'trigger',
    triggerType: trigger.type,
    color: trigger.color,
    icon: trigger.icon,
  }));

  categories.push({
    key: 'triggers',
    name: 'Triggers',
    items: triggerItems,
  });

  // Service Bubbles
  const serviceBubbles = getBubblesByType('service');
  categories.push({
    key: 'service-bubbles',
    name: 'Services',
    items: serviceBubbles.map((b) => bubbleToItem(b, 'serviceBubble')),
  });

  // Tool Bubbles
  const toolBubbles = getBubblesByType('tool');
  categories.push({
    key: 'tool-bubbles',
    name: 'Tools',
    items: toolBubbles.map((b) => bubbleToItem(b, 'toolBubble')),
  });

  // Workflow Bubbles
  const workflowBubbles = getBubblesByType('workflow');
  categories.push({
    key: 'workflow-bubbles',
    name: 'Workflows',
    items: workflowBubbles.map((b) => bubbleToItem(b, 'workflowBubble')),
  });

  // Composio Services - show ONE item per connected toolkit (not per tool)
  const composioItems: PaletteItem[] = [];
  for (const toolkitId of connectedToolkits) {
    const tools = composioTools[toolkitId.toUpperCase()] || [];
    const meta = COMPOSIO_TOOLKIT_META[toolkitId.toUpperCase()] || { icon: '🔗', color: '#6B7280' };

    // Only add the toolkit if it has tools
    if (tools.length > 0) {
      // Get a readable toolkit name
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

      composioItems.push({
        id: `composio-${toolkitId.toUpperCase()}`,
        name: toolkitNames[toolkitId.toUpperCase()] || toolkitId,
        description: `${tools.length} tools available`,
        nodeType: 'composio',
        toolkit: toolkitId.toUpperCase(),
        // Don't set toolName - user will select from dropdown
        color: meta.color,
        icon: meta.icon,
      });
    }
  }

  categories.push({
    key: 'composio-services',
    name: 'Composio Services',
    items: composioItems,
  });

  return categories;
}

/**
 * Convert bubble definition to palette item
 */
function bubbleToItem(bubble: BubbleDefinition, nodeType: string): PaletteItem {
  return {
    id: bubble.name,
    name: bubble.className.replace('Bubble', '').replace('Tool', ''),
    description: bubble.shortDescription,
    nodeType,
    bubbleName: bubble.name,
    color: bubble.color,
    icon: bubble.icon,
  };
}

/**
 * Palette item component
 */
function PaletteItemComponent({ item }: { item: PaletteItem }) {
  const handleDragStart = (event: React.DragEvent) => {
    event.dataTransfer.setData('application/reactflow-type', item.nodeType);
    if (item.bubbleName) {
      event.dataTransfer.setData('application/reactflow-bubble', item.bubbleName);
    }
    if (item.triggerType) {
      event.dataTransfer.setData('application/reactflow-trigger', item.triggerType);
    }
    // Composio-specific data
    if (item.toolkit) {
      event.dataTransfer.setData('application/reactflow-toolkit', item.toolkit);
    }
    if (item.toolName) {
      event.dataTransfer.setData('application/reactflow-toolname', item.toolName);
    }
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      className={clsx(
        'flex items-center gap-2 px-3 py-2 rounded-md cursor-grab',
        'hover:bg-accent transition-colors',
        'active:cursor-grabbing'
      )}
    >
      <div
        className="w-6 h-6 rounded flex items-center justify-center text-white text-xs"
        style={{ backgroundColor: item.color }}
      >
        {item.name[0]}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{item.name}</div>
        <div className="text-xs text-muted-foreground truncate">
          {item.description}
        </div>
      </div>
    </div>
  );
}

/**
 * Palette category component
 */
function PaletteCategoryComponent({
  category,
  isComposioCategory,
  isLoadingTools,
  onConnectClick,
}: {
  category: PaletteCategory;
  isComposioCategory?: boolean;
  isLoadingTools?: boolean;
  onConnectClick?: () => void;
}) {
  const expandedCategories = useUIStore((state) => state.paletteExpandedCategories);
  const toggleCategory = useUIStore((state) => state.togglePaletteCategory);
  const searchQuery = useUIStore((state) => state.paletteSearchQuery);

  const isExpanded = expandedCategories.includes(category.key);

  // Filter items by search
  const filteredItems = useMemo(() => {
    if (!searchQuery) return category.items;
    const lower = searchQuery.toLowerCase();
    return category.items.filter(
      (item) =>
        item.name.toLowerCase().includes(lower) ||
        item.description.toLowerCase().includes(lower)
    );
  }, [category.items, searchQuery]);

  // Hide empty categories, except for Composio which shows a connect message
  if (filteredItems.length === 0 && !isComposioCategory) return null;

  return (
    <div className="border-b border-border last:border-b-0">
      <button
        onClick={() => toggleCategory(category.key)}
        className={clsx(
          'flex items-center gap-2 w-full px-3 py-2',
          'hover:bg-accent transition-colors text-left'
        )}
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4" />
        ) : (
          <ChevronRight className="w-4 h-4" />
        )}
        <span className="font-medium text-sm">{category.name}</span>
        <span className="text-xs text-muted-foreground ml-auto">
          {filteredItems.length}
        </span>
      </button>
      {isExpanded && (
        <div className="pb-2">
          {filteredItems.length > 0 ? (
            filteredItems.map((item) => (
              <PaletteItemComponent key={item.id} item={item} />
            ))
          ) : isComposioCategory ? (
            <div className="px-3 py-4 text-center">
              {isLoadingTools ? (
                <p className="text-xs text-muted-foreground">Loading tools...</p>
              ) : (
                <>
                  <p className="text-xs text-muted-foreground mb-2">
                    No services connected yet
                  </p>
                  <button
                    onClick={onConnectClick}
                    className="text-xs text-primary hover:underline"
                  >
                    Connect a service to see tools
                  </button>
                </>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

/**
 * Node palette component
 */
export function NodePalette() {
  const searchQuery = useUIStore((state) => state.paletteSearchQuery);
  const setSearch = useUIStore((state) => state.setPaletteSearch);
  const openDialog = useUIStore((state) => state.openDialog);

  // Composio state
  const availableTools = useComposioStore((state) => state.availableTools);
  const connectedAccounts = useComposioStore((state) => state.connectedAccounts);
  const isLoadingTools = useComposioStore((state) => state.isLoadingTools);
  const fetchConnectedAccounts = useComposioStore((state) => state.fetchConnectedAccounts);
  const fetchTools = useComposioStore((state) => state.fetchTools);

  // Derive connected toolkits from accounts (memoized to avoid SSR issues)
  const connectedToolkits = useMemo(() => {
    return connectedAccounts
      .filter((account) => account.status === 'ACTIVE')
      .map((account) => account.appName?.toUpperCase() || '')
      .filter(Boolean);
  }, [connectedAccounts]);

  // Fetch Composio state on mount
  useEffect(() => {
    fetchConnectedAccounts();
  }, [fetchConnectedAccounts]);

  // Fetch tools when connected toolkits change
  useEffect(() => {
    if (connectedToolkits.length > 0) {
      fetchTools(connectedToolkits);
    }
  }, [connectedToolkits, fetchTools]);

  const categories = useMemo(
    () => buildCategories(availableTools, connectedToolkits),
    [availableTools, connectedToolkits]
  );

  return (
    <div className="flex flex-col h-full bg-card border-r border-border">
      {/* Header */}
      <div className="p-3 border-b border-border">
        <h2 className="font-semibold text-sm mb-2">Node Palette</h2>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search nodes..."
            className={clsx(
              'w-full pl-8 pr-3 py-1.5 text-sm rounded-md',
              'bg-background border border-input',
              'focus:outline-none focus:ring-2 focus:ring-ring'
            )}
          />
        </div>
      </div>

      {/* Categories */}
      <div className="flex-1 overflow-y-auto">
        {categories.map((category) => (
          <PaletteCategoryComponent
            key={category.key}
            category={category}
            isComposioCategory={category.key === 'composio-services'}
            isLoadingTools={isLoadingTools}
            onConnectClick={() => openDialog('connections')}
          />
        ))}
      </div>

      {/* Connect services link */}
      <div className="p-3 border-t border-border">
        <button
          onClick={() => openDialog('connections')}
          className={clsx(
            'flex items-center gap-2 w-full px-3 py-2 text-sm rounded-md',
            'bg-accent/50 hover:bg-accent transition-colors text-left'
          )}
        >
          <Link2 className="w-4 h-4" />
          <span>Connect Services</span>
          {connectedToolkits.length > 0 && (
            <span className="ml-auto text-xs text-muted-foreground">
              {connectedToolkits.length} connected
            </span>
          )}
        </button>
      </div>

      {/* Help text */}
      <div className="p-3 text-xs text-muted-foreground border-t border-border">
        Drag nodes to the canvas to add them
      </div>
    </div>
  );
}
