# Composio Integration for Workflow Editor

## Overview

This document describes the integration of Composio into the BubbleLab Workflow Editor. Composio provides 300+ service integrations (Gmail, Slack, Notion, Google Calendar, etc.) with managed OAuth authentication.

**Goal:** Add Composio as a new node category alongside existing BubbleRunner-based bubbles.

---

## Architecture

### Execution Flows

```
EXISTING (BubbleRunner):
  Workflow Node → Codegen → BubbleRunner → @bubblelab/bubble-core → Service

NEW (Composio):
  Composio Node → API Route → @composio/core SDK → External Service
```

### Node Categories

| Category | Source | Execution Engine |
|----------|--------|-----------------|
| Triggers | Static registry | BubbleRunner |
| Services (Bubbles) | Static registry | BubbleRunner |
| Tools (Bubbles) | Static registry | BubbleRunner |
| Workflows (Bubbles) | Static registry | BubbleRunner |
| **Composio Services** | **Composio SDK** | **Composio SDK** |

---

## Supported Toolkits

The following Composio toolkits are supported:

| Toolkit | Description | Example Tools |
|---------|-------------|---------------|
| GMAIL | Email management | GMAIL_SEND_EMAIL, GMAIL_FETCH_EMAILS |
| GOOGLECALENDAR | Calendar management | GOOGLECALENDAR_CREATE_EVENT, GOOGLECALENDAR_LIST_EVENTS |
| SLACK | Team messaging | SLACK_SEND_MESSAGE, SLACK_CREATE_CHANNEL |
| NOTION | Workspace & docs | NOTION_CREATE_PAGE, NOTION_QUERY_DATABASE |
| GOOGLEDRIVE | File storage | GOOGLEDRIVE_UPLOAD_FILE, GOOGLEDRIVE_LIST_FILES |
| GOOGLEDOCS | Document editing | GOOGLEDOCS_CREATE_DOCUMENT |
| GOOGLESHEETS | Spreadsheets | GOOGLESHEETS_BATCH_UPDATE, GOOGLESHEETS_QUERY_TABLE |
| GITHUB | Code management | GITHUB_CREATE_ISSUE, GITHUB_LIST_REPOSITORIES |
| OUTLOOK | Microsoft email/calendar | OUTLOOK_SEND_EMAIL, OUTLOOK_LIST_EVENTS |

---

## Implementation

### Phase 1: Service Layer

**Files:**
- `apps/web/src/lib/composio/composio-service.ts` - Composio SDK wrapper
- `apps/web/src/lib/composio/composio-toolkits.ts` - Toolkit metadata

**ComposioService Class:**

```typescript
import { Composio } from "@composio/core";

class ComposioService {
  private composio: Composio;

  constructor() {
    this.composio = new Composio({
      apiKey: process.env.COMPOSIO_API_KEY,
      toolkitVersions: {
        gmail: "20251222_00",
        googlecalendar: "20251222_00",
        slack: "20251222_00",
        notion: "20251027_00",
        // ...
      }
    });
  }

  // Get available tools for a user
  async getUserTools(userId: string, toolkits: string[]) {
    return await this.composio.tools.get(userId, { toolkits });
  }

  // Get user's connected accounts
  async getUserConnectedAccounts(userId: string) {
    const accounts = await this.composio.connectedAccounts.list({
      userIds: [userId]
    });
    return accounts.items;
  }

  // Start OAuth flow
  async initiateAuthentication(userId: string, authConfigId: string, redirectUrl: string) {
    return await this.composio.connectedAccounts.initiate(
      userId,
      authConfigId,
      { callbackUrl: redirectUrl }
    );
  }

  // Execute a tool
  async executeTool(toolName: string, userId: string, args: object) {
    return await this.composio.tools.execute(toolName, {
      userId,
      arguments: args
    });
  }
}

export const composioService = new ComposioService();
```

---

### Phase 2: API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/composio/tools` | GET | List available tools |
| `/api/composio/auth/[appName]` | POST | Initiate OAuth |
| `/api/composio/callback` | GET | OAuth callback |
| `/api/composio/connected-accounts` | GET | List connected accounts |
| `/api/composio/execute` | POST | Execute a tool |

**Example: Execute Tool Route**

```typescript
// apps/web/src/app/api/composio/execute/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { composioService } from '@/lib/composio/composio-service';

export async function POST(request: NextRequest) {
  const { toolName, userId, arguments: args } = await request.json();

  const result = await composioService.executeTool(toolName, userId, args);

  return NextResponse.json({
    success: result.successful,
    data: result.data,
    error: result.error
  });
}
```

---

### Phase 3: Node Types

**ComposioNodeData:**

```typescript
// packages/core/src/types/node.types.ts

export interface ComposioNodeData extends BaseNodeData {
  nodeType: 'composio';
  toolkit: string;              // 'GMAIL', 'SLACK', etc.
  toolName: string;             // 'GMAIL_SEND_EMAIL', etc.
  variableName: string;         // Variable name for outputs
  parameters: Record<string, ParameterValue>;
}
```

---

### Phase 4: State Management

**ComposioStore:**

```typescript
// packages/state/src/stores/composio-store.ts
import { create } from 'zustand';

interface ConnectedAccount {
  id: string;
  toolkit: string;
  status: 'ACTIVE' | 'INITIATED' | 'EXPIRED';
}

interface ComposioState {
  connectedAccounts: ConnectedAccount[];
  isLoading: boolean;

  // Actions
  fetchConnectedAccounts: () => Promise<void>;
  initiateAuth: (appName: string) => Promise<string>;
}

export const useComposioStore = create<ComposioState>((set) => ({
  connectedAccounts: [],
  isLoading: false,

  fetchConnectedAccounts: async () => {
    set({ isLoading: true });
    const res = await fetch('/api/composio/connected-accounts');
    const data = await res.json();
    set({ connectedAccounts: data.accounts, isLoading: false });
  },

  initiateAuth: async (appName) => {
    const res = await fetch(`/api/composio/auth/${appName}`, {
      method: 'POST',
      body: JSON.stringify({ redirectUrl: window.location.origin + '/composio/callback' })
    });
    const data = await res.json();
    return data.authRequest.redirectUrl;
  }
}));
```

---

### Phase 5: UI Components

**ComposioConnectionManager:**

```tsx
// packages/ui/src/components/composio/ComposioConnectionManager.tsx

export function ComposioConnectionManager() {
  const { connectedAccounts, fetchConnectedAccounts, initiateAuth } = useComposioStore();

  const toolkits = [
    { id: 'GMAIL', name: 'Gmail', icon: '📧' },
    { id: 'SLACK', name: 'Slack', icon: '💬' },
    { id: 'NOTION', name: 'Notion', icon: '📝' },
    // ...
  ];

  const handleConnect = async (toolkit: string) => {
    const redirectUrl = await initiateAuth(toolkit);
    window.open(redirectUrl, '_blank', 'width=600,height=700');
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      {toolkits.map(toolkit => {
        const account = connectedAccounts.find(a => a.toolkit === toolkit.id);
        const isConnected = account?.status === 'ACTIVE';

        return (
          <div key={toolkit.id} className="p-4 border rounded-lg">
            <div className="flex items-center gap-2">
              <span>{toolkit.icon}</span>
              <span>{toolkit.name}</span>
            </div>
            <button
              onClick={() => isConnected ? null : handleConnect(toolkit.id)}
              className={isConnected ? 'bg-green-100' : 'bg-blue-500 text-white'}
            >
              {isConnected ? '✓ Connected' : 'Connect'}
            </button>
          </div>
        );
      })}
    </div>
  );
}
```

---

### Phase 6: Execution Integration

**Hybrid Execution:**

```typescript
// apps/web/src/app/api/workflow/execute/route.ts

async function executeWorkflow(nodes, edges, payload) {
  const sortedNodes = topologicalSort(nodes, edges);
  const results: Record<string, any> = {};

  for (const node of sortedNodes) {
    const nodeData = node.data;

    if (nodeData.nodeType === 'composio') {
      // Execute via Composio SDK
      const resolvedParams = resolveParameters(nodeData.parameters, results);
      const result = await composioService.executeTool(
        nodeData.toolName,
        userId,
        resolvedParams
      );
      results[nodeData.variableName] = result;
    } else if (nodeData.nodeType === 'bubble') {
      // Execute via BubbleRunner (existing path)
      const result = await executeBubbleNode(node, results);
      results[nodeData.variableName] = result;
    }
  }

  return results;
}
```

---

## Environment Variables

Add to `apps/web/.env.local`:

```bash
# Composio API Key
COMPOSIO_API_KEY=your_composio_api_key

# Auth Config IDs (from Composio dashboard)
GMAIL_AUTH_CONFIG_ID=
GOOGLE_CALENDAR_AUTH_CONFIG_ID=
SLACK_AUTH_CONFIG_ID=
NOTION_AUTH_CONFIG_ID=
GITHUB_AUTH_CONFIG_ID=
GOOGLE_DRIVE_AUTH_CONFIG_ID=
GOOGLE_DOCS_AUTH_CONFIG_ID=
GOOGLE_SHEETS_AUTH_CONFIG_ID=
OUTLOOK_AUTH_CONFIG_ID=
```

---

## User Flow

### 1. Connect Services

1. User clicks "Connections" button in toolbar
2. ComposioConnectionManager dialog opens
3. User clicks "Connect Gmail"
4. OAuth popup opens → user authorizes
5. Popup closes, status updates to "Connected"

### 2. Use Composio Tools

1. NodePalette shows "Composio Services" category
2. Only connected services' tools appear (Gmail, Slack, etc.)
3. User drags "Gmail: Send Email" to canvas
4. ConfigPanel shows tool parameters (to, subject, body)
5. User configures parameters

### 3. Execute Workflow

1. User clicks "Run" button
2. Workflow execution starts
3. Bubble nodes → BubbleRunner
4. Composio nodes → Composio SDK
5. Results merged and displayed in output panel

---

## File Structure

```
apps/web/
├── src/
│   ├── lib/
│   │   └── composio/
│   │       ├── composio-service.ts      # SDK wrapper
│   │       └── composio-toolkits.ts     # Toolkit metadata
│   └── app/
│       └── api/
│           └── composio/
│               ├── tools/route.ts
│               ├── auth/[appName]/route.ts
│               ├── callback/route.ts
│               ├── connected-accounts/route.ts
│               └── execute/route.ts

packages/
├── core/
│   └── src/
│       ├── types/node.types.ts          # + ComposioNodeData
│       └── constants/composio-registry.ts
├── state/
│   └── src/
│       └── stores/composio-store.ts
├── ui/
│   └── src/
│       └── components/
│           └── composio/
│               ├── ComposioConnectionManager.tsx
│               └── ComposioAuthButton.tsx
└── nodes/
    └── src/
        └── components/
            └── composio/
                └── ComposioNode.tsx
```

---

## Reference

### blockd-backend Files (for implementation reference)

| File | Purpose |
|------|---------|
| `src/composio/composio-service.ts` | SDK patterns, tool fetching, OAuth flow |
| `src/api/composio-routes.ts` | API route structure |
| `src/mcp/composio-toolkits-data.ts` | Toolkit metadata to copy |

### External Resources

- [Composio Documentation](https://docs.composio.dev/)
- [@composio/core npm](https://www.npmjs.com/package/@composio/core)
