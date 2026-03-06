# BubbleLab Workflow Editor

A modular Next.js visual workflow editor for BubbleLab using ReactFlow, shadcn/ui, and Zustand. Generates TypeScript BubbleFlow code.

## Architecture Overview

This is a **Turborepo monorepo** with modular packages for maximum reusability and maintainability.

```
workflow-editor/
├── packages/
│   ├── @workflow-editor/core/        # Types, constants, utilities
│   ├── @workflow-editor/canvas/      # ReactFlow canvas module
│   ├── @workflow-editor/nodes/       # Node components & registry
│   ├── @workflow-editor/edges/       # Edge components
│   ├── @workflow-editor/state/       # Zustand stores
│   ├── @workflow-editor/codegen/     # TypeScript code generation
│   └── @workflow-editor/ui/          # Shared UI components (shadcn/ui)
├── apps/
│   └── web/                          # Next.js application
├── package.json                      # Workspace root
├── turbo.json                        # Turborepo config
└── tsconfig.json                     # Base TypeScript config
```

## Tech Stack

| Technology | Purpose |
|------------|---------|
| **Next.js 14+** | App Router, React Server Components |
| **ReactFlow** | Visual canvas for node-based workflows |
| **shadcn/ui** | Accessible, customizable UI components |
| **Tailwind CSS** | Utility-first styling |
| **Zustand** | Lightweight state management |
| **Turborepo** | Monorepo build system |
| **TypeScript** | Type safety throughout |

## Packages

### @workflow-editor/core
Core types, constants, and utilities shared across all packages.

- **Types:** `WorkflowNode`, `WorkflowEdge`, `BubbleNodeData`, `ParameterValue`
- **Constants:** Bubble registry (50+ bubbles), trigger types, parameter types
- **Utils:** ID generation, validation helpers

### @workflow-editor/state
Zustand stores for application state.

| Store | Responsibility |
|-------|---------------|
| `workflow-store` | Nodes, edges, metadata, trigger config |
| `canvas-store` | Viewport, grid, minimap, interaction mode |
| `selection-store` | Selected nodes/edges, hover state |
| `history-store` | Undo/redo stack |
| `ui-store` | Panel visibility, tabs, dialogs |

### @workflow-editor/canvas
ReactFlow canvas wrapper with custom hooks.

- `Canvas.tsx` - Main ReactFlow component
- `useCanvasEvents` - Drag-drop, connection handling
- `useAutoLayout` - Dagre-based auto-arrangement

### @workflow-editor/nodes
Node components and registry system.

**Node Types:**
- **Triggers:** Webhook, Cron, Slack
- **Bubbles:** Service, Tool, Workflow
- **Control Flow:** If/Else, For Loop, While, Try/Catch, Parallel
- **Utilities:** Code Block, Comment

### @workflow-editor/edges
Edge components for data and control flow.

- `DataFlowEdge` - Standard data connections
- `ControlFlowEdge` - Branching (then/else/catch)
- `ErrorEdge` - Error path visualization

### @workflow-editor/ui
Shared UI components built with shadcn/ui.

- **Palette:** Draggable node palette with search
- **Config Panel:** Parameter forms with type-specific inputs
- **Toolbar:** File, edit, view, run menus
- **Code Preview:** Syntax-highlighted TypeScript output

### @workflow-editor/codegen
TypeScript code generation from visual workflows.

**Pipeline:**
```
Workflow Graph → Topological Sort → AST Generation → TypeScript Code
```

**Output Example:**
```typescript
import { BubbleFlow, RedditScrapeTool, AIAgentBubble } from '@bubblelab/bubble-core';

export class MyFlow extends BubbleFlow<'webhook/http'> {
  async handle(payload: WebhookEvent) {
    const scrapeResult = await new RedditScrapeTool({
      subreddit: payload.subreddit,
      limit: 10,
    }).action();

    const summaryResult = await new AIAgentBubble({
      message: `Summarize: ${JSON.stringify(scrapeResult.data)}`,
      model: { model: 'google/gemini-2.5-flash' },
    }).action();

    return { summary: summaryResult.data?.response };
  }
}
```

## UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│                      EditorToolbar                          │
├──────────┬────────────────────────────────┬─────────────────┤
│          │                                │                 │
│  Node    │         Canvas                 │    Config       │
│  Palette │       (ReactFlow)              │    Panel        │
│          │                                │                 │
│ [Search] │    ┌──────┐    ┌──────┐       │  [Parameters]   │
│          │    │Trigger│───▶│Bubble│       │  [Schema]       │
│ Triggers │    └──────┘    └──────┘       │  [Code Preview] │
│ Services │                                │                 │
│ Tools    │                                │                 │
│ Control  │                                │                 │
│          │                                │                 │
└──────────┴────────────────────────────────┴─────────────────┘
```

## Getting Started

### Prerequisites
- Node.js 18+
- pnpm 8+

### Installation

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build all packages
pnpm build
```

### Development

```bash
# Run the web app in development mode
pnpm --filter web dev

# Build a specific package
pnpm --filter @workflow-editor/core build

# Type check all packages
pnpm typecheck
```

## Extensibility

The editor supports a plugin system for adding custom nodes:

```typescript
import type { WorkflowEditorPlugin } from '@workflow-editor/core';

const myPlugin: WorkflowEditorPlugin = {
  id: 'my-custom-plugin',
  name: 'My Custom Plugin',
  nodes: [
    {
      type: 'myCustomNode',
      component: MyCustomNodeComponent,
      metadata: {
        name: 'My Custom Node',
        category: 'service-bubbles',
        icon: 'custom-icon',
        color: '#7C3AED',
      },
      codeGenerator: (node) => `/* custom code */`,
    },
  ],
};
```

## Supported Bubbles

### Service Bubbles (50+)
- AI Agent (Gemini, OpenAI, Anthropic)
- Slack, Telegram, Gmail
- Google Drive, Sheets, Calendar
- PostgreSQL, Airtable, Notion
- HTTP, Resend, GitHub
- And many more...

### Tool Bubbles
- RedditScrapeTool
- TwitterTool, TikTokTool, InstagramTool
- WebSearchTool, WebScrapeTool, WebCrawlTool
- LinkedInTool, YouTubeTool
- GoogleMapsTool
- ResearchAgentTool

### Workflow Bubbles
- DatabaseAnalyzerWorkflow
- SlackNotifierWorkflow
- SlackFormatterAgentBubble

## License

MIT
