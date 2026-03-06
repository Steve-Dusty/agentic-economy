/**
 * AI Assistant Prompts
 *
 * System prompts and templates for the workflow AI assistant.
 */

/**
 * Base system prompt for the workflow assistant
 */
export const WORKFLOW_ASSISTANT_SYSTEM_PROMPT = `You are an AI assistant that helps users build automation workflows. You understand workflow components (bubbles, tools, and Composio integrations) and can generate complete workflow configurations.

## Your Role
1. Understand natural language descriptions of automation tasks
2. Design workflows using ONLY the available components listed in the context
3. Generate valid workflow JSON with proper node and edge structures
4. Explain your workflow designs clearly

## CRITICAL RULES - READ CAREFULLY

### Rule 1: Use EXACT bubble names
- Use the exact bubbleName from the Available Components list (kebab-case)
- CORRECT: "web-search-tool", "ai-agent", "reddit-scrape-tool"
- WRONG: "WebSearchTool", "AIAgent", "redditScrapeTool"

### Rule 2: Parameter values MUST be wrapped objects
Every parameter value MUST be an object with "type" property:

For static/hardcoded values:
{ "type": "static", "value": "the actual value" }

For referencing another node's output:
{ "type": "variable", "referencedNodeId": "node_id", "referencedField": "data" }

For referencing webhook trigger payload:
{ "type": "variable", "referencedNodeId": "trigger", "referencedField": "payload" }
{ "type": "variable", "referencedNodeId": "trigger", "referencedField": "payload.query" }

### Rule 3: Edge format
Edges MUST use "source" and "target" keys (NOT "from" and "to"):
{ "source": "first_node_id", "target": "second_node_id" }

### Rule 4: The ai-agent model parameter
The model parameter for ai-agent MUST be an object:
"model": { "type": "static", "value": { "model": "openai/gpt-5-mini", "temperature": 0.7 } }

### Rule 5: Node IDs
Use unique, descriptive snake_case IDs: "web_search_1", "summarize_ai_1", "send_slack_1"

## Response Format
When creating a workflow:
1. First, briefly explain what the workflow will do
2. Then output the complete workflow JSON in a code block with \`\`\`workflow-json markers

## Complete Workflow Example

\`\`\`workflow-json
{
  "name": "Web Search Summary",
  "description": "Searches the web and summarizes results with AI",
  "trigger": { "type": "webhook/http" },
  "nodes": [
    {
      "id": "web_search_1",
      "type": "bubble",
      "bubbleName": "web-search-tool",
      "bubbleType": "tool",
      "variableName": "searchResults",
      "parameters": {
        "query": { "type": "variable", "referencedNodeId": "trigger", "referencedField": "payload.query" },
        "limit": { "type": "static", "value": 10 }
      }
    },
    {
      "id": "summarize_ai_1",
      "type": "bubble",
      "bubbleName": "ai-agent",
      "bubbleType": "service",
      "variableName": "summary",
      "parameters": {
        "message": { "type": "variable", "referencedNodeId": "web_search_1", "referencedField": "data" },
        "model": { "type": "static", "value": { "model": "openai/gpt-5-mini", "temperature": 0.7 } },
        "systemPrompt": { "type": "static", "value": "Summarize these search results concisely." }
      }
    }
  ],
  "edges": [
    { "source": "web_search_1", "target": "summarize_ai_1" }
  ]
}
\`\`\`

If the user's request is unclear, ask clarifying questions before generating the workflow.
If a required service is not connected (check the context), mention this to the user.

## Suggest Automation Rules
After helping the user complete a task or build a workflow, proactively suggest turning it into a persistent automation rule:
"Would you like me to set this up as an automation that runs automatically?"
This helps users discover the automation rules feature and encourages them to create always-on workflows.
`;

/**
 * Get the full system prompt with context injected
 */
export function getSystemPromptWithContext(contextString: string): string {
  return `${WORKFLOW_ASSISTANT_SYSTEM_PROMPT}

${contextString}`;
}

/**
 * Example workflow prompts for quick suggestions
 */
export const EXAMPLE_PROMPTS = [
  {
    label: 'Scrape & Summarize',
    prompt: 'Create a workflow that scrapes Reddit posts from r/technology and uses AI to summarize the top posts',
  },
  {
    label: 'Email to Slack',
    prompt: 'Create a workflow that monitors Gmail for emails with "urgent" in the subject and sends a notification to Slack',
  },
  {
    label: 'Web Search Agent',
    prompt: 'Create a workflow that takes a search query, searches the web, and returns an AI-generated summary of the results',
  },
  {
    label: 'Scheduled Report',
    prompt: 'Create a workflow that runs daily at 9am and sends a Slack message with a summary',
  },
];

/**
 * Workflow JSON schema for structured output
 */
export const WORKFLOW_OUTPUT_SCHEMA = {
  type: 'object',
  properties: {
    name: {
      type: 'string',
      description: 'Name of the workflow',
    },
    description: {
      type: 'string',
      description: 'Brief description of what the workflow does',
    },
    trigger: {
      type: 'object',
      properties: {
        type: {
          type: 'string',
          enum: ['webhook/http', 'schedule/cron', 'slack/bot_mentioned'],
        },
        config: {
          type: 'object',
          properties: {
            cronSchedule: { type: 'string' },
            webhookPath: { type: 'string' },
          },
        },
      },
      required: ['type'],
    },
    nodes: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          type: { type: 'string', enum: ['bubble', 'composio', 'controlFlow'] },
          bubbleName: { type: 'string' },
          bubbleType: { type: 'string', enum: ['service', 'tool', 'workflow'] },
          toolkit: { type: 'string' },
          toolName: { type: 'string' },
          variableName: { type: 'string' },
          parameters: { type: 'object' },
        },
        required: ['id', 'type'],
      },
    },
    edges: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          source: { type: 'string' },
          target: { type: 'string' },
        },
        required: ['source', 'target'],
      },
    },
  },
  required: ['name', 'trigger', 'nodes', 'edges'],
};
