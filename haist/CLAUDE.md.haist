# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Is Blockd4?

An AI-powered workflow automation platform. Users build automations either by **chatting with an AI assistant** (primary UX) or by **dragging nodes on a visual canvas**. Think n8n meets ChatGPT — describe what you want, the AI builds the workflow, and it runs.

The core abstraction is a **"Bubble"** — a composable unit of work (an API call, an AI agent, a scraper, a database query, etc). Workflows are graphs of bubbles wired together. The visual graph gets compiled to executable TypeScript (`BubbleFlow` classes).

## Repo Structure

```
blockd4/
├── workflow-editor/          # Turborepo monorepo — the main product
│   ├── apps/web/             # Next.js 15 web app (App Router)
│   └── packages/
│       ├── core/             # Types, bubble registry, constants (no deps)
│       ├── state/            # Zustand stores (depends on core)
│       ├── canvas/           # ReactFlow wrapper (core, state)
│       ├── nodes/            # Node UI components (core, state)
│       ├── codegen/          # Visual graph → TypeScript code gen (core)
│       └── ui/               # Shared UI components (core, codegen, state)
└── blockd/                   # Standalone CLI runtime — executes generated workflow code
```

## Key Concepts

- **Bubble** — A unit of work. Three flavors: Service (Slack, Gmail, HTTP, PostgreSQL...), Tool (Reddit scraper, web search, Twitter...), Workflow (composed sub-workflows). Defined in `packages/core/src/constants/bubble-registry.ts`.
- **Node** — Visual representation of a bubble (or control flow, code block, trigger, etc) on the canvas. Types in `packages/core/src/types/node.types.ts`.
- **Edge** — Connection between nodes. Data flow (output → input) or control flow (then/else/catch). Types in `packages/core/src/types/edge.types.ts`.
- **Trigger** — Workflow entry point: `webhook/http`, `schedule/cron`, or `slack/bot_mentioned`.
- **Composio** — SDK integration giving access to 40+ third-party services (Gmail, Slack, Notion, GitHub, etc) via OAuth. Separate from the built-in bubble registry.
- **OpenClaw** — Local machine gateway integration. Gives the AI access to the user's filesystem, shell, and browser via a locally running OpenClaw agent. Not Composio-based — uses its own HTTP client and auth token.
- **Artifact** — Knowledge base entry. The AI accumulates context over time. Three tiers: soul (user profile), daily (daily logs), and topic (project/research notes). A "soul artifact" (`__user_profile__`) is distilled daily from all artifacts.
- **Execution Rule** — An automation rule with triggers, conditions, and steps. Can be scheduled, manual, or event-driven. Supports trigger-based (Composio webhooks), manual (chat @mention), and scheduled (cron) activation.
- **BubbleFlow** — A generated TypeScript class that represents an executable workflow. Created by codegen from the visual graph.

## Web App Pages (apps/web)

- `/` — Redirects to `/chat`.
- `/chat` — Main AI assistant interface (default landing). Chat to build workflows, invoke tools, manage artifacts. Includes integrations panel for connecting services and OpenClaw.
- `/artifacts` — Knowledge base gallery. Create, browse, search artifacts.
- `/automations` — Execution rules builder. Create rules, view logs, stats.
- The visual canvas editor is embedded in the chat as a workflow preview.

## Web App Backend (apps/web/src/)

```
app/api/
├── ai-assistant/       # Chat, conversations, tool routing (streaming), context
├── artifacts/          # CRUD, entries, semantic search
├── automations/        # Rules CRUD, invoke, logs, manual rules
├── composio/           # OAuth, tools, triggers, execution, webhook receiver
├── openclaw/           # OpenClaw gateway config (GET/POST/DELETE)
├── cron/               # Scheduled jobs: distill-memory, execute-scheduled-rules, summarize-inactive
└── notifications/      # CRUD, read/unread, read-all

lib/
├── ai-assistant/       # Tool router service, workflow AI service, prompts, conversation storage, openclaw tools, automation tools, artifact tools, user profile tools
├── artifacts/          # ArtifactService (in-memory), artifact matcher, artifact agent
├── composio/           # ComposioService (SDK wrapper), toolkit definitions + auth config mapping
├── execution-rules/    # Rule storage (in-memory), execution log storage (in-memory), trigger processing
├── memory/             # Distillation service, scheduler
├── notifications/      # Notification storage (in-memory)
├── openclaw/           # OpenClawService — HTTP client for local gateway
└── dev-user.ts         # Hardcoded dev user (id: "dev-user-001")
```

All storage is **in-memory** using `globalThis`-backed Maps/arrays (survives Next.js HMR, resets on full server restart). No persistent DB.

## Integrations

### Composio (40+ services)
OAuth-based integrations managed by Composio SDK. Auth flow:
1. Frontend calls `POST /api/composio/auth/{appName}` → gets a Composio connect link
2. User authenticates in popup → Composio redirects to `/api/composio/callback`
3. Callback closes popup, notifies parent window → frontend refreshes connected accounts

Auth config IDs are in `.env` (e.g. `GMAIL_AUTH_CONFIG_ID=ac_...`). Mapping is in `lib/composio/composio-toolkits.ts`.

Available services: Gmail, Google Calendar, Google Drive, Google Docs, Google Sheets, Google Tasks, Google Meet, Google Maps, YouTube, Outlook, OneDrive, Microsoft Teams, Slack, Discord, Notion, Linear, Jira, Asana, Calendly, GitHub, Figma, X/Twitter, LinkedIn, Reddit, Canva, Salesforce, Canvas, Apollo, Exa, Firecrawl, Browserbase.

### OpenClaw (local machine)
Gives the AI access to the user's local filesystem, shell commands, and browser via a locally running OpenClaw gateway.

- **Service**: `lib/openclaw/openclaw-service.ts` — HTTP client (singleton). Stores per-user config (URL + token) in memory.
- **API route**: `app/api/openclaw/config/route.ts` — GET (check status), POST (save config + test connection), DELETE (disconnect).
- **AI tools**: `lib/ai-assistant/openclaw-tools.ts` — Two tools registered with OpenAI Agents SDK:
  - `openclaw_run` — Send natural language instruction to OpenClaw gateway via `/v1/chat/completions`. The gateway agent decides which internal tools to use (exec, read, write, browser, etc).
  - `openclaw_status` — Check if gateway is connected and responsive.
- **Frontend**: OpenClaw appears under "Local" category in the integrations panel. Clicking it opens a modal for gateway URL + auth token. Default URL: `http://127.0.0.1:18789`.
- **System prompt**: Tool router's system prompt dynamically includes OpenClaw instructions based on `openClawService.isConfigured(userId)`.

### Tool Router (AI agent)
The AI assistant uses OpenAI Agents SDK (`@openai/agents`) with Composio tools + custom tools:
- **Composio tools** — Dynamically fetched based on user's connected accounts
- **Automation tools** — `create_automation`, `list_automations`, `invoke_automation`
- **Artifact tools** — `save_to_artifacts`, `search_artifacts`, `add_to_artifact`
- **User profile tools** — `update_user_profile`, `get_user_profile`
- **OpenClaw tools** — `openclaw_run`, `openclaw_status`

Model: GPT-5.2. Max turns: 15. Sessions cached per-user for 1 hour.

## State Management (packages/state)

Five Zustand stores:
- **workflow-store** — Nodes, edges, metadata, trigger config
- **canvas-store** — Viewport, grid, minimap, interaction mode
- **selection-store** — Selected nodes/edges, hover state
- **history-store** — Undo/redo stack
- **ui-store** — Panels, dialogs, theme, notifications, execution state

## Code Generation (packages/codegen)

`bubbleflow-generator.ts`: Visual graph → topological sort → TypeScript BubbleFlow class. Handles parameter wiring (literals, variable refs, env vars, expressions), control flow, and artifact context injection.

## AI System

- **Tool Router mode** (primary): OpenAI Agents SDK with GPT-5.2, streaming via SSE. Composio + custom tools. Full conversation context + artifact injection + user profile context.
- **Chat mode** (legacy): Direct Claude/GPT API calls via `WorkflowAIService` for workflow generation from natural language.
- Smart artifact injection (semantic matching, 0.85 threshold, top 2-3 artifacts)
- 3-tier memory: soul artifact (`__user_profile__`), daily logs (`Daily — YYYY-MM-DD`), topic artifacts
- Memory distillation — scheduled synthesis of daily logs into soul artifact

## Auth Status

No auth. All routes use a hardcoded dev user from `lib/dev-user.ts` (`id: "dev-user-001"`). The Composio entity ID is the raw user ID.

## Development Commands

```bash
# workflow-editor (monorepo)
cd workflow-editor
pnpm install
pnpm --filter web dev                       # Run web app (dev)
pnpm dev                                    # All packages (Turbo)
pnpm --filter @workflow-editor/core build   # Specific package
pnpm typecheck / pnpm lint / pnpm format / pnpm clean

# blockd (CLI runtime)
cd blockd
npm install && npm run dev      # Dev with hot reload
npm run build && npm start      # Production
```

Do NOT run production builds (`pnpm build`) during development — it conflicts with the dev server's `.next` cache.

## Key Tech

- Next.js 15 (App Router, RSC), React 18, TypeScript 5.8
- ReactFlow (@xyflow/react) for canvas
- Zustand 5 for state
- OpenAI Agents SDK (`@openai/agents`) + Composio OpenAI Agents provider
- OpenAI SDK, Anthropic SDK, Composio SDK (`@composio/core`)
- Tailwind CSS + shadcn/ui
- pnpm + Turborepo
- All storage in-memory (globalThis-backed Maps/arrays, no DB)

## Environment Variables (apps/web/.env)

```
# AI Keys
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=

# Composio
COMPOSIO_API_KEY=
EXA_API_KEY=
FIRECRAWL_API_KEY=

# Composio Auth Config IDs (one per integration)
GMAIL_AUTH_CONFIG_ID=
GOOGLE_CALENDAR_AUTH_CONFIG_ID=
SLACK_AUTH_CONFIG_ID=
GITHUB_AUTH_CONFIG_ID=
NOTION_AUTH_CONFIG_ID=
# ... (30+ services, see .env for full list)

# Other
CITY=                          # Used for weather/location context
```

## Important Notes

- This project is actively evolving — structure and features change frequently.
- The `blockd/` CLI is the runtime; `workflow-editor/` is the product.
- In-memory storage means everything resets on full restart — fine for dev, needs persistence for prod. HMR does NOT reset storage (globalThis pattern).
- Bubble registry is the source of truth for what services/tools are available on the canvas.
- Composio is the source of truth for what third-party tools the AI can use in chat.
- OpenClaw is optional — the AI works without it, but gains local machine access when connected.
- Codegen is a key differentiator — visual workflows compile to real TypeScript.
